"""High-performance concurrency manager for 10k+ concurrent requests.

Provides advanced concurrency control, backpressure handling, connection pooling,
and performance monitoring for large-scale Cloudflare bypass operations.
"""

import asyncio
import time
import weakref
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ConcurrencyMetrics:
    """Concurrency performance metrics."""
    active_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0

    # Performance metrics
    avg_task_duration: float = 0.0
    tasks_per_second: float = 0.0
    peak_concurrency: int = 0
    backpressure_events: int = 0

    # Resource utilization
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    connection_pool_size: int = 0
    active_connections: int = 0

    # Timing
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "active_tasks": self.active_tasks,
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "cancelled_tasks": self.cancelled_tasks,
            "total_tasks": self.completed_tasks + self.failed_tasks + self.cancelled_tasks,
            "avg_task_duration": self.avg_task_duration,
            "tasks_per_second": self.tasks_per_second,
            "peak_concurrency": self.peak_concurrency,
            "backpressure_events": self.backpressure_events,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "connection_pool_size": self.connection_pool_size,
            "active_connections": self.active_connections,
            "uptime_seconds": time.time() - self.start_time,
            "last_update": self.last_update,
        }


@dataclass
class TaskInfo:
    """Information about a managed task."""
    task_id: str
    priority: TaskPriority
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[Exception] = None
    result: Any = None

    @property
    def duration(self) -> Optional[float]:
        """Get task execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def wait_time(self) -> Optional[float]:
        """Get time waited before execution."""
        if self.started_at:
            return self.started_at - self.created_at
        return None


class ConcurrencyConfig:
    """Configuration for concurrency manager."""

    def __init__(self,
                 max_concurrent_tasks: int = 1000,
                 max_pending_tasks: int = 10000,
                 default_timeout: float = 30.0,
                 backpressure_threshold: float = 0.8,
                 cleanup_interval: float = 60.0,
                 enable_metrics: bool = True,
                 enable_task_tracking: bool = True,
                 max_task_history: int = 10000,
                 priority_scheduling: bool = True):

        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_pending_tasks = max_pending_tasks
        self.default_timeout = default_timeout
        self.backpressure_threshold = backpressure_threshold
        self.cleanup_interval = cleanup_interval
        self.enable_metrics = enable_metrics
        self.enable_task_tracking = enable_task_tracking
        self.max_task_history = max_task_history
        self.priority_scheduling = priority_scheduling


class ConcurrencyManager:
    """Advanced concurrency manager for high-performance operations."""

    def __init__(self, config: ConcurrencyConfig = None):
        self.config = config or ConcurrencyConfig()

        # Task management
        self._active_tasks: Set[asyncio.Task] = set()
        self._pending_queues: Dict[TaskPriority, deque] = {
            priority: deque() for priority in TaskPriority
        }
        self._task_semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        # Task tracking
        self._task_counter = 0
        self._task_info: Dict[str, TaskInfo] = {}
        self._task_history: deque = deque(maxlen=self.config.max_task_history)

        # Metrics and monitoring
        self.metrics = ConcurrencyMetrics()
        self._metrics_lock = asyncio.Lock()

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._running = False

        # Event handlers
        self._task_started_callbacks: List[Callable] = []
        self._task_completed_callbacks: List[Callable] = []
        self._backpressure_callbacks: List[Callable] = []

    async def start(self) -> None:
        """Start the concurrency manager."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        if self.config.cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        if self.config.enable_metrics:
            self._metrics_task = asyncio.create_task(self._metrics_loop())

    async def stop(self) -> None:
        """Stop the concurrency manager and wait for tasks to complete."""
        self._running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass

        # Wait for active tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # Clear pending tasks
        for queue in self._pending_queues.values():
            while queue:
                coro, future, task_info = queue.popleft()
                if not future.cancelled():
                    future.cancel()

    async def submit_task(self,
                         coro: Awaitable[Any],
                         priority: TaskPriority = TaskPriority.NORMAL,
                         timeout: Optional[float] = None,
                         task_id: Optional[str] = None) -> asyncio.Future:
        """Submit a task for concurrent execution."""

        if not self._running:
            await self.start()

        # Check backpressure
        total_pending = sum(len(queue) for queue in self._pending_queues.values())
        if total_pending >= self.config.max_pending_tasks:
            await self._trigger_backpressure()
            raise RuntimeError(f"Too many pending tasks: {total_pending}")

        # Generate task ID
        if task_id is None:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"

        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=time.time()
        )

        # Create future for result
        future = asyncio.Future()

        # Add to appropriate queue
        self._pending_queues[priority].append((coro, future, task_info))

        if self.config.enable_task_tracking:
            self._task_info[task_id] = task_info

        # Update metrics
        await self._update_metrics()

        # Try to schedule immediately if resources available
        asyncio.create_task(self._schedule_tasks())

        return future

    async def submit_batch(self,
                          coros: List[Awaitable[Any]],
                          priority: TaskPriority = TaskPriority.NORMAL,
                          timeout: Optional[float] = None) -> List[asyncio.Future]:
        """Submit a batch of tasks for concurrent execution."""

        futures = []
        for i, coro in enumerate(coros):
            task_id = f"batch_{self._task_counter}_{i}"
            future = await self.submit_task(coro, priority, timeout, task_id)
            futures.append(future)

        return futures

    async def wait_for_completion(self,
                                futures: List[asyncio.Future],
                                timeout: Optional[float] = None,
                                return_when: str = asyncio.ALL_COMPLETED) -> Tuple[Set, Set]:
        """Wait for futures to complete."""
        return await asyncio.wait(futures, timeout=timeout, return_when=return_when)

    async def _schedule_tasks(self) -> None:
        """Schedule pending tasks for execution."""

        while self._running and len(self._active_tasks) < self.config.max_concurrent_tasks:
            # Find next task to schedule
            next_task = await self._get_next_task()
            if not next_task:
                break

            coro, future, task_info = next_task

            # Acquire semaphore
            await self._task_semaphore.acquire()

            # Create and start task
            task = asyncio.create_task(self._run_task(coro, future, task_info))
            self._active_tasks.add(task)

            # Update task status
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = time.time()

            # Trigger callbacks
            for callback in self._task_started_callbacks:
                try:
                    await callback(task_info)
                except Exception:
                    pass

    async def _get_next_task(self) -> Optional[Tuple[Awaitable, asyncio.Future, TaskInfo]]:
        """Get next task to execute based on priority."""

        if not self.config.priority_scheduling:
            # Simple FIFO scheduling
            for queue in self._pending_queues.values():
                if queue:
                    return queue.popleft()
            return None

        # Priority-based scheduling
        for priority in reversed(list(TaskPriority)):
            queue = self._pending_queues[priority]
            if queue:
                return queue.popleft()

        return None

    async def _run_task(self,
                       coro: Awaitable[Any],
                       future: asyncio.Future,
                       task_info: TaskInfo) -> None:
        """Run a single task and handle its completion."""

        try:
            # Execute the coroutine with timeout
            timeout = self.config.default_timeout
            result = await asyncio.wait_for(coro, timeout=timeout)

            # Task completed successfully
            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = time.time()
            task_info.result = result

            if not future.cancelled():
                future.set_result(result)

        except asyncio.CancelledError:
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = time.time()

            if not future.cancelled():
                future.cancel()

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = time.time()
            task_info.error = e

            if not future.cancelled():
                future.set_exception(e)

        finally:
            # Clean up
            current_task = asyncio.current_task()
            if current_task in self._active_tasks:
                self._active_tasks.remove(current_task)

            self._task_semaphore.release()

            # Move to history
            if self.config.enable_task_tracking:
                self._task_history.append(task_info)

            # Trigger callbacks
            for callback in self._task_completed_callbacks:
                try:
                    await callback(task_info)
                except Exception:
                    pass

            # Update metrics
            await self._update_metrics()

            # Schedule more tasks if available
            asyncio.create_task(self._schedule_tasks())

    async def _update_metrics(self) -> None:
        """Update performance metrics."""
        if not self.config.enable_metrics:
            return

        async with self._metrics_lock:
            now = time.time()

            # Basic counts
            self.metrics.active_tasks = len(self._active_tasks)
            self.metrics.pending_tasks = sum(len(queue) for queue in self._pending_queues.values())

            # Count completed/failed tasks from history
            completed = sum(1 for task in self._task_history
                          if task.status == TaskStatus.COMPLETED)
            failed = sum(1 for task in self._task_history
                       if task.status == TaskStatus.FAILED)
            cancelled = sum(1 for task in self._task_history
                          if task.status == TaskStatus.CANCELLED)

            self.metrics.completed_tasks = completed
            self.metrics.failed_tasks = failed
            self.metrics.cancelled_tasks = cancelled

            # Performance calculations
            if self._task_history:
                durations = [task.duration for task in self._task_history
                           if task.duration is not None]
                if durations:
                    self.metrics.avg_task_duration = sum(durations) / len(durations)

                # Tasks per second calculation
                time_window = 60.0  # Last minute
                recent_tasks = [task for task in self._task_history
                              if task.completed_at and now - task.completed_at < time_window]
                if recent_tasks:
                    self.metrics.tasks_per_second = len(recent_tasks) / time_window

            # Peak concurrency
            current_total = self.metrics.active_tasks + self.metrics.pending_tasks
            if current_total > self.metrics.peak_concurrency:
                self.metrics.peak_concurrency = current_total

            self.metrics.last_update = now

    async def _trigger_backpressure(self) -> None:
        """Trigger backpressure handling."""
        self.metrics.backpressure_events += 1

        for callback in self._backpressure_callbacks:
            try:
                await callback(self.metrics)
            except Exception:
                pass

    async def _cleanup_loop(self) -> None:
        """Background cleanup task."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_completed_tasks()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _cleanup_completed_tasks(self) -> None:
        """Clean up completed task information."""
        if not self.config.enable_task_tracking:
            return

        # Remove old task info
        cutoff_time = time.time() - (self.config.cleanup_interval * 10)
        to_remove = [
            task_id for task_id, task_info in self._task_info.items()
            if task_info.completed_at and task_info.completed_at < cutoff_time
        ]

        for task_id in to_remove:
            del self._task_info[task_id]

    async def _metrics_loop(self) -> None:
        """Background metrics update task."""
        while self._running:
            try:
                await asyncio.sleep(1.0)  # Update every second
                await self._update_metrics()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    # Public API methods
    def get_metrics(self) -> ConcurrencyMetrics:
        """Get current performance metrics."""
        return self.metrics

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get information about a specific task."""
        return self._task_info.get(task_id)

    def get_active_task_count(self) -> int:
        """Get number of currently active tasks."""
        return len(self._active_tasks)

    def get_pending_task_count(self) -> int:
        """Get number of pending tasks."""
        return sum(len(queue) for queue in self._pending_queues.values())

    def is_overloaded(self) -> bool:
        """Check if manager is experiencing high load."""
        total_tasks = self.get_active_task_count() + self.get_pending_task_count()
        max_total = self.config.max_concurrent_tasks + self.config.max_pending_tasks
        return (total_tasks / max_total) > self.config.backpressure_threshold

    def add_task_started_callback(self, callback: Callable[[TaskInfo], Awaitable[None]]) -> None:
        """Add callback for when tasks start."""
        self._task_started_callbacks.append(callback)

    def add_task_completed_callback(self, callback: Callable[[TaskInfo], Awaitable[None]]) -> None:
        """Add callback for when tasks complete."""
        self._task_completed_callbacks.append(callback)

    def add_backpressure_callback(self, callback: Callable[[ConcurrencyMetrics], Awaitable[None]]) -> None:
        """Add callback for backpressure events."""
        self._backpressure_callbacks.append(callback)


# Utility functions
def create_concurrency_manager(max_concurrent: int = 1000,
                             max_pending: int = 10000,
                             enable_metrics: bool = True) -> ConcurrencyManager:
    """Create a concurrency manager with specified limits."""
    config = ConcurrencyConfig(
        max_concurrent_tasks=max_concurrent,
        max_pending_tasks=max_pending,
        enable_metrics=enable_metrics
    )
    return ConcurrencyManager(config)


def create_high_performance_config(max_concurrent: int = 5000,
                                  max_pending: int = 20000) -> ConcurrencyConfig:
    """Create configuration for high-performance scenarios."""
    return ConcurrencyConfig(
        max_concurrent_tasks=max_concurrent,
        max_pending_tasks=max_pending,
        default_timeout=60.0,
        backpressure_threshold=0.9,
        cleanup_interval=30.0,
        enable_metrics=True,
        priority_scheduling=True
    )


def create_memory_optimized_config(max_concurrent: int = 1000,
                                  max_pending: int = 5000) -> ConcurrencyConfig:
    """Create memory-optimized configuration."""
    return ConcurrencyConfig(
        max_concurrent_tasks=max_concurrent,
        max_pending_tasks=max_pending,
        default_timeout=30.0,
        enable_task_tracking=False,
        max_task_history=1000,
        cleanup_interval=10.0
    )