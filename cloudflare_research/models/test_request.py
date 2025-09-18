"""TestRequest model for browser emulation requests.

Represents a single browser emulation request with configuration and timing data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4


class RequestStatus(Enum):
    """Status enumeration for test requests."""
    CREATED = "created"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class HttpMethod(Enum):
    """HTTP method enumeration."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class BrowserConfig:
    """Browser fingerprint configuration."""
    version: str = "124.0.0.0"
    user_agent: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    timezone: str = "America/New_York"
    language: str = "en-US"
    platform: str = "Win32"


@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    type: str  # http, https, socks4, socks5
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class RequestTiming:
    """Timing information for request execution."""
    dns_resolution_ms: int = 0
    tcp_connection_ms: int = 0
    tls_handshake_ms: int = 0
    request_sent_ms: int = 0
    response_received_ms: int = 0
    total_duration_ms: int = 0


@dataclass
class TestRequest:
    """
    Represents a single browser emulation request.

    This entity captures all configuration and timing data for a single HTTP request
    with browser emulation, including headers, payload, and execution timing.
    """

    # Core identifiers
    request_id: UUID = field(default_factory=uuid4)
    session_id: Optional[UUID] = None

    # Request configuration
    url: str = ""
    method: HttpMethod = HttpMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None

    # Browser emulation configuration
    browser_config: BrowserConfig = field(default_factory=BrowserConfig)
    proxy_config: Optional[ProxyConfig] = None

    # Request settings
    timeout: int = 30  # seconds

    # Status and timing
    status: RequestStatus = RequestStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Response data
    status_code: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[str] = None
    timing: RequestTiming = field(default_factory=RequestTiming)

    # Error handling
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate request configuration after initialization."""
        self._validate_url()
        self._validate_timeout()
        self._validate_headers()

    def _validate_url(self) -> None:
        """Validate URL format."""
        if not self.url:
            raise ValueError("URL is required")

        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")

    def _validate_timeout(self) -> None:
        """Validate timeout value."""
        if not isinstance(self.timeout, int):
            raise TypeError("Timeout must be an integer")

        if not (1 <= self.timeout <= 300):
            raise ValueError("Timeout must be between 1 and 300 seconds")

    def _validate_headers(self) -> None:
        """Validate HTTP headers format."""
        if not isinstance(self.headers, dict):
            raise TypeError("Headers must be a dictionary")

        for key, value in self.headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError("Header keys and values must be strings")

    @property
    def is_completed(self) -> bool:
        """Check if request is in a completed state."""
        return self.status in {
            RequestStatus.COMPLETED,
            RequestStatus.FAILED,
            RequestStatus.TIMEOUT
        }

    @property
    def is_successful(self) -> bool:
        """Check if request completed successfully."""
        return (
            self.status == RequestStatus.COMPLETED and
            self.status_code is not None and
            200 <= self.status_code < 400
        )

    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate total request duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    def start_execution(self) -> None:
        """Mark request as started."""
        self.status = RequestStatus.EXECUTING
        self.started_at = datetime.now()

    def mark_completed(self, status_code: int, headers: Dict[str, str],
                      body: str, timing: RequestTiming) -> None:
        """Mark request as completed with response data."""
        self.status = RequestStatus.COMPLETED
        self.completed_at = datetime.now()
        self.status_code = status_code
        self.response_headers = headers
        self.response_body = body
        self.timing = timing

    def mark_failed(self, error_message: str) -> None:
        """Mark request as failed with error message."""
        self.status = RequestStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message

    def mark_timeout(self) -> None:
        """Mark request as timed out."""
        self.status = RequestStatus.TIMEOUT
        self.completed_at = datetime.now()
        self.error_message = f"Request timed out after {self.timeout} seconds"

    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary for serialization."""
        return {
            "request_id": str(self.request_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "url": self.url,
            "method": self.method.value,
            "headers": self.headers,
            "body": self.body,
            "browser_config": {
                "version": self.browser_config.version,
                "user_agent": self.browser_config.user_agent,
                "viewport_width": self.browser_config.viewport_width,
                "viewport_height": self.browser_config.viewport_height,
                "timezone": self.browser_config.timezone,
                "language": self.browser_config.language,
                "platform": self.browser_config.platform,
            },
            "proxy_config": {
                "type": self.proxy_config.type,
                "host": self.proxy_config.host,
                "port": self.proxy_config.port,
                "username": self.proxy_config.username,
                "password": self.proxy_config.password,
            } if self.proxy_config else None,
            "timeout": self.timeout,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "timing": {
                "dns_resolution_ms": self.timing.dns_resolution_ms,
                "tcp_connection_ms": self.timing.tcp_connection_ms,
                "tls_handshake_ms": self.timing.tls_handshake_ms,
                "request_sent_ms": self.timing.request_sent_ms,
                "response_received_ms": self.timing.response_received_ms,
                "total_duration_ms": self.timing.total_duration_ms,
            },
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestRequest":
        """Create TestRequest from dictionary."""
        # Parse browser config
        browser_config_data = data.get("browser_config", {})
        browser_config = BrowserConfig(
            version=browser_config_data.get("version", "124.0.0.0"),
            user_agent=browser_config_data.get("user_agent"),
            viewport_width=browser_config_data.get("viewport_width", 1920),
            viewport_height=browser_config_data.get("viewport_height", 1080),
            timezone=browser_config_data.get("timezone", "America/New_York"),
            language=browser_config_data.get("language", "en-US"),
            platform=browser_config_data.get("platform", "Win32"),
        )

        # Parse proxy config
        proxy_config = None
        if data.get("proxy_config"):
            proxy_data = data["proxy_config"]
            proxy_config = ProxyConfig(
                type=proxy_data["type"],
                host=proxy_data["host"],
                port=proxy_data["port"],
                username=proxy_data.get("username"),
                password=proxy_data.get("password"),
            )

        # Parse timing
        timing_data = data.get("timing", {})
        timing = RequestTiming(
            dns_resolution_ms=timing_data.get("dns_resolution_ms", 0),
            tcp_connection_ms=timing_data.get("tcp_connection_ms", 0),
            tls_handshake_ms=timing_data.get("tls_handshake_ms", 0),
            request_sent_ms=timing_data.get("request_sent_ms", 0),
            response_received_ms=timing_data.get("response_received_ms", 0),
            total_duration_ms=timing_data.get("total_duration_ms", 0),
        )

        # Parse timestamps
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None

        return cls(
            request_id=UUID(data["request_id"]) if data.get("request_id") else uuid4(),
            session_id=UUID(data["session_id"]) if data.get("session_id") else None,
            url=data["url"],
            method=HttpMethod(data.get("method", "GET")),
            headers=data.get("headers", {}),
            body=data.get("body"),
            browser_config=browser_config,
            proxy_config=proxy_config,
            timeout=data.get("timeout", 30),
            status=RequestStatus(data.get("status", "created")),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            status_code=data.get("status_code"),
            response_headers=data.get("response_headers", {}),
            response_body=data.get("response_body"),
            timing=timing,
            error_message=data.get("error_message"),
        )