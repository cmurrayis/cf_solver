"""HTTP module for browser emulation.

This module provides HTTP client functionality with browser emulation,
cookie management, and HTTP/2 support.
"""

from .client import (
    AsyncHTTPClient,
    BrowserHTTPClient,
    HTTPClientConfig,
    HTTPResponse,
    HTTPClientError,
    RateLimitExceeded,
    ChallengeError,
    create_http_client,
)

from .response import (
    EnhancedResponse,
    ResponseMetadata,
    create_response_from_tls,
    analyze_response_content,
)

from .http2 import (
    HTTP2Configuration,
    HTTP2Settings,
    HTTP2HeaderCompressor,
    HTTP2PriorityManager,
    HTTP2StreamManager,
    create_chrome_http2_config,
    get_chrome_http2_headers,
    encode_http2_priority_frame,
    CHROME_HTTP2_SETTINGS,
    CHROME_WINDOW_UPDATE_SIZE,
)

from .cookies import (
    Cookie,
    CookieJar,
    create_chrome_cookie_jar,
    parse_cookie_header,
)

# Utility functions
def create_browser_client(browser_version: str = "124.0.0.0",
                         proxy_url: str = None,
                         handle_challenges: bool = True) -> BrowserHTTPClient:
    """Create a browser HTTP client with default configuration."""
    config = HTTPClientConfig(
        browser_version=browser_version,
        proxy_url=proxy_url,
        handle_challenges=handle_challenges,
        prefer_http2=True,
    )
    return BrowserHTTPClient(config)

def get_chrome_headers(version: str = "124.0.0.0", mobile: bool = False) -> dict[str, str]:
    """Get Chrome-compatible HTTP headers."""
    chrome_version = version.split('.')[0]

    if mobile:
        user_agent = (
            f"Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36"
        )
        sec_ch_ua_mobile = "?1"
        sec_ch_ua_platform = '"Android"'
    else:
        user_agent = (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{version} Safari/537.36"
        )
        sec_ch_ua_mobile = "?0"
        sec_ch_ua_platform = '"Windows"'

    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-CH-UA": f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}", "Not-A.Brand";v="99"',
        "Sec-CH-UA-Mobile": sec_ch_ua_mobile,
        "Sec-CH-UA-Platform": sec_ch_ua_platform,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": user_agent,
    }

# Export public API
__all__ = [
    # Classes
    "AsyncHTTPClient",
    "BrowserHTTPClient",
    "HTTPClientConfig",
    "HTTPResponse",
    "EnhancedResponse",
    "ResponseMetadata",
    "HTTP2Configuration",
    "HTTP2Settings",
    "Cookie",
    "CookieJar",

    # Exceptions
    "HTTPClientError",
    "RateLimitExceeded",
    "ChallengeError",

    # Functions
    "create_http_client",
    "create_browser_client",
    "create_chrome_cookie_jar",
    "get_chrome_headers",
]