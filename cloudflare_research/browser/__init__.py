"""Browser emulation module for realistic Chrome behavior.

This module provides comprehensive browser emulation including headers,
fingerprinting, timing, and behavioral patterns that match Chrome.
"""

from .headers import (
    RequestType,
    RequestContext,
    ChromeHeadersGenerator,
    create_chrome_headers_generator,
    get_default_chrome_headers,
    get_xhr_headers,
    get_fetch_headers,
    get_resource_headers,
)

from .fingerprint import (
    FingerprintComponent,
    ScreenProperties,
    JavaScriptFeatures,
    BrowserFingerprint,
    BrowserFingerprintManager,
    create_fingerprint_manager,
    get_chrome_fingerprint,
    randomize_fingerprint,
)

from .timing import (
    RequestPriority,
    ConnectionState,
    TimingProfile,
    RequestTimingContext,
    BrowserTimingEmulator,
    create_timing_emulator,
    emulate_request_timing,
    add_realistic_delay,
    FAST_NETWORK_PROFILE,
    SLOW_NETWORK_PROFILE,
    MOBILE_NETWORK_PROFILE,
)

# Browser configuration constants
CHROME_VERSIONS = [
    "124.0.6367.60",
    "124.0.6367.78",
    "124.0.6367.91",
    "124.0.6367.118",
    "125.0.6422.60",
    "125.0.6422.76",
    "125.0.6422.112",
]

DEFAULT_CHROME_VERSION = "124.0.6367.118"

# Common screen resolutions
COMMON_RESOLUTIONS = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (2560, 1440),
    (1280, 720),
    (1600, 900),
    (1024, 768),
]

# Browser behavior constants
DEFAULT_VIEWPORT_SIZES = [
    (1200, 800),
    (1366, 728),
    (1440, 860),
    (1536, 824),
    (1920, 1040),
]

# Network timing profiles by connection type
NETWORK_PROFILES = {
    "fast": FAST_NETWORK_PROFILE,
    "normal": TimingProfile(),  # Default profile
    "slow": SLOW_NETWORK_PROFILE,
    "mobile": MOBILE_NETWORK_PROFILE,
}

# User agent patterns
USER_AGENT_PATTERNS = {
    "windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
    "macos": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
    "linux": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
    "android": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
}


class BrowserSession:
    """Manages a complete browser session with consistent state."""

    def __init__(self, chrome_version: str = DEFAULT_CHROME_VERSION, platform: str = "windows"):
        self.chrome_version = chrome_version
        self.platform = platform.lower()

        # Initialize components
        self.headers_generator = create_chrome_headers_generator(chrome_version)
        self.fingerprint_manager = create_fingerprint_manager()
        self.timing_emulator = create_timing_emulator()

        # Get consistent fingerprint
        self.fingerprint = self.fingerprint_manager.get_random_profile(platform)

        # Session state
        self._request_count = 0
        self._session_start_time = None

    async def prepare_request(self, url: str, method: str = "GET",
                            request_type: RequestType = RequestType.DOCUMENT,
                            referer: str = None) -> dict:
        """Prepare headers and timing for a request."""
        context = RequestContext(
            request_type=request_type,
            referer_url=referer,
            is_same_origin=self._is_same_origin(url, referer) if referer else True,
        )

        # Generate headers
        headers = self.headers_generator.generate_headers(url, context)

        # Calculate timing
        timing_context = RequestTimingContext(
            url=url,
            method=method,
            priority=self._get_request_priority(request_type),
            user_initiated=context.user_initiated,
        )

        timing = await self.timing_emulator.calculate_request_timing(timing_context)

        self._request_count += 1

        return {
            "headers": headers,
            "timing": timing,
            "fingerprint": self.fingerprint.to_dict(),
        }

    def _is_same_origin(self, url: str, referer: str) -> bool:
        """Check if request is same-origin."""
        from urllib.parse import urlparse

        try:
            url_parsed = urlparse(url)
            referer_parsed = urlparse(referer)

            return (url_parsed.scheme == referer_parsed.scheme and
                   url_parsed.netloc == referer_parsed.netloc)
        except Exception:
            return False

    def _get_request_priority(self, request_type: RequestType) -> RequestPriority:
        """Map request type to priority."""
        priority_mapping = {
            RequestType.DOCUMENT: RequestPriority.CRITICAL,
            RequestType.XHR: RequestPriority.HIGH,
            RequestType.FETCH: RequestPriority.HIGH,
            RequestType.SCRIPT: RequestPriority.HIGH,
            RequestType.STYLESHEET: RequestPriority.CRITICAL,
            RequestType.IMAGE: RequestPriority.MEDIUM,
            RequestType.FONT: RequestPriority.HIGH,
            RequestType.WEBSOCKET: RequestPriority.MEDIUM,
            RequestType.MANIFEST: RequestPriority.MEDIUM,
            RequestType.WORKER: RequestPriority.MEDIUM,
        }

        return priority_mapping.get(request_type, RequestPriority.MEDIUM)

    def get_navigator_properties(self) -> dict:
        """Get navigator object properties for JavaScript."""
        return self.fingerprint.get_navigator_properties()

    def get_screen_properties(self) -> dict:
        """Get screen properties for JavaScript."""
        return self.fingerprint.screen.to_dict()

    def reset_session(self) -> None:
        """Reset session state."""
        self._request_count = 0
        self.timing_emulator.reset_state()
        # Generate new fingerprint variation
        self.fingerprint = self.fingerprint_manager.generate_randomized_profile()


def create_browser_session(chrome_version: str = DEFAULT_CHROME_VERSION,
                          platform: str = "windows") -> BrowserSession:
    """Create a browser session with specified configuration."""
    return BrowserSession(chrome_version, platform)


def get_random_chrome_version() -> str:
    """Get random Chrome version from common versions."""
    import random
    return random.choice(CHROME_VERSIONS)


def get_random_resolution() -> tuple[int, int]:
    """Get random screen resolution."""
    import random
    return random.choice(COMMON_RESOLUTIONS)


def build_user_agent(platform: str = "windows",
                    chrome_version: str = DEFAULT_CHROME_VERSION) -> str:
    """Build user agent string for platform and version."""
    pattern = USER_AGENT_PATTERNS.get(platform.lower(), USER_AGENT_PATTERNS["windows"])
    return pattern.format(version=chrome_version)


# Export public API
__all__ = [
    # Classes
    "BrowserSession",
    "RequestType",
    "RequestContext",
    "ChromeHeadersGenerator",
    "BrowserFingerprint",
    "BrowserFingerprintManager",
    "BrowserTimingEmulator",
    "RequestPriority",
    "ConnectionState",
    "TimingProfile",
    "RequestTimingContext",

    # Functions
    "create_browser_session",
    "create_chrome_headers_generator",
    "create_fingerprint_manager",
    "create_timing_emulator",
    "get_random_chrome_version",
    "get_random_resolution",
    "build_user_agent",
    "get_chrome_fingerprint",
    "randomize_fingerprint",
    "emulate_request_timing",

    # Constants
    "CHROME_VERSIONS",
    "DEFAULT_CHROME_VERSION",
    "COMMON_RESOLUTIONS",
    "NETWORK_PROFILES",
    "USER_AGENT_PATTERNS",
]