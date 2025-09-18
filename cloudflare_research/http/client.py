"""Async HTTP client base class for browser emulation.

This module provides a high-level async HTTP client that combines
TLS fingerprinting, browser emulation, and challenge handling.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Union, List, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

from ..models import (
    TestRequest, RequestTiming, HttpMethod,
    BrowserConfig, ProxyConfig, RequestStatus
)
from ..tls import CurlCffiClient, TLSClientConfig, TLSResponse


@dataclass
class HTTPClientConfig:
    """Configuration for HTTP client behavior."""
    # Browser emulation
    browser_version: str = "124.0.0.0"
    user_agent: Optional[str] = None
    
    # Connection settings
    timeout: int = 30
    max_redirects: int = 10
    verify_ssl: bool = True
    
    # Proxy configuration
    proxy_url: Optional[str] = None
    
    # Rate limiting
    requests_per_second: float = 10.0
    burst_limit: int = 50
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    
    # Challenge handling
    handle_challenges: bool = True
    challenge_timeout: int = 30
    
    # HTTP version preference
    prefer_http2: bool = True


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class RateLimitExceeded(HTTPClientError):
    """Exception raised when rate limit is exceeded."""
    pass


class ChallengeError(HTTPClientError):
    """Exception raised when challenge handling fails."""
    pass


class AsyncHTTPClient(ABC):
    """
    Abstract base class for async HTTP clients.
    
    Defines the interface that all HTTP client implementations must follow
    for browser emulation and challenge handling.
    """

    @abstractmethod
    async def get(self, url: str, **kwargs) -> 'HTTPResponse':
        """Perform GET request."""
        pass

    @abstractmethod
    async def post(self, url: str, **kwargs) -> 'HTTPResponse':
        """Perform POST request."""
        pass

    @abstractmethod
    async def request(self, method: str, url: str, **kwargs) -> 'HTTPResponse':
        """Perform HTTP request with specified method."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close client and cleanup resources."""
        pass


class BrowserHTTPClient(AsyncHTTPClient):
    """
    High-level HTTP client for browser emulation.
    
    Combines TLS fingerprinting, rate limiting, retry logic,
    and challenge handling into a single interface.
    """

    def __init__(self, config: Optional[HTTPClientConfig] = None):
        self.config = config or HTTPClientConfig()
        self._tls_client: Optional[CurlCffiClient] = None
        self._closed = False
        
        # Rate limiting
        self._request_times: List[float] = []
        self._request_semaphore = asyncio.Semaphore(self.config.burst_limit)
        
        # Session management
        self._cookies: Dict[str, str] = {}
        self._session_headers: Dict[str, str] = {}
        
        # Challenge handling
        self._challenge_handler: Optional[Callable] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _initialize(self) -> None:
        """Initialize the HTTP client."""
        if self._tls_client is not None:
            return

        # Create TLS client configuration
        tls_config = TLSClientConfig(
            chrome_version=self.config.browser_version,
            verify_ssl=self.config.verify_ssl,
            follow_redirects=True,
            max_redirects=self.config.max_redirects,
            timeout=self.config.timeout,
            proxy_url=self.config.proxy_url,
            http2=self.config.prefer_http2,
        )

        # Initialize TLS client
        self._tls_client = CurlCffiClient(tls_config)
        await self._tls_client._initialize_session()

        # Set up default headers
        self._setup_default_headers()

    def _setup_default_headers(self) -> None:
        """Setup default headers for browser emulation."""
        chrome_version = self.config.browser_version.split('.')[0]
        
        self._session_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-CH-UA": f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}", "Not-A.Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        if self.config.user_agent:
            self._session_headers["User-Agent"] = self.config.user_agent

    async def get(self, url: str, **kwargs) -> 'HTTPResponse':
        """Perform GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, data: Optional[Any] = None,
                  json: Optional[Any] = None, **kwargs) -> 'HTTPResponse':
        """Perform POST request."""
        if json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, data: Optional[Any] = None,
                 json: Optional[Any] = None, **kwargs) -> 'HTTPResponse':
        """Perform PUT request."""
        if json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> 'HTTPResponse':
        """Perform DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, data: Optional[Any] = None,
                   json: Optional[Any] = None, **kwargs) -> 'HTTPResponse':
        """Perform PATCH request."""
        if json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        return await self.request("PATCH", url, **kwargs)

    async def head(self, url: str, **kwargs) -> 'HTTPResponse':
        """Perform HEAD request."""
        return await self.request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> 'HTTPResponse':
        """Perform OPTIONS request."""
        return await self.request("OPTIONS", url, **kwargs)

    async def request(self, method: str, url: str, **kwargs) -> 'HTTPResponse':
        """Perform HTTP request with browser emulation."""
        if self._closed:
            raise HTTPClientError("Client has been closed")

        if not self._tls_client:
            await self._initialize()

        # Apply rate limiting
        await self._apply_rate_limit()

        # Prepare request
        start_time = time.perf_counter()
        timing = RequestTiming()
        
        # Merge headers
        headers = self._session_headers.copy()
        headers.update(kwargs.pop("headers", {}))
        
        # Add cookies
        if self._cookies:
            cookie_header = "; ".join([f"{k}={v}" for k, v in self._cookies.items()])
            headers["Cookie"] = cookie_header

        # Perform request with retry logic
        response = await self._request_with_retry(
            method, url, headers=headers, timing=timing, **kwargs
        )

        # Update session state
        self._update_cookies(response)
        
        # Handle challenges if enabled
        if self.config.handle_challenges and self._is_challenge_response(response):
            response = await self._handle_challenge(response, method, url, headers, **kwargs)

        return HTTPResponse(response, timing)

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting to requests."""
        async with self._request_semaphore:
            current_time = time.time()
            
            # Clean old request times
            cutoff_time = current_time - 1.0  # Last second
            self._request_times = [t for t in self._request_times if t > cutoff_time]
            
            # Check rate limit
            if len(self._request_times) >= self.config.requests_per_second:
                sleep_time = 1.0 / self.config.requests_per_second
                await asyncio.sleep(sleep_time)
            
            self._request_times.append(current_time)

    async def _request_with_retry(self, method: str, url: str,
                                 timing: RequestTiming, **kwargs) -> TLSResponse:
        """Perform request with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Record timing
                request_start = time.perf_counter()
                
                # Make request
                response = await self._tls_client._request(method, url, **kwargs)
                
                request_end = time.perf_counter()
                timing.total_duration_ms = int((request_end - request_start) * 1000)
                
                return response
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    # Calculate backoff delay
                    delay = self.config.retry_delay * (self.config.backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                else:
                    break
        
        raise HTTPClientError(f"Request failed after {self.config.max_retries + 1} attempts") from last_exception

    def _update_cookies(self, response: TLSResponse) -> None:
        """Update session cookies from response."""
        # Extract cookies from Set-Cookie headers
        set_cookie_headers = response.headers.get("Set-Cookie", "")
        if set_cookie_headers:
            # Simplified cookie parsing - real implementation would be more robust
            for cookie in set_cookie_headers.split(","):
                if "=" in cookie:
                    name, value = cookie.split("=", 1)
                    name = name.strip()
                    value = value.split(";")[0].strip()
                    self._cookies[name] = value

    def _is_challenge_response(self, response: TLSResponse) -> bool:
        """Check if response contains a Cloudflare challenge."""
        # Check status codes that might indicate challenges
        if response.status_code not in [403, 503, 429]:
            return False
        
        # Check for Cloudflare server header
        server_header = response.headers.get("server", "").lower()
        if "cloudflare" not in server_header:
            return False
        
        # Check response body for challenge indicators
        body = response.text.lower()
        challenge_indicators = [
            "challenge", "checking your browser", "cf_chl_opt",
            "turnstile", "cf-turnstile", "ray id"
        ]
        
        return any(indicator in body for indicator in challenge_indicators)

    async def _handle_challenge(self, response: TLSResponse, method: str,
                              url: str, headers: Dict[str, str], **kwargs) -> TLSResponse:
        """Handle Cloudflare challenge."""
        if not self._challenge_handler:
            raise ChallengeError("Challenge detected but no handler configured")
        
        try:
            # Use configured challenge handler
            solved_response = await self._challenge_handler(
                response, method, url, headers, **kwargs
            )
            return solved_response
        except Exception as e:
            raise ChallengeError(f"Challenge handling failed: {str(e)}") from e

    def set_challenge_handler(self, handler: Callable) -> None:
        """Set custom challenge handler function."""
        self._challenge_handler = handler

    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update session headers."""
        self._session_headers.update(headers)

    def get_cookies(self) -> Dict[str, str]:
        """Get current session cookies."""
        return self._cookies.copy()

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Set session cookies."""
        self._cookies.update(cookies)

    def clear_cookies(self) -> None:
        """Clear all session cookies."""
        self._cookies.clear()

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._tls_client and not self._closed:
            await self._tls_client.close()
            self._closed = True

    def get_client_info(self) -> Dict[str, Any]:
        """Get information about client configuration."""
        return {
            "browser_version": self.config.browser_version,
            "user_agent": self.config.user_agent,
            "timeout": self.config.timeout,
            "max_redirects": self.config.max_redirects,
            "verify_ssl": self.config.verify_ssl,
            "proxy_url": self.config.proxy_url,
            "rate_limit": self.config.requests_per_second,
            "handle_challenges": self.config.handle_challenges,
            "prefer_http2": self.config.prefer_http2,
            "cookies_count": len(self._cookies),
            "tls_info": self._tls_client.get_client_info() if self._tls_client else None,
        }


class HTTPResponse:
    """
    Wrapper for HTTP responses with timing and browser emulation info.
    
    Provides a unified interface for response data regardless of the
    underlying HTTP client implementation.
    """

    def __init__(self, tls_response: TLSResponse, timing: RequestTiming):
        self._response = tls_response
        self._timing = timing

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._response.status_code

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return self._response.headers

    @property
    def text(self) -> str:
        """Response text content."""
        return self._response.text

    @property
    def content(self) -> bytes:
        """Response binary content."""
        return self._response.content

    @property
    def url(self) -> str:
        """Final response URL."""
        return self._response.url

    @property
    def elapsed(self) -> float:
        """Request elapsed time in seconds."""
        return self._response.elapsed

    @property
    def cookies(self) -> Dict[str, str]:
        """Response cookies."""
        return self._response.cookies

    @property
    def timing(self) -> RequestTiming:
        """Detailed timing information."""
        return self._timing

    @property
    def ok(self) -> bool:
        """True if status indicates success."""
        return self._response.ok

    @property
    def is_redirect(self) -> bool:
        """True if status indicates redirect."""
        return self._response.is_redirect

    def json(self) -> Any:
        """Parse response as JSON."""
        return self._response.json()

    def raise_for_status(self) -> None:
        """Raise exception for HTTP errors."""
        self._response.raise_for_status()

    def get_tls_info(self) -> Dict[str, Any]:
        """Get TLS connection information."""
        return self._response.tls_info

    def __repr__(self) -> str:
        """String representation."""
        return f"<HTTPResponse [{self.status_code}] {self.url}>"


# Utility functions
async def create_http_client(browser_version: str = "124.0.0.0",
                           proxy_url: Optional[str] = None,
                           handle_challenges: bool = True) -> BrowserHTTPClient:
    """Create and initialize an HTTP client."""
    config = HTTPClientConfig(
        browser_version=browser_version,
        proxy_url=proxy_url,
        handle_challenges=handle_challenges,
    )
    
    client = BrowserHTTPClient(config)
    await client._initialize()
    return client