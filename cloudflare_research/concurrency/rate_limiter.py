"""Advanced rate limiting and backpressure handling.

Provides sophisticated rate limiting algorithms, adaptive throttling,
and backpressure management for high-volume Cloudflare bypass operations.
"""

import asyncio
import time
import math
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


class BackpressureStrategy(Enum):
    """Backpressure handling strategies."""
    BLOCK = "block"           # Block until capacity available
    DROP = "drop"             # Drop requests when over limit
    DELAY = "delay"           # Add exponential delays
    ADAPTIVE_DELAY = "adaptive_delay"  # Adaptive delay based on load


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 100.0
    burst_size: int = 200
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DELAY

    # Adaptive rate limiting
    enable_adaptive: bool = True
    min_rate: float = 10.0
    max_rate: float = 1000.0
    adaptation_window: float = 60.0  # seconds

    # Backpressure configuration
    max_queue_size: int = 10000
    max_delay: float = 30.0
    delay_factor: float = 1.5

    # Window configuration (for window-based algorithms)
    window_size: float = 1.0  # seconds
    sub_windows: int = 10


@dataclass
class RateLimitStatus:
    """Current rate limiter status."""
    current_rate: float = 0.0
    available_tokens: float = 0.0
    queue_size: int = 0
    total_requests: int = 0
    dropped_requests: int = 0
    delayed_requests: int = 0
    avg_delay: float = 0.0
    last_request_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_rate": self.current_rate,
            "available_tokens": self.available_tokens,
            "queue_size": self.queue_size,
            "total_requests": self.total_requests,
            "dropped_requests": self.dropped_requests,
            "delayed_requests": self.delayed_requests,
            "avg_delay": self.avg_delay,
            "last_request_time": self.last_request_time,
            "drop_rate": self.dropped_requests / max(1, self.total_requests),
        }


class TokenBucketRateLimiter:
    """Token bucket rate limiting algorithm."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_size)
        self.last_update = time.time()

    async def acquire(self, tokens: float = 1.0) -> bool:
        """Acquire tokens from the bucket."""
        now = time.time()

        # Add tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(
            self.config.burst_size,
            self.tokens + elapsed * self.config.requests_per_second
        )
        self.last_update = now

        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_available_tokens(self) -> float:
        """Get number of available tokens."""
        now = time.time()
        elapsed = now - self.last_update
        return min(
            self.config.burst_size,
            self.tokens + elapsed * self.config.requests_per_second
        )


class LeakyBucketRateLimiter:
    """Leaky bucket rate limiting algorithm."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.queue: deque = deque()
        self.last_leak = time.time()

    async def acquire(self, tokens: float = 1.0) -> bool:
        """Add request to the leaky bucket."""
        now = time.time()

        # Leak tokens
        elapsed = now - self.last_leak
        tokens_to_leak = elapsed * self.config.requests_per_second

        # Remove leaked requests
        while tokens_to_leak > 0 and self.queue:
            self.queue.popleft()
            tokens_to_leak -= 1.0

        self.last_leak = now

        # Check if we can add more requests
        if len(self.queue) < self.config.burst_size:
            self.queue.append(now)
            return True

        return False

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)


class SlidingWindowRateLimiter:
    """Sliding window rate limiting algorithm."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: deque = deque()

    async def acquire(self, tokens: float = 1.0) -> bool:
        """Check if request is allowed in sliding window."""
        now = time.time()
        window_start = now - self.config.window_size

        # Remove old requests
        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

        # Check rate limit
        if len(self.requests) < self.config.requests_per_second * self.config.window_size:
            self.requests.append(now)
            return True

        return False

    def get_current_rate(self) -> float:
        """Get current request rate."""
        now = time.time()
        window_start = now - self.config.window_size

        # Count requests in window
        count = sum(1 for req_time in self.requests if req_time >= window_start)
        return count / self.config.window_size


class AdaptiveRateLimiter:
    """Adaptive rate limiting that adjusts based on success rates."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.current_rate = config.requests_per_second
        self.base_limiter = TokenBucketRateLimiter(config)

        # Adaptation tracking
        self.success_count = 0
        self.failure_count = 0
        self.last_adaptation = time.time()
        self.rate_history: deque = deque(maxlen=100)

    async def acquire(self, tokens: float = 1.0) -> bool:
        """Acquire with adaptive rate adjustment."""
        # Update base limiter rate
        self.base_limiter.config.requests_per_second = self.current_rate

        # Check adaptation
        await self._check_adaptation()

        return await self.base_limiter.acquire(tokens)

    async def _check_adaptation(self) -> None:
        """Check if rate adaptation is needed."""
        now = time.time()
        if now - self.last_adaptation < self.config.adaptation_window:
            return

        total_requests = self.success_count + self.failure_count
        if total_requests == 0:
            return

        success_rate = self.success_count / total_requests

        # Adjust rate based on success rate
        if success_rate > 0.95:  # High success rate - increase rate
            self.current_rate = min(
                self.config.max_rate,
                self.current_rate * 1.1
            )
        elif success_rate < 0.8:  # Low success rate - decrease rate
            self.current_rate = max(
                self.config.min_rate,
                self.current_rate * 0.9
            )

        # Record rate change
        self.rate_history.append((now, self.current_rate, success_rate))

        # Reset counters
        self.success_count = 0
        self.failure_count = 0
        self.last_adaptation = now

    def record_success(self) -> None:
        """Record a successful request."""
        self.success_count += 1

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1

    def get_current_rate(self) -> float:
        """Get current adaptive rate."""
        return self.current_rate


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies and backpressure handling."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.status = RateLimitStatus()

        # Initialize rate limiter based on algorithm
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            self.limiter = TokenBucketRateLimiter(config)
        elif config.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            self.limiter = LeakyBucketRateLimiter(config)
        elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            self.limiter = SlidingWindowRateLimiter(config)
        elif config.algorithm == RateLimitAlgorithm.ADAPTIVE:
            self.limiter = AdaptiveRateLimiter(config)
        else:
            self.limiter = TokenBucketRateLimiter(config)

        # Backpressure management
        self.pending_queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self.delay_history: deque = deque(maxlen=1000)

    async def acquire(self, tokens: float = 1.0, priority: int = 0) -> bool:
        """Acquire permission for request with backpressure handling."""
        now = time.time()
        self.status.total_requests += 1
        self.status.last_request_time = now

        # Try immediate acquisition
        if await self.limiter.acquire(tokens):
            return True

        # Handle backpressure based on strategy
        if self.config.backpressure_strategy == BackpressureStrategy.DROP:
            self.status.dropped_requests += 1
            return False

        elif self.config.backpressure_strategy == BackpressureStrategy.BLOCK:
            return await self._block_until_available(tokens)

        elif self.config.backpressure_strategy == BackpressureStrategy.DELAY:
            return await self._delay_and_retry(tokens, priority)

        elif self.config.backpressure_strategy == BackpressureStrategy.ADAPTIVE_DELAY:
            return await self._adaptive_delay_and_retry(tokens, priority)

        return False

    async def _block_until_available(self, tokens: float) -> bool:
        """Block until tokens are available."""
        while True:
            if await self.limiter.acquire(tokens):
                return True
            await asyncio.sleep(0.01)  # Small delay before retry

    async def _delay_and_retry(self, tokens: float, priority: int) -> bool:
        """Apply exponential delay and retry."""
        delay = 0.1  # Start with 100ms delay

        for attempt in range(10):  # Max 10 attempts
            await asyncio.sleep(delay)

            if await self.limiter.acquire(tokens):
                self.status.delayed_requests += 1
                self.delay_history.append(delay)
                self._update_avg_delay()
                return True

            # Exponential backoff
            delay = min(delay * self.config.delay_factor, self.config.max_delay)

        # Failed after all attempts
        self.status.dropped_requests += 1
        return False

    async def _adaptive_delay_and_retry(self, tokens: float, priority: int) -> bool:
        """Apply adaptive delay based on current load."""
        # Calculate adaptive delay based on queue size and success rate
        queue_ratio = self.status.queue_size / max(1, self.config.max_queue_size)
        base_delay = 0.1 + (queue_ratio * 2.0)  # 100ms to 2.1s based on load

        # Priority adjustment
        priority_factor = max(0.1, 1.0 - (priority * 0.1))
        delay = base_delay * priority_factor

        await asyncio.sleep(delay)

        if await self.limiter.acquire(tokens):
            self.status.delayed_requests += 1
            self.delay_history.append(delay)
            self._update_avg_delay()
            return True

        self.status.dropped_requests += 1
        return False

    def _update_avg_delay(self) -> None:
        """Update average delay statistics."""
        if self.delay_history:
            self.status.avg_delay = sum(self.delay_history) / len(self.delay_history)

    async def record_result(self, success: bool) -> None:
        """Record request result for adaptive rate limiting."""
        if isinstance(self.limiter, AdaptiveRateLimiter):
            if success:
                self.limiter.record_success()
            else:
                self.limiter.record_failure()

    def get_status(self) -> RateLimitStatus:
        """Get current rate limiter status."""
        # Update dynamic status
        if hasattr(self.limiter, 'get_available_tokens'):
            self.status.available_tokens = self.limiter.get_available_tokens()

        if hasattr(self.limiter, 'get_current_rate'):
            self.status.current_rate = self.limiter.get_current_rate()
        elif hasattr(self.limiter, 'current_rate'):
            self.status.current_rate = self.limiter.current_rate
        else:
            self.status.current_rate = self.config.requests_per_second

        self.status.queue_size = self.pending_queue.qsize()

        return self.status

    def reset_stats(self) -> None:
        """Reset rate limiter statistics."""
        self.status = RateLimitStatus()
        self.delay_history.clear()


class RateLimiterPool:
    """Pool of rate limiters for different domains/endpoints."""

    def __init__(self, default_config: RateLimitConfig):
        self.default_config = default_config
        self.limiters: Dict[str, AdvancedRateLimiter] = {}
        self.global_limiter = AdvancedRateLimiter(default_config)

    def get_limiter(self, key: str) -> AdvancedRateLimiter:
        """Get rate limiter for specific key (domain/endpoint)."""
        if key not in self.limiters:
            self.limiters[key] = AdvancedRateLimiter(self.default_config)
        return self.limiters[key]

    async def acquire(self, key: str, tokens: float = 1.0, priority: int = 0) -> bool:
        """Acquire from both specific and global rate limiters."""
        # Check global rate limit first
        if not await self.global_limiter.acquire(tokens, priority):
            return False

        # Check specific rate limit
        specific_limiter = self.get_limiter(key)
        return await specific_limiter.acquire(tokens, priority)

    async def record_result(self, key: str, success: bool) -> None:
        """Record result for both limiters."""
        await self.global_limiter.record_result(success)
        if key in self.limiters:
            await self.limiters[key].record_result(success)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all rate limiters."""
        stats = {
            "global": self.global_limiter.get_status().to_dict(),
            "per_key": {}
        }

        for key, limiter in self.limiters.items():
            stats["per_key"][key] = limiter.get_status().to_dict()

        return stats


# Utility functions
def create_rate_limiter(requests_per_second: float = 100.0,
                       burst_size: int = 200,
                       algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET) -> AdvancedRateLimiter:
    """Create a rate limiter with specified parameters."""
    config = RateLimitConfig(
        requests_per_second=requests_per_second,
        burst_size=burst_size,
        algorithm=algorithm
    )
    return AdvancedRateLimiter(config)


def create_adaptive_rate_limiter(min_rate: float = 10.0,
                               max_rate: float = 1000.0,
                               initial_rate: float = 100.0) -> AdvancedRateLimiter:
    """Create an adaptive rate limiter."""
    config = RateLimitConfig(
        requests_per_second=initial_rate,
        algorithm=RateLimitAlgorithm.ADAPTIVE,
        min_rate=min_rate,
        max_rate=max_rate,
        enable_adaptive=True
    )
    return AdvancedRateLimiter(config)


def create_high_performance_config() -> RateLimitConfig:
    """Create configuration for high-performance scenarios."""
    return RateLimitConfig(
        requests_per_second=1000.0,
        burst_size=2000,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        backpressure_strategy=BackpressureStrategy.ADAPTIVE_DELAY,
        max_queue_size=50000,
        max_delay=10.0
    )


def create_conservative_config() -> RateLimitConfig:
    """Create conservative configuration to avoid detection."""
    return RateLimitConfig(
        requests_per_second=50.0,
        burst_size=100,
        algorithm=RateLimitAlgorithm.ADAPTIVE,
        backpressure_strategy=BackpressureStrategy.DELAY,
        enable_adaptive=True,
        min_rate=5.0,
        max_rate=100.0
    )