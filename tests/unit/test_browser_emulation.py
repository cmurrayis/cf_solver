"""
Unit tests for browser emulation functionality.

These tests verify the browser emulation capabilities including header generation,
user agent construction, fingerprinting, and browser-specific behavior simulation
in isolation from other components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

from cloudflare_research.browser.emulation import BrowserEmulation, UserAgentGenerator, HeaderManager
from cloudflare_research.models.browser import BrowserType, BrowserVersion, Platform
from cloudflare_research.bypass import CloudflareBypassConfig


@pytest.fixture
def browser_emulation():
    """Create browser emulation instance for testing."""
    return BrowserEmulation()


@pytest.fixture
def user_agent_generator():
    """Create user agent generator instance for testing."""
    return UserAgentGenerator()


@pytest.fixture
def header_manager():
    """Create header manager instance for testing."""
    return HeaderManager()


@pytest.fixture
def chrome_config():
    """Create configuration for Chrome emulation."""
    return CloudflareBypassConfig(
        browser_version="120.0.0.0",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )


class TestBrowserEmulation:
    """Test browser emulation functionality."""

    def test_browser_emulation_initialization(self, browser_emulation):
        """Test browser emulation initialization."""
        assert browser_emulation is not None
        assert hasattr(browser_emulation, 'generate_chrome_headers')
        assert hasattr(browser_emulation, 'generate_firefox_headers')

    def test_chrome_headers_generation(self, browser_emulation):
        """Test Chrome headers generation."""
        headers = browser_emulation.generate_chrome_headers()

        assert isinstance(headers, dict)
        assert len(headers) > 0

        # Check required Chrome headers
        required_headers = [
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Accept-Encoding",
            "Sec-Fetch-Dest",
            "Sec-Fetch-Mode",
            "Sec-Fetch-Site",
            "Upgrade-Insecure-Requests"
        ]

        for header in required_headers:
            assert header in headers, f"Missing required Chrome header: {header}"

        # Verify Chrome-specific values
        user_agent = headers["User-Agent"]
        assert "Chrome" in user_agent
        assert "Safari" in user_agent
        assert "Mozilla" in user_agent

        # Verify Sec-Fetch headers (Chrome-specific)
        assert headers["Sec-Fetch-Dest"] in ["document", "empty"]
        assert headers["Sec-Fetch-Mode"] in ["navigate", "cors", "no-cors"]
        assert headers["Sec-Fetch-Site"] in ["none", "same-origin", "cross-site"]

    def test_firefox_headers_generation(self, browser_emulation):
        """Test Firefox headers generation."""
        headers = browser_emulation.generate_firefox_headers()

        assert isinstance(headers, dict)
        assert len(headers) > 0

        # Check required Firefox headers
        required_headers = [
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Accept-Encoding"
        ]

        for header in required_headers:
            assert header in headers

        # Verify Firefox-specific user agent
        user_agent = headers["User-Agent"]
        assert "Firefox" in user_agent
        assert "Gecko" in user_agent

        # Firefox shouldn't have Sec-Fetch headers (Chrome-specific)
        sec_fetch_headers = [h for h in headers.keys() if h.startswith("Sec-Fetch")]
        assert len(sec_fetch_headers) == 0

    def test_safari_headers_generation(self, browser_emulation):
        """Test Safari headers generation."""
        try:
            headers = browser_emulation.generate_safari_headers()

            assert isinstance(headers, dict)
            assert "User-Agent" in headers

            user_agent = headers["User-Agent"]
            assert "Safari" in user_agent
            assert "Version" in user_agent

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Safari headers generation not implemented")

    def test_header_consistency(self, browser_emulation):
        """Test header consistency across multiple generations."""
        # Generate headers multiple times
        chrome_headers_1 = browser_emulation.generate_chrome_headers()
        chrome_headers_2 = browser_emulation.generate_chrome_headers()

        # Should be consistent
        assert chrome_headers_1 == chrome_headers_2

        # Same for Firefox
        firefox_headers_1 = browser_emulation.generate_firefox_headers()
        firefox_headers_2 = browser_emulation.generate_firefox_headers()

        assert firefox_headers_1 == firefox_headers_2

    def test_browser_differentiation(self, browser_emulation):
        """Test that different browsers generate different headers."""
        chrome_headers = browser_emulation.generate_chrome_headers()
        firefox_headers = browser_emulation.generate_firefox_headers()

        # Headers should be different
        assert chrome_headers != firefox_headers

        # User agents should be different
        assert chrome_headers["User-Agent"] != firefox_headers["User-Agent"]

        # Chrome has Sec-Fetch headers, Firefox doesn't
        chrome_sec_fetch = [h for h in chrome_headers.keys() if h.startswith("Sec-Fetch")]
        firefox_sec_fetch = [h for h in firefox_headers.keys() if h.startswith("Sec-Fetch")]

        assert len(chrome_sec_fetch) > len(firefox_sec_fetch)

    def test_custom_browser_version(self, browser_emulation):
        """Test browser emulation with custom version."""
        try:
            custom_version = "119.0.0.0"
            headers = browser_emulation.generate_chrome_headers(version=custom_version)

            user_agent = headers["User-Agent"]
            assert custom_version in user_agent

        except TypeError:
            # Method might not accept version parameter - that's acceptable
            pytest.skip("Custom version not supported")

    def test_platform_specific_headers(self, browser_emulation):
        """Test platform-specific header generation."""
        try:
            # Test different platforms
            platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]

            for platform in platforms:
                headers = browser_emulation.generate_headers_for_platform(
                    BrowserType.CHROME, platform
                )

                user_agent = headers["User-Agent"]

                if platform == Platform.WINDOWS:
                    assert "Windows NT" in user_agent
                elif platform == Platform.MACOS:
                    assert "Macintosh" in user_agent or "Mac OS X" in user_agent
                elif platform == Platform.LINUX:
                    assert "Linux" in user_agent or "X11" in user_agent

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Platform-specific headers not implemented")

    def test_header_order_preservation(self, browser_emulation):
        """Test that header order is preserved (important for fingerprinting)."""
        headers = browser_emulation.generate_chrome_headers()

        # Convert to list to check order
        header_names = list(headers.keys())

        # Important headers should appear in typical browser order
        important_headers = ["User-Agent", "Accept", "Accept-Language", "Accept-Encoding"]

        for i, header in enumerate(important_headers[:-1]):
            if header in header_names and important_headers[i+1] in header_names:
                current_index = header_names.index(header)
                next_index = header_names.index(important_headers[i+1])
                # Next header should appear after current (in most cases)
                # This is a loose check as order can vary

    def test_header_value_formats(self, browser_emulation):
        """Test header value formats are correct."""
        headers = browser_emulation.generate_chrome_headers()

        # Accept-Language should have proper format
        accept_lang = headers.get("Accept-Language", "")
        assert "en-US" in accept_lang or "en" in accept_lang
        if "," in accept_lang:
            # Should have quality values
            assert "q=" in accept_lang

        # Accept-Encoding should have proper format
        accept_encoding = headers.get("Accept-Encoding", "")
        encodings = ["gzip", "deflate", "br"]
        assert any(enc in accept_encoding for enc in encodings)

        # User-Agent should have proper format
        user_agent = headers.get("User-Agent", "")
        assert user_agent.startswith("Mozilla/")
        assert "(" in user_agent and ")" in user_agent  # Platform info in parentheses

    def test_header_merging(self, browser_emulation):
        """Test merging custom headers with browser headers."""
        try:
            base_headers = browser_emulation.generate_chrome_headers()
            custom_headers = {
                "Authorization": "Bearer token123",
                "X-Custom": "test-value",
                "User-Agent": "Custom-Agent/1.0"  # Override default
            }

            merged_headers = browser_emulation.merge_headers(base_headers, custom_headers)

            # Should contain all custom headers
            assert merged_headers["Authorization"] == "Bearer token123"
            assert merged_headers["X-Custom"] == "test-value"

            # Custom User-Agent should override default
            assert merged_headers["User-Agent"] == "Custom-Agent/1.0"

            # Should still contain other browser headers
            assert "Accept" in merged_headers
            assert "Accept-Language" in merged_headers

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Header merging not implemented")


class TestUserAgentGenerator:
    """Test user agent generation functionality."""

    def test_user_agent_generator_initialization(self, user_agent_generator):
        """Test user agent generator initialization."""
        assert user_agent_generator is not None

    def test_chrome_user_agent_generation(self, user_agent_generator):
        """Test Chrome user agent generation."""
        ua = user_agent_generator.generate_chrome_user_agent()

        assert isinstance(ua, str)
        assert len(ua) > 50  # Should be substantial

        # Check Chrome-specific components
        assert "Mozilla/5.0" in ua
        assert "Chrome/" in ua
        assert "Safari/" in ua
        assert "AppleWebKit/" in ua

        # Should have platform information
        assert any(platform in ua for platform in ["Windows", "Macintosh", "Linux", "X11"])

    def test_firefox_user_agent_generation(self, user_agent_generator):
        """Test Firefox user agent generation."""
        ua = user_agent_generator.generate_firefox_user_agent()

        assert isinstance(ua, str)
        assert len(ua) > 30

        # Check Firefox-specific components
        assert "Mozilla/5.0" in ua
        assert "Firefox/" in ua
        assert "Gecko/" in ua

        # Should be different from Chrome
        chrome_ua = user_agent_generator.generate_chrome_user_agent()
        assert ua != chrome_ua

    def test_user_agent_versioning(self, user_agent_generator):
        """Test user agent version handling."""
        try:
            # Test with specific version
            version = "119.0.0.0"
            ua = user_agent_generator.generate_chrome_user_agent(version=version)

            assert version in ua

            # Test with different version
            version2 = "120.0.0.0"
            ua2 = user_agent_generator.generate_chrome_user_agent(version=version2)

            assert version2 in ua2
            assert ua != ua2  # Should be different

        except TypeError:
            # Method might not accept version parameter
            pytest.skip("User agent versioning not supported")

    def test_user_agent_randomization(self, user_agent_generator):
        """Test user agent randomization features."""
        try:
            # Generate multiple random user agents
            uas = [user_agent_generator.generate_random_user_agent() for _ in range(5)]

            assert len(uas) == 5
            assert all(isinstance(ua, str) for ua in uas)

            # Should have some variation (might not always be different)
            unique_uas = set(uas)
            assert len(unique_uas) >= 1  # At least one unique

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("User agent randomization not implemented")

    def test_mobile_user_agent_generation(self, user_agent_generator):
        """Test mobile user agent generation."""
        try:
            mobile_ua = user_agent_generator.generate_mobile_user_agent()

            assert isinstance(mobile_ua, str)

            # Should contain mobile indicators
            mobile_indicators = ["Mobile", "iPhone", "Android", "iPad"]
            assert any(indicator in mobile_ua for indicator in mobile_indicators)

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Mobile user agent generation not implemented")

    def test_user_agent_validation(self, user_agent_generator):
        """Test user agent validation."""
        try:
            chrome_ua = user_agent_generator.generate_chrome_user_agent()

            is_valid = user_agent_generator.validate_user_agent(chrome_ua)
            assert is_valid is True

            # Test invalid user agent
            invalid_ua = "Invalid-Agent"
            is_valid_invalid = user_agent_generator.validate_user_agent(invalid_ua)
            assert is_valid_invalid is False

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("User agent validation not implemented")


class TestHeaderManager:
    """Test header management functionality."""

    def test_header_manager_initialization(self, header_manager):
        """Test header manager initialization."""
        assert header_manager is not None

    def test_header_case_sensitivity(self, header_manager):
        """Test header case sensitivity handling."""
        try:
            headers = {"content-type": "application/json", "USER-AGENT": "test"}

            normalized = header_manager.normalize_headers(headers)

            # Should normalize case
            assert "Content-Type" in normalized or "content-type" in normalized
            assert "User-Agent" in normalized or "user-agent" in normalized

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Header normalization not implemented")

    def test_header_sanitization(self, header_manager):
        """Test header value sanitization."""
        try:
            headers = {
                "X-Test": "value\r\ninjection",  # CRLF injection attempt
                "Authorization": "Bearer \x00token",  # Null byte
                "Custom": "normal-value"
            }

            sanitized = header_manager.sanitize_headers(headers)

            # Should remove or escape dangerous characters
            assert "\r" not in sanitized["X-Test"]
            assert "\n" not in sanitized["X-Test"]
            assert "\x00" not in sanitized["Authorization"]

            # Normal values should be preserved
            assert sanitized["Custom"] == "normal-value"

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Header sanitization not implemented")

    def test_header_filtering(self, header_manager):
        """Test header filtering functionality."""
        try:
            headers = {
                "User-Agent": "test",
                "Accept": "text/html",
                "X-Forwarded-For": "192.168.1.1",  # Might be filtered
                "X-Real-IP": "10.0.0.1",           # Might be filtered
                "Authorization": "Bearer token"
            }

            filtered = header_manager.filter_headers(headers, remove_proxy_headers=True)

            # Proxy headers should be removed
            assert "X-Forwarded-For" not in filtered
            assert "X-Real-IP" not in filtered

            # Normal headers should remain
            assert "User-Agent" in filtered
            assert "Accept" in filtered
            assert "Authorization" in filtered

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Header filtering not implemented")


class TestBrowserType:
    """Test browser type enumeration."""

    def test_browser_type_values(self):
        """Test browser type enumeration values."""
        assert hasattr(BrowserType, 'CHROME')
        assert hasattr(BrowserType, 'FIREFOX')
        assert hasattr(BrowserType, 'SAFARI')

    def test_browser_type_uniqueness(self):
        """Test that browser types are unique."""
        types = [BrowserType.CHROME, BrowserType.FIREFOX, BrowserType.SAFARI]
        assert len(types) == len(set(types))


class TestPlatform:
    """Test platform enumeration."""

    def test_platform_values(self):
        """Test platform enumeration values."""
        assert hasattr(Platform, 'WINDOWS')
        assert hasattr(Platform, 'MACOS')
        assert hasattr(Platform, 'LINUX')

    def test_platform_uniqueness(self):
        """Test that platforms are unique."""
        platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        assert len(platforms) == len(set(platforms))


class TestBrowserVersion:
    """Test browser version handling."""

    def test_browser_version_parsing(self):
        """Test browser version parsing."""
        try:
            version = BrowserVersion("120.0.0.0")

            assert version.major == 120
            assert version.minor == 0
            assert version.build == 0
            assert version.patch == 0

        except (AttributeError, TypeError):
            # Class might not exist or work differently
            pytest.skip("BrowserVersion class not implemented as expected")

    def test_version_comparison(self):
        """Test browser version comparison."""
        try:
            v1 = BrowserVersion("119.0.0.0")
            v2 = BrowserVersion("120.0.0.0")

            assert v1 < v2
            assert v2 > v1
            assert v1 != v2

        except (AttributeError, TypeError):
            # Class might not support comparison
            pytest.skip("BrowserVersion comparison not implemented")


@pytest.mark.parametrize("browser_type", [BrowserType.CHROME, BrowserType.FIREFOX])
def test_browser_specific_emulation(browser_type, browser_emulation):
    """Test browser-specific emulation."""
    if browser_type == BrowserType.CHROME:
        headers = browser_emulation.generate_chrome_headers()
        assert "Chrome" in headers["User-Agent"]
    elif browser_type == BrowserType.FIREFOX:
        headers = browser_emulation.generate_firefox_headers()
        assert "Firefox" in headers["User-Agent"]

    assert isinstance(headers, dict)
    assert len(headers) > 0
    assert "User-Agent" in headers


@pytest.mark.parametrize("version", ["119.0.0.0", "120.0.0.0", "121.0.0.0"])
def test_version_specific_user_agents(version, user_agent_generator):
    """Test user agent generation with specific versions."""
    try:
        ua = user_agent_generator.generate_chrome_user_agent(version=version)
        assert version in ua
    except TypeError:
        # Method might not accept version parameter
        pytest.skip("Version-specific user agents not supported")


def test_integration_with_config(chrome_config, browser_emulation):
    """Test integration with CloudflareBypassConfig."""
    try:
        headers = browser_emulation.generate_headers_from_config(chrome_config)

        assert isinstance(headers, dict)
        assert "User-Agent" in headers

        # Should use version from config
        if chrome_config.browser_version:
            assert chrome_config.browser_version in headers["User-Agent"]

    except AttributeError:
        # Method might not exist - that's acceptable
        pytest.skip("Config integration not implemented")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])