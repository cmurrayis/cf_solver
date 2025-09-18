"""Request timing emulation for realistic browser behavior.

Provides timing patterns that match real Chrome browser behavior
to avoid detection through timing analysis.
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse


class RequestPriority(Enum):
    """Request priority levels affecting timing."""
    CRITICAL = "critical"  # HTML, CSS blocking
    HIGH = "high"         # Scripts, fonts
    MEDIUM = "medium"     # Images, XHR
    LOW = "low"           # Prefetch, analytics
    IDLE = "idle"         # Background tasks


class ConnectionState(Enum):
    """HTTP connection states."""
    NEW = "new"
    REUSED = "reused"
    POOLED = "pooled"


@dataclass
class TimingProfile:
    """Timing characteristics for different request types."""
    dns_resolution_range: Tuple[int, int] = (5, 25)      # ms
    tcp_connection_range: Tuple[int, int] = (10, 50)     # ms
    tls_handshake_range: Tuple[int, int] = (15, 75)      # ms
    request_processing_range: Tuple[int, int] = (1, 5)    # ms
    response_download_base: float = 0.1                   # ms per byte
    network_jitter_factor: float = 0.2                   # Variability


@dataclass
class RequestTimingContext:
    """Context for request timing calculation."""
    url: str
    method: str = "GET"
    request_size: int = 1024
    response_size: int = 10240
    priority: RequestPriority = RequestPriority.MEDIUM
    connection_state: ConnectionState = ConnectionState.NEW
    is_same_origin: bool = True
    has_cache: bool = False
    user_initiated: bool = True


class BrowserTimingEmulator:
    """
    Emulates Chrome browser request timing patterns.
    
    Generates realistic timing that matches Chrome's network behavior
    including connection reuse, prioritization, and human-like delays.
    """

    def __init__(self):
        self._connection_pool: Dict[str, float] = {}  # domain -> last_use_time
        self._request_history: List[Tuple[str, float]] = []  # (url, timestamp)
        self._timing_profiles = self._load_timing_profiles()
        self._base_latency = self._estimate_base_latency()

    def _load_timing_profiles(self) -> Dict[RequestPriority, TimingProfile]:
        """Load timing profiles for different request priorities."""
        return {
            RequestPriority.CRITICAL: TimingProfile(
                dns_resolution_range=(3, 15),
                tcp_connection_range=(8, 30),
                tls_handshake_range=(12, 45),
                request_processing_range=(1, 3),
                response_download_base=0.05,
            ),
            RequestPriority.HIGH: TimingProfile(
                dns_resolution_range=(5, 20),
                tcp_connection_range=(10, 40),
                tls_handshake_range=(15, 60),
                request_processing_range=(1, 4),
                response_download_base=0.08,
            ),
            RequestPriority.MEDIUM: TimingProfile(
                dns_resolution_range=(8, 25),
                tcp_connection_range=(12, 50),
                tls_handshake_range=(18, 75),
                request_processing_range=(2, 5),
                response_download_base=0.1,
            ),
            RequestPriority.LOW: TimingProfile(
                dns_resolution_range=(10, 35),
                tcp_connection_range=(15, 60),
                tls_handshake_range=(20, 90),
                request_processing_range=(3, 8),
                response_download_base=0.15,
            ),
            RequestPriority.IDLE: TimingProfile(
                dns_resolution_range=(15, 50),
                tcp_connection_range=(20, 80),
                tls_handshake_range=(25, 120),
                request_processing_range=(5, 15),
                response_download_base=0.2,
            ),
        }

    def _estimate_base_latency(self) -> float:
        """Estimate base network latency."""
        # Simulate network conditions (could be configurable)
        return random.uniform(20, 100)  # Base RTT in ms

    async def calculate_request_timing(self, context: RequestTimingContext) -> Dict[str, int]:
        """Calculate realistic timing for a request."""
        profile = self._timing_profiles[context.priority]
        parsed_url = urlparse(context.url)
        domain = parsed_url.netloc

        # Determine connection state
        connection_state = self._determine_connection_state(domain, context)

        # Calculate timing components
        timing = {
            "dns_resolution_ms": 0,
            "tcp_connection_ms": 0,
            "tls_handshake_ms": 0,
            "request_sent_ms": 0,
            "response_received_ms": 0,
            "total_duration_ms": 0,
        }

        # DNS resolution (skip if IP or cached)
        if not self._is_ip_address(domain) and connection_state == ConnectionState.NEW:
            timing["dns_resolution_ms"] = self._random_timing(
                profile.dns_resolution_range, profile.network_jitter_factor
            )

        # TCP connection (skip if reused)
        if connection_state == ConnectionState.NEW:
            timing["tcp_connection_ms"] = self._random_timing(
                profile.tcp_connection_range, profile.network_jitter_factor
            )

        # TLS handshake (skip if reused, reduce if resumed)
        if parsed_url.scheme == "https":
            if connection_state == ConnectionState.NEW:
                timing["tls_handshake_ms"] = self._random_timing(
                    profile.tls_handshake_range, profile.network_jitter_factor
                )
            elif connection_state == ConnectionState.POOLED:
                # TLS session resumption
                timing["tls_handshake_ms"] = self._random_timing(
                    (5, 15), profile.network_jitter_factor
                )

        # Request processing
        timing["request_sent_ms"] = self._random_timing(
            profile.request_processing_range, profile.network_jitter_factor
        )

        # Response download
        download_time = self._calculate_download_time(
            context.response_size, profile, context.has_cache
        )
        timing["response_received_ms"] = download_time

        # Total time
        timing["total_duration_ms"] = sum(timing.values())

        # Add human-like delays for user-initiated requests
        if context.user_initiated:
            timing["total_duration_ms"] += self._add_human_delay(context)

        # Update connection pool
        self._update_connection_pool(domain)

        # Record request in history
        self._request_history.append((context.url, time.time()))
        if len(self._request_history) > 1000:  # Limit history size
            self._request_history = self._request_history[-500:]

        return timing

    def _determine_connection_state(self, domain: str, context: RequestTimingContext) -> ConnectionState:
        """Determine if connection can be reused."""
        if context.connection_state != ConnectionState.NEW:
            return context.connection_state

        current_time = time.time()
        last_use = self._connection_pool.get(domain)

        if last_use and (current_time - last_use) < 60:  # 60 second keep-alive
            return ConnectionState.REUSED
        elif last_use and (current_time - last_use) < 300:  # 5 minute pool
            return ConnectionState.POOLED
        else:
            return ConnectionState.NEW

    def _is_ip_address(self, hostname: str) -> bool:
        """Check if hostname is an IP address."""
        import ipaddress
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    def _random_timing(self, range_tuple: Tuple[int, int], jitter_factor: float) -> int:
        """Generate random timing with jitter."""
        min_val, max_val = range_tuple
        base_time = random.uniform(min_val, max_val)
        
        # Add network jitter
        jitter = random.uniform(-jitter_factor, jitter_factor) * base_time
        final_time = base_time + jitter + (self._base_latency * 0.1)
        
        return max(1, int(final_time))

    def _calculate_download_time(self, response_size: int, profile: TimingProfile,
                               has_cache: bool) -> int:
        """Calculate response download time."""
        if has_cache and random.random() < 0.8:  # 80% cache hit rate
            return random.randint(1, 5)  # Very fast for cached content

        # Simulate bandwidth (varies by content type and network)
        base_rate = profile.response_download_base
        bandwidth_factor = random.uniform(0.5, 2.0)  # Network variability
        
        download_time = response_size * base_rate * bandwidth_factor
        
        # Add minimum download time
        return max(5, int(download_time))

    def _add_human_delay(self, context: RequestTimingContext) -> int:
        """Add human-like delays for user-initiated requests."""
        if not context.user_initiated:
            return 0

        # Add small delays that simulate human behavior
        delays = {
            "think_time": random.randint(50, 200),     # Human processing
            "mouse_movement": random.randint(10, 50),  # Mouse to click target
            "click_processing": random.randint(5, 20), # Click event processing
        }

        # Only add delays occasionally to avoid being too slow
        if random.random() < 0.3:  # 30% chance of noticeable delay
            return sum(delays.values())
        else:
            return random.randint(10, 30)  # Minimal delay

    def _update_connection_pool(self, domain: str) -> None:
        """Update connection pool with current usage."""
        self._connection_pool[domain] = time.time()
        
        # Clean old connections
        current_time = time.time()
        expired_domains = [
            d for d, last_use in self._connection_pool.items()
            if current_time - last_use > 300  # 5 minute expiry
        ]
        
        for domain in expired_domains:
            del self._connection_pool[domain]

    async def emulate_page_load_timing(self, main_url: str,
                                     resources: List[str]) -> Dict[str, Dict[str, int]]:
        """Emulate timing for a complete page load."""
        timing_results = {}
        
        # Main document (highest priority)
        main_context = RequestTimingContext(
            url=main_url,
            priority=RequestPriority.CRITICAL,
            user_initiated=True,
            response_size=50000,  # Typical HTML size
        )
        timing_results[main_url] = await self.calculate_request_timing(main_context)

        # Simulate browser parsing delay
        await asyncio.sleep(random.uniform(0.01, 0.05))

        # Load resources in priority order
        resource_priorities = self._assign_resource_priorities(resources)
        
        # Group by priority for parallel loading
        priority_groups = {}
        for resource, priority in resource_priorities.items():
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(resource)

        # Load in priority order
        for priority in [RequestPriority.CRITICAL, RequestPriority.HIGH, 
                        RequestPriority.MEDIUM, RequestPriority.LOW]:
            if priority in priority_groups:
                # Load resources in this priority group concurrently
                tasks = []
                for resource in priority_groups[priority]:
                    context = RequestTimingContext(
                        url=resource,
                        priority=priority,
                        user_initiated=False,
                        response_size=self._estimate_resource_size(resource),
                        is_same_origin=self._is_same_origin(main_url, resource),
                    )
                    tasks.append(self.calculate_request_timing(context))
                
                # Execute concurrently with some delay between starts
                results = []
                for i, task in enumerate(tasks):
                    if i > 0:
                        await asyncio.sleep(random.uniform(0.001, 0.01))
                    result = await task
                    results.append(result)
                
                # Store results
                for resource, result in zip(priority_groups[priority], results):
                    timing_results[resource] = result

        return timing_results

    def _assign_resource_priorities(self, resources: List[str]) -> Dict[str, RequestPriority]:
        """Assign priorities to resources based on type."""
        priorities = {}
        
        for resource in resources:
            if resource.endswith(('.css', '.scss')):
                priorities[resource] = RequestPriority.CRITICAL
            elif resource.endswith(('.js', '.mjs')):
                priorities[resource] = RequestPriority.HIGH
            elif resource.endswith(('.woff', '.woff2', '.ttf', '.otf')):
                priorities[resource] = RequestPriority.HIGH
            elif resource.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                priorities[resource] = RequestPriority.MEDIUM
            elif 'api' in resource or 'ajax' in resource:
                priorities[resource] = RequestPriority.HIGH
            else:
                priorities[resource] = RequestPriority.MEDIUM
        
        return priorities

    def _estimate_resource_size(self, resource_url: str) -> int:
        """Estimate resource size based on type."""
        size_estimates = {
            '.css': (5000, 50000),
            '.js': (10000, 200000),
            '.png': (5000, 100000),
            '.jpg': (10000, 500000),
            '.gif': (1000, 50000),
            '.woff': (20000, 100000),
            '.woff2': (15000, 80000),
            '.svg': (1000, 20000),
        }
        
        for ext, (min_size, max_size) in size_estimates.items():
            if resource_url.endswith(ext):
                return random.randint(min_size, max_size)
        
        return random.randint(5000, 50000)  # Default

    def _is_same_origin(self, url1: str, url2: str) -> bool:
        """Check if two URLs are same origin."""
        try:
            parsed1 = urlparse(url1)
            parsed2 = urlparse(url2)
            return (parsed1.scheme == parsed2.scheme and 
                   parsed1.netloc == parsed2.netloc)
        except Exception:
            return False

    def get_connection_stats(self):
        """Get connection pool statistics."""
        current_time = time.time()
        active_connections = sum(
            1 for last_use in self._connection_pool.values()
            if current_time - last_use < 60
        )
        
        return {
            "total_domains": len(self._connection_pool),
            "active_connections": active_connections,
            "requests_in_history": len(self._request_history),
            "base_latency_ms": self._base_latency,
        }

    def reset_state(self) -> None:
        """Reset emulator state."""
        self._connection_pool.clear()
        self._request_history.clear()
        self._base_latency = self._estimate_base_latency()


# Utility functions
def create_timing_emulator() -> BrowserTimingEmulator:
    """Create browser timing emulator instance."""
    return BrowserTimingEmulator()


async def emulate_request_timing(url: str, method: str = "GET",
                               request_size: int = 1024,
                               response_size: int = 10240) -> Dict[str, int]:
    """Quick utility to emulate timing for a single request."""
    emulator = BrowserTimingEmulator()
    context = RequestTimingContext(
        url=url,
        method=method,
        request_size=request_size,
        response_size=response_size,
    )
    return await emulator.calculate_request_timing(context)


def add_realistic_delay(base_timing: Dict[str, int], 
                       variance_factor: float = 0.1) -> Dict[str, int]:
    """Add realistic variance to timing values."""
    adjusted_timing = {}
    
    for key, value in base_timing.items():
        if value > 0:
            variance = random.uniform(-variance_factor, variance_factor) * value
            adjusted_timing[key] = max(1, int(value + variance))
        else:
            adjusted_timing[key] = value
    
    return adjusted_timing


# Predefined timing profiles
FAST_NETWORK_PROFILE = TimingProfile(
    dns_resolution_range=(2, 10),
    tcp_connection_range=(5, 20),
    tls_handshake_range=(8, 30),
    request_processing_range=(1, 3),
    response_download_base=0.03,
    network_jitter_factor=0.1,
)

SLOW_NETWORK_PROFILE = TimingProfile(
    dns_resolution_range=(20, 100),
    tcp_connection_range=(50, 200),
    tls_handshake_range=(75, 300),
    request_processing_range=(10, 30),
    response_download_base=0.5,
    network_jitter_factor=0.3,
)

MOBILE_NETWORK_PROFILE = TimingProfile(
    dns_resolution_range=(30, 150),
    tcp_connection_range=(100, 400),
    tls_handshake_range=(150, 500),
    request_processing_range=(20, 50),
    response_download_base=0.8,
    network_jitter_factor=0.4,
)