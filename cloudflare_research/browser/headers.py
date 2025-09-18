"""Chrome headers generator for accurate browser emulation.

This module provides dynamic header generation that matches Chrome's behavior
across different request types, versions, and contexts.
"""

import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin


class RequestType(Enum):
    """Types of HTTP requests for header customization."""
    DOCUMENT = "document"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    IMAGE = "image"
    FONT = "font"
    XHR = "xmlhttprequest"
    FETCH = "fetch"
    WEBSOCKET = "websocket"
    MANIFEST = "manifest"
    WORKER = "worker"


class NavigationType(Enum):
    """Navigation types affecting header generation."""
    NAVIGATE = "navigate"
    RELOAD = "reload"
    BACK_FORWARD = "back_forward"
    PRERENDER = "prerender"


@dataclass
class RequestContext:
    """Context information for header generation."""
    request_type: RequestType = RequestType.DOCUMENT
    navigation_type: NavigationType = NavigationType.NAVIGATE
    referer_url: Optional[str] = None
    origin_url: Optional[str] = None
    is_same_origin: bool = True
    is_cors: bool = False
    is_mobile: bool = False
    is_incognito: bool = False
    user_initiated: bool = True


@dataclass
class ChromeProfile:
    """Chrome browser profile configuration."""
    version: str = "124.0.0.0"
    platform: str = "Windows"
    architecture: str = "x64"
    os_version: str = "10.0"
    device_model: Optional[str] = None  # For mobile

    @property
    def major_version(self) -> str:
        """Get major version number."""
        return self.version.split('.')[0]

    @property
    def is_mobile(self) -> bool:
        """Check if profile is for mobile."""
        return self.device_model is not None


class ChromeHeadersGenerator:
    """
    Generates Chrome-accurate HTTP headers for different request contexts.

    This class emulates Chrome's header generation behavior including
    order, values, and conditional inclusion based on request type.
    """

    def __init__(self, profile: Optional[ChromeProfile] = None):
        self.profile = profile or ChromeProfile()
        self._user_agent_cache: Dict[str, str] = {}
        self._sec_ch_ua_cache: Dict[str, str] = {}

    def generate_headers(self, url: str, context: Optional[RequestContext] = None) -> Dict[str, str]:
        """Generate headers for a request to the specified URL."""
        context = context or RequestContext()
        headers = {}

        # Generate headers in Chrome's typical order
        if context.request_type == RequestType.DOCUMENT:
            headers.update(self._generate_document_headers(url, context))
        elif context.request_type == RequestType.XHR:
            headers.update(self._generate_xhr_headers(url, context))
        elif context.request_type == RequestType.FETCH:
            headers.update(self._generate_fetch_headers(url, context))
        elif context.request_type in [RequestType.STYLESHEET, RequestType.SCRIPT, RequestType.IMAGE]:
            headers.update(self._generate_resource_headers(url, context))
        else:
            headers.update(self._generate_default_headers(url, context))

        return headers

    def _generate_document_headers(self, url: str, context: RequestContext) -> Dict[str, str]:
        """Generate headers for document (navigation) requests."""
        headers = {
            "Accept": self._get_accept_header(context.request_type),
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Cache-Control": "no-cache" if context.navigation_type == NavigationType.RELOAD else "max-age=0",
            "Pragma": "no-cache" if context.navigation_type == NavigationType.RELOAD else None,
            "Sec-CH-UA": self._get_sec_ch_ua(),
            "Sec-CH-UA-Mobile": "?1" if self.profile.is_mobile else "?0",
            "Sec-CH-UA-Platform": self._get_sec_ch_ua_platform(),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": self._get_sec_fetch_site(url, context),
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self._get_user_agent(),
        }

        # Add referer if present
        if context.referer_url:
            headers["Referer"] = context.referer_url

        # Remove None values
        return {k: v for k, v in headers.items() if v is not None}

    def _generate_xhr_headers(self, url: str, context: RequestContext) -> Dict[str, str]:
        """Generate headers for XMLHttpRequest."""
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",  # Default, often overridden
            "Sec-CH-UA": self._get_sec_ch_ua(),
            "Sec-CH-UA-Mobile": "?1" if self.profile.is_mobile else "?0",
            "Sec-CH-UA-Platform": self._get_sec_ch_ua_platform(),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": self._get_sec_fetch_site(url, context),
            "User-Agent": self._get_user_agent(),
            "X-Requested-With": "XMLHttpRequest",
        }

        # Add origin for CORS requests
        if context.is_cors and context.origin_url:
            headers["Origin"] = context.origin_url

        # Add referer
        if context.referer_url:
            headers["Referer"] = context.referer_url

        return headers

    def _generate_fetch_headers(self, url: str, context: RequestContext) -> Dict[str, str]:
        """Generate headers for Fetch API requests."""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Content-Type": "application/json",  # Default for JSON APIs
            "Sec-CH-UA": self._get_sec_ch_ua(),
            "Sec-CH-UA-Mobile": "?1" if self.profile.is_mobile else "?0",
            "Sec-CH-UA-Platform": self._get_sec_ch_ua_platform(),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": self._get_sec_fetch_site(url, context),
            "User-Agent": self._get_user_agent(),
        }

        # Add origin for CORS requests
        if context.is_cors and context.origin_url:
            headers["Origin"] = context.origin_url

        # Add referer
        if context.referer_url:
            headers["Referer"] = context.referer_url

        return headers

    def _generate_resource_headers(self, url: str, context: RequestContext) -> Dict[str, str]:
        """Generate headers for resource requests (CSS, JS, images)."""
        headers = {
            "Accept": self._get_accept_header(context.request_type),
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Sec-CH-UA": self._get_sec_ch_ua(),
            "Sec-CH-UA-Mobile": "?1" if self.profile.is_mobile else "?0",
            "Sec-CH-UA-Platform": self._get_sec_ch_ua_platform(),
            "Sec-Fetch-Dest": context.request_type.value,
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": self._get_sec_fetch_site(url, context),
            "User-Agent": self._get_user_agent(),
        }

        # Add referer
        if context.referer_url:
            headers["Referer"] = context.referer_url

        return headers

    def _generate_default_headers(self, url: str, context: RequestContext) -> Dict[str, str]:
        """Generate default headers for other request types."""
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Sec-CH-UA": self._get_sec_ch_ua(),
            "Sec-CH-UA-Mobile": "?1" if self.profile.is_mobile else "?0",
            "Sec-CH-UA-Platform": self._get_sec_ch_ua_platform(),
            "Sec-Fetch-Dest": context.request_type.value,
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": self._get_sec_fetch_site(url, context),
            "User-Agent": self._get_user_agent(),
        }

        if context.referer_url:
            headers["Referer"] = context.referer_url

        return headers

    def _get_user_agent(self) -> str:
        """Generate User-Agent header."""
        cache_key = f"{self.profile.version}_{self.profile.platform}_{self.profile.is_mobile}"

        if cache_key not in self._user_agent_cache:
            if self.profile.is_mobile:
                ua = (
                    f"Mozilla/5.0 (Linux; Android 10; {self.profile.device_model or 'SM-G973F'}) "
                    f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.profile.version} "
                    f"Mobile Safari/537.36"
                )
            elif self.profile.platform == "macOS":
                ua = (
                    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.profile.version} "
                    f"Safari/537.36"
                )
            elif self.profile.platform == "Linux":
                ua = (
                    f"Mozilla/5.0 (X11; Linux {self.profile.architecture}) "
                    f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.profile.version} "
                    f"Safari/537.36"
                )
            else:  # Windows
                ua = (
                    f"Mozilla/5.0 (Windows NT {self.profile.os_version}; "
                    f"Win64; {self.profile.architecture}) AppleWebKit/537.36 "
                    f"(KHTML, like Gecko) Chrome/{self.profile.version} Safari/537.36"
                )

            self._user_agent_cache[cache_key] = ua

        return self._user_agent_cache[cache_key]

    def _get_sec_ch_ua(self) -> str:
        """Generate Sec-CH-UA header."""
        cache_key = self.profile.major_version

        if cache_key not in self._sec_ch_ua_cache:
            major_version = self.profile.major_version
            ua = (
                f'"Chromium";v="{major_version}", '
                f'"Google Chrome";v="{major_version}", '
                f'"Not-A.Brand";v="99"'
            )
            self._sec_ch_ua_cache[cache_key] = ua

        return self._sec_ch_ua_cache[cache_key]

    def _get_sec_ch_ua_platform(self) -> str:
        """Generate Sec-CH-UA-Platform header."""
        platform_map = {
            "Windows": '"Windows"',
            "macOS": '"macOS"',
            "Linux": '"Linux"',
        }

        if self.profile.is_mobile:
            return '"Android"'

        return platform_map.get(self.profile.platform, '"Windows"')

    def _get_accept_header(self, request_type: RequestType) -> str:
        """Get Accept header based on request type."""
        accept_map = {
            RequestType.DOCUMENT: (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8,"
                "application/signed-exchange;v=b3;q=0.7"
            ),
            RequestType.STYLESHEET: "text/css,*/*;q=0.1",
            RequestType.SCRIPT: "*/*",
            RequestType.IMAGE: "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            RequestType.FONT: "*/*",
            RequestType.XHR: "*/*",
            RequestType.FETCH: "application/json, text/plain, */*",
            RequestType.WEBSOCKET: "*/*",
            RequestType.MANIFEST: "*/*",
            RequestType.WORKER: "*/*",
        }

        return accept_map.get(request_type, "*/*")

    def _get_accept_language(self) -> str:
        """Generate Accept-Language header."""
        # Could be randomized or configured
        return "en-US,en;q=0.9"

    def _get_sec_fetch_site(self, url: str, context: RequestContext) -> str:
        """Determine Sec-Fetch-Site value."""
        if not context.referer_url:
            return "none"

        try:
            request_domain = urlparse(url).netloc.lower()
            referer_domain = urlparse(context.referer_url).netloc.lower()

            if request_domain == referer_domain:
                return "same-origin"

            # Check for same-site (same eTLD+1)
            if self._is_same_site(request_domain, referer_domain):
                return "same-site"

            return "cross-site"

        except Exception:
            return "cross-site"

    def _is_same_site(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are same-site (same eTLD+1)."""
        # Simplified implementation - real version would use Public Suffix List
        def get_etld_plus1(domain: str) -> str:
            parts = domain.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain

        return get_etld_plus1(domain1) == get_etld_plus1(domain2)

    def update_profile(self, **kwargs) -> None:
        """Update Chrome profile settings."""
        for key, value in kwargs.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)

        # Clear caches when profile changes
        self._user_agent_cache.clear()
        self._sec_ch_ua_cache.clear()

    def randomize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Add subtle randomization to headers to avoid detection."""
        randomized = headers.copy()

        # Slightly randomize Accept-Language quality values
        if "Accept-Language" in randomized:
            # Keep it subtle - just minor variations
            variants = [
                "en-US,en;q=0.9",
                "en-US,en;q=0.8,*;q=0.5",
                "en-US,en;q=0.9,*;q=0.5",
            ]
            randomized["Accept-Language"] = random.choice(variants)

        # Sometimes add Cache-Control: no-cache
        if random.random() < 0.1 and "Cache-Control" not in randomized:
            randomized["Cache-Control"] = "no-cache"

        return randomized

    def get_websocket_headers(self, url: str, context: Optional[RequestContext] = None) -> Dict[str, str]:
        """Generate headers for WebSocket upgrade requests."""
        context = context or RequestContext(request_type=RequestType.WEBSOCKET)

        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Cache-Control": "no-cache",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Sec-WebSocket-Key": self._generate_websocket_key(),
            "Sec-WebSocket-Version": "13",
            "Upgrade": "websocket",
            "User-Agent": self._get_user_agent(),
        }

        if context.origin_url:
            headers["Origin"] = context.origin_url

        return headers

    def _generate_websocket_key(self) -> str:
        """Generate WebSocket-Key header value."""
        import base64
        import os
        key_bytes = os.urandom(16)
        return base64.b64encode(key_bytes).decode('ascii')

    def get_preload_headers(self, resource_type: str) -> Dict[str, str]:
        """Generate headers for resource preloading."""
        headers = {
            "Accept": self._get_accept_header(RequestType(resource_type)),
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": self._get_accept_language(),
            "Sec-CH-UA": self._get_sec_ch_ua(),
            "Sec-CH-UA-Mobile": "?1" if self.profile.is_mobile else "?0",
            "Sec-CH-UA-Platform": self._get_sec_ch_ua_platform(),
            "Sec-Fetch-Dest": resource_type,
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": self._get_user_agent(),
        }

        return headers


# Utility functions
def create_chrome_headers_generator(version: str = "124.0.0.0",
                                  platform: str = "Windows",
                                  mobile: bool = False) -> ChromeHeadersGenerator:
    """Create headers generator with specified configuration."""
    profile = ChromeProfile(
        version=version,
        platform=platform,
        device_model="SM-G973F" if mobile else None
    )
    return ChromeHeadersGenerator(profile)


def get_headers_for_url(url: str, referer: Optional[str] = None,
                       request_type: RequestType = RequestType.DOCUMENT) -> Dict[str, str]:
    """Quick utility to get headers for a URL."""
    generator = ChromeHeadersGenerator()
    context = RequestContext(
        request_type=request_type,
        referer_url=referer
    )
    return generator.generate_headers(url, context)


# Pre-defined header sets for common scenarios
CHROME_124_WINDOWS_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

API_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


# Utility functions for common operations
def get_default_chrome_headers(version: str = "124.0.0.0") -> Dict[str, str]:
    """Get default Chrome headers for document requests."""
    generator = create_chrome_headers_generator(version)
    return generator.get_base_headers()


def get_xhr_headers(url: str, referer: str = None, version: str = "124.0.0.0") -> Dict[str, str]:
    """Get headers optimized for XHR requests."""
    generator = create_chrome_headers_generator(version)
    context = RequestContext(
        request_type=RequestType.XHR,
        referer_url=referer
    )
    return generator.generate_headers(url, context)


def get_fetch_headers(url: str, referer: str = None, version: str = "124.0.0.0") -> Dict[str, str]:
    """Get headers optimized for fetch API requests."""
    generator = create_chrome_headers_generator(version)
    context = RequestContext(
        request_type=RequestType.FETCH,
        referer_url=referer
    )
    return generator.generate_headers(url, context)


def get_resource_headers(url: str, referer: str = None, version: str = "124.0.0.0") -> Dict[str, str]:
    """Get headers optimized for resource requests (images, CSS, JS)."""
    generator = create_chrome_headers_generator(version)
    context = RequestContext(
        request_type=RequestType.IMAGE,  # Use IMAGE for generic resources
        referer_url=referer
    )
    return generator.generate_headers(url, context)