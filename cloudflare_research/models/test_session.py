"""TestSession model for managing collections of test requests.

Represents a test session with shared configuration and aggregated metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4


class SessionStatus(Enum):
    """Status enumeration for test sessions."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class SessionStats:
    """Statistics for a test session."""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    challenges_encountered: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.completed_requests / self.total_requests) * 100

    @property
    def pending_requests(self) -> int:
        """Calculate number of pending requests."""
        return self.total_requests - self.completed_requests - self.failed_requests


@dataclass
class SessionConfig:
    """Configuration settings for a test session."""
    name: str
    description: Optional[str] = None
    browser_version: str = "124.0.0.0"
    concurrency_limit: int = 100
    rate_limit: float = 10.0  # requests per second
    default_timeout: int = 30  # seconds

    def __post_init__(self):
        """Validate session configuration."""
        self._validate_concurrency_limit()
        self._validate_rate_limit()
        self._validate_timeout()
        self._validate_browser_version()

    def _validate_concurrency_limit(self) -> None:
        """Validate concurrency limit."""
        if not isinstance(self.concurrency_limit, int):
            raise TypeError("Concurrency limit must be an integer")

        if not (1 <= self.concurrency_limit <= 10000):
            raise ValueError("Concurrency limit must be between 1 and 10,000")

    def _validate_rate_limit(self) -> None:
        """Validate rate limit."""
        if not isinstance(self.rate_limit, (int, float)):
            raise TypeError("Rate limit must be a number")

        if self.rate_limit <= 0:
            raise ValueError("Rate limit must be positive")

    def _validate_timeout(self) -> None:
        """Validate default timeout."""
        if not isinstance(self.default_timeout, int):
            raise TypeError("Timeout must be an integer")

        if not (1 <= self.default_timeout <= 300):
            raise ValueError("Timeout must be between 1 and 300 seconds")

    def _validate_browser_version(self) -> None:
        """Validate browser version format."""
        if not isinstance(self.browser_version, str):
            raise TypeError("Browser version must be a string")

        # Basic validation for Chrome version format (e.g., "124.0.0.0")
        parts = self.browser_version.split(".")
        if len(parts) != 4:
            raise ValueError("Browser version must be in format 'x.y.z.w'")

        try:
            [int(part) for part in parts]
        except ValueError:
            raise ValueError("Browser version parts must be integers")


@dataclass
class TestSession:
    """
    Represents a collection of related test requests.

    A test session groups multiple requests with shared configuration and provides
    aggregated metrics and status tracking for the entire batch.
    """

    # Core identifiers
    session_id: UUID = field(default_factory=uuid4)

    # Configuration
    config: SessionConfig = field(default_factory=lambda: SessionConfig(name="Default Session"))

    # Status and timing
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Statistics
    stats: SessionStats = field(default_factory=SessionStats)

    # Error handling
    error_message: Optional[str] = None

    @property
    def name(self) -> str:
        """Get session name from config."""
        return self.config.name

    @property
    def description(self) -> Optional[str]:
        """Get session description from config."""
        return self.config.description

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status in {SessionStatus.CREATED, SessionStatus.RUNNING}

    @property
    def is_completed(self) -> bool:
        """Check if session is in a completed state."""
        return self.status in {
            SessionStatus.COMPLETED,
            SessionStatus.CANCELLED,
            SessionStatus.FAILED
        }

    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate total session duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        elif self.started_at:
            # Session is still running
            delta = datetime.now() - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    def start_session(self) -> None:
        """Mark session as started."""
        if self.status != SessionStatus.CREATED:
            raise ValueError(f"Cannot start session in {self.status.value} state")

        self.status = SessionStatus.RUNNING
        self.started_at = datetime.now()

    def complete_session(self) -> None:
        """Mark session as completed."""
        if self.status != SessionStatus.RUNNING:
            raise ValueError(f"Cannot complete session in {self.status.value} state")

        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now()

    def cancel_session(self, reason: Optional[str] = None) -> None:
        """Cancel the session."""
        if self.is_completed:
            raise ValueError(f"Cannot cancel session in {self.status.value} state")

        self.status = SessionStatus.CANCELLED
        self.completed_at = datetime.now()
        if reason:
            self.error_message = f"Session cancelled: {reason}"

    def fail_session(self, error_message: str) -> None:
        """Mark session as failed."""
        if self.is_completed:
            raise ValueError(f"Cannot fail session in {self.status.value} state")

        self.status = SessionStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message

    def add_request(self) -> None:
        """Increment total request count."""
        self.stats.total_requests += 1

    def complete_request(self, success: bool = True) -> None:
        """Record completion of a request."""
        if success:
            self.stats.completed_requests += 1
        else:
            self.stats.failed_requests += 1

    def add_challenge(self) -> None:
        """Record a challenge encounter."""
        self.stats.challenges_encountered += 1

    def get_progress_percentage(self) -> float:
        """Calculate session progress percentage."""
        if self.stats.total_requests == 0:
            return 0.0

        completed_total = self.stats.completed_requests + self.stats.failed_requests
        return (completed_total / self.stats.total_requests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": str(self.session_id),
            "name": self.config.name,
            "description": self.config.description,
            "config": {
                "browser_version": self.config.browser_version,
                "concurrency_limit": self.config.concurrency_limit,
                "rate_limit": self.config.rate_limit,
                "default_timeout": self.config.default_timeout,
            },
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stats": {
                "total_requests": self.stats.total_requests,
                "completed_requests": self.stats.completed_requests,
                "failed_requests": self.stats.failed_requests,
                "challenges_encountered": self.stats.challenges_encountered,
                "success_rate": self.stats.success_rate,
                "pending_requests": self.stats.pending_requests,
            },
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "progress_percentage": self.get_progress_percentage(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestSession":
        """Create TestSession from dictionary."""
        # Parse configuration
        config_data = data.get("config", {})
        config = SessionConfig(
            name=data["name"],
            description=data.get("description"),
            browser_version=config_data.get("browser_version", "124.0.0.0"),
            concurrency_limit=config_data.get("concurrency_limit", 100),
            rate_limit=config_data.get("rate_limit", 10.0),
            default_timeout=config_data.get("default_timeout", 30),
        )

        # Parse statistics
        stats_data = data.get("stats", {})
        stats = SessionStats(
            total_requests=stats_data.get("total_requests", 0),
            completed_requests=stats_data.get("completed_requests", 0),
            failed_requests=stats_data.get("failed_requests", 0),
            challenges_encountered=stats_data.get("challenges_encountered", 0),
        )

        # Parse timestamps
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None

        return cls(
            session_id=UUID(data["session_id"]) if data.get("session_id") else uuid4(),
            config=config,
            status=SessionStatus(data.get("status", "created")),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            stats=stats,
            error_message=data.get("error_message"),
        )

    def validate_request_capacity(self) -> bool:
        """Check if session can accept more requests."""
        return (
            self.is_active and
            self.stats.pending_requests < self.config.concurrency_limit
        )

    def get_estimated_completion_time(self) -> Optional[datetime]:
        """Estimate session completion time based on current progress."""
        if not self.started_at or self.stats.total_requests == 0:
            return None

        if self.stats.completed_requests + self.stats.failed_requests == 0:
            return None

        elapsed_time = datetime.now() - self.started_at
        completed_count = self.stats.completed_requests + self.stats.failed_requests

        if completed_count == 0:
            return None

        time_per_request = elapsed_time / completed_count
        remaining_requests = self.stats.pending_requests

        estimated_remaining_time = time_per_request * remaining_requests
        return datetime.now() + estimated_remaining_time

    def __str__(self) -> str:
        """String representation of the session."""
        return (
            f"TestSession(id={str(self.session_id)[:8]}..., "
            f"name='{self.config.name}', status={self.status.value}, "
            f"requests={self.stats.completed_requests + self.stats.failed_requests}/"
            f"{self.stats.total_requests})"
        )