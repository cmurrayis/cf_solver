"""Utility functions and helpers for Cloudflare research operations.

This module provides essential utility functions for high-performance operations,
including timing utilities, data validation, async helpers, and system utilities.
"""

import asyncio
import time
import random
import string
import hashlib
import base64
import json
import re
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, TypeVar, Generic
from urllib.parse import urlparse, urljoin, quote, unquote
from dataclasses import dataclass, asdict
from functools import wraps
import logging

# Import resource management
from .resources import (
    ResourceMonitor,
    ResourceManager,
    ResourceType,
    ResourceLimit,
    SystemResources,
    create_resource_monitor,
    create_resource_manager,
    get_system_limits,
    check_system_health,
    wait_for_resources,
)

T = TypeVar('T')


# Timing utilities
class Timer:
    """High-precision timer for performance measurements."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop the timer and return elapsed time."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        self.end_time = time.perf_counter()
        return self.elapsed

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.perf_counter()
        return end - self.start_time

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        with Timer() as timer:
            result = await func(*args, **kwargs)
        logging.debug(f"{func.__name__} took {timer.elapsed:.3f}s")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        with Timer() as timer:
            result = func(*args, **kwargs)
        logging.debug(f"{func.__name__} took {timer.elapsed:.3f}s")
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


# Async utilities
class AsyncCache(Generic[T]):
    """Simple async-safe cache with TTL support."""

    def __init__(self, ttl: float = 300.0):
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: T) -> None:
        """Set value in cache."""
        async with self._lock:
            self._cache[key] = (value, time.time())

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """Get cache size."""
        async with self._lock:
            return len(self._cache)


async def retry_async(func: Callable[..., Awaitable[T]],
                     max_attempts: int = 3,
                     delay: float = 1.0,
                     backoff_factor: float = 2.0,
                     exceptions: tuple = (Exception,)) -> T:
    """Retry an async function with exponential backoff."""

    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts - 1:
                break

            wait_time = delay * (backoff_factor ** attempt)
            await asyncio.sleep(wait_time)

    raise last_exception


async def timeout_after(coro: Awaitable[T], timeout: float) -> T:
    """Run coroutine with timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)


async def gather_with_limit(coros: List[Awaitable[T]], limit: int) -> List[T]:
    """Run coroutines concurrently with concurrency limit."""

    semaphore = asyncio.Semaphore(limit)

    async def limited_coro(coro):
        async with semaphore:
            return await coro

    limited_coros = [limited_coro(coro) for coro in coros]
    return await asyncio.gather(*limited_coros)


# String utilities
def generate_random_string(length: int = 16,
                         chars: str = string.ascii_letters + string.digits) -> str:
    """Generate a random string of specified length."""
    return ''.join(random.choice(chars) for _ in range(length))


def generate_request_id() -> str:
    """Generate a unique request ID."""
    timestamp = str(int(time.time() * 1000))
    random_part = generate_random_string(8)
    return f"req_{timestamp}_{random_part}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    timestamp = str(int(time.time()))
    random_part = generate_random_string(12)
    return f"sess_{timestamp}_{random_part}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# URL utilities
def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def normalize_url(url: str) -> str:
    """Normalize URL for consistent comparison."""
    try:
        parsed = urlparse(url.lower().strip())

        # Remove default ports
        netloc = parsed.netloc
        if ':80' in netloc and parsed.scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and parsed.scheme == 'https':
            netloc = netloc.replace(':443', '')

        # Remove trailing slash from path
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'

        # Reconstruct URL
        return f"{parsed.scheme}://{netloc}{path}"
    except Exception:
        return url


def build_url(base: str, path: str = "", params: Dict[str, Any] = None) -> str:
    """Build URL from components."""
    url = urljoin(base, path)

    if params:
        query_parts = []
        for key, value in params.items():
            if value is not None:
                query_parts.append(f"{quote(str(key))}={quote(str(value))}")

        if query_parts:
            separator = "&" if "?" in url else "?"
            url += separator + "&".join(query_parts)

    return url


# Data utilities
def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []

    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely parse JSON with default fallback."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "null") -> str:
    """Safely serialize to JSON with default fallback."""
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError):
        return default


# Hashing utilities
def compute_hash(data: Union[str, bytes], algorithm: str = 'sha256') -> str:
    """Compute hash of data."""
    if isinstance(data, str):
        data = data.encode('utf-8')

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def compute_md5(data: Union[str, bytes]) -> str:
    """Compute MD5 hash."""
    return compute_hash(data, 'md5')


def compute_sha256(data: Union[str, bytes]) -> str:
    """Compute SHA256 hash."""
    return compute_hash(data, 'sha256')


def encode_base64(data: Union[str, bytes]) -> str:
    """Encode data as base64."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(data).decode('ascii')


def decode_base64(data: str) -> bytes:
    """Decode base64 data."""
    return base64.b64decode(data)


# Validation utilities
def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_ip_address(ip: str) -> bool:
    """Validate IP address format."""
    try:
        import ipaddress
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_port(port: Union[int, str]) -> bool:
    """Validate port number."""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


# Rate limiting utilities
class RateLimit:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 1):
        self.rate = rate  # tokens per second
        self.burst = burst  # max tokens
        self.tokens = burst
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from bucket."""
        async with self._lock:
            now = time.time()

            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait(self, tokens: int = 1) -> None:
        """Wait until tokens are available."""
        while not await self.acquire(tokens):
            await asyncio.sleep(0.01)


# Performance utilities
class PerformanceCollector:
    """Collect performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def record(self, name: str, value: float) -> None:
        """Record a metric value."""
        async with self._lock:
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(value)

    async def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        async with self._lock:
            values = self.metrics.get(name, [])

            if not values:
                return {}

            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'total': sum(values),
            }

    async def clear(self) -> None:
        """Clear all metrics."""
        async with self._lock:
            self.metrics.clear()


# System utilities
def get_user_agent() -> str:
    """Get a realistic user agent string."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)


def get_random_chrome_version() -> str:
    """Get a random Chrome version string."""
    major_versions = [119, 120, 121]
    minor_version = random.randint(0, 9)
    build_version = random.randint(6000, 6999)
    patch_version = random.randint(100, 999)

    major = random.choice(major_versions)
    return f"{major}.0.{build_version}.{patch_version}"


# Export all utilities
__all__ = [
    # Resource management
    'ResourceMonitor', 'ResourceManager', 'ResourceType', 'ResourceLimit', 'SystemResources',
    'create_resource_monitor', 'create_resource_manager', 'get_system_limits',
    'check_system_health', 'wait_for_resources',

    # Timing utilities
    'Timer', 'timing_decorator',

    # Async utilities
    'AsyncCache', 'retry_async', 'timeout_after', 'gather_with_limit',

    # String utilities
    'generate_random_string', 'generate_request_id', 'generate_session_id',
    'sanitize_filename', 'truncate_string',

    # URL utilities
    'is_valid_url', 'extract_domain', 'normalize_url', 'build_url',

    # Data utilities
    'deep_merge_dicts', 'flatten_dict', 'safe_json_loads', 'safe_json_dumps',

    # Hashing utilities
    'compute_hash', 'compute_md5', 'compute_sha256', 'encode_base64', 'decode_base64',

    # Validation utilities
    'validate_email', 'validate_ip_address', 'validate_port',

    # Rate limiting
    'RateLimit',

    # Performance utilities
    'PerformanceCollector',

    # System utilities
    'get_user_agent', 'get_random_chrome_version',
]