"""TLS module for Chrome browser emulation.

This module provides TLS fingerprinting and client capabilities for
accurate Chrome browser emulation.
"""

from .fingerprint import (
    ChromeTLSFingerprintManager,
    TLSFingerprint,
    ChromeVersion,
    TLSVersion,
    TLSExtension,
    CipherSuite,
)

from .client import (
    CurlCffiClient,
    TLSClientConfig,
    TLSResponse,
    TLSClientError,
    create_tls_client,
    get_supported_chrome_versions,
    validate_chrome_version,
)

# Aliases for compatibility
TLSFingerprintManager = ChromeTLSFingerprintManager

# Convenience functions
def create_fingerprint_manager() -> ChromeTLSFingerprintManager:
    """Create a new TLS fingerprint manager instance."""
    return ChromeTLSFingerprintManager()

def create_tls_fingerprint_manager() -> ChromeTLSFingerprintManager:
    """Create a new TLS fingerprint manager instance (alias)."""
    return ChromeTLSFingerprintManager()

def get_chrome_fingerprint(version: str = "124.0.0.0") -> TLSFingerprint:
    """Get TLS fingerprint for specified Chrome version."""
    manager = ChromeTLSFingerprintManager()
    return manager.get_fingerprint_by_string(version)

def get_ja3_fingerprint(version: str = "124.0.0.0") -> str:
    """Get JA3 fingerprint string for specified Chrome version."""
    manager = ChromeTLSFingerprintManager()
    fingerprint = manager.get_fingerprint_by_string(version)
    return manager.get_ja3_fingerprint(fingerprint)

def generate_ja3_fingerprint(version: str = "124.0.0.0") -> str:
    """Generate JA3 fingerprint string for specified Chrome version (alias)."""
    return get_ja3_fingerprint(version)

def get_chrome_tls_fingerprint(version: str = "124.0.0.0") -> TLSFingerprint:
    """Get Chrome TLS fingerprint (alias for get_chrome_fingerprint)."""
    return get_chrome_fingerprint(version)

# Default configurations
DEFAULT_CHROME_VERSION = "124.0.0.0"
SUPPORTED_PROTOCOLS = ["h2", "http/1.1"]
DEFAULT_CIPHER_SUITES = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
]

# Export public API
__all__ = [
    # Classes
    "ChromeTLSFingerprintManager",
    "TLSFingerprintManager",  # Alias
    "TLSFingerprint",
    "CurlCffiClient",
    "TLSClientConfig",
    "TLSResponse",

    # Enums
    "ChromeVersion",
    "TLSVersion",

    # Data classes
    "TLSExtension",
    "CipherSuite",

    # Exceptions
    "TLSClientError",

    # Functions
    "create_fingerprint_manager",
    "create_tls_fingerprint_manager",  # Alias
    "get_chrome_fingerprint",
    "get_chrome_tls_fingerprint",  # Alias
    "get_ja3_fingerprint",
    "generate_ja3_fingerprint",  # Alias
    "create_tls_client",
    "get_supported_chrome_versions",
    "validate_chrome_version",

    # Constants
    "DEFAULT_CHROME_VERSION",
    "SUPPORTED_PROTOCOLS",
    "DEFAULT_CIPHER_SUITES",
]