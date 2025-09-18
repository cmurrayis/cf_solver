"""Concurrency and performance module for high-volume operations.

This module provides advanced concurrency management, rate limiting,
and performance monitoring for 10k+ concurrent Cloudflare bypass operations.
"""

from .manager import (
    TaskPriority,
    TaskStatus,
    ConcurrencyMetrics,
    TaskInfo,
    ConcurrencyConfig,
    ConcurrencyManager,
    create_concurrency_manager,
    create_high_performance_config,
    create_memory_optimized_config,
)

from .rate_limiter import (
    RateLimitAlgorithm,
    BackpressureStrategy,
    RateLimitConfig,
    RateLimitStatus,
    TokenBucketRateLimiter,
    LeakyBucketRateLimiter,
    SlidingWindowRateLimiter,
    AdaptiveRateLimiter,
    AdvancedRateLimiter,
    RateLimiterPool,
    create_rate_limiter,
    create_adaptive_rate_limiter,
    create_high_performance_config as create_high_perf_rate_config,
    create_conservative_config as create_conservative_rate_config,
)

from .monitor import (
    MetricType,
    AlertLevel,
    MetricData,
    SystemMetrics,
    PerformanceMetrics,
    Alert,
    MetricsCollector,
    SystemMonitor,
    PerformanceMonitor,
    AlertManager,
    ComprehensiveMonitor,
    create_monitor,
    create_metrics_collector,
    create_performance_monitor,
)

# Performance configuration presets
HIGH_PERFORMANCE_CONCURRENCY_CONFIG = ConcurrencyConfig(
    max_concurrent_tasks=5000,
    max_pending_tasks=20000,
    default_timeout=60.0,
    backpressure_threshold=0.9,
    cleanup_interval=30.0,
    enable_metrics=True,
    priority_scheduling=True
)

MEMORY_OPTIMIZED_CONCURRENCY_CONFIG = ConcurrencyConfig(
    max_concurrent_tasks=1000,
    max_pending_tasks=5000,
    default_timeout=30.0,
    enable_task_tracking=False,
    max_task_history=1000,
    cleanup_interval=10.0
)

HIGH_PERFORMANCE_RATE_CONFIG = RateLimitConfig(
    requests_per_second=1000.0,
    burst_size=2000,
    algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
    backpressure_strategy=BackpressureStrategy.ADAPTIVE_DELAY,
    max_queue_size=50000,
    max_delay=10.0
)

CONSERVATIVE_RATE_CONFIG = RateLimitConfig(
    requests_per_second=50.0,
    burst_size=100,
    algorithm=RateLimitAlgorithm.ADAPTIVE,
    backpressure_strategy=BackpressureStrategy.DELAY,
    enable_adaptive=True,
    min_rate=5.0,
    max_rate=100.0
)

# Default thresholds and limits
DEFAULT_CONCURRENCY_LIMITS = {
    "max_concurrent_tasks": 1000,
    "max_pending_tasks": 10000,
    "default_timeout": 30.0,
    "backpressure_threshold": 0.8,
}

DEFAULT_RATE_LIMITS = {
    "requests_per_second": 100.0,
    "burst_size": 200,
    "max_queue_size": 10000,
    "max_delay": 30.0,
}

DEFAULT_MONITORING_CONFIG = {
    "monitoring_interval": 1.0,
    "metrics_history_size": 10000,
    "performance_window": 60,  # seconds
    "enable_system_monitoring": True,
    "enable_alerts": True,
}


class HighPerformanceManager:
    """High-level manager combining all concurrency components."""

    def __init__(self,
                 max_concurrent: int = 1000,
                 max_rate: float = 100.0,
                 enable_monitoring: bool = True,
                 enable_adaptive_rate: bool = True):

        # Create concurrency manager
        concurrency_config = ConcurrencyConfig(
            max_concurrent_tasks=max_concurrent,
            max_pending_tasks=max_concurrent * 10,
            enable_metrics=enable_monitoring
        )
        self.concurrency = ConcurrencyManager(concurrency_config)

        # Create rate limiter
        if enable_adaptive_rate:
            rate_config = RateLimitConfig(
                requests_per_second=max_rate,
                algorithm=RateLimitAlgorithm.ADAPTIVE,
                enable_adaptive=True,
                min_rate=max_rate * 0.1,
                max_rate=max_rate * 2.0
            )
        else:
            rate_config = RateLimitConfig(
                requests_per_second=max_rate,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            )

        self.rate_limiter = AdvancedRateLimiter(rate_config)
        self.rate_pool = RateLimiterPool(rate_config)

        # Create monitoring
        if enable_monitoring:
            self.monitor = create_monitor()
        else:
            self.monitor = None

        self._running = False

    async def start(self) -> None:
        """Start all components."""
        if self._running:
            return

        await self.concurrency.start()

        if self.monitor:
            await self.monitor.start_monitoring()

        self._running = True

    async def stop(self) -> None:
        """Stop all components."""
        if not self._running:
            return

        await self.concurrency.stop()

        if self.monitor:
            await self.monitor.stop_monitoring()

        self._running = False

    async def submit_request(self, coro, domain: str = "global",
                           priority: TaskPriority = TaskPriority.NORMAL) -> bool:
        """Submit a request with rate limiting and concurrency control."""
        # Check rate limit first
        if not await self.rate_pool.acquire(domain):
            return False

        # Submit to concurrency manager
        try:
            future = await self.concurrency.submit_task(coro, priority)
            return True
        except RuntimeError:
            # Backpressure - couldn't submit
            return False

    async def submit_batch(self, coros, domain: str = "global",
                         priority: TaskPriority = TaskPriority.NORMAL) -> list:
        """Submit batch of requests."""
        results = []
        for coro in coros:
            result = await self.submit_request(coro, domain, priority)
            results.append(result)
        return results

    def get_comprehensive_stats(self):
        """Get statistics from all components."""
        stats = {
            "concurrency": self.concurrency.get_metrics().to_dict(),
            "rate_limiting": self.rate_pool.get_stats(),
            "running": self._running,
        }

        if self.monitor:
            stats["monitoring"] = self.monitor.get_comprehensive_stats()

        return stats

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        if not self._running:
            return False

        # Check if overloaded
        if self.concurrency.is_overloaded():
            return False

        # Check active alerts if monitoring enabled
        if self.monitor:
            active_alerts = self.monitor.alerts.get_active_alerts()
            critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
            if critical_alerts:
                return False

        return True


def create_high_performance_manager(max_concurrent: int = 5000,
                                   max_rate: float = 1000.0) -> HighPerformanceManager:
    """Create high-performance manager for large-scale operations."""
    return HighPerformanceManager(
        max_concurrent=max_concurrent,
        max_rate=max_rate,
        enable_monitoring=True,
        enable_adaptive_rate=True
    )


def create_conservative_manager(max_concurrent: int = 100,
                              max_rate: float = 50.0) -> HighPerformanceManager:
    """Create conservative manager to avoid detection."""
    return HighPerformanceManager(
        max_concurrent=max_concurrent,
        max_rate=max_rate,
        enable_monitoring=True,
        enable_adaptive_rate=True
    )


def create_memory_efficient_manager(max_concurrent: int = 500,
                                   max_rate: float = 200.0) -> HighPerformanceManager:
    """Create memory-efficient manager for resource-constrained environments."""
    manager = HighPerformanceManager(
        max_concurrent=max_concurrent,
        max_rate=max_rate,
        enable_monitoring=False,  # Disable monitoring to save memory
        enable_adaptive_rate=False
    )

    # Use memory-optimized configuration
    manager.concurrency.config = MEMORY_OPTIMIZED_CONCURRENCY_CONFIG
    return manager


# Utility functions for common operations
async def execute_with_concurrency_limit(coros, max_concurrent: int = 100):
    """Execute coroutines with concurrency limit."""
    manager = create_concurrency_manager(max_concurrent, max_concurrent * 10)
    await manager.start()

    try:
        futures = await manager.submit_batch(coros)
        done, pending = await manager.wait_for_completion(futures)

        results = []
        for future in done:
            try:
                result = await future
                results.append(result)
            except Exception as e:
                results.append(e)

        return results

    finally:
        await manager.stop()


async def execute_with_rate_limit(coros, requests_per_second: float = 100.0):
    """Execute coroutines with rate limiting."""
    rate_limiter = create_rate_limiter(requests_per_second)
    results = []

    for coro in coros:
        # Wait for rate limit
        while not await rate_limiter.acquire():
            await asyncio.sleep(0.01)

        # Execute coroutine
        try:
            result = await coro
            results.append(result)
            await rate_limiter.record_result(True)
        except Exception as e:
            results.append(e)
            await rate_limiter.record_result(False)

    return results


# Export public API
__all__ = [
    # Enums
    "TaskPriority",
    "TaskStatus",
    "RateLimitAlgorithm",
    "BackpressureStrategy",
    "MetricType",
    "AlertLevel",

    # Classes
    "ConcurrencyMetrics",
    "TaskInfo",
    "ConcurrencyConfig",
    "ConcurrencyManager",
    "RateLimitConfig",
    "RateLimitStatus",
    "AdvancedRateLimiter",
    "RateLimiterPool",
    "MetricData",
    "SystemMetrics",
    "PerformanceMetrics",
    "Alert",
    "MetricsCollector",
    "SystemMonitor",
    "PerformanceMonitor",
    "AlertManager",
    "ComprehensiveMonitor",
    "HighPerformanceManager",

    # Factory functions
    "create_concurrency_manager",
    "create_rate_limiter",
    "create_adaptive_rate_limiter",
    "create_monitor",
    "create_metrics_collector",
    "create_performance_monitor",
    "create_high_performance_manager",
    "create_conservative_manager",
    "create_memory_efficient_manager",

    # Configuration presets
    "HIGH_PERFORMANCE_CONCURRENCY_CONFIG",
    "MEMORY_OPTIMIZED_CONCURRENCY_CONFIG",
    "HIGH_PERFORMANCE_RATE_CONFIG",
    "CONSERVATIVE_RATE_CONFIG",

    # Constants
    "DEFAULT_CONCURRENCY_LIMITS",
    "DEFAULT_RATE_LIMITS",
    "DEFAULT_MONITORING_CONFIG",

    # Utility functions
    "execute_with_concurrency_limit",
    "execute_with_rate_limit",
]