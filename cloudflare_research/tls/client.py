"""curl_cffi client integration for TLS fingerprinting.

This module provides integration with curl_cffi library to enable
advanced TLS fingerprinting and HTTP/2 support with Chrome emulation.
"""

import asyncio
import ssl
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

try:
    import curl_cffi
    from curl_cffi.requests import AsyncSession, Response
    CURL_CFFI_AVAILABLE = True
except ImportError:
    # Fallback for when curl_cffi is not available
    CURL_CFFI_AVAILABLE = False
    AsyncSession = None
    Response = None

from .fingerprint import ChromeTLSFingerprintManager, TLSFingerprint, ChromeVersion


@dataclass
class TLSClientConfig:
    """Configuration for TLS client behavior."""
    chrome_version: str = "124.0.0.0"
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_redirects: int = 10
    timeout: int = 30
    proxy_url: Optional[str] = None
    impersonate: str = "chrome124"  # curl_cffi impersonation target
    ja3_fingerprint: Optional[str] = None
    http2: bool = True


class TLSClientError(Exception):
    """Custom exception for TLS client errors."""
    pass


class CurlCffiClient:
    """
    Advanced HTTP client using curl_cffi for TLS fingerprinting.

    This client provides Chrome-accurate TLS fingerprinting and HTTP/2 support
    through the curl_cffi library, which uses libcurl with Chrome's BoringSSL.
    """

    def __init__(self, config: Optional[TLSClientConfig] = None):
        if not CURL_CFFI_AVAILABLE:
            raise TLSClientError(
                "curl_cffi is not available. Install with: pip install curl_cffi"
            )

        self.config = config or TLSClientConfig()
        self.fingerprint_manager = ChromeTLSFingerprintManager()
        self._session: Optional[AsyncSession] = None
        self._closed = False

        # Get TLS fingerprint for the specified Chrome version
        try:
            chrome_version = ChromeVersion(self.config.chrome_version)
            self.tls_fingerprint = self.fingerprint_manager.get_fingerprint(chrome_version)
        except ValueError:
            # Fallback to latest supported version
            self.tls_fingerprint = self.fingerprint_manager.get_fingerprint(ChromeVersion.CHROME_124)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _initialize_session(self) -> None:
        """Initialize the curl_cffi async session."""
        if self._session is not None:
            return

        # Configure session parameters
        session_kwargs = {
            "impersonate": self.config.impersonate,
            "verify": self.config.verify_ssl,
            "timeout": self.config.timeout,
        }

        # Add proxy if configured
        if self.config.proxy_url:
            session_kwargs["proxies"] = {"http": self.config.proxy_url, "https": self.config.proxy_url}

        # Create session
        self._session = AsyncSession(**session_kwargs)

        # Configure additional curl options
        await self._configure_curl_options()

    async def _configure_curl_options(self) -> None:
        """Configure advanced curl options for fingerprinting."""
        if not self._session:
            return

        # Access the underlying curl handle for advanced configuration
        # Note: This is a simplified approach - real implementation would
        # use curl_cffi's lower-level APIs for precise control

        # HTTP/2 configuration
        if self.config.http2:
            # curl_cffi handles HTTP/2 automatically with Chrome impersonation
            pass

        # Additional headers to match Chrome exactly
        chrome_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-CH-UA": f'"Chromium";v="{self.config.chrome_version.split(".")[0]}", "Google Chrome";v="{self.config.chrome_version.split(".")[0]}", "Not-A.Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.tls_fingerprint.user_agent,
        }

        # Update session headers
        self._session.headers.update(chrome_headers)

    async def get(self, url: str, **kwargs) -> 'TLSResponse':
        """Perform GET request with TLS fingerprinting."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, data: Optional[Any] = None,
                  json: Optional[Any] = None, **kwargs) -> 'TLSResponse':
        """Perform POST request with TLS fingerprinting."""
        if json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, data: Optional[Any] = None,
                 json: Optional[Any] = None, **kwargs) -> 'TLSResponse':
        """Perform PUT request with TLS fingerprinting."""
        if json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        return await self._request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> 'TLSResponse':
        """Perform DELETE request with TLS fingerprinting."""
        return await self._request("DELETE", url, **kwargs)

    async def patch(self, url: str, data: Optional[Any] = None,
                   json: Optional[Any] = None, **kwargs) -> 'TLSResponse':
        """Perform PATCH request with TLS fingerprinting."""
        if json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        return await self._request("PATCH", url, **kwargs)

    async def head(self, url: str, **kwargs) -> 'TLSResponse':
        """Perform HEAD request with TLS fingerprinting."""
        return await self._request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> 'TLSResponse':
        """Perform OPTIONS request with TLS fingerprinting."""
        return await self._request("OPTIONS", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> 'TLSResponse':
        """Internal method to perform HTTP requests."""
        if self._closed:
            raise TLSClientError("Client has been closed")

        if not self._session:
            await self._initialize_session()

        try:
            # Extract custom headers
            headers = kwargs.pop("headers", {})

            # Merge with default headers
            request_headers = self._session.headers.copy()
            request_headers.update(headers)

            # Update headers for specific request types
            if method in ["POST", "PUT", "PATCH"]:
                if "json" in kwargs and "Content-Type" not in request_headers:
                    request_headers["Content-Type"] = "application/json"
                elif "data" in kwargs and "Content-Type" not in request_headers:
                    request_headers["Content-Type"] = "application/x-www-form-urlencoded"

            # Add Referer header if not present
            if "Referer" not in request_headers:
                parsed_url = urlparse(url)
                request_headers["Referer"] = f"{parsed_url.scheme}://{parsed_url.netloc}/"

            # Perform the request
            response = await self._session.request(
                method=method,
                url=url,
                headers=request_headers,
                **kwargs
            )

            return TLSResponse(response, self.tls_fingerprint)

        except Exception as e:
            raise TLSClientError(f"Request failed: {str(e)}") from e

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._session and not self._closed:
            await self._session.close()
            self._closed = True

    def get_ja3_fingerprint(self) -> str:
        """Get the JA3 fingerprint being used by this client."""
        return self.fingerprint_manager.get_ja3_fingerprint(self.tls_fingerprint)

    def get_client_info(self) -> Dict[str, Any]:
        """Get information about the client configuration."""
        return {
            "chrome_version": self.config.chrome_version,
            "impersonate": self.config.impersonate,
            "http2_enabled": self.config.http2,
            "tls_fingerprint": self.fingerprint_manager.get_fingerprint_info(self.tls_fingerprint),
            "ja3_fingerprint": self.get_ja3_fingerprint(),
            "user_agent": self.tls_fingerprint.user_agent,
        }


class TLSResponse:
    """
    Wrapper for HTTP responses with TLS information.

    Provides access to response data along with TLS handshake details
    and fingerprinting information.
    """

    def __init__(self, response: Response, tls_fingerprint: TLSFingerprint):
        self._response = response
        self._tls_fingerprint = tls_fingerprint

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._response.status_code

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return dict(self._response.headers)

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
        """Final response URL (after redirects)."""
        return str(self._response.url)

    @property
    def elapsed(self) -> float:
        """Request elapsed time in seconds."""
        return self._response.elapsed.total_seconds()

    @property
    def cookies(self) -> Dict[str, str]:
        """Response cookies."""
        return dict(self._response.cookies)

    @property
    def encoding(self) -> Optional[str]:
        """Response encoding."""
        return self._response.encoding

    @property
    def reason(self) -> str:
        """HTTP status reason phrase."""
        return self._response.reason

    def json(self) -> Any:
        """Parse response as JSON."""
        return self._response.json()

    def raise_for_status(self) -> None:
        """Raise exception for HTTP error status codes."""
        self._response.raise_for_status()

    @property
    def ok(self) -> bool:
        """True if status code indicates success."""
        return self._response.ok

    @property
    def is_redirect(self) -> bool:
        """True if status code indicates redirect."""
        return 300 <= self.status_code < 400

    @property
    def tls_info(self) -> Dict[str, Any]:
        """Get TLS connection information."""
        return {
            "chrome_version": self._tls_fingerprint.browser_version.value,
            "tls_version": f"{self._tls_fingerprint.min_tls_version.value} - {self._tls_fingerprint.max_tls_version.value}",
            "cipher_suites_count": len(self._tls_fingerprint.cipher_suites),
            "alpn_protocols": self._tls_fingerprint.alpn_protocols,
            "http2_used": "h2" in self.headers.get("alt-svc", "").lower(),
        }

    def get_timing_info(self) -> Dict[str, float]:
        """Get detailed timing information."""
        return {
            "total_time": self.elapsed,
            # Note: curl_cffi doesn't expose detailed timing by default
            # Real implementation would extract from curl's timing info
            "dns_lookup": 0.0,
            "tcp_connect": 0.0,
            "tls_handshake": 0.0,
            "request_sent": 0.0,
            "response_received": self.elapsed,
        }

    def __repr__(self) -> str:
        """String representation of the response."""
        return f"<TLSResponse [{self.status_code}] {self.url}>"


# Utility functions for TLS client management
async def create_tls_client(chrome_version: str = "124.0.0.0",
                           proxy_url: Optional[str] = None,
                           verify_ssl: bool = True) -> CurlCffiClient:
    """Create and initialize a TLS client with specified configuration."""
    config = TLSClientConfig(
        chrome_version=chrome_version,
        proxy_url=proxy_url,
        verify_ssl=verify_ssl,
    )

    client = CurlCffiClient(config)
    await client._initialize_session()
    return client


def get_supported_chrome_versions() -> List[str]:
    """Get list of supported Chrome versions for TLS fingerprinting."""
    manager = ChromeTLSFingerprintManager()
    return manager.get_supported_versions()


def validate_chrome_version(version: str) -> bool:
    """Validate if a Chrome version is supported for TLS fingerprinting."""
    supported_versions = get_supported_chrome_versions()
    return version in supported_versions