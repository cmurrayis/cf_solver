"""TestConfiguration model for browser emulation settings.

Represents configuration settings controlling browser emulation behavior
and test parameters.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4


class BrowserProfile(Enum):
    """Predefined browser profiles for emulation."""
    CHROME_WINDOWS = "chrome_windows"
    CHROME_MACOS = "chrome_macos"
    CHROME_LINUX = "chrome_linux"
    CHROME_MOBILE = "chrome_mobile"


class TLSProfile(Enum):
    """TLS fingerprint profiles."""
    CHROME_124 = "chrome_124"
    CHROME_123 = "chrome_123"
    CHROME_122 = "chrome_122"
    FIREFOX_LATEST = "firefox_latest"
    SAFARI_LATEST = "safari_latest"


@dataclass
class HeadersProfile:
    """HTTP headers configuration profile."""
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    accept_encoding: str = "gzip, deflate, br"
    accept_language: str = "en-US,en;q=0.9"
    cache_control: str = "no-cache"
    pragma: str = "no-cache"
    sec_ch_ua: str = '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"'
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: str = '"Windows"'
    sec_fetch_dest: str = "document"
    sec_fetch_mode: str = "navigate"
    sec_fetch_site: str = "none"
    sec_fetch_user: str = "?1"
    upgrade_insecure_requests: str = "1"
    custom_headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """Convert headers profile to dictionary."""
        headers = {
            "Accept": self.accept,
            "Accept-Encoding": self.accept_encoding,
            "Accept-Language": self.accept_language,
            "Cache-Control": self.cache_control,
            "Pragma": self.pragma,
            "Sec-CH-UA": self.sec_ch_ua,
            "Sec-CH-UA-Mobile": self.sec_ch_ua_mobile,
            "Sec-CH-UA-Platform": self.sec_ch_ua_platform,
            "Sec-Fetch-Dest": self.sec_fetch_dest,
            "Sec-Fetch-Mode": self.sec_fetch_mode,
            "Sec-Fetch-Site": self.sec_fetch_site,
            "Sec-Fetch-User": self.sec_fetch_user,
            "Upgrade-Insecure-Requests": self.upgrade_insecure_requests,
        }
        headers.update(self.custom_headers)
        return headers


@dataclass
class ProxySettings:
    """Default proxy configuration."""
    enabled: bool = False
    type: str = "http"  # http, https, socks4, socks5
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    rotation_enabled: bool = False
    pool_size: int = 1


@dataclass
class RateLimits:
    """Rate limiting configuration."""
    requests_per_second: float = 10.0
    burst_limit: int = 50
    concurrent_limit: int = 100
    backoff_enabled: bool = True
    backoff_factor: float = 1.5
    max_backoff_seconds: int = 60


@dataclass
class ChallengeSettings:
    """Challenge handling configuration."""
    enabled: bool = True
    javascript_timeout_ms: int = 10000
    turnstile_timeout_ms: int = 15000
    managed_timeout_ms: int = 30000
    max_retries: int = 3
    retry_delay_ms: int = 1000
    auto_solve: bool = True
    cache_solutions: bool = True
    cache_duration_minutes: int = 30


@dataclass
class TestConfiguration:
    """
    Represents configuration settings for browser emulation.

    This entity controls all aspects of browser emulation behavior,
    including fingerprinting, headers, TLS settings, and test parameters.
    """

    # Core identifiers
    config_id: UUID = field(default_factory=uuid4)
    name: str = "Default Configuration"

    # Browser emulation settings
    browser_version: str = "124.0.0.0"
    user_agent: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    timezone: str = "America/New_York"
    language: str = "en-US"
    platform: str = "Win32"

    # Profile settings
    browser_profile: BrowserProfile = BrowserProfile.CHROME_WINDOWS
    tls_profile: TLSProfile = TLSProfile.CHROME_124

    # Configuration objects
    headers_profile: HeadersProfile = field(default_factory=HeadersProfile)
    proxy_settings: ProxySettings = field(default_factory=ProxySettings)
    rate_limits: RateLimits = field(default_factory=RateLimits)
    challenge_settings: ChallengeSettings = field(default_factory=ChallengeSettings)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_browser_version()
        self._validate_viewport()
        self._validate_timezone()
        self._validate_language()
        self._update_user_agent()

    def _validate_browser_version(self) -> None:
        """Validate browser version format."""
        if not isinstance(self.browser_version, str):
            raise TypeError("Browser version must be a string")

        parts = self.browser_version.split(".")
        if len(parts) != 4:
            raise ValueError("Browser version must be in format 'x.y.z.w'")

        try:
            [int(part) for part in parts]
        except ValueError:
            raise ValueError("Browser version parts must be integers")

    def _validate_viewport(self) -> None:
        """Validate viewport dimensions."""
        if not isinstance(self.viewport_width, int) or self.viewport_width <= 0:
            raise ValueError("Viewport width must be a positive integer")

        if not isinstance(self.viewport_height, int) or self.viewport_height <= 0:
            raise ValueError("Viewport height must be a positive integer")

    def _validate_timezone(self) -> None:
        """Validate timezone format."""
        # Basic validation - in real implementation would use pytz or zoneinfo
        if not isinstance(self.timezone, str):
            raise TypeError("Timezone must be a string")

        if "/" not in self.timezone:
            raise ValueError("Timezone must be in IANA format (e.g., 'America/New_York')")

    def _validate_language(self) -> None:
        """Validate language locale format."""
        if not isinstance(self.language, str):
            raise TypeError("Language must be a string")

        if "-" not in self.language or len(self.language) != 5:
            raise ValueError("Language must be in format 'xx-XX' (e.g., 'en-US')")

    def _update_user_agent(self) -> None:
        """Update user agent based on browser profile if not explicitly set."""
        if self.user_agent is not None:
            return

        if self.browser_profile == BrowserProfile.CHROME_WINDOWS:
            self.user_agent = (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{self.browser_version} Safari/537.36"
            )
        elif self.browser_profile == BrowserProfile.CHROME_MACOS:
            self.user_agent = (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{self.browser_version} Safari/537.36"
            )
        elif self.browser_profile == BrowserProfile.CHROME_LINUX:
            self.user_agent = (
                f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{self.browser_version} Safari/537.36"
            )
        elif self.browser_profile == BrowserProfile.CHROME_MOBILE:
            self.user_agent = (
                f"Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{self.browser_version} Mobile Safari/537.36"
            )

    def update_configuration(self) -> None:
        """Update the configuration timestamp."""
        self.updated_at = datetime.now()

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests."""
        headers = self.headers_profile.to_dict()
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        return headers

    def get_tls_config(self) -> Dict[str, Any]:
        """Get TLS configuration based on profile."""
        # This would return TLS fingerprint configuration
        # Implementation details would be in TLS module
        return {
            "profile": self.tls_profile.value,
            "version": self.browser_version,
            "ciphers": self._get_cipher_suites(),
            "extensions": self._get_tls_extensions(),
        }

    def _get_cipher_suites(self) -> List[str]:
        """Get cipher suites for TLS profile."""
        # Simplified - real implementation would have full cipher lists
        return [
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
        ]

    def _get_tls_extensions(self) -> List[str]:
        """Get TLS extensions for profile."""
        return [
            "server_name", "extended_master_secret", "renegotiation_info",
            "supported_groups", "ec_point_formats", "session_ticket",
            "application_layer_protocol_negotiation", "status_request",
            "signature_algorithms", "signed_certificate_timestamp",
            "key_share", "psk_key_exchange_modes", "supported_versions",
            "compress_certificate", "application_settings"
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "config_id": str(self.config_id),
            "name": self.name,
            "browser_version": self.browser_version,
            "user_agent": self.user_agent,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "timezone": self.timezone,
            "language": self.language,
            "platform": self.platform,
            "browser_profile": self.browser_profile.value,
            "tls_profile": self.tls_profile.value,
            "headers_profile": {
                "accept": self.headers_profile.accept,
                "accept_encoding": self.headers_profile.accept_encoding,
                "accept_language": self.headers_profile.accept_language,
                "custom_headers": self.headers_profile.custom_headers,
            },
            "proxy_settings": {
                "enabled": self.proxy_settings.enabled,
                "type": self.proxy_settings.type,
                "host": self.proxy_settings.host,
                "port": self.proxy_settings.port,
                "rotation_enabled": self.proxy_settings.rotation_enabled,
                "pool_size": self.proxy_settings.pool_size,
            },
            "rate_limits": {
                "requests_per_second": self.rate_limits.requests_per_second,
                "burst_limit": self.rate_limits.burst_limit,
                "concurrent_limit": self.rate_limits.concurrent_limit,
                "backoff_enabled": self.rate_limits.backoff_enabled,
            },
            "challenge_settings": {
                "enabled": self.challenge_settings.enabled,
                "javascript_timeout_ms": self.challenge_settings.javascript_timeout_ms,
                "auto_solve": self.challenge_settings.auto_solve,
                "max_retries": self.challenge_settings.max_retries,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestConfiguration":
        """Create TestConfiguration from dictionary."""
        # Parse nested objects
        headers_data = data.get("headers_profile", {})
        headers_profile = HeadersProfile(
            accept=headers_data.get("accept", HeadersProfile().accept),
            accept_encoding=headers_data.get("accept_encoding", HeadersProfile().accept_encoding),
            accept_language=headers_data.get("accept_language", HeadersProfile().accept_language),
            custom_headers=headers_data.get("custom_headers", {}),
        )

        proxy_data = data.get("proxy_settings", {})
        proxy_settings = ProxySettings(
            enabled=proxy_data.get("enabled", False),
            type=proxy_data.get("type", "http"),
            host=proxy_data.get("host"),
            port=proxy_data.get("port"),
            rotation_enabled=proxy_data.get("rotation_enabled", False),
            pool_size=proxy_data.get("pool_size", 1),
        )

        rate_data = data.get("rate_limits", {})
        rate_limits = RateLimits(
            requests_per_second=rate_data.get("requests_per_second", 10.0),
            burst_limit=rate_data.get("burst_limit", 50),
            concurrent_limit=rate_data.get("concurrent_limit", 100),
            backoff_enabled=rate_data.get("backoff_enabled", True),
        )

        challenge_data = data.get("challenge_settings", {})
        challenge_settings = ChallengeSettings(
            enabled=challenge_data.get("enabled", True),
            javascript_timeout_ms=challenge_data.get("javascript_timeout_ms", 10000),
            auto_solve=challenge_data.get("auto_solve", True),
            max_retries=challenge_data.get("max_retries", 3),
        )

        # Parse timestamps
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()

        return cls(
            config_id=UUID(data["config_id"]) if data.get("config_id") else uuid4(),
            name=data["name"],
            browser_version=data.get("browser_version", "124.0.0.0"),
            user_agent=data.get("user_agent"),
            viewport_width=data.get("viewport_width", 1920),
            viewport_height=data.get("viewport_height", 1080),
            timezone=data.get("timezone", "America/New_York"),
            language=data.get("language", "en-US"),
            platform=data.get("platform", "Win32"),
            browser_profile=BrowserProfile(data.get("browser_profile", "chrome_windows")),
            tls_profile=TLSProfile(data.get("tls_profile", "chrome_124")),
            headers_profile=headers_profile,
            proxy_settings=proxy_settings,
            rate_limits=rate_limits,
            challenge_settings=challenge_settings,
            created_at=created_at,
            updated_at=updated_at,
        )

    @classmethod
    def create_profile(cls, profile: BrowserProfile, name: str) -> "TestConfiguration":
        """Create configuration from predefined profile."""
        config = cls(name=name, browser_profile=profile)
        
        if profile == BrowserProfile.CHROME_MOBILE:
            config.viewport_width = 412
            config.viewport_height = 915
            config.platform = "Linux"
        elif profile == BrowserProfile.CHROME_MACOS:
            config.platform = "MacIntel"
            config.timezone = "America/Los_Angeles"
        elif profile == BrowserProfile.CHROME_LINUX:
            config.platform = "Linux x86_64"
            config.timezone = "UTC"
        
        return config

    def __str__(self) -> str:
        """String representation of the configuration."""
        return (
            f"TestConfiguration(name='{self.name}', "
            f"profile={self.browser_profile.value}, "
            f"version={self.browser_version})"
        )