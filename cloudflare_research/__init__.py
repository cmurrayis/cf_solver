"""High-Performance Browser Emulation Module for Cloudflare Challenge Research.

A comprehensive Python module that enables researchers to conduct legitimate testing
and analysis of Cloudflare-protected infrastructure by emulating browser behavior
at scale for security research, performance analysis, and quality assurance purposes.

Key Features:
- High-performance concurrent operations (10,000+ requests)
- Advanced browser fingerprinting and emulation
- TLS fingerprinting with Chrome-compatible profiles
- JavaScript challenge solving
- Rate limiting and backpressure handling
- Comprehensive performance monitoring
- HTTP/2 support with stream management
"""

import time
from typing import Dict, List, Any

# Simple scraper interface (cloudscraper-like) - PRIMARY INTERFACE
from .scraper import (
    create_scraper,
    CloudflareScraper,
    ScrapeResponse,
    get,
    post,
)

# Main bypass interface
from .bypass import (
    CloudflareBypass,
    CloudflareBypassConfig,
    create_cloudflare_bypass,
    create_high_performance_bypass,
    create_stealth_bypass,
)

# Core models and data structures
from .models import (
    TestRequest,
    RequestResult,
    TestSession,
    ChallengeRecord,
    PerformanceMetrics,
    TestConfiguration,
    HttpMethod,
    RequestTiming,
    BrowserConfig,
    ProxyConfig,
)

# Browser emulation components
from .browser import (
    BrowserSession,
    RequestType,
    RequestContext,
    ChromeHeadersGenerator,
    BrowserFingerprint,
    BrowserFingerprintManager,
    BrowserTimingEmulator,
    create_browser_session,
    get_random_chrome_version,
    DEFAULT_CHROME_VERSION,
    CHROME_VERSIONS,
)

# HTTP and networking
from .http import (
    AsyncHTTPClient,
    BrowserHTTPClient,
    HTTPClientConfig,
    HTTPResponse,
    EnhancedResponse,
    create_browser_client,
    get_chrome_headers,
)

# TLS fingerprinting
from .tls import (
    TLSFingerprint,
    TLSFingerprintManager,
    create_tls_fingerprint_manager,
    get_chrome_tls_fingerprint,
    generate_ja3_fingerprint,
)

# Challenge detection and solving
from .challenge import (
    ChallengeType,
    ChallengeInfo,
    ChallengeSolution,
    ChallengeResult,
    ChallengeConfig,
    CloudflareDetector,
    JSChallengeSolver,
    ChallengeHandler,
    ChallengeManager,
    create_challenge_manager,
    detect_challenge_quick,
    analyze_challenge_response,
)

# Concurrency and performance
from .concurrency import (
    TaskPriority,
    RateLimitAlgorithm,
    ConcurrencyManager,
    AdvancedRateLimiter,
    ComprehensiveMonitor,
    HighPerformanceManager,
    create_high_performance_manager,
    create_conservative_manager,
)

# Version information
__version__ = "1.0.0"
__author__ = "Cloudflare Research Team"
__license__ = "MIT"

# Module metadata
__title__ = "cloudflare-research"
__description__ = "High-Performance Browser Emulation Module for Cloudflare Challenge Research"
__url__ = "https://github.com/cloudflare-research/cf-solver"

# API compatibility levels
API_VERSION = "1.0"
SUPPORTED_CHROME_VERSIONS = [
    "124.0.6367.60",
    "124.0.6367.78",
    "124.0.6367.91",
    "124.0.6367.118",
    "125.0.6422.60",
    "125.0.6422.76",
    "125.0.6422.112",
]

# Default configuration presets
DEFAULT_CONFIG = CloudflareBypassConfig()

HIGH_PERFORMANCE_CONFIG = CloudflareBypassConfig(
    max_concurrent_requests=5000,
    requests_per_second=1000.0,
    enable_adaptive_rate=True,
    enable_monitoring=True,
    enable_browser_emulation=True,
    enable_tls_fingerprinting=True,
    solve_javascript_challenges=True,
)

STEALTH_CONFIG = CloudflareBypassConfig(
    max_concurrent_requests=50,
    requests_per_second=10.0,
    enable_adaptive_rate=True,
    enable_monitoring=True,
    enable_browser_emulation=True,
    enable_tls_fingerprinting=True,
    ja3_randomization=True,
    solve_javascript_challenges=True,
)

RESEARCH_CONFIG = CloudflareBypassConfig(
    max_concurrent_requests=100,
    requests_per_second=25.0,
    enable_adaptive_rate=True,
    enable_monitoring=True,
    enable_browser_emulation=True,
    enable_tls_fingerprinting=True,
    solve_javascript_challenges=True,
    enable_detailed_logging=True,
)


# Convenience functions for common use cases
async def quick_test(url: str, **kwargs) -> RequestResult:
    """
    Quick test of a single URL with default configuration.

    Args:
        url: Target URL to test
        **kwargs: Additional request parameters

    Returns:
        RequestResult with response data and metrics
    """
    async with create_cloudflare_bypass() as bypass:
        return await bypass.get(url, **kwargs)


async def batch_test(urls: List[str], max_concurrent: int = 100, **kwargs) -> List[RequestResult]:
    """
    Batch test multiple URLs with concurrency control.

    Args:
        urls: List of URLs to test
        max_concurrent: Maximum concurrent requests
        **kwargs: Additional request parameters

    Returns:
        List of RequestResult objects
    """
    async with create_cloudflare_bypass(max_concurrent=max_concurrent) as bypass:
        return await bypass.batch_get(urls, **kwargs)


async def performance_test(url: str, num_requests: int = 100,
                         max_concurrent: int = 50) -> Dict[str, Any]:
    """
    Performance test a URL with multiple concurrent requests.

    Args:
        url: Target URL to test
        num_requests: Total number of requests to make
        max_concurrent: Maximum concurrent requests

    Returns:
        Performance metrics and results
    """
    urls = [f"{url}?test={i}" for i in range(num_requests)]

    start_time = time.time()
    async with create_cloudflare_bypass(max_concurrent=max_concurrent) as bypass:
        results = await bypass.batch_get(urls)
    total_time = time.time() - start_time

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return {
        "total_requests": len(results),
        "successful_requests": successful,
        "failed_requests": failed,
        "success_rate": successful / len(results),
        "total_time_seconds": total_time,
        "requests_per_second": len(results) / total_time,
        "avg_response_time_ms": sum(r.timing.total_duration_ms for r in results) / len(results),
        "results": results
    }


def get_module_info() -> Dict[str, Any]:
    """Get module information and capabilities."""
    return {
        "version": __version__,
        "api_version": API_VERSION,
        "supported_chrome_versions": SUPPORTED_CHROME_VERSIONS,
        "features": {
            "browser_emulation": True,
            "tls_fingerprinting": True,
            "javascript_challenge_solving": True,
            "high_concurrency": True,
            "rate_limiting": True,
            "performance_monitoring": True,
            "http2_support": True,
            "adaptive_rate_limiting": True,
        },
        "performance_limits": {
            "max_concurrent_requests": 10000,
            "max_requests_per_second": 5000,
            "supported_challenge_types": [
                "javascript",
                "rate_limited",
                "managed",
                "turnstile"
            ]
        }
    }


# Export public API
__all__ = [
    # Simple interface (cloudscraper-like) - PRIMARY
    "create_scraper",
    "CloudflareScraper",
    "ScrapeResponse",
    "get",
    "post",

    # Main classes
    "CloudflareBypass",
    "CloudflareBypassConfig",

    # Core models
    "TestRequest",
    "RequestResult",
    "TestSession",
    "ChallengeRecord",
    "PerformanceMetrics",
    "TestConfiguration",

    # Enums
    "HttpMethod",
    "ChallengeType",
    "RequestType",
    "TaskPriority",
    "RateLimitAlgorithm",

    # Browser emulation
    "BrowserSession",
    "BrowserFingerprint",
    "ChromeHeadersGenerator",
    "BrowserTimingEmulator",

    # HTTP and TLS
    "BrowserHTTPClient",
    "HTTPClientConfig",
    "TLSFingerprint",
    "TLSFingerprintManager",

    # Challenge handling
    "ChallengeManager",
    "JSChallengeSolver",
    "ChallengeHandler",

    # Concurrency
    "HighPerformanceManager",
    "ConcurrencyManager",
    "AdvancedRateLimiter",
    "ComprehensiveMonitor",

    # Factory functions
    "create_cloudflare_bypass",
    "create_high_performance_bypass",
    "create_stealth_bypass",
    "create_browser_session",
    "create_challenge_manager",
    "create_high_performance_manager",

    # Configuration presets
    "DEFAULT_CONFIG",
    "HIGH_PERFORMANCE_CONFIG",
    "STEALTH_CONFIG",
    "RESEARCH_CONFIG",

    # Convenience functions
    "quick_test",
    "batch_test",
    "performance_test",
    "get_module_info",

    # Constants
    "DEFAULT_CHROME_VERSION",
    "CHROME_VERSIONS",
    "SUPPORTED_CHROME_VERSIONS",
    "API_VERSION",

    # Utility functions
    "get_random_chrome_version",
    "detect_challenge_quick",
    "analyze_challenge_response",
    "get_chrome_headers",
    "generate_ja3_fingerprint",

    # Version info
    "__version__",
    "__author__",
    "__license__",
    "__title__",
    "__description__",
]


# Module initialization
def _initialize_logging():
    """Initialize default logging configuration."""
    import logging

    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


# Initialize on import
_initialize_logging()

# Module docstring for help()
__doc__ = f"""
cloudflare-research v{__version__}

{__description__}

This module provides a comprehensive toolkit for researching and testing
Cloudflare-protected websites through legitimate browser emulation and
challenge solving capabilities.

Quick Start:
    >>> import cloudflare_research as cf
    >>>
    >>> # Simple single request
    >>> result = await cf.quick_test("https://example.com")
    >>> print(f"Status: {{result.status_code}}, Success: {{result.success}}")
    >>>
    >>> # High-performance batch testing
    >>> bypass = cf.create_high_performance_bypass(max_concurrent=1000)
    >>> async with bypass:
    ...     results = await bypass.batch_get(urls)
    >>>
    >>> # Custom configuration
    >>> config = cf.CloudflareBypassConfig(
    ...     max_concurrent_requests=500,
    ...     requests_per_second=100,
    ...     solve_javascript_challenges=True
    ... )
    >>> bypass = cf.CloudflareBypass(config)

Key Features:
- Browser fingerprint emulation (Chrome profiles)
- TLS fingerprinting with JA3 generation
- JavaScript challenge solving
- High-concurrency operations (10k+ requests)
- Advanced rate limiting and backpressure handling
- Comprehensive performance monitoring
- HTTP/2 support with proper stream management

For detailed documentation and examples, visit:
{__url__}
"""