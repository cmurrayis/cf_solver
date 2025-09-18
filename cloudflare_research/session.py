"""Session management integration for CloudflareBypass operations.

Provides comprehensive session management with persistence, concurrency control,
and integration with all CloudflareBypass components for coordinated operations.
"""

import asyncio
import json
import time
import weakref
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

# Core models
from .models.test_session import TestSession, SessionConfig, SessionStatus, SessionStats
from .models.test_request import TestRequest, HttpMethod, RequestTiming
from .models.challenge_record import ChallengeRecord
from .models.performance_metrics import PerformanceMetrics

# Components
from .browser import BrowserSession, create_browser_session
from .http import BrowserHTTPClient, create_browser_client
from .challenge import ChallengeManager, ChallengeResult, ChallengeConfig
from .concurrency import HighPerformanceManager, TaskPriority
from .utils import generate_session_id, Timer, AsyncCache


@dataclass
class SessionPersistenceConfig:
    """Configuration for session persistence."""
    enabled: bool = True
    storage_path: str = "./sessions"
    auto_save_interval: float = 30.0  # seconds
    max_session_files: int = 1000
    compress_old_sessions: bool = True
    retention_days: int = 30


@dataclass
class SessionManagerConfig:
    """Configuration for session manager."""
    max_concurrent_sessions: int = 10
    session_timeout: float = 3600.0  # 1 hour
    auto_cleanup_interval: float = 300.0  # 5 minutes
    enable_persistence: bool = True
    enable_metrics: bool = True
    challenge_config: Optional[ChallengeConfig] = None


class SessionManager:
    """Manages multiple CloudflareBypass sessions with coordination and persistence."""

    def __init__(self, config: SessionManagerConfig = None, persistence_config: SessionPersistenceConfig = None):
        self.config = config or SessionManagerConfig()
        self.persistence_config = persistence_config or SessionPersistenceConfig()

        # Session storage
        self._active_sessions: Dict[str, 'ManagedSession'] = {}
        self._session_cache = AsyncCache[TestSession](ttl=3600.0)

        # Concurrency and coordination
        self._manager_lock = asyncio.Lock()
        self._session_semaphore = asyncio.Semaphore(self.config.max_concurrent_sessions)

        # Background tasks
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._auto_save_task: Optional[asyncio.Task] = None

        # Event callbacks
        self._session_created_callbacks: List[Callable] = []
        self._session_completed_callbacks: List[Callable] = []
        self._session_failed_callbacks: List[Callable] = []

        # Setup persistence
        if self.persistence_config.enabled:
            self._setup_persistence()

    def _setup_persistence(self) -> None:
        """Setup persistence storage."""
        storage_path = Path(self.persistence_config.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """Start the session manager."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        if self.persistence_config.enabled and self.persistence_config.auto_save_interval > 0:
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())

        logging.info("Session manager started")

    async def stop(self) -> None:
        """Stop the session manager and clean up resources."""
        self._running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._auto_save_task:
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass

        # Stop all active sessions
        session_list = list(self._active_sessions.values())
        for session in session_list:
            await session.stop()

        # Final save
        if self.persistence_config.enabled:
            await self._save_all_sessions()

        logging.info("Session manager stopped")

    async def create_session(self, config: SessionConfig) -> 'ManagedSession':
        """Create a new managed session."""
        if not self._running:
            await self.start()

        async with self._manager_lock:
            # Check limits
            if len(self._active_sessions) >= self.config.max_concurrent_sessions:
                raise RuntimeError(f"Maximum concurrent sessions ({self.config.max_concurrent_sessions}) reached")

            # Create test session
            test_session = TestSession(config=config)

            # Create managed session
            managed_session = ManagedSession(
                test_session=test_session,
                manager=self,
                challenge_config=self.config.challenge_config
            )

            # Store in active sessions
            session_id = str(test_session.session_id)
            self._active_sessions[session_id] = managed_session

            # Cache the session
            await self._session_cache.set(session_id, test_session)

            # Trigger callbacks
            for callback in self._session_created_callbacks:
                try:
                    await callback(managed_session)
                except Exception as e:
                    logging.error(f"Session created callback error: {e}")

            logging.info(f"Created session {session_id} ({test_session.name})")
            return managed_session

    async def get_session(self, session_id: str) -> Optional['ManagedSession']:
        """Get an active session by ID."""
        return self._active_sessions.get(session_id)

    async def list_active_sessions(self) -> List['ManagedSession']:
        """Get list of all active sessions."""
        return list(self._active_sessions.values())

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        async with self._manager_lock:
            active_sessions = list(self._active_sessions.values())

            stats = {
                "active_sessions": len(active_sessions),
                "max_concurrent": self.config.max_concurrent_sessions,
                "total_requests": 0,
                "completed_requests": 0,
                "failed_requests": 0,
                "challenges_encountered": 0,
                "sessions_by_status": {},
            }

            # Aggregate statistics
            for session in active_sessions:
                test_session = session.test_session
                stats["total_requests"] += test_session.stats.total_requests
                stats["completed_requests"] += test_session.stats.completed_requests
                stats["failed_requests"] += test_session.stats.failed_requests
                stats["challenges_encountered"] += test_session.stats.challenges_encountered

                # Count by status
                status = test_session.status.value
                stats["sessions_by_status"][status] = stats["sessions_by_status"].get(status, 0) + 1

            # Calculate rates
            if stats["total_requests"] > 0:
                stats["success_rate"] = (stats["completed_requests"] / stats["total_requests"]) * 100
            else:
                stats["success_rate"] = 0.0

            return stats

    async def _remove_session(self, session_id: str) -> None:
        """Remove session from active sessions (called by ManagedSession)."""
        async with self._manager_lock:
            if session_id in self._active_sessions:
                session = self._active_sessions.pop(session_id)

                # Save session if persistence enabled
                if self.persistence_config.enabled:
                    await self._save_session(session.test_session)

                logging.info(f"Removed session {session_id}")

    async def _cleanup_loop(self) -> None:
        """Background cleanup task."""
        while self._running:
            try:
                await asyncio.sleep(self.config.auto_cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Session cleanup error: {e}")

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        now = datetime.now()
        expired_sessions = []

        async with self._manager_lock:
            for session_id, session in self._active_sessions.items():
                test_session = session.test_session

                # Check for timeout
                if test_session.started_at:
                    session_age = now - test_session.started_at
                    if session_age.total_seconds() > self.config.session_timeout:
                        expired_sessions.append(session_id)

        # Stop expired sessions
        for session_id in expired_sessions:
            session = self._active_sessions.get(session_id)
            if session:
                await session.timeout()

    async def _auto_save_loop(self) -> None:
        """Background auto-save task."""
        while self._running:
            try:
                await asyncio.sleep(self.persistence_config.auto_save_interval)
                await self._save_all_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Auto-save error: {e}")

    async def _save_all_sessions(self) -> None:
        """Save all active sessions."""
        if not self.persistence_config.enabled:
            return

        sessions_to_save = list(self._active_sessions.values())
        for session in sessions_to_save:
            await self._save_session(session.test_session)

    async def _save_session(self, test_session: TestSession) -> None:
        """Save a single session to disk."""
        try:
            storage_path = Path(self.persistence_config.storage_path)
            file_path = storage_path / f"session_{test_session.session_id}.json"

            session_data = test_session.to_dict()
            session_data["saved_at"] = datetime.now().isoformat()

            with open(file_path, 'w') as f:
                json.dump(session_data, f, indent=2)

        except Exception as e:
            logging.error(f"Failed to save session {test_session.session_id}: {e}")

    async def load_session(self, session_id: str) -> Optional[TestSession]:
        """Load a session from disk."""
        if not self.persistence_config.enabled:
            return None

        try:
            storage_path = Path(self.persistence_config.storage_path)
            file_path = storage_path / f"session_{session_id}.json"

            if not file_path.exists():
                return None

            with open(file_path, 'r') as f:
                session_data = json.load(f)

            return TestSession.from_dict(session_data)

        except Exception as e:
            logging.error(f"Failed to load session {session_id}: {e}")
            return None

    # Event handler registration
    def add_session_created_callback(self, callback: Callable) -> None:
        """Add callback for session creation events."""
        self._session_created_callbacks.append(callback)

    def add_session_completed_callback(self, callback: Callable) -> None:
        """Add callback for session completion events."""
        self._session_completed_callbacks.append(callback)

    def add_session_failed_callback(self, callback: Callable) -> None:
        """Add callback for session failure events."""
        self._session_failed_callbacks.append(callback)


class ManagedSession:
    """A managed session that integrates with CloudflareBypass components."""

    def __init__(self, test_session: TestSession, manager: SessionManager,
                 challenge_config: Optional[ChallengeConfig] = None):
        self.test_session = test_session
        self.manager = manager
        self._challenge_config = challenge_config

        # Component instances
        self.browser_session: Optional[BrowserSession] = None
        self.http_client: Optional[BrowserHTTPClient] = None
        self.challenge_manager: Optional[ChallengeManager] = None
        self.concurrency_manager: Optional[HighPerformanceManager] = None

        # Session state
        self._started = False
        self._stopping = False
        self._active_requests: Set[str] = set()
        self._request_lock = asyncio.Lock()

        # Performance tracking
        self._performance_timer = Timer()
        self._request_timings: List[float] = []

    @property
    def session_id(self) -> str:
        """Get session ID."""
        return str(self.test_session.session_id)

    @property
    def name(self) -> str:
        """Get session name."""
        return self.test_session.name

    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self._started and not self._stopping and self.test_session.is_active

    async def start(self) -> None:
        """Start the managed session and initialize components."""
        if self._started:
            return

        # Start the test session
        self.test_session.start_session()

        # Initialize browser session
        self.browser_session = await create_browser_session(
            version=self.test_session.config.browser_version
        )

        # Initialize HTTP client
        self.http_client = await create_browser_client(
            browser_session=self.browser_session
        )

        # Initialize challenge manager
        challenge_config = self._challenge_config or ChallengeConfig()
        self.challenge_manager = ChallengeManager(challenge_config)

        # Initialize concurrency manager
        self.concurrency_manager = HighPerformanceManager(
            max_concurrent=self.test_session.config.concurrency_limit,
            max_rate=self.test_session.config.rate_limit
        )
        await self.concurrency_manager.start()

        self._started = True
        self._performance_timer.start()

        logging.info(f"Started managed session {self.session_id}")

    async def stop(self) -> None:
        """Stop the managed session and clean up resources."""
        if self._stopping:
            return

        self._stopping = True

        # Wait for active requests to complete
        await self._wait_for_active_requests()

        # Stop concurrency manager
        if self.concurrency_manager:
            await self.concurrency_manager.stop()

        # Close HTTP client
        if self.http_client:
            await self.http_client.close()

        # Complete the test session
        if self.test_session.is_active:
            self.test_session.complete_session()

        # Remove from manager
        await self.manager._remove_session(self.session_id)

        logging.info(f"Stopped managed session {self.session_id}")

    async def timeout(self) -> None:
        """Handle session timeout."""
        self.test_session.fail_session("Session timed out")
        await self.stop()

    async def execute_request(self, request: TestRequest) -> Any:
        """Execute a request within this session."""
        if not self.is_active:
            raise RuntimeError("Session is not active")

        if not self._started:
            await self.start()

        request_id = str(request.request_id)

        async with self._request_lock:
            self._active_requests.add(request_id)
            self.test_session.add_request()

        try:
            # Execute request through concurrency manager
            coro = self._execute_single_request(request)
            success = await self.concurrency_manager.submit_request(
                coro,
                domain=request.url_domain or "global",
                priority=TaskPriority.NORMAL
            )

            if not success:
                raise RuntimeError("Failed to submit request due to rate limiting or backpressure")

            return success

        finally:
            async with self._request_lock:
                self._active_requests.discard(request_id)

    async def _execute_single_request(self, request: TestRequest) -> Any:
        """Execute a single request with challenge handling."""
        try:
            # Record start time
            request_timer = Timer()
            request_timer.start()

            # Make HTTP request
            if request.method == HttpMethod.GET:
                response = await self.http_client.get(
                    request.url,
                    headers=request.headers,
                    timeout=request.timeout or self.test_session.config.default_timeout
                )
            elif request.method == HttpMethod.POST:
                response = await self.http_client.post(
                    request.url,
                    data=request.body,
                    headers=request.headers,
                    timeout=request.timeout or self.test_session.config.default_timeout
                )
            else:
                raise ValueError(f"Unsupported method: {request.method}")

            # Check for challenges
            if self.challenge_manager.is_response_challenging(
                response.text, dict(response.headers), response.status_code
            ):
                self.test_session.add_challenge()

                # Handle challenge
                challenge_result = await self.challenge_manager.process_response(
                    response.text, dict(response.headers), response.status_code,
                    request.url, self.http_client
                )

                if challenge_result.success:
                    response = challenge_result.bypass_response

            # Record completion
            elapsed = request_timer.stop()
            self._request_timings.append(elapsed)

            self.test_session.complete_request(success=True)
            return response

        except Exception as e:
            self.test_session.complete_request(success=False)
            raise e

    async def _wait_for_active_requests(self, timeout: float = 30.0) -> None:
        """Wait for all active requests to complete."""
        start_time = time.time()

        while self._active_requests and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)

        if self._active_requests:
            logging.warning(f"Session {self.session_id} has {len(self._active_requests)} requests still active after timeout")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this session."""
        if not self._request_timings:
            return {}

        return {
            "request_count": len(self._request_timings),
            "avg_response_time": sum(self._request_timings) / len(self._request_timings),
            "min_response_time": min(self._request_timings),
            "max_response_time": max(self._request_timings),
            "total_time": self._performance_timer.elapsed,
            "requests_per_second": len(self._request_timings) / max(self._performance_timer.elapsed, 0.001),
        }

    @asynccontextmanager
    async def request_context(self):
        """Context manager for request execution."""
        if not self._started:
            await self.start()

        try:
            yield self
        finally:
            # Cleanup if needed
            pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert managed session to dictionary."""
        result = self.test_session.to_dict()
        result["performance"] = self.get_performance_stats()
        result["active_requests"] = len(self._active_requests)
        result["is_managed_active"] = self.is_active
        return result


# Utility functions
def create_session_manager(config: SessionManagerConfig = None,
                         persistence_config: SessionPersistenceConfig = None) -> SessionManager:
    """Create a new session manager."""
    return SessionManager(config, persistence_config)


def create_session_config(name: str,
                        description: str = None,
                        concurrency_limit: int = 100,
                        rate_limit: float = 10.0,
                        browser_version: str = "124.0.0.0") -> SessionConfig:
    """Create a session configuration."""
    return SessionConfig(
        name=name,
        description=description,
        concurrency_limit=concurrency_limit,
        rate_limit=rate_limit,
        browser_version=browser_version
    )


async def execute_requests_in_session(requests: List[TestRequest],
                                    session_config: SessionConfig,
                                    manager: SessionManager = None) -> ManagedSession:
    """Execute multiple requests in a managed session."""
    if manager is None:
        manager = create_session_manager()
        await manager.start()

    session = await manager.create_session(session_config)

    try:
        await session.start()

        # Execute all requests
        results = []
        for request in requests:
            try:
                result = await session.execute_request(request)
                results.append(result)
            except Exception as e:
                logging.error(f"Request failed: {e}")
                results.append(e)

        return session

    except Exception as e:
        await session.stop()
        raise e


# Export public API
__all__ = [
    "SessionManager",
    "ManagedSession",
    "SessionManagerConfig",
    "SessionPersistenceConfig",
    "create_session_manager",
    "create_session_config",
    "execute_requests_in_session",
]