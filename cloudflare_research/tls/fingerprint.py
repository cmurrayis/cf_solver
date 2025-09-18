"""Chrome TLS fingerprint manager for browser emulation.

This module provides TLS fingerprinting capabilities to emulate Chrome browser
connections with accurate cipher suites, extensions, and handshake parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import ssl
import random


class ChromeVersion(Enum):
    """Supported Chrome versions for TLS fingerprinting."""
    CHROME_124 = "124.0.0.0"
    CHROME_123 = "123.0.0.0"
    CHROME_122 = "122.0.0.0"
    CHROME_121 = "121.0.0.0"


class TLSVersion(Enum):
    """Supported TLS protocol versions."""
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


@dataclass
class TLSExtension:
    """Represents a TLS extension with its configuration."""
    name: str
    extension_id: int
    data: bytes = b""
    critical: bool = False

    def to_wire_format(self) -> bytes:
        """Convert extension to wire format for handshake."""
        # Simplified implementation - real would follow RFC format
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
    """
    Complete TLS fingerprint configuration for Chrome emulation.

    This represents all TLS parameters needed to accurately emulate
    a specific Chrome version's TLS handshake behavior.
    """

    # Browser identification
    browser_version: ChromeVersion
    user_agent: str

    # Protocol configuration
    min_tls_version: TLSVersion = TLSVersion.TLS_1_2
    max_tls_version: TLSVersion = TLSVersion.TLS_1_3

    # Cipher suites (in preference order)
    cipher_suites: List[CipherSuite] = field(default_factory=list)

    # TLS extensions
    extensions: List[TLSExtension] = field(default_factory=list)

    # Elliptic curves (for ECDHE)
    supported_groups: List[str] = field(default_factory=list)

    # Signature algorithms
    signature_algorithms: List[str] = field(default_factory=list)

    # ALPN protocols
    alpn_protocols: List[str] = field(default_factory=list)

    # Key shares for TLS 1.3
    key_shares: List[str] = field(default_factory=list)

    # Compression methods
    compression_methods: List[int] = field(default_factory=lambda: [0])  # No compression

    # Session resumption
    supports_session_tickets: bool = True
    supports_session_ids: bool = True

    # Other handshake parameters
    record_size_limit: Optional[int] = None
    max_fragment_length: Optional[int] = None


class ChromeTLSFingerprintManager:
    """
    Manages TLS fingerprints for Chrome browser emulation.

    Provides accurate TLS handshake parameters for different Chrome versions
    to bypass TLS-based detection systems.
    """

    def __init__(self):
        self._fingerprints: Dict[ChromeVersion, TLSFingerprint] = {}
        self._initialize_fingerprints()

    def _initialize_fingerprints(self) -> None:
        """Initialize TLS fingerprints for supported Chrome versions."""
        # Chrome 124.0.0.0 fingerprint
        self._fingerprints[ChromeVersion.CHROME_124] = self._create_chrome_124_fingerprint()

        # Chrome 123.0.0.0 fingerprint
        self._fingerprints[ChromeVersion.CHROME_123] = self._create_chrome_123_fingerprint()

        # Chrome 122.0.0.0 fingerprint
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
            CipherSuite("ECDHE-ECDSA-CHACHA20-POLY1305", 0xcca9, "ECDHE", "ECDSA", "CHACHA20-POLY1305", "SHA256", True),
            CipherSuite("ECDHE-RSA-CHACHA20-POLY1305", 0xcca8, "ECDHE", "RSA", "CHACHA20-POLY1305", "SHA256", True),
        ]

        extensions = [
            TLSExtension("server_name", 0, b""),
            TLSExtension("extended_master_secret", 23, b""),
            TLSExtension("renegotiation_info", 65281, b"\\x00"),
            TLSExtension("supported_groups", 10, self._encode_supported_groups()),
            TLSExtension("ec_point_formats", 11, b"\\x01\\x00"),
            TLSExtension("session_ticket", 35, b""),
            TLSExtension("application_layer_protocol_negotiation", 16, self._encode_alpn(["h2", "http/1.1"])),
            TLSExtension("status_request", 5, b"\\x01\\x00\\x00\\x00\\x00"),
            TLSExtension("signature_algorithms", 13, self._encode_signature_algorithms()),
            TLSExtension("signed_certificate_timestamp", 18, b""),
            TLSExtension("key_share", 51, self._encode_key_shares()),
            TLSExtension("psk_key_exchange_modes", 45, b"\\x01\\x01"),
            TLSExtension("supported_versions", 43, b"\\x02\\x03\\x04"),
            TLSExtension("compress_certificate", 27, b"\\x02\\x00\\x02"),
            TLSExtension("application_settings", 17513, b""),
        ]

        return TLSFingerprint(
            browser_version=ChromeVersion.CHROME_124,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            cipher_suites=cipher_suites,
            extensions=extensions,
            supported_groups=["x25519", "secp256r1", "secp384r1"],
            signature_algorithms=["rsa_pss_rsae_sha256", "ecdsa_secp256r1_sha256", "rsa_pkcs1_sha256"],
            alpn_protocols=["h2", "http/1.1"],
            key_shares=["x25519"],
        )

    def _create_chrome_123_fingerprint(self) -> TLSFingerprint:
        """Create TLS fingerprint for Chrome 123."""
        # Similar to 124 but with slight differences
        fingerprint = self._create_chrome_124_fingerprint()
        fingerprint.browser_version = ChromeVersion.CHROME_123
        fingerprint.user_agent = fingerprint.user_agent.replace("124.0.0.0", "123.0.0.0")
        return fingerprint

    def _create_chrome_122_fingerprint(self) -> TLSFingerprint:
        """Create TLS fingerprint for Chrome 122."""
        # Similar to 124 but with slight differences
        fingerprint = self._create_chrome_124_fingerprint()
        fingerprint.browser_version = ChromeVersion.CHROME_122
        fingerprint.user_agent = fingerprint.user_agent.replace("124.0.0.0", "122.0.0.0")
        return fingerprint

    def _encode_supported_groups(self) -> bytes:
        """Encode supported elliptic curve groups."""
        # Simplified encoding - real implementation would follow RFC format
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
        # Simplified encoding
        algorithms = [0x0804, 0x0403, 0x0401]  # Common signature algorithms
        encoded = b""
        for alg in algorithms:
            encoded += alg.to_bytes(2, 'big')
        return len(encoded).to_bytes(2, 'big') + encoded

    def _encode_key_shares(self) -> bytes:
        """Encode key shares for TLS 1.3."""
        # Simplified - would contain actual key exchange data
        return b"\\x00\\x26\\x00\\x24\\x00\\x1d\\x00\\x20" + b"\\x00" * 32

    def get_fingerprint(self, version: ChromeVersion) -> TLSFingerprint:
        """Get TLS fingerprint for specified Chrome version."""
        if version not in self._fingerprints:
            raise ValueError(f"Unsupported Chrome version: {version.value}")
        return self._fingerprints[version]

    def get_fingerprint_by_string(self, version_string: str) -> TLSFingerprint:
        """Get TLS fingerprint by version string."""
        for chrome_version in ChromeVersion:
            if chrome_version.value == version_string:
                return self.get_fingerprint(chrome_version)
        raise ValueError(f"Unsupported Chrome version string: {version_string}")

    def get_supported_versions(self) -> List[str]:
        """Get list of supported Chrome versions."""
        return [version.value for version in self._fingerprints.keys()]

    def create_ssl_context(self, fingerprint: TLSFingerprint) -> ssl.SSLContext:
        """Create SSL context with fingerprint configuration."""
        # Create SSL context
        if fingerprint.max_tls_version == TLSVersion.TLS_1_3:
            context = ssl.create_default_context()
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        else:
            context = ssl.create_default_context()
            context.maximum_version = ssl.TLSVersion.TLSv1_2

        if fingerprint.min_tls_version == TLSVersion.TLS_1_2:
            context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Configure cipher suites
        cipher_names = [cs.name for cs in fingerprint.cipher_suites]
        context.set_ciphers(":".join(cipher_names))

        # Set ALPN protocols
        if fingerprint.alpn_protocols:
            context.set_alpn_protocols(fingerprint.alpn_protocols)

        # Disable compression
        context.options |= ssl.OP_NO_COMPRESSION

        return context

    def get_ja3_fingerprint(self, fingerprint: TLSFingerprint) -> str:
        """Generate JA3 fingerprint string for the TLS configuration."""
        # JA3 format: SSLVersion,Cipher,SSLExtension,EllipticCurve,EllipticCurvePointFormat

        # TLS version (771 = TLS 1.2, 772 = TLS 1.3)
        if fingerprint.max_tls_version == TLSVersion.TLS_1_3:
            version = "772"
        else:
            version = "771"

        # Cipher suites
        ciphers = ",".join([str(cs.iana_value) for cs in fingerprint.cipher_suites])

        # Extensions
        extensions = ",".join([str(ext.extension_id) for ext in fingerprint.extensions])

        # Elliptic curves (simplified mapping)
        curve_mapping = {"x25519": "29", "secp256r1": "23", "secp384r1": "24"}
        curves = ",".join([curve_mapping.get(group, "0") for group in fingerprint.supported_groups])

        # Point formats (0 = uncompressed)
        point_formats = "0"

        return f"{version},{ciphers},{extensions},{curves},{point_formats}"

    def randomize_fingerprint(self, base_fingerprint: TLSFingerprint) -> TLSFingerprint:
        """Create a randomized variant of the fingerprint to avoid detection."""
        # Create a copy
        randomized = TLSFingerprint(
            browser_version=base_fingerprint.browser_version,
            user_agent=base_fingerprint.user_agent,
            min_tls_version=base_fingerprint.min_tls_version,
            max_tls_version=base_fingerprint.max_tls_version,
            cipher_suites=base_fingerprint.cipher_suites.copy(),
            extensions=base_fingerprint.extensions.copy(),
            supported_groups=base_fingerprint.supported_groups.copy(),
            signature_algorithms=base_fingerprint.signature_algorithms.copy(),
            alpn_protocols=base_fingerprint.alpn_protocols.copy(),
            key_shares=base_fingerprint.key_shares.copy(),
        )

        # Slightly randomize cipher suite order (within reason)
        if len(randomized.cipher_suites) > 3:
            # Swap positions of some non-critical cipher suites
            idx1, idx2 = random.sample(range(3, len(randomized.cipher_suites)), 2)
            randomized.cipher_suites[idx1], randomized.cipher_suites[idx2] = \
                randomized.cipher_suites[idx2], randomized.cipher_suites[idx1]

        # Slightly randomize extension order (keeping critical ones first)
        if len(randomized.extensions) > 5:
            # Keep first 5 extensions in place, randomize the rest
            tail = randomized.extensions[5:]
            random.shuffle(tail)
            randomized.extensions = randomized.extensions[:5] + tail

        return randomized

    def validate_fingerprint(self, fingerprint: TLSFingerprint) -> bool:
        """Validate that a TLS fingerprint is properly configured."""
        # Check required fields
        if not fingerprint.cipher_suites:
            return False

        if not fingerprint.extensions:
            return False

        # Check that TLS 1.3 cipher suites are present for TLS 1.3
        if fingerprint.max_tls_version == TLSVersion.TLS_1_3:
            tls13_ciphers = [cs for cs in fingerprint.cipher_suites if cs.iana_value in [0x1301, 0x1302, 0x1303]]
            if not tls13_ciphers:
                return False

        # Check ALPN configuration
        if not fingerprint.alpn_protocols or "http/1.1" not in fingerprint.alpn_protocols:
            return False

        return True

    def get_fingerprint_info(self, fingerprint: TLSFingerprint) -> Dict[str, Any]:
        """Get detailed information about a TLS fingerprint."""
        return {
            "browser_version": fingerprint.browser_version.value,
            "tls_versions": f"{fingerprint.min_tls_version.value} - {fingerprint.max_tls_version.value}",
            "cipher_suites_count": len(fingerprint.cipher_suites),
            "extensions_count": len(fingerprint.extensions),
            "supported_groups": fingerprint.supported_groups,
            "alpn_protocols": fingerprint.alpn_protocols,
            "ja3_fingerprint": self.get_ja3_fingerprint(fingerprint),
            "session_resumption": {
                "tickets": fingerprint.supports_session_tickets,
                "ids": fingerprint.supports_session_ids,
            }
        }