"""Response wrapper and processing utilities.

Provides enhanced response handling with timing, caching, and content processing.
"""

import json
import gzip
import time
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from ..models import RequestTiming


@dataclass
class ResponseMetadata:
    """Metadata about the HTTP response."""
    request_url: str
    final_url: str
    redirect_count: int
    content_encoding: Optional[str]
    content_type: Optional[str]
    content_length: Optional[int]
    server: Optional[str]
    cloudflare_ray: Optional[str]
    cache_control: Optional[str]
    etag: Optional[str]
    last_modified: Optional[str]


class EnhancedResponse:
    """
    Enhanced response wrapper with additional processing capabilities.
    
    Provides content decoding, caching, and analysis features
    beyond basic HTTP response functionality.
    """

    def __init__(self, status_code: int, headers: Dict[str, str],
                 content: bytes, url: str, timing: RequestTiming):
        self._status_code = status_code
        self._headers = headers
        self._content = content
        self._url = url
        self._timing = timing
        self._text: Optional[str] = None
        self._json_data: Optional[Any] = None
        self._metadata: Optional[ResponseMetadata] = None

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._status_code

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return self._headers

    @property
    def content(self) -> bytes:
        """Raw response content."""
        return self._content

    @property
    def url(self) -> str:
        """Response URL."""
        return self._url

    @property
    def timing(self) -> RequestTiming:
        """Request timing information."""
        return self._timing

    @property
    def text(self) -> str:
        """Decoded text content."""
        if self._text is None:
            self._text = self._decode_content()
        return self._text

    @property
    def metadata(self) -> ResponseMetadata:
        """Response metadata."""
        if self._metadata is None:
            self._metadata = self._extract_metadata()
        return self._metadata

    @property
    def ok(self) -> bool:
        """True if status indicates success."""
        return 200 <= self._status_code < 400

    @property
    def is_redirect(self) -> bool:
        """True if status indicates redirect."""
        return 300 <= self._status_code < 400

    @property
    def is_client_error(self) -> bool:
        """True if status indicates client error."""
        return 400 <= self._status_code < 500

    @property
    def is_server_error(self) -> bool:
        """True if status indicates server error."""
        return 500 <= self._status_code < 600

    @property
    def encoding(self) -> Optional[str]:
        """Content encoding from headers."""
        content_type = self._headers.get("content-type", "")
        if "charset=" in content_type:
            return content_type.split("charset=")[1].split(";")[0].strip()
        return None

    def _decode_content(self) -> str:
        """Decode response content to text."""
        content = self._content
        
        # Handle content encoding
        encoding = self._headers.get("content-encoding", "").lower()
        if encoding == "gzip":
            try:
                content = gzip.decompress(content)
            except Exception:
                pass  # Use original content if decompression fails
        elif encoding == "deflate":
            try:
                import zlib
                content = zlib.decompress(content)
            except Exception:
                pass
        
        # Decode to text
        text_encoding = self.encoding or "utf-8"
        try:
            return content.decode(text_encoding)
        except UnicodeDecodeError:
            # Fallback encodings
            for fallback in ["latin-1", "ascii", "utf-8"]:
                try:
                    return content.decode(fallback, errors="ignore")
                except UnicodeDecodeError:
                    continue
            return content.decode("utf-8", errors="replace")

    def _extract_metadata(self) -> ResponseMetadata:
        """Extract metadata from headers."""
        return ResponseMetadata(
            request_url=self._url,  # Would be set from original request
            final_url=self._url,
            redirect_count=0,  # Would be tracked during request
            content_encoding=self._headers.get("content-encoding"),
            content_type=self._headers.get("content-type"),
            content_length=int(self._headers.get("content-length", 0)) or None,
            server=self._headers.get("server"),
            cloudflare_ray=self._headers.get("cf-ray"),
            cache_control=self._headers.get("cache-control"),
            etag=self._headers.get("etag"),
            last_modified=self._headers.get("last-modified"),
        )

    def json(self, **kwargs) -> Any:
        """Parse response as JSON."""
        if self._json_data is None:
            try:
                self._json_data = json.loads(self.text, **kwargs)
            except json.JSONDecodeError as e:
                raise ValueError(f"Response is not valid JSON: {e}")
        return self._json_data

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get header value (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self._headers.items():
            if key.lower() == name_lower:
                return value
        return default

    def has_header(self, name: str) -> bool:
        """Check if header exists (case-insensitive)."""
        return self.get_header(name) is not None

    def get_cookies(self) -> Dict[str, str]:
        """Extract cookies from Set-Cookie headers."""
        cookies = {}
        set_cookie = self.get_header("set-cookie")
        if set_cookie:
            # Simple cookie parsing - real implementation would be more robust
            for cookie_str in set_cookie.split(","):
                if "=" in cookie_str:
                    name, value = cookie_str.split("=", 1)
                    name = name.strip()
                    value = value.split(";")[0].strip()
                    cookies[name] = value
        return cookies

    def is_html(self) -> bool:
        """Check if response is HTML content."""
        content_type = self.get_header("content-type", "").lower()
        return "text/html" in content_type

    def is_json(self) -> bool:
        """Check if response is JSON content."""
        content_type = self.get_header("content-type", "").lower()
        return any(json_type in content_type for json_type in [
            "application/json", "text/json", "application/javascript"
        ])

    def is_xml(self) -> bool:
        """Check if response is XML content."""
        content_type = self.get_header("content-type", "").lower()
        return any(xml_type in content_type for xml_type in [
            "application/xml", "text/xml", "application/xhtml+xml"
        ])

    def is_text(self) -> bool:
        """Check if response is text content."""
        content_type = self.get_header("content-type", "").lower()
        return content_type.startswith("text/")

    def contains_cloudflare_challenge(self) -> bool:
        """Check if response contains Cloudflare challenge."""
        if not self.is_html():
            return False
        
        text_lower = self.text.lower()
        challenge_indicators = [
            "challenge", "checking your browser", "cf_chl_opt",
            "turnstile", "cf-turnstile", "ray id", "cloudflare"
        ]
        
        return any(indicator in text_lower for indicator in challenge_indicators)

    def get_cloudflare_ray_id(self) -> Optional[str]:
        """Extract Cloudflare Ray ID from headers or content."""
        # Check headers first
        ray_id = self.get_header("cf-ray")
        if ray_id:
            return ray_id
        
        # Check content for Ray ID
        import re
        ray_pattern = r"Ray ID: ([a-f0-9]+)"
        match = re.search(ray_pattern, self.text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the response."""
        return {
            "status_code": self.status_code,
            "content_length": len(self.content),
            "text_length": len(self.text),
            "timing": {
                "total_duration_ms": self.timing.total_duration_ms,
                "dns_resolution_ms": self.timing.dns_resolution_ms,
                "tcp_connection_ms": self.timing.tcp_connection_ms,
                "tls_handshake_ms": self.timing.tls_handshake_ms,
                "request_sent_ms": self.timing.request_sent_ms,
                "response_received_ms": self.timing.response_received_ms,
            },
            "content_type": self.metadata.content_type,
            "server": self.metadata.server,
            "cloudflare_ray": self.metadata.cloudflare_ray,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "url": self.url,
            "content_length": len(self.content),
            "text_length": len(self.text),
            "timing": {
                "total_duration_ms": self.timing.total_duration_ms,
                "dns_resolution_ms": self.timing.dns_resolution_ms,
                "tcp_connection_ms": self.timing.tcp_connection_ms,
                "tls_handshake_ms": self.timing.tls_handshake_ms,
                "request_sent_ms": self.timing.request_sent_ms,
                "response_received_ms": self.timing.response_received_ms,
            },
            "metadata": {
                "content_type": self.metadata.content_type,
                "content_encoding": self.metadata.content_encoding,
                "server": self.metadata.server,
                "cloudflare_ray": self.metadata.cloudflare_ray,
            },
            "is_html": self.is_html(),
            "is_json": self.is_json(),
            "is_challenge": self.contains_cloudflare_challenge(),
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<EnhancedResponse [{self.status_code}] {self.url}>"


# Utility functions for response processing
def create_response_from_tls(tls_response, timing: RequestTiming) -> EnhancedResponse:
    """Create enhanced response from TLS response."""
    return EnhancedResponse(
        status_code=tls_response.status_code,
        headers=tls_response.headers,
        content=tls_response.content,
        url=tls_response.url,
        timing=timing,
    )


def analyze_response_content(response: EnhancedResponse) -> Dict[str, Any]:
    """Analyze response content for useful information."""
    analysis = {
        "content_type": response.metadata.content_type,
        "is_html": response.is_html(),
        "is_json": response.is_json(),
        "is_xml": response.is_xml(),
        "contains_forms": False,
        "contains_scripts": False,
        "contains_iframes": False,
        "external_resources": [],
        "meta_tags": {},
    }
    
    if response.is_html():
        text_lower = response.text.lower()
        analysis["contains_forms"] = "<form" in text_lower
        analysis["contains_scripts"] = "<script" in text_lower
        analysis["contains_iframes"] = "<iframe" in text_lower
        
        # Extract meta tags (simplified)
        import re
        meta_pattern = r'<meta\s+name="([^"]+)"\s+content="([^"]+)"'
        for match in re.finditer(meta_pattern, response.text, re.IGNORECASE):
            analysis["meta_tags"][match.group(1)] = match.group(2)
    
    return analysis