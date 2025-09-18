"""
CloudflareScraper - Simple interface similar to cloudscraper

This module provides a simple, synchronous interface for bypassing Cloudflare protection,
designed as a drop-in replacement for cloudscraper.

Example usage:
    import cloudflare_research as cfr

    scraper = cfr.create_scraper()
    response = scraper.get("https://example.com")
    print(response.text)
"""

import asyncio
import threading
from typing import Optional, Dict, Any, Union
from .bypass import CloudflareBypass, CloudflareBypassConfig
from .models import RequestResult


class CloudflareScraper:
    """Synchronous scraper interface for Cloudflare bypass."""

    def __init__(self, config: Optional[CloudflareBypassConfig] = None):
        """Initialize the scraper with optional configuration."""
        self.config = config or CloudflareBypassConfig()
        self._bypass: Optional[CloudflareBypass] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_closed = False

        # Start event loop in background thread
        self._start_event_loop()

    def _start_event_loop(self):
        """Start the async event loop in a background thread."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        # Wait for loop to be ready
        while self._loop is None:
            threading.Event().wait(0.001)

    def _ensure_bypass(self):
        """Ensure the CloudflareBypass instance is initialized."""
        if self._bypass is None:
            future = asyncio.run_coroutine_threadsafe(
                CloudflareBypass(self.config).__aenter__(),
                self._loop
            )
            self._bypass = future.result(timeout=10)

    def get(self, url: str, **kwargs) -> 'ScrapeResponse':
        """Perform a GET request."""
        return self.request('GET', url, **kwargs)

    def post(self, url: str, data=None, json=None, **kwargs) -> 'ScrapeResponse':
        """Perform a POST request."""
        if data is not None:
            kwargs['data'] = data
        if json is not None:
            kwargs['json'] = json
        return self.request('POST', url, **kwargs)

    def put(self, url: str, data=None, **kwargs) -> 'ScrapeResponse':
        """Perform a PUT request."""
        if data is not None:
            kwargs['data'] = data
        return self.request('PUT', url, **kwargs)

    def delete(self, url: str, **kwargs) -> 'ScrapeResponse':
        """Perform a DELETE request."""
        return self.request('DELETE', url, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> 'ScrapeResponse':
        """Perform an HTTP request with Cloudflare bypass."""
        if self._is_closed:
            raise RuntimeError("Scraper has been closed")

        self._ensure_bypass()

        # Map common requests library parameters
        headers = kwargs.pop('headers', {})
        timeout = kwargs.pop('timeout', None)
        data = kwargs.pop('data', None)
        json_data = kwargs.pop('json', None)

        # Convert to CloudflareBypass parameters
        bypass_kwargs = {
            'headers': headers,
            **kwargs
        }

        if timeout:
            bypass_kwargs['timeout'] = timeout

        # Choose the right method based on HTTP method
        if method.upper() == 'GET':
            coro = self._bypass.get(url, **bypass_kwargs)
        elif method.upper() == 'POST':
            coro = self._bypass.post(url, data=data, json_data=json_data, **bypass_kwargs)
        elif method.upper() == 'PUT':
            coro = self._bypass.put(url, data=data, json_data=json_data, **bypass_kwargs)
        elif method.upper() == 'DELETE':
            coro = self._bypass.delete(url, **bypass_kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Execute the request asynchronously
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        try:
            result = future.result(timeout=timeout or self.config.timeout)
            return ScrapeResponse(result)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request to {url} timed out")

    def close(self):
        """Close the scraper and clean up resources."""
        if self._is_closed:
            return

        self._is_closed = True

        if self._bypass:
            future = asyncio.run_coroutine_threadsafe(
                self._bypass.__aexit__(None, None, None),
                self._loop
            )
            try:
                future.result(timeout=5)
            except:
                pass  # Best effort cleanup

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager protocol."""
        self.close()

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            self.close()
        except:
            pass  # Ignore errors during cleanup


class ScrapeResponse:
    """Response wrapper that mimics requests.Response interface."""

    def __init__(self, request_result: RequestResult):
        self._result = request_result

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._result.status_code

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return self._result.headers

    @property
    def text(self) -> str:
        """Response body as text."""
        return self._result.body

    @property
    def content(self) -> bytes:
        """Response body as bytes."""
        return self._result.body.encode('utf-8')

    @property
    def url(self) -> str:
        """Final URL after redirects."""
        return self._result.url

    @property
    def ok(self) -> bool:
        """True if status code is less than 400."""
        return 200 <= self.status_code < 400

    def json(self, **kwargs) -> Any:
        """Parse response body as JSON."""
        import json
        return json.loads(self.text, **kwargs)

    def raise_for_status(self):
        """Raise an exception for HTTP error status codes."""
        if not self.ok:
            raise Exception(f"HTTP {self.status_code} Error for url: {self.url}")

    def __repr__(self):
        return f"<ScrapeResponse [{self.status_code}]>"


def create_scraper(config: Optional[CloudflareBypassConfig] = None, **kwargs) -> CloudflareScraper:
    """
    Create a CloudflareScraper instance.

    This function mimics cloudscraper.create_scraper() for easy migration.

    Args:
        config: Optional CloudflareBypassConfig for advanced configuration
        **kwargs: Additional configuration options that will be passed to CloudflareBypassConfig

    Returns:
        CloudflareScraper instance ready for use

    Example:
        >>> import cloudflare_research as cfr
        >>> scraper = cfr.create_scraper()
        >>> response = scraper.get("https://example.com")
        >>> print(response.text)
    """
    if config is None:
        # Create config from kwargs for convenience
        config = CloudflareBypassConfig(**kwargs)

    return CloudflareScraper(config)


# Convenience functions for one-off requests
def get(url: str, **kwargs) -> ScrapeResponse:
    """Perform a GET request (convenience function)."""
    with create_scraper() as scraper:
        return scraper.get(url, **kwargs)


def post(url: str, data=None, json=None, **kwargs) -> ScrapeResponse:
    """Perform a POST request (convenience function)."""
    with create_scraper() as scraper:
        return scraper.post(url, data=data, json=json, **kwargs)


# Backward compatibility aliases
CloudScraper = CloudflareScraper  # Alternative name