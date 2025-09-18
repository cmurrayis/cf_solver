"""Contract test for CloudflareBypass.get() method.

This test validates the GET request interface against the API specification.
Tests MUST fail initially to follow TDD principles.
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock

# Import will fail until implementation exists - this is expected for TDD
try:
    from cloudflare_research import CloudflareBypass
    from cloudflare_research.models import RequestResult, RequestTiming, Challenge
except ImportError:
    # Expected during TDD phase - tests should fail initially
    CloudflareBypass = None
    RequestResult = None
    RequestTiming = None
    Challenge = None


@pytest.mark.contract
@pytest.mark.asyncio
class TestCloudflareBypassGet:
    """Contract tests for CloudflareBypass.get() method."""

    @pytest.fixture
    def bypass_client(self):
        """Create CloudflareBypass instance for testing."""
        if CloudflareBypass is None:
            pytest.skip("CloudflareBypass not implemented yet - TDD phase")
        return CloudflareBypass()

    async def test_get_method_exists(self, bypass_client):
        """Test that get() method exists and is callable."""
        assert hasattr(bypass_client, 'get')
        assert callable(getattr(bypass_client, 'get'))

    async def test_get_simple_request(self, bypass_client):
        """Test GET request with minimal parameters."""
        # Contract: get(url) -> RequestResult
        result = await bypass_client.get("https://example.com")

        # Validate result structure matches API spec
        assert isinstance(result, RequestResult)
        assert hasattr(result, 'request_id')
        assert hasattr(result, 'url')
        assert hasattr(result, 'status_code')
        assert hasattr(result, 'headers')
        assert hasattr(result, 'body')
        assert hasattr(result, 'timing')
        assert hasattr(result, 'success')

        # Validate types
        assert isinstance(result.request_id, str)
        assert isinstance(result.url, str)
        assert isinstance(result.status_code, int)
        assert isinstance(result.headers, dict)
        assert isinstance(result.body, str)
        assert isinstance(result.timing, RequestTiming)
        assert isinstance(result.success, bool)

    async def test_get_with_headers(self, bypass_client):
        """Test GET request with custom headers."""
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer token123",
            "User-Agent": "Test-Agent/1.0"
        }

        result = await bypass_client.get(
            "https://example.com/api",
            headers=headers
        )

        assert isinstance(result, RequestResult)
        assert result.url == "https://example.com/api"

    async def test_get_with_timeout(self, bypass_client):
        """Test GET request with timeout parameter."""
        result = await bypass_client.get(
            "https://example.com",
            timeout=60
        )

        assert isinstance(result, RequestResult)

    async def test_get_with_browser_version(self, bypass_client):
        """Test GET request with specific browser version."""
        result = await bypass_client.get(
            "https://example.com",
            browser_version="124.0.0.0"
        )

        assert isinstance(result, RequestResult)

    async def test_get_with_proxy(self, bypass_client):
        """Test GET request with proxy configuration."""
        proxy_config = {
            "type": "http",
            "host": "proxy.example.com",
            "port": 8080,
            "username": "user",
            "password": "pass"
        }

        result = await bypass_client.get(
            "https://example.com",
            proxy=proxy_config
        )

        assert isinstance(result, RequestResult)

    async def test_get_invalid_url(self, bypass_client):
        """Test GET request with invalid URL raises appropriate error."""
        with pytest.raises((ValueError, TypeError)):
            await bypass_client.get("not-a-valid-url")

    async def test_get_timeout_validation(self, bypass_client):
        """Test GET request timeout parameter validation."""
        # Timeout too small
        with pytest.raises(ValueError):
            await bypass_client.get("https://example.com", timeout=0)

        # Timeout too large
        with pytest.raises(ValueError):
            await bypass_client.get("https://example.com", timeout=301)

    async def test_get_browser_version_validation(self, bypass_client):
        """Test GET request browser version validation."""
        # Invalid format
        with pytest.raises(ValueError):
            await bypass_client.get(
                "https://example.com",
                browser_version="invalid-version"
            )

    async def test_get_request_timing_structure(self, bypass_client):
        """Test that timing information follows API specification."""
        result = await bypass_client.get("https://example.com")

        timing = result.timing
        assert hasattr(timing, 'dns_resolution_ms')
        assert hasattr(timing, 'tcp_connection_ms')
        assert hasattr(timing, 'tls_handshake_ms')
        assert hasattr(timing, 'request_sent_ms')
        assert hasattr(timing, 'response_received_ms')
        assert hasattr(timing, 'total_duration_ms')

        # All timing values should be non-negative integers
        assert timing.dns_resolution_ms >= 0
        assert timing.tcp_connection_ms >= 0
        assert timing.tls_handshake_ms >= 0
        assert timing.request_sent_ms >= 0
        assert timing.response_received_ms >= 0
        assert timing.total_duration_ms >= 0

    async def test_get_challenge_handling(self, bypass_client):
        """Test challenge detection and handling in GET requests."""
        # This should work with sites that have Cloudflare protection
        result = await bypass_client.get("https://protected-site.example.com")

        if result.challenge:
            assert isinstance(result.challenge, Challenge)
            assert hasattr(result.challenge, 'challenge_id')
            assert hasattr(result.challenge, 'type')
            assert hasattr(result.challenge, 'solved')
            assert hasattr(result.challenge, 'solve_duration_ms')

    async def test_get_response_headers_structure(self, bypass_client):
        """Test response headers are properly formatted."""
        result = await bypass_client.get("https://example.com")

        assert isinstance(result.headers, dict)
        # Headers should be string key-value pairs
        for key, value in result.headers.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    async def test_get_method_signature(self, bypass_client):
        """Test get() method has correct signature."""
        import inspect

        sig = inspect.signature(bypass_client.get)
        params = sig.parameters

        # Check required parameter
        assert 'url' in params

        # Check optional parameters exist
        expected_optional = ['headers', 'timeout', 'browser_version', 'proxy']
        for param in expected_optional:
            assert param in params
            assert params[param].default is not inspect.Parameter.empty

    async def test_get_return_type_annotation(self, bypass_client):
        """Test get() method has correct return type annotation."""
        import inspect

        sig = inspect.signature(bypass_client.get)
        return_annotation = sig.return_annotation

        # Should return RequestResult or Awaitable[RequestResult]
        assert return_annotation is not inspect.Signature.empty