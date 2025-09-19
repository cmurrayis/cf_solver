#!/usr/bin/env python3
"""
CloudflareScraper Standalone - Complete Browser Emulation for Cloudflare Bypass

A fully self-contained Python module that combines all CloudflareScraper functionality
into a single file. This standalone version includes browser emulation, TLS fingerprinting,
JavaScript challenge solving, and high-performance concurrent operations.

Features:
- Complete browser fingerprinting and emulation (Chrome profiles)
- TLS fingerprinting with JA3 generation
- JavaScript challenge detection and solving
- HTTP/2 support with stream management
- Advanced rate limiting and backpressure handling
- Session management and cookie handling
- Performance monitoring and metrics
- Sync and async interfaces
- cloudscraper-compatible API

Usage:
    # Sync interface (cloudscraper-compatible)
    import cloudflare_scraper_standalone as cfs
    scraper = cfs.create_scraper()
    response = scraper.get("https://example.com")

    # Async interface
    async with cfs.create_cloudflare_bypass() as bypass:
        result = await bypass.get("https://example.com")
"""

import asyncio
import base64
import hashlib
import json
import logging
import random
import re
import ssl
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import weakref
import threading
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import sys
import os

# External dependencies (minimal)
try:
    import aiohttp
    import yarl
except ImportError:
    print("Warning: aiohttp not available, some features may be limited")
    aiohttp = None
    yarl = None

try:
    from py_mini_racer import py_mini_racer
    MINIRACER_AVAILABLE = True
except ImportError:
    MINIRACER_AVAILABLE = False
    py_mini_racer = None

try:
    import curl_cffi
    from curl_cffi.requests import AsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    curl_cffi = None
    AsyncSession = None

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class HttpMethod(Enum):
    """HTTP methods supported by the scraper."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"


class RequestStatus(Enum):
    """Request completion status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CHALLENGE_FAILED = "challenge_failed"


class ChallengeType(Enum):
    """Types of Cloudflare challenges detected."""
    NONE = "none"
    JAVASCRIPT = "javascript"
    CAPTCHA = "captcha"
    RATE_LIMITED = "rate_limited"
    MANAGED = "managed"
    TURNSTILE = "turnstile"
    WAF_BLOCK = "waf_block"
    UNKNOWN = "unknown"


class RequestType(Enum):
    """Types of HTTP requests for header generation."""
    DOCUMENT = "document"
    XHR = "xhr"
    FETCH = "fetch"
    NAVIGATION = "navigation"
    IMAGE = "image"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"


class TaskPriority(Enum):
    """Task priority levels for concurrency management."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    ADAPTIVE = "adaptive"


class BackpressureStrategy(Enum):
    """Backpressure handling strategies."""
    DROP = "drop"
    DELAY = "delay"
    QUEUE = "queue"
    ADAPTIVE_DELAY = "adaptive_delay"


class ChromeVersion(Enum):
    """Supported Chrome versions for fingerprinting."""
    CHROME_124 = "124.0.0.0"
    CHROME_123 = "123.0.0.0"
    CHROME_122 = "122.0.0.0"
    CHROME_121 = "121.0.0.0"


class TLSVersion(Enum):
    """Supported TLS protocol versions."""
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


# Constants
DEFAULT_CHROME_VERSION = "124.0.6367.60"
CHROME_VERSIONS = [
    "124.0.6367.60", "124.0.6367.78", "124.0.6367.91",
    "124.0.6367.118", "125.0.6422.60", "125.0.6422.76"
]

USER_AGENTS = {
    "124.0.0.0": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "123.0.0.0": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "122.0.0.0": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

# Challenge detection patterns
CHALLENGE_PATTERNS = {
    ChallengeType.JAVASCRIPT: [
        r'<script[^>]*>\s*window\._cf_chl_opt',
        r'<script[^>]*>\s*\(function\(\)\{\s*var\s+a\s*=\s*document\.createElement',
        r'window\._cf_chl_opt\s*=\s*\{',
        r'cf_chl_opt\.cHash\s*=',
        r'cf_chl_opt\.cRay\s*=',
        r'cf_chl_opt\.cType\s*=',
        r'chkWork\.call\(',
        r'jschl-answer',
        r'cf-challenge-form',
    ],
    ChallengeType.TURNSTILE: [
        r'<div[^>]*cf-turnstile',
        r'turnstile\.render',
        r'cf-turnstile-response',
        r'turnstile_callback',
    ],
    ChallengeType.RATE_LIMITED: [
        r'<title>Access denied \| .* used Cloudflare',
        r'<h1>Rate limited</h1>',
        r'<p>You are being rate limited</p>',
        r'cf-error-code.*1015',
    ],
    ChallengeType.MANAGED: [
        r'<title>Just a moment\.\.\.</title>',
        r'<h1>Please wait\.\.\.</h1>',
        r'cf-browser-verification',
        r'Checking your browser before accessing',
        r'This process is automatic',
        r'cf-spinner-please-wait',
    ],
}

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class RequestTiming:
    """Timing information for HTTP requests."""
    dns_lookup_ms: int = 0
    tcp_connect_ms: int = 0
    tls_handshake_ms: int = 0
    request_send_ms: int = 0
    response_wait_ms: int = 0
    response_download_ms: int = 0
    total_duration_ms: int = 0
    redirect_time_ms: int = 0


@dataclass
class BrowserConfig:
    """Browser configuration for emulation."""
    user_agent: str = ""
    accept_language: str = "en-US,en;q=0.9"
    platform: str = "Win32"
    screen_resolution: str = "1920x1080"
    timezone: str = "America/New_York"
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    canvas_fingerprint: str = ""


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    proxy_url: Optional[str] = None
    proxy_type: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    rotate_proxies: bool = False
    proxy_pool: List[str] = field(default_factory=list)


@dataclass
class TestRequest:
    """Request configuration for testing."""
    url: str
    method: HttpMethod = HttpMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    data: Optional[Union[str, bytes, Dict[str, Any]]] = None
    json_data: Optional[Dict[str, Any]] = None
    params: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    follow_redirects: bool = True
    max_redirects: int = 10
    verify_ssl: bool = True
    proxy_config: Optional[ProxyConfig] = None
    browser_config: Optional[BrowserConfig] = None


@dataclass
class RequestResult:
    """Result of an HTTP request."""
    url: str
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    cookies: Dict[str, str]
    timing: RequestTiming
    success: bool
    error_message: Optional[str] = None
    challenge_type: ChallengeType = ChallengeType.NONE
    challenge_solved: bool = False
    redirect_history: List[str] = field(default_factory=list)
    tls_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def json(self) -> Any:
        """Parse response as JSON."""
        try:
            return json.loads(self.text)
        except (json.JSONDecodeError, ValueError):
            return None

    @property
    def ok(self) -> bool:
        """True if status indicates success."""
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        """True if status indicates redirect."""
        return 300 <= self.status_code < 400


@dataclass
class ChallengeInfo:
    """Information about detected challenge."""
    challenge_type: ChallengeType
    challenge_data: Dict[str, Any] = field(default_factory=dict)
    form_data: Dict[str, str] = field(default_factory=dict)
    submit_url: str = ""
    ray_id: str = ""
    challenge_ts: float = 0.0
    confidence: float = 0.0


@dataclass
class ChallengeSolution:
    """Solution to a challenge."""
    challenge_type: ChallengeType
    solution_data: Dict[str, Any] = field(default_factory=dict)
    form_params: Dict[str, str] = field(default_factory=dict)
    submit_url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    delay_ms: int = 0


@dataclass
class ChallengeResult:
    """Result of challenge solving attempt."""
    success: bool
    solution: Optional[ChallengeSolution] = None
    error_message: Optional[str] = None
    attempts: int = 1
    total_time_ms: int = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    requests_sent: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    challenges_detected: int = 0
    challenges_solved: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    total_bytes_downloaded: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.requests_sent
        return (self.requests_successful / total) if total > 0 else 0.0

    @property
    def challenge_solve_rate(self) -> float:
        """Calculate challenge solve rate."""
        total = self.challenges_detected
        return (self.challenges_solved / total) if total > 0 else 0.0


@dataclass
class TestSession:
    """Session for maintaining state across requests."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    chrome_version: str = DEFAULT_CHROME_VERSION
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    request_count: int = 0
    challenge_count: int = 0
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)


@dataclass
class ChallengeRecord:
    """Record of a challenge encounter."""
    challenge_type: ChallengeType
    url: str
    timestamp: float
    solved: bool
    solution_time_ms: int
    attempts: int
    error_message: Optional[str] = None


@dataclass
class TestConfiguration:
    """Configuration for test execution."""
    concurrent_requests: int = 10
    requests_per_second: float = 5.0
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_javascript: bool = True
    enable_cookies: bool = True
    follow_redirects: bool = True
    verify_ssl: bool = True


# =============================================================================
# TLS FINGERPRINTING
# =============================================================================

@dataclass
class TLSExtension:
    """Represents a TLS extension with its configuration."""
    name: str
    extension_id: int
    data: bytes = b""
    critical: bool = False

    def to_wire_format(self) -> bytes:
        """Convert extension to wire format for handshake."""
        ext_type = self.extension_id.to_bytes(2, 'big')
        ext_length = len(self.data).to_bytes(2, 'big')
        return ext_type + ext_length + self.data


@dataclass
class CipherSuite:
    """Represents a TLS cipher suite."""
    name: str
    iana_value: int
    key_exchange: str
    authentication: str
    encryption: str
    hash_algorithm: str
    is_aead: bool = False

    @property
    def wire_value(self) -> bytes:
        """Get cipher suite value in wire format."""
        return self.iana_value.to_bytes(2, 'big')


@dataclass
class TLSFingerprint:
    """Complete TLS fingerprint configuration for Chrome emulation."""
    browser_version: ChromeVersion
    user_agent: str
    min_tls_version: TLSVersion = TLSVersion.TLS_1_2
    max_tls_version: TLSVersion = TLSVersion.TLS_1_3
    cipher_suites: List[CipherSuite] = field(default_factory=list)
    extensions: List[TLSExtension] = field(default_factory=list)
    supported_groups: List[str] = field(default_factory=list)
    signature_algorithms: List[str] = field(default_factory=list)
    alpn_protocols: List[str] = field(default_factory=list)
    key_shares: List[str] = field(default_factory=list)
    compression_methods: List[int] = field(default_factory=lambda: [0])
    supports_session_tickets: bool = True
    supports_session_ids: bool = True
    record_size_limit: Optional[int] = None
    max_fragment_length: Optional[int] = None


class ChromeTLSFingerprintManager:
    """Manages TLS fingerprints for Chrome browser emulation."""

    def __init__(self):
        self._fingerprints: Dict[ChromeVersion, TLSFingerprint] = {}
        self._initialize_fingerprints()

    def _initialize_fingerprints(self) -> None:
        """Initialize TLS fingerprints for supported Chrome versions."""
        self._fingerprints[ChromeVersion.CHROME_124] = self._create_chrome_124_fingerprint()
        self._fingerprints[ChromeVersion.CHROME_123] = self._create_chrome_123_fingerprint()
        self._fingerprints[ChromeVersion.CHROME_122] = self._create_chrome_122_fingerprint()

    def _create_chrome_124_fingerprint(self) -> TLSFingerprint:
        """Create TLS fingerprint for Chrome 124."""
        cipher_suites = [
            CipherSuite("TLS_AES_128_GCM_SHA256", 0x1301, "ECDHE", "RSA", "AES128-GCM", "SHA256", True),
            CipherSuite("TLS_AES_256_GCM_SHA384", 0x1302, "ECDHE", "RSA", "AES256-GCM", "SHA384", True),
            CipherSuite("TLS_CHACHA20_POLY1305_SHA256", 0x1303, "ECDHE", "RSA", "CHACHA20-POLY1305", "SHA256", True),
            CipherSuite("ECDHE-ECDSA-AES128-GCM-SHA256", 0xc02b, "ECDHE", "ECDSA", "AES128-GCM", "SHA256", True),
            CipherSuite("ECDHE-RSA-AES128-GCM-SHA256", 0xc02f, "ECDHE", "RSA", "AES128-GCM", "SHA256", True),
            CipherSuite("ECDHE-ECDSA-AES256-GCM-SHA384", 0xc02c, "ECDHE", "ECDSA", "AES256-GCM", "SHA384", True),
            CipherSuite("ECDHE-RSA-AES256-GCM-SHA384", 0xc030, "ECDHE", "RSA", "AES256-GCM", "SHA384", True),
        ]

        extensions = [
            TLSExtension("server_name", 0, b""),
            TLSExtension("extended_master_secret", 23, b""),
            TLSExtension("renegotiation_info", 65281, b"\x00"),
            TLSExtension("supported_groups", 10, self._encode_supported_groups()),
            TLSExtension("ec_point_formats", 11, b"\x01\x00"),
            TLSExtension("session_ticket", 35, b""),
            TLSExtension("application_layer_protocol_negotiation", 16, self._encode_alpn(["h2", "http/1.1"])),
            TLSExtension("status_request", 5, b"\x01\x00\x00\x00\x00"),
            TLSExtension("signature_algorithms", 13, self._encode_signature_algorithms()),
            TLSExtension("signed_certificate_timestamp", 18, b""),
            TLSExtension("key_share", 51, self._encode_key_shares()),
            TLSExtension("psk_key_exchange_modes", 45, b"\x01\x01"),
            TLSExtension("supported_versions", 43, b"\x02\x03\x04"),
        ]

        return TLSFingerprint(
            browser_version=ChromeVersion.CHROME_124,
            user_agent=USER_AGENTS["124.0.0.0"],
            cipher_suites=cipher_suites,
            extensions=extensions,
            supported_groups=["x25519", "secp256r1", "secp384r1"],
            signature_algorithms=["rsa_pss_rsae_sha256", "ecdsa_secp256r1_sha256", "rsa_pkcs1_sha256"],
            alpn_protocols=["h2", "http/1.1"],
            key_shares=["x25519"],
        )

    def _create_chrome_123_fingerprint(self) -> TLSFingerprint:
        """Create TLS fingerprint for Chrome 123."""
        fingerprint = self._create_chrome_124_fingerprint()
        fingerprint.browser_version = ChromeVersion.CHROME_123
        fingerprint.user_agent = USER_AGENTS["123.0.0.0"]
        return fingerprint

    def _create_chrome_122_fingerprint(self) -> TLSFingerprint:
        """Create TLS fingerprint for Chrome 122."""
        fingerprint = self._create_chrome_124_fingerprint()
        fingerprint.browser_version = ChromeVersion.CHROME_122
        fingerprint.user_agent = USER_AGENTS["122.0.0.0"]
        return fingerprint

    def _encode_supported_groups(self) -> bytes:
        """Encode supported elliptic curve groups."""
        groups = [29, 23, 24]  # x25519, secp256r1, secp384r1
        encoded = b""
        for group in groups:
            encoded += group.to_bytes(2, 'big')
        return len(encoded).to_bytes(2, 'big') + encoded

    def _encode_alpn(self, protocols: List[str]) -> bytes:
        """Encode ALPN protocol list."""
        encoded = b""
        for protocol in protocols:
            protocol_bytes = protocol.encode('ascii')
            encoded += len(protocol_bytes).to_bytes(1, 'big') + protocol_bytes
        return len(encoded).to_bytes(2, 'big') + encoded

    def _encode_signature_algorithms(self) -> bytes:
        """Encode signature algorithms list."""
        algorithms = [0x0804, 0x0403, 0x0401]
        encoded = b""
        for alg in algorithms:
            encoded += alg.to_bytes(2, 'big')
        return len(encoded).to_bytes(2, 'big') + encoded

    def _encode_key_shares(self) -> bytes:
        """Encode key shares for TLS 1.3."""
        return b"\x00\x26\x00\x24\x00\x1d\x00\x20" + b"\x00" * 32

    def get_fingerprint(self, version: ChromeVersion) -> TLSFingerprint:
        """Get TLS fingerprint for specified Chrome version."""
        if version not in self._fingerprints:
            raise ValueError(f"Unsupported Chrome version: {version.value}")
        return self._fingerprints[version]

    def get_fingerprint_by_string(self, version_string: str) -> TLSFingerprint:
        """Get TLS fingerprint by version string."""
        # Extract major version from detailed version strings like "124.0.6367.60"
        major_version = version_string.split('.')[0]

        # Map to ChromeVersion enum
        version_map = {
            "124": ChromeVersion.CHROME_124,
            "123": ChromeVersion.CHROME_123,
            "122": ChromeVersion.CHROME_122,
            "121": ChromeVersion.CHROME_121,
        }

        chrome_version = version_map.get(major_version)
        if chrome_version:
            return self.get_fingerprint(chrome_version)

        # Fallback to latest version if unsupported
        logger.warning(f"Unsupported Chrome version {version_string}, falling back to Chrome 124")
        return self.get_fingerprint(ChromeVersion.CHROME_124)

    def get_ja3_fingerprint(self, fingerprint: TLSFingerprint) -> str:
        """Generate JA3 fingerprint string for the TLS configuration."""
        # TLS version (771 = TLS 1.2, 772 = TLS 1.3)
        version = "772" if fingerprint.max_tls_version == TLSVersion.TLS_1_3 else "771"

        # Cipher suites
        ciphers = ",".join([str(cs.iana_value) for cs in fingerprint.cipher_suites])

        # Extensions
        extensions = ",".join([str(ext.extension_id) for ext in fingerprint.extensions])

        # Elliptic curves
        curve_mapping = {"x25519": "29", "secp256r1": "23", "secp384r1": "24"}
        curves = ",".join([curve_mapping.get(group, "0") for group in fingerprint.supported_groups])

        # Point formats
        point_formats = "0"

        return f"{version},{ciphers},{extensions},{curves},{point_formats}"


# =============================================================================
# BROWSER EMULATION
# =============================================================================

class ChromeHeadersGenerator:
    """Generates Chrome-compatible HTTP headers."""

    def __init__(self, chrome_version: str = DEFAULT_CHROME_VERSION):
        self.chrome_version = chrome_version
        self.major_version = chrome_version.split('.')[0]

    def get_headers(self, request_type: RequestType = RequestType.DOCUMENT,
                   url: str = "", referer: str = "", mobile: bool = False) -> Dict[str, str]:
        """Generate appropriate headers for request type."""

        base_headers = self._get_base_headers(mobile)

        if request_type == RequestType.DOCUMENT:
            return self._get_document_headers(base_headers, url, referer)
        elif request_type == RequestType.XHR:
            return self._get_xhr_headers(base_headers, url, referer)
        elif request_type == RequestType.FETCH:
            return self._get_fetch_headers(base_headers, url, referer)
        elif request_type == RequestType.NAVIGATION:
            return self._get_navigation_headers(base_headers, url)
        else:
            return base_headers

    def _get_base_headers(self, mobile: bool = False) -> Dict[str, str]:
        """Get base headers common to all requests."""
        if mobile:
            user_agent = (
                f"Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{self.chrome_version} Mobile Safari/537.36"
            )
            sec_ch_ua_mobile = "?1"
            sec_ch_ua_platform = '"Android"'
        else:
            user_agent = (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{self.chrome_version} Safari/537.36"
            )
            sec_ch_ua_mobile = "?0"
            sec_ch_ua_platform = '"Windows"'

        return {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            f"Sec-CH-UA": f'"Chromium";v="{self.major_version}", "Google Chrome";v="{self.major_version}", "Not-A.Brand";v="99"',
            "Sec-CH-UA-Mobile": sec_ch_ua_mobile,
            "Sec-CH-UA-Platform": sec_ch_ua_platform,
            "Upgrade-Insecure-Requests": "1",
        }

    def _get_document_headers(self, base_headers: Dict[str, str],
                            url: str, referer: str) -> Dict[str, str]:
        """Get headers for document requests."""
        headers = base_headers.copy()
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

        if referer:
            headers["Referer"] = referer
            headers["Sec-Fetch-Site"] = "same-origin" if self._is_same_origin(url, referer) else "cross-site"

        return headers

    def _get_xhr_headers(self, base_headers: Dict[str, str],
                        url: str, referer: str) -> Dict[str, str]:
        """Get headers for XHR requests."""
        headers = base_headers.copy()
        headers.update({
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin" if self._is_same_origin(url, referer) else "cross-site",
        })

        if referer:
            headers["Referer"] = referer

        return headers

    def _get_fetch_headers(self, base_headers: Dict[str, str],
                          url: str, referer: str) -> Dict[str, str]:
        """Get headers for fetch API requests."""
        headers = base_headers.copy()
        headers.update({
            "Accept": "*/*",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin" if self._is_same_origin(url, referer) else "cross-site",
        })

        if referer:
            headers["Referer"] = referer

        return headers

    def _get_navigation_headers(self, base_headers: Dict[str, str], url: str) -> Dict[str, str]:
        """Get headers for navigation requests."""
        headers = base_headers.copy()
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })
        return headers

    def _is_same_origin(self, url1: str, url2: str) -> bool:
        """Check if two URLs have the same origin."""
        try:
            parsed1 = urlparse(url1)
            parsed2 = urlparse(url2)
            return (parsed1.scheme == parsed2.scheme and
                   parsed1.netloc == parsed2.netloc)
        except:
            return False


@dataclass
class BrowserFingerprint:
    """Browser fingerprint data."""
    user_agent: str
    accept_language: str
    screen_resolution: str
    color_depth: int
    timezone: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_fingerprint: str
    audio_fingerprint: str
    fonts: List[str]
    plugins: List[str]


class BrowserFingerprintManager:
    """Manages browser fingerprint generation."""

    def __init__(self):
        self.fingerprints = {}

    def generate_fingerprint(self, chrome_version: str = DEFAULT_CHROME_VERSION) -> BrowserFingerprint:
        """Generate a realistic browser fingerprint."""
        return BrowserFingerprint(
            user_agent=self._generate_user_agent(chrome_version),
            accept_language="en-US,en;q=0.9",
            screen_resolution=random.choice(["1920x1080", "1366x768", "1536x864", "1440x900"]),
            color_depth=24,
            timezone=random.choice(["America/New_York", "America/Los_Angeles", "Europe/London"]),
            platform="Win32",
            webgl_vendor="Google Inc. (NVIDIA)",
            webgl_renderer="ANGLE (NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)",
            canvas_fingerprint=self._generate_canvas_fingerprint(),
            audio_fingerprint=self._generate_audio_fingerprint(),
            fonts=self._get_common_fonts(),
            plugins=self._get_common_plugins(),
        )

    def _generate_user_agent(self, chrome_version: str) -> str:
        """Generate user agent string."""
        # Extract major version and map to simplified format
        major_version = chrome_version.split('.')[0]
        simplified_version = f"{major_version}.0.0.0"

        # Try to get user agent, fallback to generating one
        if simplified_version in USER_AGENTS:
            return USER_AGENTS[simplified_version]

        # Generate user agent with the actual chrome version
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"

    def _generate_canvas_fingerprint(self) -> str:
        """Generate canvas fingerprint."""
        return hashlib.md5(f"canvas_{random.randint(1000, 9999)}".encode()).hexdigest()

    def _generate_audio_fingerprint(self) -> str:
        """Generate audio fingerprint."""
        return hashlib.md5(f"audio_{random.randint(1000, 9999)}".encode()).hexdigest()

    def _get_common_fonts(self) -> List[str]:
        """Get list of common fonts."""
        return [
            "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
            "Courier New", "Georgia", "Impact", "Times New Roman", "Trebuchet MS",
            "Verdana", "Segoe UI", "Tahoma", "Microsoft YaHei"
        ]

    def _get_common_plugins(self) -> List[str]:
        """Get list of common browser plugins."""
        return [
            "Chrome PDF Plugin",
            "Chrome PDF Viewer",
            "Native Client",
            "Widevine Content Decryption Module"
        ]


class BrowserTimingEmulator:
    """Emulates realistic browser timing patterns."""

    def __init__(self):
        self.last_request_time = 0.0
        self.request_intervals = deque(maxlen=100)

    def get_realistic_delay(self) -> float:
        """Get realistic delay between requests."""
        current_time = time.time()

        if self.last_request_time > 0:
            interval = current_time - self.last_request_time
            self.request_intervals.append(interval)

        # Simulate human-like delays
        base_delay = random.uniform(0.5, 3.0)

        # Add some randomness
        jitter = random.uniform(-0.2, 0.5)

        delay = max(0.1, base_delay + jitter)
        self.last_request_time = current_time + delay

        return delay

    def get_think_time(self) -> float:
        """Get realistic think time for user interactions."""
        return random.uniform(1.0, 5.0)


class BrowserSession:
    """Manages browser session state."""

    def __init__(self, chrome_version: str = DEFAULT_CHROME_VERSION):
        self.session_id = str(uuid.uuid4())
        self.chrome_version = chrome_version
        self.headers_generator = ChromeHeadersGenerator(chrome_version)
        self.fingerprint_manager = BrowserFingerprintManager()
        self.timing_emulator = BrowserTimingEmulator()

        self.cookies = {}
        self.session_headers = {}
        self.fingerprint = self.fingerprint_manager.generate_fingerprint(chrome_version)
        self.created_at = time.time()
        self.last_used = time.time()
        self.request_count = 0

    def get_headers(self, request_type: RequestType = RequestType.DOCUMENT,
                   url: str = "", referer: str = "") -> Dict[str, str]:
        """Get headers for request."""
        headers = self.headers_generator.get_headers(request_type, url, referer)
        headers.update(self.session_headers)
        return headers

    def update_cookies(self, new_cookies: Dict[str, str]) -> None:
        """Update session cookies."""
        self.cookies.update(new_cookies)

    def add_header(self, name: str, value: str) -> None:
        """Add persistent header to session."""
        self.session_headers[name] = value

    def remove_header(self, name: str) -> None:
        """Remove header from session."""
        self.session_headers.pop(name, None)

    def mark_used(self) -> None:
        """Mark session as recently used."""
        self.last_used = time.time()
        self.request_count += 1


# =============================================================================
# CHALLENGE DETECTION AND SOLVING
# =============================================================================

class CloudflareDetector:
    """Detects Cloudflare challenges in HTTP responses."""

    def __init__(self):
        self.patterns = CHALLENGE_PATTERNS
        self.confidence_threshold = 0.7

    def detect_challenge(self, response_text: str, status_code: int,
                        headers: Dict[str, str]) -> ChallengeInfo:
        """Detect challenge type and extract information."""

        # Quick checks based on status code and headers
        server_header = headers.get("server", "").lower()
        if "cloudflare" not in server_header and status_code not in [403, 503, 429]:
            return ChallengeInfo(ChallengeType.NONE)

        # Check each challenge type
        best_match = ChallengeType.NONE
        best_confidence = 0.0
        challenge_data = {}

        for challenge_type, patterns in self.patterns.items():
            confidence = self._calculate_confidence(response_text, patterns)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = challenge_type

        if best_confidence < self.confidence_threshold:
            return ChallengeInfo(ChallengeType.UNKNOWN, confidence=best_confidence)

        # Extract challenge-specific data
        if best_match == ChallengeType.JAVASCRIPT:
            challenge_data = self._extract_js_challenge_data(response_text)
        elif best_match == ChallengeType.TURNSTILE:
            challenge_data = self._extract_turnstile_data(response_text)

        return ChallengeInfo(
            challenge_type=best_match,
            challenge_data=challenge_data,
            confidence=best_confidence,
            ray_id=headers.get("cf-ray", ""),
            challenge_ts=time.time()
        )

    def _calculate_confidence(self, text: str, patterns: List[str]) -> float:
        """Calculate confidence score for challenge type."""
        text_lower = text.lower()
        matches = 0

        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                matches += 1

        return matches / len(patterns) if patterns else 0.0

    def _extract_js_challenge_data(self, html: str) -> Dict[str, Any]:
        """Extract JavaScript challenge data."""
        data = {}

        # Extract challenge options
        chl_opt_match = re.search(r'window\._cf_chl_opt\s*=\s*(\{[^}]+\})', html, re.DOTALL)
        if chl_opt_match:
            try:
                # Basic JSON-like parsing (simplified)
                opt_text = chl_opt_match.group(1)
                data['chl_opt'] = opt_text
            except:
                pass

        # Extract form data
        form_match = re.search(r'<form[^>]*id=["\']challenge-form["\'][^>]*>(.*?)</form>', html, re.DOTALL)
        if form_match:
            form_html = form_match.group(1)

            # Extract hidden inputs
            input_matches = re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', form_html)
            for name, value in input_matches:
                data[name] = value

        # Extract challenge parameters
        param_patterns = {
            'cHash': r'cf_chl_opt\.cHash\s*=\s*["\']([^"\']+)["\']',
            'cRay': r'cf_chl_opt\.cRay\s*=\s*["\']([^"\']+)["\']',
            'cType': r'cf_chl_opt\.cType\s*=\s*["\']([^"\']+)["\']',
        }

        for param, pattern in param_patterns.items():
            match = re.search(pattern, html)
            if match:
                data[param] = match.group(1)

        return data

    def _extract_turnstile_data(self, html: str) -> Dict[str, Any]:
        """Extract Turnstile challenge data."""
        data = {}

        # Extract site key
        sitekey_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
        if sitekey_match:
            data['sitekey'] = sitekey_match.group(1)

        # Extract callback
        callback_match = re.search(r'data-callback=["\']([^"\']+)["\']', html)
        if callback_match:
            data['callback'] = callback_match.group(1)

        return data


class JSChallengeSolver:
    """Solves JavaScript challenges using various execution methods."""

    def __init__(self):
        self.timeout = 30  # seconds
        self.use_miniracer = MINIRACER_AVAILABLE

    def solve_challenge(self, challenge_info: ChallengeInfo,
                       html_content: str) -> ChallengeResult:
        """Solve JavaScript challenge."""

        if challenge_info.challenge_type != ChallengeType.JAVASCRIPT:
            return ChallengeResult(
                success=False,
                error_message="Not a JavaScript challenge"
            )

        try:
            start_time = time.time()

            # Extract JavaScript code
            js_code = self._extract_javascript(html_content)
            if not js_code:
                return ChallengeResult(
                    success=False,
                    error_message="Could not extract JavaScript code"
                )

            # Execute JavaScript
            if self.use_miniracer:
                result = self._solve_with_miniracer(js_code, challenge_info)
            else:
                result = self._solve_with_fallback(js_code, challenge_info)

            total_time = int((time.time() - start_time) * 1000)

            if result:
                solution = ChallengeSolution(
                    challenge_type=ChallengeType.JAVASCRIPT,
                    solution_data=result,
                    form_params=self._prepare_form_params(result, challenge_info),
                    delay_ms=max(4000, total_time)  # Minimum 4 second delay
                )

                return ChallengeResult(
                    success=True,
                    solution=solution,
                    total_time_ms=total_time
                )
            else:
                return ChallengeResult(
                    success=False,
                    error_message="JavaScript execution failed",
                    total_time_ms=total_time
                )

        except Exception as e:
            return ChallengeResult(
                success=False,
                error_message=f"Challenge solving error: {str(e)}"
            )

    def _extract_javascript(self, html: str) -> str:
        """Extract JavaScript challenge code."""
        # Look for the main challenge script
        script_patterns = [
            r'<script[^>]*>(.*?window\._cf_chl_opt.*?)</script>',
            r'<script[^>]*>(.*?chkWork\.call.*?)</script>',
            r'<script[^>]*>(.*?setTimeout\(function.*?)</script>',
        ]

        for pattern in script_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                return match.group(1)

        return ""

    def _solve_with_miniracer(self, js_code: str, challenge_info: ChallengeInfo) -> Optional[Dict[str, Any]]:
        """Solve challenge using MiniRacer."""
        if not MINIRACER_AVAILABLE:
            return None

        try:
            ctx = py_mini_racer.MiniRacer()

            # Set up browser environment
            setup_js = """
            var window = this;
            var document = {
                getElementById: function(id) {
                    if (id === 'challenge-form') {
                        return {
                            submit: function() {},
                            action: '/cdn-cgi/l/chk_jschl'
                        };
                    }
                    return null;
                },
                createElement: function(tag) {
                    return {
                        style: {},
                        submit: function() {}
                    };
                }
            };
            var location = { reload: function() {} };
            var setTimeout = function(fn, delay) { return fn(); };
            var navigator = { userAgent: 'Mozilla/5.0...' };

            var result = {};
            """

            ctx.eval(setup_js)

            # Execute the challenge code
            ctx.eval(js_code)

            # Try to extract the result
            try:
                jschl_answer = ctx.eval("window.jschl_answer || result.jschl_answer || ''")
                return {"jschl_answer": str(jschl_answer)} if jschl_answer else None
            except:
                return None

        except Exception as e:
            logging.warning(f"MiniRacer execution failed: {e}")
            return None

    def _solve_with_fallback(self, js_code: str, challenge_info: ChallengeInfo) -> Optional[Dict[str, Any]]:
        """Fallback solver using pattern matching."""
        try:
            # Look for mathematical operations in the JavaScript
            # This is a simplified approach that works for some challenges

            # Extract number operations
            numbers = re.findall(r'[\+\-\*/]\s*(\d+(?:\.\d+)?)', js_code)
            if not numbers:
                return None

            # Simple calculation (this is very basic)
            result = 0
            for i, num in enumerate(numbers):
                if i == 0:
                    result = float(num)
                else:
                    result += float(num)  # Simplified operation

            return {"jschl_answer": str(int(result))}

        except Exception as e:
            logging.warning(f"Fallback solver failed: {e}")
            return None

    def _prepare_form_params(self, solution: Dict[str, Any],
                           challenge_info: ChallengeInfo) -> Dict[str, str]:
        """Prepare form parameters for submission."""
        params = {}

        # Add solution
        if "jschl_answer" in solution:
            params["jschl_answer"] = str(solution["jschl_answer"])

        # Add challenge data
        for key, value in challenge_info.challenge_data.items():
            if key not in params and isinstance(value, str):
                params[key] = value

        return params


class ChallengeHandler:
    """Handles challenge detection and solving workflow."""

    def __init__(self):
        self.detector = CloudflareDetector()
        self.js_solver = JSChallengeSolver()
        self.max_attempts = 3
        self.retry_delay = 2.0

    async def handle_challenge(self, response_text: str, status_code: int,
                             headers: Dict[str, str], url: str) -> ChallengeResult:
        """Handle challenge detection and solving."""

        # Detect challenge type
        challenge_info = self.detector.detect_challenge(response_text, status_code, headers)

        if challenge_info.challenge_type == ChallengeType.NONE:
            return ChallengeResult(success=True)

        # Handle different challenge types
        if challenge_info.challenge_type == ChallengeType.JAVASCRIPT:
            return self.js_solver.solve_challenge(challenge_info, response_text)
        elif challenge_info.challenge_type == ChallengeType.RATE_LIMITED:
            # Wait and retry
            await asyncio.sleep(5)
            return ChallengeResult(success=True)
        elif challenge_info.challenge_type == ChallengeType.MANAGED:
            # Wait for automatic challenge
            await asyncio.sleep(5)
            return ChallengeResult(success=True)
        else:
            return ChallengeResult(
                success=False,
                error_message=f"Unsupported challenge type: {challenge_info.challenge_type}"
            )


# =============================================================================
# RATE LIMITING AND CONCURRENCY
# =============================================================================

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    burst_size: int = 50
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DELAY
    max_queue_size: int = 1000
    max_delay: float = 30.0
    enable_adaptive: bool = False
    min_rate: float = 1.0
    max_rate: float = 100.0


class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_size)
        self.max_tokens = float(config.burst_size)
        self.refill_rate = config.requests_per_second
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from bucket."""
        async with self._lock:
            now = time.time()

            # Refill tokens
            time_passed = now - self.last_refill
            self.tokens = min(self.max_tokens,
                            self.tokens + time_passed * self.refill_rate)
            self.last_refill = now

            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                # Apply backpressure strategy
                if self.config.backpressure_strategy == BackpressureStrategy.DROP:
                    return False
                elif self.config.backpressure_strategy == BackpressureStrategy.DELAY:
                    wait_time = (tokens - self.tokens) / self.refill_rate
                    if wait_time <= self.config.max_delay:
                        await asyncio.sleep(wait_time)
                        self.tokens = max(0, self.tokens - tokens)
                        return True
                    return False
                else:
                    return False


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple algorithms and adaptive behavior."""

    def __init__(self, config: RateLimitConfig):
        self.config = config

        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            self.limiter = TokenBucketRateLimiter(config)
        else:
            self.limiter = TokenBucketRateLimiter(config)  # Default fallback

        self.request_times = deque(maxlen=1000)
        self.success_rate = 1.0
        self.adaptive_rate = config.requests_per_second

    async def acquire(self, domain: str = "global") -> bool:
        """Acquire permission to make request."""
        return await self.limiter.acquire()

    async def record_result(self, success: bool) -> None:
        """Record request result for adaptive behavior."""
        self.request_times.append((time.time(), success))

        if self.config.enable_adaptive:
            await self._update_adaptive_rate()

    async def _update_adaptive_rate(self) -> None:
        """Update rate based on success/failure patterns."""
        if len(self.request_times) < 10:
            return

        # Calculate recent success rate
        recent_requests = [r for r in self.request_times if time.time() - r[0] < 60]
        if recent_requests:
            self.success_rate = sum(1 for _, success in recent_requests if success) / len(recent_requests)

            # Adjust rate based on success rate
            if self.success_rate > 0.95:
                # Increase rate
                self.adaptive_rate = min(self.config.max_rate, self.adaptive_rate * 1.1)
            elif self.success_rate < 0.8:
                # Decrease rate
                self.adaptive_rate = max(self.config.min_rate, self.adaptive_rate * 0.8)

            # Update limiter rate
            self.limiter.refill_rate = self.adaptive_rate


@dataclass
class ConcurrencyConfig:
    """Configuration for concurrency management."""
    max_concurrent_tasks: int = 100
    max_pending_tasks: int = 1000
    default_timeout: float = 30.0
    backpressure_threshold: float = 0.8
    cleanup_interval: float = 60.0
    enable_metrics: bool = True
    priority_scheduling: bool = False
    enable_task_tracking: bool = True
    max_task_history: int = 10000


@dataclass
class TaskInfo:
    """Information about a task."""
    task_id: str
    priority: TaskPriority
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class ConcurrencyMetrics:
    """Metrics for concurrency management."""
    active_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_tasks: int = 0
    avg_execution_time: float = 0.0
    success_rate: float = 0.0


class ConcurrencyManager:
    """Manages concurrent task execution with backpressure."""

    def __init__(self, config: ConcurrencyConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self.pending_queue = asyncio.Queue(maxsize=config.max_pending_tasks)
        self.active_tasks: Set[asyncio.Task] = set()
        self.task_history = deque(maxlen=config.max_task_history)
        self.metrics = ConcurrencyMetrics()
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the concurrency manager."""
        if self._running:
            return

        self._running = True
        if self.config.cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the concurrency manager."""
        if not self._running:
            return

        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel active tasks
        for task in list(self.active_tasks):
            task.cancel()

        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

    async def submit_task(self, coro, priority: TaskPriority = TaskPriority.NORMAL) -> asyncio.Future:
        """Submit a task for execution."""
        if not self._running:
            raise RuntimeError("ConcurrencyManager not started")

        # Check backpressure
        utilization = len(self.active_tasks) / self.config.max_concurrent_tasks
        if utilization >= self.config.backpressure_threshold:
            if self.pending_queue.full():
                raise RuntimeError("Queue full - backpressure activated")

        # Create task info
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=time.time()
        )

        # Submit to queue
        future = asyncio.Future()
        await self.pending_queue.put((coro, task_info, future))

        # Start processing if not at limit
        if len(self.active_tasks) < self.config.max_concurrent_tasks:
            asyncio.create_task(self._process_next())

        return future

    async def _process_next(self) -> None:
        """Process next task from queue."""
        try:
            coro, task_info, future = await self.pending_queue.get()

            task_info.status = TaskStatus.RUNNING
            task_info.started_at = time.time()

            # Execute with semaphore
            async with self.semaphore:
                task = asyncio.create_task(self._execute_task(coro, task_info, future))
                self.active_tasks.add(task)

                try:
                    await task
                finally:
                    self.active_tasks.discard(task)

        except Exception as e:
            if not future.done():
                future.set_exception(e)

    async def _execute_task(self, coro, task_info: TaskInfo, future: asyncio.Future) -> None:
        """Execute a single task."""
        try:
            result = await asyncio.wait_for(coro, timeout=self.config.default_timeout)

            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = time.time()

            if not future.done():
                future.set_result(result)

            self.metrics.completed_tasks += 1

        except asyncio.TimeoutError:
            task_info.status = TaskStatus.FAILED
            task_info.error_message = "Timeout"
            task_info.completed_at = time.time()

            if not future.done():
                future.set_exception(asyncio.TimeoutError("Task timeout"))

            self.metrics.failed_tasks += 1

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error_message = str(e)
            task_info.completed_at = time.time()

            if not future.done():
                future.set_exception(e)

            self.metrics.failed_tasks += 1

        finally:
            if self.config.enable_task_tracking:
                self.task_history.append(task_info)

            # Update metrics
            self._update_metrics()

            # Process next task if queue not empty
            if not self.pending_queue.empty():
                asyncio.create_task(self._process_next())

    def _update_metrics(self) -> None:
        """Update performance metrics."""
        self.metrics.active_tasks = len(self.active_tasks)
        self.metrics.pending_tasks = self.pending_queue.qsize()
        self.metrics.total_tasks = self.metrics.completed_tasks + self.metrics.failed_tasks

        if self.metrics.total_tasks > 0:
            self.metrics.success_rate = self.metrics.completed_tasks / self.metrics.total_tasks

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of completed tasks."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)

                # Remove old task history
                cutoff_time = time.time() - 3600  # 1 hour
                while (self.task_history and
                       self.task_history[0].completed_at and
                       self.task_history[0].completed_at < cutoff_time):
                    self.task_history.popleft()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.warning(f"Cleanup error: {e}")

    def get_metrics(self) -> ConcurrencyMetrics:
        """Get current metrics."""
        self._update_metrics()
        return self.metrics

    def is_overloaded(self) -> bool:
        """Check if system is overloaded."""
        utilization = len(self.active_tasks) / self.config.max_concurrent_tasks
        return utilization >= self.config.backpressure_threshold


# =============================================================================
# HTTP CLIENT IMPLEMENTATION
# =============================================================================

@dataclass
class HTTPClientConfig:
    """Configuration for HTTP client."""
    browser_version: str = DEFAULT_CHROME_VERSION
    user_agent: Optional[str] = None
    timeout: int = 30
    max_redirects: int = 10
    verify_ssl: bool = True
    proxy_url: Optional[str] = None
    requests_per_second: float = 10.0
    burst_limit: int = 50
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    handle_challenges: bool = True
    challenge_timeout: int = 30
    prefer_http2: bool = True


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class ChallengeError(HTTPClientError):
    """Exception raised when challenge handling fails."""
    pass


@dataclass
class TLSResponse:
    """Response from TLS client."""
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    url: str
    elapsed: float
    cookies: Dict[str, str] = field(default_factory=dict)
    tls_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if not self.ok:
            raise HTTPClientError(f"HTTP {self.status_code}")


class CurlCffiClient:
    """HTTP client using curl-cffi for TLS fingerprinting."""

    def __init__(self, config: HTTPClientConfig):
        self.config = config
        self.session: Optional[AsyncSession] = None
        self.tls_manager = ChromeTLSFingerprintManager()
        self.fingerprint = self.tls_manager.get_fingerprint_by_string(config.browser_version)

    async def _initialize_session(self) -> None:
        """Initialize curl-cffi session."""
        if CURL_CFFI_AVAILABLE and self.session is None:
            self.session = AsyncSession(
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                proxies={"http": self.config.proxy_url, "https": self.config.proxy_url} if self.config.proxy_url else None,
                impersonate="chrome124" if "124" in self.config.browser_version else "chrome"
            )

    async def _request(self, method: str, url: str, **kwargs) -> TLSResponse:
        """Make HTTP request with TLS fingerprinting."""
        if not CURL_CFFI_AVAILABLE:
            # Fallback to basic aiohttp
            return await self._fallback_request(method, url, **kwargs)

        await self._initialize_session()

        start_time = time.time()

        try:
            response = await self.session.request(
                method=method,
                url=url,
                **kwargs
            )

            elapsed = time.time() - start_time

            return TLSResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.content,
                text=response.text,
                url=str(response.url),
                elapsed=elapsed,
                cookies=dict(response.cookies),
                tls_info={"fingerprint": self.tls_manager.get_ja3_fingerprint(self.fingerprint)}
            )

        except Exception as e:
            raise HTTPClientError(f"Request failed: {str(e)}")

    async def _fallback_request(self, method: str, url: str, **kwargs) -> TLSResponse:
        """Fallback HTTP request using aiohttp."""
        if not aiohttp:
            raise HTTPClientError("No HTTP client available")

        start_time = time.time()

        connector = aiohttp.TCPConnector(verify_ssl=self.config.verify_ssl)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                async with session.request(method, url, **kwargs) as response:
                    content = await response.read()
                    text = await response.text()
                    elapsed = time.time() - start_time

                    return TLSResponse(
                        status_code=response.status,
                        headers=dict(response.headers),
                        content=content,
                        text=text,
                        url=str(response.url),
                        elapsed=elapsed,
                        cookies={c.key: c.value for c in response.cookies.values()},
                        tls_info={"fallback": True}
                    )

            except Exception as e:
                raise HTTPClientError(f"Fallback request failed: {str(e)}")

    async def close(self) -> None:
        """Close the client session."""
        if self.session:
            await self.session.close()

    def get_client_info(self) -> Dict[str, Any]:
        """Get client information."""
        return {
            "browser_version": self.config.browser_version,
            "curl_cffi_available": CURL_CFFI_AVAILABLE,
            "fingerprint": self.tls_manager.get_ja3_fingerprint(self.fingerprint)
        }


class BrowserHTTPClient:
    """High-level HTTP client for browser emulation."""

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
        self._challenge_handler: Optional[ChallengeHandler] = None

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

        self._tls_client = CurlCffiClient(self.config)
        await self._tls_client._initialize_session()
        self._setup_default_headers()

        if self.config.handle_challenges:
            self._challenge_handler = ChallengeHandler()

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
        if (self.config.handle_challenges and self._challenge_handler and
            self._is_challenge_response(response)):
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
                request_start = time.perf_counter()
                response = await self._tls_client._request(method, url, **kwargs)
                request_end = time.perf_counter()
                timing.total_duration_ms = int((request_end - request_start) * 1000)
                return response

            except Exception as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                else:
                    break

        raise HTTPClientError(f"Request failed after {self.config.max_retries + 1} attempts") from last_exception

    def _update_cookies(self, response: TLSResponse) -> None:
        """Update session cookies from response."""
        self._cookies.update(response.cookies)

    def _is_challenge_response(self, response: TLSResponse) -> bool:
        """Check if response contains a Cloudflare challenge."""
        if response.status_code not in [403, 503, 429]:
            return False

        server_header = response.headers.get("server", "").lower()
        if "cloudflare" not in server_header:
            return False

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
            challenge_result = await self._challenge_handler.handle_challenge(
                response.text, response.status_code, response.headers, url
            )

            if challenge_result.success and challenge_result.solution:
                # Submit challenge solution
                solution = challenge_result.solution

                # Wait for required delay
                if solution.delay_ms > 0:
                    await asyncio.sleep(solution.delay_ms / 1000.0)

                # Submit solution
                submit_headers = headers.copy()
                submit_headers.update(solution.headers)

                return await self._tls_client._request(
                    "POST", solution.submit_url or url,
                    headers=submit_headers,
                    data=solution.form_params
                )
            else:
                raise ChallengeError(f"Challenge solving failed: {challenge_result.error_message}")

        except Exception as e:
            raise ChallengeError(f"Challenge handling failed: {str(e)}") from e

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._tls_client and not self._closed:
            await self._tls_client.close()
            self._closed = True


class HTTPResponse:
    """Wrapper for HTTP responses with timing and browser emulation info."""

    def __init__(self, tls_response: TLSResponse, timing: RequestTiming):
        self._response = tls_response
        self._timing = timing

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> Dict[str, str]:
        return self._response.headers

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def url(self) -> str:
        return self._response.url

    @property
    def elapsed(self) -> float:
        return self._response.elapsed

    @property
    def cookies(self) -> Dict[str, str]:
        return self._response.cookies

    @property
    def timing(self) -> RequestTiming:
        return self._timing

    @property
    def ok(self) -> bool:
        return self._response.ok

    @property
    def is_redirect(self) -> bool:
        return self._response.is_redirect

    def json(self) -> Any:
        return self._response.json()

    def raise_for_status(self) -> None:
        self._response.raise_for_status()


# =============================================================================
# MAIN CLOUDFLARE BYPASS IMPLEMENTATION
# =============================================================================

@dataclass
class CloudflareBypassConfig:
    """Configuration for Cloudflare bypass operations."""
    max_concurrent_requests: int = 100
    requests_per_second: float = 10.0
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

    # Browser emulation
    chrome_version: str = DEFAULT_CHROME_VERSION
    enable_browser_emulation: bool = True
    enable_tls_fingerprinting: bool = True
    ja3_randomization: bool = False

    # Challenge handling
    solve_javascript_challenges: bool = True
    solve_turnstile_challenges: bool = False
    challenge_timeout: float = 30.0
    max_challenge_attempts: int = 3

    # Rate limiting
    enable_adaptive_rate: bool = True
    min_rate_limit: float = 1.0
    max_rate_limit: float = 100.0

    # Monitoring
    enable_monitoring: bool = True
    enable_detailed_logging: bool = False

    # Session management
    session_persistence: bool = True
    max_session_age: float = 3600.0  # 1 hour

    # Proxy support
    proxy_url: Optional[str] = None
    proxy_rotation: bool = False


class CloudflareBypass:
    """Main class for bypassing Cloudflare protection with high performance."""

    def __init__(self, config: Optional[CloudflareBypassConfig] = None):
        self.config = config or CloudflareBypassConfig()

        # Core components
        self.http_client: Optional[BrowserHTTPClient] = None
        self.browser_session: Optional[BrowserSession] = None
        self.concurrency_manager: Optional[ConcurrencyManager] = None
        self.rate_limiter: Optional[AdvancedRateLimiter] = None

        # Session management
        self.sessions: Dict[str, BrowserSession] = {}
        self.default_session_id = "default"

        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        self.challenge_records: List[ChallengeRecord] = []

        # State
        self._initialized = False
        self._closed = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        # Initialize HTTP client
        http_config = HTTPClientConfig(
            browser_version=self.config.chrome_version,
            timeout=int(self.config.timeout),
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
            handle_challenges=self.config.solve_javascript_challenges,
            requests_per_second=self.config.requests_per_second,
            proxy_url=self.config.proxy_url,
        )

        self.http_client = BrowserHTTPClient(http_config)
        await self.http_client._initialize()

        # Initialize browser session
        self.browser_session = BrowserSession(self.config.chrome_version)
        self.sessions[self.default_session_id] = self.browser_session

        # Initialize concurrency manager
        concurrency_config = ConcurrencyConfig(
            max_concurrent_tasks=self.config.max_concurrent_requests,
            enable_metrics=self.config.enable_monitoring,
        )
        self.concurrency_manager = ConcurrencyManager(concurrency_config)
        await self.concurrency_manager.start()

        # Initialize rate limiter
        rate_config = RateLimitConfig(
            requests_per_second=self.config.requests_per_second,
            enable_adaptive=self.config.enable_adaptive_rate,
            min_rate=self.config.min_rate_limit,
            max_rate=self.config.max_rate_limit,
        )
        self.rate_limiter = AdvancedRateLimiter(rate_config)

        self._initialized = True

    async def get(self, url: str, **kwargs) -> RequestResult:
        """Perform GET request with Cloudflare bypass."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, data: Optional[Any] = None,
                  json_data: Optional[Dict[str, Any]] = None, **kwargs) -> RequestResult:
        """Perform POST request with Cloudflare bypass."""
        if json_data:
            kwargs["json"] = json_data
        elif data:
            kwargs["data"] = data
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, data: Optional[Any] = None,
                 json_data: Optional[Dict[str, Any]] = None, **kwargs) -> RequestResult:
        """Perform PUT request with Cloudflare bypass."""
        if json_data:
            kwargs["json"] = json_data
        elif data:
            kwargs["data"] = data
        return await self._request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> RequestResult:
        """Perform DELETE request with Cloudflare bypass."""
        return await self._request("DELETE", url, **kwargs)

    async def head(self, url: str, **kwargs) -> RequestResult:
        """Perform HEAD request with Cloudflare bypass."""
        return await self._request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> RequestResult:
        """Perform OPTIONS request with Cloudflare bypass."""
        return await self._request("OPTIONS", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> RequestResult:
        """Internal request method with full bypass logic."""
        if not self._initialized:
            await self.initialize()

        # Apply rate limiting
        if not await self.rate_limiter.acquire():
            return RequestResult(
                url=url,
                status_code=0,
                headers={},
                content=b"",
                text="",
                cookies={},
                timing=RequestTiming(),
                success=False,
                error_message="Rate limited"
            )

        # Get session
        session_id = kwargs.pop("session_id", self.default_session_id)
        session = self.sessions.get(session_id)
        if not session:
            session = BrowserSession(self.config.chrome_version)
            self.sessions[session_id] = session

        # Prepare headers
        request_type = kwargs.pop("request_type", RequestType.DOCUMENT)
        referer = kwargs.pop("referer", "")
        headers = session.get_headers(request_type, url, referer)
        headers.update(kwargs.pop("headers", {}))

        # Add cookies
        if session.cookies:
            cookie_header = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
            headers["Cookie"] = cookie_header

        try:
            # Make request
            start_time = time.time()
            response = await self.http_client.request(method, url, headers=headers, **kwargs)
            request_time = time.time() - start_time

            # Update session
            session.update_cookies(response.cookies)
            session.mark_used()

            # Record metrics
            await self.rate_limiter.record_result(response.ok)
            self.performance_metrics.requests_sent += 1

            if response.ok:
                self.performance_metrics.requests_successful += 1
            else:
                self.performance_metrics.requests_failed += 1

            # Check for challenges
            challenge_type = self._detect_challenge_type(response)
            challenge_solved = False

            if challenge_type != ChallengeType.NONE:
                self.performance_metrics.challenges_detected += 1
                # Challenge handling is done by HTTP client
                challenge_solved = response.ok

            # Create result
            result = RequestResult(
                url=response.url,
                status_code=response.status_code,
                headers=response.headers,
                content=response.content,
                text=response.text,
                cookies=response.cookies,
                timing=RequestTiming(total_duration_ms=int(request_time * 1000)),
                success=response.ok,
                challenge_type=challenge_type,
                challenge_solved=challenge_solved,
                tls_info=response._response.tls_info if hasattr(response._response, 'tls_info') else {}
            )

            return result

        except Exception as e:
            await self.rate_limiter.record_result(False)
            self.performance_metrics.requests_failed += 1

            return RequestResult(
                url=url,
                status_code=0,
                headers={},
                content=b"",
                text="",
                cookies={},
                timing=RequestTiming(),
                success=False,
                error_message=str(e)
            )

    def _detect_challenge_type(self, response: HTTPResponse) -> ChallengeType:
        """Detect Cloudflare challenge type from response."""
        if response.status_code not in [403, 503, 429]:
            return ChallengeType.NONE

        text_lower = response.text.lower()

        if any(pattern in text_lower for pattern in ["cf_chl_opt", "challenge-form"]):
            return ChallengeType.JAVASCRIPT
        elif "turnstile" in text_lower:
            return ChallengeType.TURNSTILE
        elif "rate limited" in text_lower:
            return ChallengeType.RATE_LIMITED
        elif "just a moment" in text_lower:
            return ChallengeType.MANAGED
        else:
            return ChallengeType.UNKNOWN

    async def batch_get(self, urls: List[str], **kwargs) -> List[RequestResult]:
        """Perform batch GET requests with concurrency control."""
        if not self._initialized:
            await self.initialize()

        # Create coroutines
        coros = [self.get(url, **kwargs) for url in urls]

        # Submit to concurrency manager
        futures = []
        for coro in coros:
            future = await self.concurrency_manager.submit_task(coro)
            futures.append(future)

        # Wait for completion
        results = []
        for future in futures:
            try:
                result = await future
                results.append(result)
            except Exception as e:
                # Create error result
                error_result = RequestResult(
                    url="unknown",
                    status_code=0,
                    headers={},
                    content=b"",
                    text="",
                    cookies={},
                    timing=RequestTiming(),
                    success=False,
                    error_message=str(e)
                )
                results.append(error_result)

        return results

    async def batch_post(self, requests: List[Tuple[str, Any]], **kwargs) -> List[RequestResult]:
        """Perform batch POST requests."""
        if not self._initialized:
            await self.initialize()

        coros = [self.post(url, data=data, **kwargs) for url, data in requests]

        futures = []
        for coro in coros:
            future = await self.concurrency_manager.submit_task(coro)
            futures.append(future)

        results = []
        for future in futures:
            try:
                result = await future
                results.append(result)
            except Exception as e:
                error_result = RequestResult(
                    url="unknown",
                    status_code=0,
                    headers={},
                    content=b"",
                    text="",
                    cookies={},
                    timing=RequestTiming(),
                    success=False,
                    error_message=str(e)
                )
                results.append(error_result)

        return results

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.performance_metrics

    def get_session_info(self, session_id: str = None) -> Dict[str, Any]:
        """Get session information."""
        session_id = session_id or self.default_session_id
        session = self.sessions.get(session_id)

        if not session:
            return {}

        return {
            "session_id": session.session_id,
            "chrome_version": session.chrome_version,
            "created_at": session.created_at,
            "last_used": session.last_used,
            "request_count": session.request_count,
            "cookies_count": len(session.cookies),
            "fingerprint": {
                "user_agent": session.fingerprint.user_agent,
                "screen_resolution": session.fingerprint.screen_resolution,
                "timezone": session.fingerprint.timezone,
            }
        }

    async def close(self) -> None:
        """Close all resources and cleanup."""
        if self._closed:
            return

        if self.http_client:
            await self.http_client.close()

        if self.concurrency_manager:
            await self.concurrency_manager.stop()

        self._closed = True


# =============================================================================
# SYNC INTERFACE (CLOUDSCRAPER COMPATIBILITY)
# =============================================================================

class ScrapeResponse:
    """Response wrapper for sync interface."""

    def __init__(self, request_result: RequestResult):
        self._result = request_result

    @property
    def status_code(self) -> int:
        return self._result.status_code

    @property
    def headers(self) -> Dict[str, str]:
        return self._result.headers

    @property
    def content(self) -> bytes:
        return self._result.content

    @property
    def text(self) -> str:
        return self._result.text

    @property
    def url(self) -> str:
        return self._result.url

    @property
    def cookies(self) -> Dict[str, str]:
        return self._result.cookies

    @property
    def ok(self) -> bool:
        return self._result.ok

    @property
    def elapsed(self) -> float:
        return self._result.timing.total_duration_ms / 1000.0

    def json(self) -> Any:
        return self._result.json

    def raise_for_status(self) -> None:
        if not self.ok:
            raise HTTPClientError(f"HTTP {self.status_code}")


class CloudflareScraper:
    """Sync interface compatible with cloudscraper."""

    def __init__(self, **kwargs):
        # Extract configuration from kwargs
        config = CloudflareBypassConfig()

        if "browser" in kwargs:
            browser_info = kwargs["browser"]
            if isinstance(browser_info, dict):
                config.chrome_version = browser_info.get("browser", DEFAULT_CHROME_VERSION)

        if "delay" in kwargs:
            config.requests_per_second = 1.0 / kwargs["delay"]

        if "timeout" in kwargs:
            config.timeout = kwargs["timeout"]

        # Initialize bypass
        self._bypass = CloudflareBypass(config)
        self._loop = None
        self._thread = None
        self._initialized = False

        # Session state
        self.cookies = {}
        self.headers = {}

    def _ensure_loop(self):
        """Ensure event loop is running in thread."""
        if not self._initialized:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            # Wait for initialization
            while not self._initialized:
                time.sleep(0.01)

    def _run_loop(self):
        """Run event loop in separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Initialize bypass
        self._loop.run_until_complete(self._bypass.initialize())
        self._initialized = True

        # Keep loop running
        try:
            self._loop.run_forever()
        except:
            pass

    def _run_async(self, coro):
        """Run async coroutine from sync context."""
        self._ensure_loop()

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self._bypass.config.timeout + 10)

    def get(self, url: str, **kwargs) -> ScrapeResponse:
        """Perform GET request (sync)."""
        # Merge session headers and cookies
        headers = self.headers.copy()
        headers.update(kwargs.pop("headers", {}))

        if self.cookies and "cookies" not in kwargs:
            kwargs["cookies"] = self.cookies

        result = self._run_async(self._bypass.get(url, headers=headers, **kwargs))

        # Update session state
        self.cookies.update(result.cookies)

        return ScrapeResponse(result)

    def post(self, url: str, data=None, **kwargs) -> ScrapeResponse:
        """Perform POST request (sync)."""
        headers = self.headers.copy()
        headers.update(kwargs.pop("headers", {}))

        if self.cookies and "cookies" not in kwargs:
            kwargs["cookies"] = self.cookies

        result = self._run_async(self._bypass.post(url, data=data, headers=headers, **kwargs))

        # Update session state
        self.cookies.update(result.cookies)

        return ScrapeResponse(result)

    def put(self, url: str, data=None, **kwargs) -> ScrapeResponse:
        """Perform PUT request (sync)."""
        headers = self.headers.copy()
        headers.update(kwargs.pop("headers", {}))

        if self.cookies and "cookies" not in kwargs:
            kwargs["cookies"] = self.cookies

        result = self._run_async(self._bypass.put(url, data=data, headers=headers, **kwargs))

        # Update session state
        self.cookies.update(result.cookies)

        return ScrapeResponse(result)

    def delete(self, url: str, **kwargs) -> ScrapeResponse:
        """Perform DELETE request (sync)."""
        headers = self.headers.copy()
        headers.update(kwargs.pop("headers", {}))

        if self.cookies and "cookies" not in kwargs:
            kwargs["cookies"] = self.cookies

        result = self._run_async(self._bypass.delete(url, headers=headers, **kwargs))

        # Update session state
        self.cookies.update(result.cookies)

        return ScrapeResponse(result)

    def head(self, url: str, **kwargs) -> ScrapeResponse:
        """Perform HEAD request (sync)."""
        headers = self.headers.copy()
        headers.update(kwargs.pop("headers", {}))

        if self.cookies and "cookies" not in kwargs:
            kwargs["cookies"] = self.cookies

        result = self._run_async(self._bypass.head(url, headers=headers, **kwargs))

        # Update session state
        self.cookies.update(result.cookies)

        return ScrapeResponse(result)

    def close(self):
        """Close the scraper and cleanup resources."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._bypass.close(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)


# =============================================================================
# FACTORY FUNCTIONS AND UTILITIES
# =============================================================================

def create_scraper(**kwargs) -> CloudflareScraper:
    """Create a new CloudflareScraper instance (cloudscraper compatibility)."""
    return CloudflareScraper(**kwargs)


def create_cloudflare_bypass(max_concurrent: int = 100,
                           requests_per_second: float = 10.0,
                           **kwargs) -> CloudflareBypass:
    """Create a CloudflareBypass instance with custom configuration."""
    config = CloudflareBypassConfig(
        max_concurrent_requests=max_concurrent,
        requests_per_second=requests_per_second,
        **kwargs
    )
    return CloudflareBypass(config)


def create_high_performance_bypass(max_concurrent: int = 1000,
                                 requests_per_second: float = 100.0) -> CloudflareBypass:
    """Create high-performance bypass configuration."""
    config = CloudflareBypassConfig(
        max_concurrent_requests=max_concurrent,
        requests_per_second=requests_per_second,
        enable_adaptive_rate=True,
        enable_monitoring=True,
        enable_browser_emulation=True,
        enable_tls_fingerprinting=True,
        solve_javascript_challenges=True,
    )
    return CloudflareBypass(config)


def create_stealth_bypass(max_concurrent: int = 10,
                        requests_per_second: float = 2.0) -> CloudflareBypass:
    """Create stealth bypass configuration for avoiding detection."""
    config = CloudflareBypassConfig(
        max_concurrent_requests=max_concurrent,
        requests_per_second=requests_per_second,
        enable_adaptive_rate=True,
        enable_browser_emulation=True,
        enable_tls_fingerprinting=True,
        ja3_randomization=True,
        solve_javascript_challenges=True,
        retry_delay=5.0,  # Longer delays
    )
    return CloudflareBypass(config)


# Sync convenience functions (cloudscraper compatibility)
def get(url: str, **kwargs) -> ScrapeResponse:
    """Perform single GET request (sync)."""
    scraper = create_scraper()
    try:
        return scraper.get(url, **kwargs)
    finally:
        scraper.close()


def post(url: str, data=None, **kwargs) -> ScrapeResponse:
    """Perform single POST request (sync)."""
    scraper = create_scraper()
    try:
        return scraper.post(url, data=data, **kwargs)
    finally:
        scraper.close()


# Async convenience functions
async def quick_test(url: str, **kwargs) -> RequestResult:
    """Quick test of a single URL (async)."""
    async with create_cloudflare_bypass() as bypass:
        return await bypass.get(url, **kwargs)


async def batch_test(urls: List[str], max_concurrent: int = 100, **kwargs) -> List[RequestResult]:
    """Batch test multiple URLs (async)."""
    async with create_cloudflare_bypass(max_concurrent=max_concurrent) as bypass:
        return await bypass.batch_get(urls, **kwargs)


# Utility functions
def get_random_chrome_version() -> str:
    """Get a random Chrome version."""
    return random.choice(CHROME_VERSIONS)


def get_chrome_headers(version: str = DEFAULT_CHROME_VERSION, mobile: bool = False) -> Dict[str, str]:
    """Get Chrome-compatible headers."""
    generator = ChromeHeadersGenerator(version)
    return generator.get_headers(mobile=mobile)


def generate_ja3_fingerprint(version: str = DEFAULT_CHROME_VERSION) -> str:
    """Generate JA3 fingerprint for Chrome version."""
    manager = ChromeTLSFingerprintManager()
    fingerprint = manager.get_fingerprint_by_string(version)
    return manager.get_ja3_fingerprint(fingerprint)


def detect_challenge_quick(response_text: str, status_code: int,
                         headers: Dict[str, str]) -> ChallengeType:
    """Quick challenge detection."""
    detector = CloudflareDetector()
    challenge_info = detector.detect_challenge(response_text, status_code, headers)
    return challenge_info.challenge_type


# =============================================================================
# MODULE METADATA AND EXPORTS
# =============================================================================

__version__ = "1.0.0"
__author__ = "Cloudflare Research Team"
__license__ = "MIT"
__title__ = "cloudflare-scraper-standalone"
__description__ = "Complete CloudflareScraper implementation in a single file"

# Export public API
__all__ = [
    # Main classes
    "CloudflareBypass",
    "CloudflareBypassConfig",
    "CloudflareScraper",
    "ScrapeResponse",

    # Data models
    "RequestResult",
    "TestRequest",
    "TestSession",
    "ChallengeRecord",
    "PerformanceMetrics",
    "RequestTiming",
    "BrowserConfig",
    "ProxyConfig",

    # Enums
    "HttpMethod",
    "RequestStatus",
    "ChallengeType",
    "RequestType",
    "TaskPriority",
    "ChromeVersion",

    # Browser emulation
    "BrowserSession",
    "BrowserFingerprint",
    "ChromeHeadersGenerator",
    "BrowserTimingEmulator",

    # TLS fingerprinting
    "TLSFingerprint",
    "ChromeTLSFingerprintManager",

    # Challenge handling
    "ChallengeInfo",
    "ChallengeSolution",
    "ChallengeResult",
    "CloudflareDetector",
    "JSChallengeSolver",
    "ChallengeHandler",

    # HTTP client
    "BrowserHTTPClient",
    "HTTPClientConfig",
    "HTTPResponse",

    # Concurrency
    "ConcurrencyManager",
    "AdvancedRateLimiter",
    "RateLimitConfig",

    # Factory functions
    "create_scraper",
    "create_cloudflare_bypass",
    "create_high_performance_bypass",
    "create_stealth_bypass",

    # Sync convenience functions
    "get",
    "post",

    # Async convenience functions
    "quick_test",
    "batch_test",

    # Utility functions
    "get_random_chrome_version",
    "get_chrome_headers",
    "generate_ja3_fingerprint",
    "detect_challenge_quick",

    # Constants
    "DEFAULT_CHROME_VERSION",
    "CHROME_VERSIONS",
    "USER_AGENTS",

    # Exceptions
    "HTTPClientError",
    "ChallengeError",
]

# Module docstring
__doc__ = f"""
cloudflare-scraper-standalone v{__version__}

{__description__}

A complete, self-contained implementation of CloudflareScraper that includes:
- Browser fingerprint emulation (Chrome profiles)
- TLS fingerprinting with JA3 generation
- JavaScript challenge detection and solving
- High-concurrency operations (1000+ requests)
- Advanced rate limiting and backpressure handling
- Session management and cookie handling
- Performance monitoring and metrics
- Both sync and async interfaces
- cloudscraper-compatible API

Quick Start (Sync):
    import cloudflare_scraper_standalone as cfs

    # Simple request
    scraper = cfs.create_scraper()
    response = scraper.get("https://example.com")
    print(response.text)
    scraper.close()

    # One-off request
    response = cfs.get("https://example.com")
    print(response.status_code)

Quick Start (Async):
    import cloudflare_scraper_standalone as cfs

    # Single request
    result = await cfs.quick_test("https://example.com")
    print(f"Status: {{result.status_code}}, Success: {{result.success}}")

    # High-performance batch
    async with cfs.create_high_performance_bypass(max_concurrent=500) as bypass:
        results = await bypass.batch_get(urls)

    # Custom configuration
    config = cfs.CloudflareBypassConfig(
        max_concurrent_requests=100,
        requests_per_second=50,
        solve_javascript_challenges=True
    )
    async with cfs.CloudflareBypass(config) as bypass:
        result = await bypass.get("https://example.com")

Dependencies:
- Minimal external dependencies (aiohttp, curl-cffi optional)
- py-mini-racer for JavaScript execution (optional, has fallback)
- Standard library only for basic functionality

For advanced usage and configuration options, see the individual class documentation.
"""

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Module initialization message
if __name__ != "__main__":
    logger = logging.getLogger(__name__)
    logger.info(f"CloudflareScraper Standalone v{__version__} loaded")
    logger.info(f"MiniRacer available: {MINIRACER_AVAILABLE}")
    logger.info(f"curl-cffi available: {CURL_CFFI_AVAILABLE}")
    logger.info(f"aiohttp available: {aiohttp is not None}")


# =============================================================================
# MAIN EXECUTION (for testing)
# =============================================================================

if __name__ == "__main__":
    # Test script
    async def main():
        print(f"CloudflareScraper Standalone v{__version__}")
        print("Running basic functionality test...")

        # Test sync interface
        print("\n1. Testing sync interface:")
        try:
            scraper = create_scraper()
            response = scraper.get("https://httpbin.org/get")
            print(f"   Status: {response.status_code}")
            print(f"   Success: {response.ok}")
            scraper.close()
        except Exception as e:
            print(f"   Error: {e}")

        # Test async interface
        print("\n2. Testing async interface:")
        try:
            result = await quick_test("https://httpbin.org/get")
            print(f"   Status: {result.status_code}")
            print(f"   Success: {result.success}")
        except Exception as e:
            print(f"   Error: {e}")

        # Test batch operations
        print("\n3. Testing batch operations:")
        try:
            urls = ["https://httpbin.org/get", "https://httpbin.org/uuid"]
            results = await batch_test(urls, max_concurrent=2)
            print(f"   Processed {len(results)} URLs")
            print(f"   Success rate: {sum(1 for r in results if r.success) / len(results):.2%}")
        except Exception as e:
            print(f"   Error: {e}")

        # Test utilities
        print("\n4. Testing utilities:")
        try:
            version = get_random_chrome_version()
            print(f"   Random Chrome version: {version}")

            headers = get_chrome_headers(version)
            print(f"   Generated {len(headers)} headers")

            ja3 = generate_ja3_fingerprint(version)
            print(f"   JA3 fingerprint: {ja3[:50]}...")
        except Exception as e:
            print(f"   Error: {e}")

        print("\nTest completed!")

    # Run test
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")