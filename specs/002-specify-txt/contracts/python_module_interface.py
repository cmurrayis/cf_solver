"""
Python Module Interface Contract for Cloudflare Research Bypass

This file defines the public interface contracts for the cloudflare_research module.
These interfaces must be implemented to satisfy the functional requirements.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union, AsyncIterator
import asyncio
from datetime import datetime


class ChallengeType(Enum):
    """Types of challenges that can be encountered"""
    JAVASCRIPT = "javascript"
    TURNSTILE = "turnstile"
    MANAGED = "managed"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


class SessionStatus(Enum):
    """Test session status values"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class ProxyConfig:
    """Proxy configuration for requests"""
    type: str  # http, https, socks4, socks5
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class BrowserConfig:
    """Browser emulation configuration"""
    version: str = "124.0.0.0"
    user_agent: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    timezone: str = "America/New_York"
    language: str = "en-US"
    platform: str = "Windows"


@dataclass
class RequestConfig:
    """Configuration for a single request"""
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Union[str, bytes, Dict]] = None
    timeout: int = 30
    proxy: Optional[ProxyConfig] = None
    browser_config: Optional[BrowserConfig] = None


@dataclass
class RequestTiming:
    """Timing information for a request"""
    dns_resolution_ms: int
    tcp_connection_ms: int
    tls_handshake_ms: int
    request_sent_ms: int
    response_received_ms: int
    total_duration_ms: int


@dataclass
class Challenge:
    """Information about a detected challenge"""
    challenge_id: str
    request_id: str
    type: ChallengeType
    url: str
    solved: bool
    solve_duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    detected_at: datetime = None
    solved_at: Optional[datetime] = None


@dataclass
class Response:
    """HTTP response with metadata"""
    request_id: str
    url: str
    status_code: int
    headers: Dict[str, str]
    body: Union[str, bytes]
    timing: RequestTiming
    challenge: Optional[Challenge] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class SessionMetrics:
    """Performance metrics for a test session"""
    session_id: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    min_response_time_ms: int
    max_response_time_ms: int
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    concurrent_connections_peak: int
    memory_usage_mb: float
    cpu_usage_percent: float
    challenges_total: int
    challenges_solved: int
    challenge_solve_rate: float


@dataclass
class SessionConfig:
    """Configuration for a test session"""
    name: Optional[str] = None
    description: Optional[str] = None
    max_concurrent: int = 100
    rate_limit: Optional[float] = None
    default_timeout: int = 30
    browser_config: Optional[BrowserConfig] = None


class IChallengeDetector(ABC):
    """Interface for detecting different types of challenges"""

    @abstractmethod
    async def detect_challenge(self, response: Response) -> Optional[ChallengeType]:
        """
        Detect if response contains a challenge

        Args:
            response: HTTP response to analyze

        Returns:
            ChallengeType if challenge detected, None otherwise
        """
        pass

    @abstractmethod
    async def extract_challenge_data(self, response: Response) -> Dict[str, Any]:
        """
        Extract challenge-specific data from response

        Args:
            response: HTTP response containing challenge

        Returns:
            Dictionary containing challenge data
        """
        pass


class IChallengeSolver(ABC):
    """Interface for solving challenges"""

    @abstractmethod
    async def solve_challenge(self, challenge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve a detected challenge

        Args:
            challenge_data: Challenge data from detector

        Returns:
            Solution data including cookies and tokens
        """
        pass

    @abstractmethod
    def supports_challenge_type(self, challenge_type: ChallengeType) -> bool:
        """
        Check if solver supports given challenge type

        Args:
            challenge_type: Type of challenge to solve

        Returns:
            True if supported, False otherwise
        """
        pass


class IBrowserEmulator(ABC):
    """Interface for browser behavior emulation"""

    @abstractmethod
    def get_chrome_headers(self, url: str) -> Dict[str, str]:
        """
        Generate Chrome-like headers for URL

        Args:
            url: Target URL for request

        Returns:
            Dictionary of HTTP headers
        """
        pass

    @abstractmethod
    def get_tls_config(self) -> Dict[str, Any]:
        """
        Get TLS configuration for Chrome emulation

        Returns:
            TLS configuration parameters
        """
        pass

    @abstractmethod
    async def emulate_timing(self) -> None:
        """Add realistic timing delays between requests"""
        pass


class IPerformanceMonitor(ABC):
    """Interface for performance monitoring"""

    @abstractmethod
    async def record_request_timing(self, request_id: str, timing: RequestTiming) -> None:
        """Record timing data for a request"""
        pass

    @abstractmethod
    async def record_resource_usage(self, memory_mb: float, cpu_percent: float) -> None:
        """Record current resource usage"""
        pass

    @abstractmethod
    async def get_session_metrics(self, session_id: str) -> SessionMetrics:
        """Get aggregated metrics for a session"""
        pass


class CloudflareBypass:
    """
    Main interface for the Cloudflare research bypass module

    This class provides the primary API for conducting browser emulation
    research against Cloudflare-protected infrastructure.
    """

    def __init__(self,
                 max_concurrent: int = 1000,
                 session_config: Optional[SessionConfig] = None):
        """
        Initialize the bypass client

        Args:
            max_concurrent: Maximum concurrent requests (1-10000)
            session_config: Optional session configuration
        """
        pass

    async def get(self, url: str, **kwargs) -> Response:
        """
        Execute GET request with full browser emulation

        Args:
            url: Target URL
            **kwargs: Additional request configuration

        Returns:
            Response object with timing and challenge data

        Raises:
            ValueError: Invalid URL or configuration
            TimeoutError: Request timed out
            ConnectionError: Network connection failed
        """
        pass

    async def post(self, url: str, data: Optional[Any] = None, **kwargs) -> Response:
        """
        Execute POST request with full browser emulation

        Args:
            url: Target URL
            data: Request body data
            **kwargs: Additional request configuration

        Returns:
            Response object with timing and challenge data
        """
        pass

    async def put(self, url: str, data: Optional[Any] = None, **kwargs) -> Response:
        """Execute PUT request with full browser emulation"""
        pass

    async def delete(self, url: str, **kwargs) -> Response:
        """Execute DELETE request with full browser emulation"""
        pass

    async def batch_request(self, requests: List[RequestConfig]) -> List[Response]:
        """
        Execute multiple requests concurrently

        Args:
            requests: List of request configurations (max 10,000)

        Returns:
            List of Response objects in same order as input

        Raises:
            ValueError: Too many requests or invalid configuration
            ResourceExhaustedError: System resource limits reached
        """
        pass

    async def stream_requests(self,
                            requests: List[RequestConfig]) -> AsyncIterator[Response]:
        """
        Stream request results as they complete

        Args:
            requests: List of request configurations

        Yields:
            Response objects as they complete
        """
        pass

    async def create_session(self, config: SessionConfig) -> str:
        """
        Create a new test session

        Args:
            config: Session configuration

        Returns:
            Session ID string
        """
        pass

    async def get_session_metrics(self, session_id: str) -> SessionMetrics:
        """
        Get performance metrics for a session

        Args:
            session_id: Session identifier

        Returns:
            SessionMetrics object with performance data
        """
        pass

    async def export_session_data(self,
                                 session_id: str,
                                 format: str = "json") -> str:
        """
        Export session data for analysis

        Args:
            session_id: Session identifier
            format: Export format ("json" or "csv")

        Returns:
            Serialized session data
        """
        pass

    async def close(self) -> None:
        """
        Close the bypass client and cleanup resources

        This method should be called to properly cleanup connections
        and resources when done with the client.
        """
        pass

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Type aliases for common patterns
RequestList = List[RequestConfig]
ResponseList = List[Response]
HeaderDict = Dict[str, str]
MetricsDict = Dict[str, Union[int, float, str]]

# Module-level convenience functions
async def get(url: str, **kwargs) -> Response:
    """
    Convenience function for single GET request

    Args:
        url: Target URL
        **kwargs: Request configuration options

    Returns:
        Response object
    """
    async with CloudflareBypass() as client:
        return await client.get(url, **kwargs)


async def post(url: str, data: Optional[Any] = None, **kwargs) -> Response:
    """
    Convenience function for single POST request

    Args:
        url: Target URL
        data: Request body data
        **kwargs: Request configuration options

    Returns:
        Response object
    """
    async with CloudflareBypass() as client:
        return await client.post(url, data=data, **kwargs)


async def batch_get(urls: List[str], **kwargs) -> List[Response]:
    """
    Convenience function for batch GET requests

    Args:
        urls: List of URLs to request
        **kwargs: Common request configuration

    Returns:
        List of Response objects
    """
    requests = [RequestConfig(url=url, **kwargs) for url in urls]
    async with CloudflareBypass() as client:
        return await client.batch_request(requests)


# Example usage patterns
if __name__ == "__main__":
    async def example_usage():
        """Example usage of the cloudflare_research module"""

        # Single request
        response = await get("https://example.com")
        print(f"Status: {response.status_code}")

        # Batch requests
        urls = [f"https://example.com/page/{i}" for i in range(100)]
        responses = await batch_get(urls)

        # Advanced usage with session
        async with CloudflareBypass(max_concurrent=500) as client:
            # Configure session
            session_id = await client.create_session(
                SessionConfig(name="Load Test", max_concurrent=100)
            )

            # Execute requests
            requests = [RequestConfig(url=url) for url in urls]
            results = await client.batch_request(requests)

            # Get metrics
            metrics = await client.get_session_metrics(session_id)
            print(f"Success rate: {metrics.challenge_solve_rate}%")

            # Export data
            data = await client.export_session_data(session_id, format="json")

    # Run example
    asyncio.run(example_usage())