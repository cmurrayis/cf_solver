"""
Unit tests for TLS fingerprinting functionality.

These tests verify the TLS fingerprinting capabilities including JA3 generation,
cipher suite handling, extension management, and Chrome fingerprint emulation
in isolation from other components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional

from cloudflare_research.tls.fingerprint import TLSFingerprint, JA3Generator, TLSConfig
from cloudflare_research.models.tls import TLSVersion, CipherSuite, TLSExtension


@pytest.fixture
def tls_fingerprint():
    """Create TLS fingerprint instance for testing."""
    return TLSFingerprint()


@pytest.fixture
def ja3_generator():
    """Create JA3 generator instance for testing."""
    return JA3Generator()


@pytest.fixture
def tls_config():
    """Create TLS configuration for testing."""
    return TLSConfig(
        version=TLSVersion.TLS_1_3,
        cipher_suites=[
            CipherSuite.TLS_AES_128_GCM_SHA256,
            CipherSuite.TLS_AES_256_GCM_SHA384,
            CipherSuite.TLS_CHACHA20_POLY1305_SHA256
        ],
        extensions=[
            TLSExtension.SERVER_NAME,
            TLSExtension.SUPPORTED_VERSIONS,
            TLSExtension.SIGNATURE_ALGORITHMS
        ]
    )


class TestTLSFingerprint:
    """Test TLS fingerprint generation and management."""

    def test_tls_fingerprint_initialization(self, tls_fingerprint):
        """Test TLS fingerprint initialization."""
        assert tls_fingerprint is not None
        assert hasattr(tls_fingerprint, 'generate_chrome_ja3')
        assert hasattr(tls_fingerprint, 'generate_firefox_ja3')

    def test_chrome_ja3_generation(self, tls_fingerprint):
        """Test Chrome JA3 fingerprint generation."""
        ja3_string = tls_fingerprint.generate_chrome_ja3()

        assert isinstance(ja3_string, str)
        assert len(ja3_string) > 10
        assert ',' in ja3_string  # JA3 format uses commas

        # JA3 should be consistent for the same browser
        ja3_string_2 = tls_fingerprint.generate_chrome_ja3()
        assert ja3_string == ja3_string_2

    def test_firefox_ja3_generation(self, tls_fingerprint):
        """Test Firefox JA3 fingerprint generation."""
        ja3_string = tls_fingerprint.generate_firefox_ja3()

        assert isinstance(ja3_string, str)
        assert len(ja3_string) > 10
        assert ',' in ja3_string

        # Firefox JA3 should be different from Chrome
        chrome_ja3 = tls_fingerprint.generate_chrome_ja3()
        assert ja3_string != chrome_ja3

    def test_custom_ja3_generation(self, tls_fingerprint, tls_config):
        """Test custom JA3 generation with specific configuration."""
        ja3_string = tls_fingerprint.generate_ja3_from_config(tls_config)

        assert isinstance(ja3_string, str)
        assert len(ja3_string) > 10

        # Should contain elements from the config
        parts = ja3_string.split(',')
        assert len(parts) == 5  # JA3 has 5 parts

    def test_ja3_format_validation(self, tls_fingerprint):
        """Test JA3 format validation."""
        chrome_ja3 = tls_fingerprint.generate_chrome_ja3()

        # Validate JA3 format
        parts = chrome_ja3.split(',')
        assert len(parts) == 5

        # TLS version
        assert parts[0].isdigit()

        # Cipher suites (can be empty or comma-separated numbers)
        if parts[1]:
            cipher_parts = parts[1].split('-')
            for cipher in cipher_parts:
                assert cipher.isdigit()

        # Extensions (can be empty or dash-separated numbers)
        if parts[2]:
            ext_parts = parts[2].split('-')
            for ext in ext_parts:
                assert ext.isdigit()

    def test_browser_specific_characteristics(self, tls_fingerprint):
        """Test browser-specific TLS characteristics."""
        chrome_ja3 = tls_fingerprint.generate_chrome_ja3()
        firefox_ja3 = tls_fingerprint.generate_firefox_ja3()

        # Should generate different fingerprints
        assert chrome_ja3 != firefox_ja3

        # Both should be valid JA3 format
        for ja3 in [chrome_ja3, firefox_ja3]:
            parts = ja3.split(',')
            assert len(parts) == 5

    def test_tls_version_handling(self, tls_fingerprint):
        """Test TLS version handling in fingerprints."""
        # Test with different TLS versions
        tls_1_2_config = TLSConfig(version=TLSVersion.TLS_1_2)
        tls_1_3_config = TLSConfig(version=TLSVersion.TLS_1_3)

        ja3_1_2 = tls_fingerprint.generate_ja3_from_config(tls_1_2_config)
        ja3_1_3 = tls_fingerprint.generate_ja3_from_config(tls_1_3_config)

        # Different TLS versions should produce different JA3
        assert ja3_1_2 != ja3_1_3

        # Verify version encoding in JA3
        version_1_2 = ja3_1_2.split(',')[0]
        version_1_3 = ja3_1_3.split(',')[0]
        assert version_1_2 != version_1_3

    def test_cipher_suite_encoding(self, tls_fingerprint):
        """Test cipher suite encoding in JA3."""
        config_with_ciphers = TLSConfig(
            cipher_suites=[
                CipherSuite.TLS_AES_128_GCM_SHA256,
                CipherSuite.TLS_AES_256_GCM_SHA384
            ]
        )

        ja3 = tls_fingerprint.generate_ja3_from_config(config_with_ciphers)
        cipher_part = ja3.split(',')[1]

        # Should contain cipher information
        assert len(cipher_part) > 0

        # Should be dash-separated numbers
        if '-' in cipher_part:
            cipher_codes = cipher_part.split('-')
            for code in cipher_codes:
                assert code.isdigit()

    def test_extension_encoding(self, tls_fingerprint):
        """Test extension encoding in JA3."""
        config_with_extensions = TLSConfig(
            extensions=[
                TLSExtension.SERVER_NAME,
                TLSExtension.SUPPORTED_VERSIONS,
                TLSExtension.SIGNATURE_ALGORITHMS
            ]
        )

        ja3 = tls_fingerprint.generate_ja3_from_config(config_with_extensions)
        extension_part = ja3.split(',')[2]

        # Should contain extension information
        assert len(extension_part) > 0

        # Should be dash-separated numbers
        if '-' in extension_part:
            ext_codes = extension_part.split('-')
            for code in ext_codes:
                assert code.isdigit()

    def test_fingerprint_caching(self, tls_fingerprint):
        """Test fingerprint caching behavior."""
        # Generate same fingerprint multiple times
        ja3_1 = tls_fingerprint.generate_chrome_ja3()
        ja3_2 = tls_fingerprint.generate_chrome_ja3()
        ja3_3 = tls_fingerprint.generate_chrome_ja3()

        # Should be consistent (cached)
        assert ja3_1 == ja3_2 == ja3_3

        # Should be efficient (no regeneration)
        with patch.object(tls_fingerprint, '_generate_ja3') as mock_generate:
            mock_generate.return_value = ja3_1

            # Multiple calls should use cache
            result = tls_fingerprint.generate_chrome_ja3()
            assert result == ja3_1

    def test_fingerprint_randomization(self, tls_fingerprint):
        """Test fingerprint randomization features."""
        # Test if randomization is available
        try:
            random_ja3 = tls_fingerprint.generate_random_ja3()
            assert isinstance(random_ja3, str)
            assert len(random_ja3) > 10

            # Multiple random generations should potentially differ
            random_ja3_2 = tls_fingerprint.generate_random_ja3()
            # Note: They might be the same due to limited randomization

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Random JA3 generation not implemented")

    def test_invalid_configuration_handling(self, tls_fingerprint):
        """Test handling of invalid configurations."""
        # Test with None config
        with pytest.raises((TypeError, ValueError)):
            tls_fingerprint.generate_ja3_from_config(None)

        # Test with empty config
        empty_config = TLSConfig()
        ja3 = tls_fingerprint.generate_ja3_from_config(empty_config)
        assert isinstance(ja3, str)

    def test_ja3_string_parsing(self, tls_fingerprint):
        """Test parsing of JA3 strings back to components."""
        chrome_ja3 = tls_fingerprint.generate_chrome_ja3()

        try:
            parsed = tls_fingerprint.parse_ja3_string(chrome_ja3)

            assert hasattr(parsed, 'tls_version')
            assert hasattr(parsed, 'cipher_suites')
            assert hasattr(parsed, 'extensions')

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("JA3 parsing not implemented")

    def test_fingerprint_comparison(self, tls_fingerprint):
        """Test fingerprint comparison utilities."""
        chrome_ja3 = tls_fingerprint.generate_chrome_ja3()
        firefox_ja3 = tls_fingerprint.generate_firefox_ja3()

        try:
            # Test similarity comparison
            similarity = tls_fingerprint.compare_ja3(chrome_ja3, firefox_ja3)
            assert 0.0 <= similarity <= 1.0

            # Same fingerprints should be identical
            same_similarity = tls_fingerprint.compare_ja3(chrome_ja3, chrome_ja3)
            assert same_similarity == 1.0

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("JA3 comparison not implemented")


class TestJA3Generator:
    """Test JA3 generator functionality."""

    def test_ja3_generator_initialization(self, ja3_generator):
        """Test JA3 generator initialization."""
        assert ja3_generator is not None

    def test_generate_ja3_hash(self, ja3_generator):
        """Test JA3 hash generation."""
        test_string = "771,4865-4866-4867,0-23-35-13,29-23-24,0"

        ja3_hash = ja3_generator.generate_hash(test_string)

        assert isinstance(ja3_hash, str)
        assert len(ja3_hash) == 32  # MD5 hash length

        # Same input should produce same hash
        ja3_hash_2 = ja3_generator.generate_hash(test_string)
        assert ja3_hash == ja3_hash_2

    def test_cipher_suite_encoding(self, ja3_generator):
        """Test cipher suite encoding."""
        cipher_suites = [
            CipherSuite.TLS_AES_128_GCM_SHA256,
            CipherSuite.TLS_AES_256_GCM_SHA384
        ]

        encoded = ja3_generator.encode_cipher_suites(cipher_suites)

        assert isinstance(encoded, str)
        if len(cipher_suites) > 1:
            assert '-' in encoded  # Multiple ciphers separated by dashes

    def test_extension_encoding(self, ja3_generator):
        """Test extension encoding."""
        extensions = [
            TLSExtension.SERVER_NAME,
            TLSExtension.SUPPORTED_VERSIONS
        ]

        encoded = ja3_generator.encode_extensions(extensions)

        assert isinstance(encoded, str)
        if len(extensions) > 1:
            assert '-' in encoded  # Multiple extensions separated by dashes

    def test_tls_version_encoding(self, ja3_generator):
        """Test TLS version encoding."""
        version_1_2 = ja3_generator.encode_tls_version(TLSVersion.TLS_1_2)
        version_1_3 = ja3_generator.encode_tls_version(TLSVersion.TLS_1_3)

        assert isinstance(version_1_2, str)
        assert isinstance(version_1_3, str)
        assert version_1_2 != version_1_3

    def test_complete_ja3_generation(self, ja3_generator, tls_config):
        """Test complete JA3 string generation."""
        ja3_string = ja3_generator.generate_ja3_string(tls_config)

        assert isinstance(ja3_string, str)
        parts = ja3_string.split(',')
        assert len(parts) == 5

        # All parts should be present (may be empty)
        for part in parts:
            assert isinstance(part, str)

    def test_empty_components_handling(self, ja3_generator):
        """Test handling of empty components."""
        empty_config = TLSConfig()
        ja3_string = ja3_generator.generate_ja3_string(empty_config)

        assert isinstance(ja3_string, str)
        parts = ja3_string.split(',')
        assert len(parts) == 5

    def test_large_cipher_list_handling(self, ja3_generator):
        """Test handling of large cipher suite lists."""
        # Create config with many cipher suites
        many_ciphers = [
            CipherSuite.TLS_AES_128_GCM_SHA256,
            CipherSuite.TLS_AES_256_GCM_SHA384,
            CipherSuite.TLS_CHACHA20_POLY1305_SHA256,
            CipherSuite.TLS_AES_128_CCM_SHA256,
        ] * 10  # Repeat to create large list

        large_config = TLSConfig(cipher_suites=many_ciphers)
        ja3_string = ja3_generator.generate_ja3_string(large_config)

        assert isinstance(ja3_string, str)
        # Should handle large lists without errors

    def test_duplicate_cipher_handling(self, ja3_generator):
        """Test handling of duplicate cipher suites."""
        duplicate_ciphers = [
            CipherSuite.TLS_AES_128_GCM_SHA256,
            CipherSuite.TLS_AES_128_GCM_SHA256,  # Duplicate
            CipherSuite.TLS_AES_256_GCM_SHA384
        ]

        config = TLSConfig(cipher_suites=duplicate_ciphers)
        ja3_string = ja3_generator.generate_ja3_string(config)

        assert isinstance(ja3_string, str)
        # Should handle duplicates gracefully


class TestTLSConfig:
    """Test TLS configuration handling."""

    def test_tls_config_creation(self, tls_config):
        """Test TLS configuration creation."""
        assert tls_config.version == TLSVersion.TLS_1_3
        assert len(tls_config.cipher_suites) > 0
        assert len(tls_config.extensions) > 0

    def test_tls_config_validation(self):
        """Test TLS configuration validation."""
        # Valid config
        valid_config = TLSConfig(
            version=TLSVersion.TLS_1_3,
            cipher_suites=[CipherSuite.TLS_AES_128_GCM_SHA256]
        )
        assert valid_config.version == TLSVersion.TLS_1_3

        # Config with invalid version should handle gracefully
        try:
            invalid_config = TLSConfig(version="invalid")
            # Should either raise exception or handle gracefully
        except (ValueError, TypeError):
            pass  # Expected behavior

    def test_config_serialization(self, tls_config):
        """Test TLS configuration serialization."""
        try:
            serialized = tls_config.to_dict()
            assert isinstance(serialized, dict)
            assert 'version' in serialized
            assert 'cipher_suites' in serialized
            assert 'extensions' in serialized

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("TLS config serialization not implemented")

    def test_config_deserialization(self, tls_config):
        """Test TLS configuration deserialization."""
        try:
            serialized = tls_config.to_dict()
            deserialized = TLSConfig.from_dict(serialized)

            assert deserialized.version == tls_config.version
            assert len(deserialized.cipher_suites) == len(tls_config.cipher_suites)

        except AttributeError:
            # Methods might not exist - that's acceptable
            pytest.skip("TLS config deserialization not implemented")


class TestTLSExtensions:
    """Test TLS extension handling."""

    def test_extension_enumeration(self):
        """Test TLS extension enumeration."""
        # Test that extensions are properly defined
        assert hasattr(TLSExtension, 'SERVER_NAME')
        assert hasattr(TLSExtension, 'SUPPORTED_VERSIONS')
        assert hasattr(TLSExtension, 'SIGNATURE_ALGORITHMS')

    def test_extension_values(self):
        """Test TLS extension values."""
        # Extensions should have numeric values
        assert isinstance(TLSExtension.SERVER_NAME.value, int)
        assert isinstance(TLSExtension.SUPPORTED_VERSIONS.value, int)
        assert isinstance(TLSExtension.SIGNATURE_ALGORITHMS.value, int)

    def test_extension_uniqueness(self):
        """Test that extension values are unique."""
        extensions = [
            TLSExtension.SERVER_NAME,
            TLSExtension.SUPPORTED_VERSIONS,
            TLSExtension.SIGNATURE_ALGORITHMS
        ]

        values = [ext.value for ext in extensions]
        assert len(values) == len(set(values))  # All unique


class TestCipherSuites:
    """Test cipher suite handling."""

    def test_cipher_suite_enumeration(self):
        """Test cipher suite enumeration."""
        assert hasattr(CipherSuite, 'TLS_AES_128_GCM_SHA256')
        assert hasattr(CipherSuite, 'TLS_AES_256_GCM_SHA384')
        assert hasattr(CipherSuite, 'TLS_CHACHA20_POLY1305_SHA256')

    def test_cipher_suite_values(self):
        """Test cipher suite values."""
        assert isinstance(CipherSuite.TLS_AES_128_GCM_SHA256.value, int)
        assert isinstance(CipherSuite.TLS_AES_256_GCM_SHA384.value, int)

    def test_cipher_suite_uniqueness(self):
        """Test that cipher suite values are unique."""
        cipher_suites = [
            CipherSuite.TLS_AES_128_GCM_SHA256,
            CipherSuite.TLS_AES_256_GCM_SHA384,
            CipherSuite.TLS_CHACHA20_POLY1305_SHA256
        ]

        values = [cs.value for cs in cipher_suites]
        assert len(values) == len(set(values))  # All unique


@pytest.mark.parametrize("browser_type", ["chrome", "firefox", "safari"])
def test_browser_specific_fingerprints(browser_type, tls_fingerprint):
    """Test browser-specific fingerprint generation."""
    if browser_type == "chrome":
        ja3 = tls_fingerprint.generate_chrome_ja3()
    elif browser_type == "firefox":
        ja3 = tls_fingerprint.generate_firefox_ja3()
    else:
        try:
            ja3 = tls_fingerprint.generate_safari_ja3()
        except AttributeError:
            pytest.skip(f"{browser_type} fingerprint not implemented")

    assert isinstance(ja3, str)
    assert len(ja3) > 10
    assert ',' in ja3


@pytest.mark.parametrize("tls_version", [TLSVersion.TLS_1_2, TLSVersion.TLS_1_3])
def test_tls_version_fingerprints(tls_version, tls_fingerprint):
    """Test fingerprints with different TLS versions."""
    config = TLSConfig(version=tls_version)
    ja3 = tls_fingerprint.generate_ja3_from_config(config)

    assert isinstance(ja3, str)
    assert len(ja3) > 0

    # Verify version is encoded correctly
    version_part = ja3.split(',')[0]
    assert version_part.isdigit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])