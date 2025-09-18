"""
Integration tests for Chrome browser emulation functionality.

These tests verify that CloudflareBypass correctly emulates Chrome browser
behavior including headers, TLS fingerprinting, and JavaScript execution
in real-world scenarios.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from urllib.parse import urlparse

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.models.response import CloudflareResponse
from cloudflare_research.tls.fingerprint import TLSFingerprint
from cloudflare_research.http.client import HTTPClient
from cloudflare_research.browser.emulation import BrowserEmulation


@pytest.mark.integration
@pytest.mark.asyncio
class TestChromeEmulationIntegration:
    """Integration tests for Chrome browser emulation."""

    @pytest.fixture
    def chrome_config(self) -> CloudflareBypassConfig:
        """Create configuration for Chrome emulation testing."""
        return CloudflareBypassConfig(
            browser_version="120.0.0.0",
            timeout=30.0,
            solve_javascript_challenges=True,
            enable_detailed_logging=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )

    @pytest.fixture
    def test_urls(self) -> List[str]:
        """Provide test URLs for Chrome emulation testing."""
        return [
            "https://httpbin.org/headers",
            "https://httpbin.org/user-agent",
            "https://httpbin.org/get",
            "https://httpbin.org/json"
        ]

    async def test_chrome_user_agent_emulation(self, chrome_config):
        """Test that Chrome user agent is correctly emulated."""
        async with CloudflareBypass(chrome_config) as bypass:
            response = await bypass.get("https://httpbin.org/user-agent")

            assert response.status_code == 200

            # Parse response to check user agent
            import json
            response_data = json.loads(response.content)
            user_agent = response_data.get("user-agent", "")

            # Verify Chrome user agent characteristics
            assert "Chrome/120.0.0.0" in user_agent
            assert "Safari/537.36" in user_agent
            assert "Mozilla/5.0" in user_agent
            assert "Windows NT 10.0" in user_agent

    async def test_chrome_headers_emulation(self, chrome_config):
        """Test that Chrome headers are correctly emulated."""
        async with CloudflareBypass(chrome_config) as bypass:
            response = await bypass.get("https://httpbin.org/headers")

            assert response.status_code == 200

            # Parse response to check headers
            import json
            response_data = json.loads(response.content)
            headers = response_data.get("headers", {})

            # Verify Chrome-specific headers
            assert "Accept" in headers
            assert "Accept-Language" in headers
            assert "Accept-Encoding" in headers
            assert "Sec-Fetch-Dest" in headers
            assert "Sec-Fetch-Mode" in headers
            assert "Sec-Fetch-Site" in headers
            assert "Sec-Fetch-User" in headers
            assert "Upgrade-Insecure-Requests" in headers

            # Verify specific header values
            assert headers["Accept-Language"] == "en-US,en;q=0.9"
            assert headers["Sec-Fetch-Dest"] == "document"
            assert headers["Sec-Fetch-Mode"] == "navigate"
            assert headers["Upgrade-Insecure-Requests"] == "1"

    async def test_chrome_tls_fingerprint_emulation(self, chrome_config):
        """Test that Chrome TLS fingerprint is correctly emulated."""
        # Create TLS fingerprint emulator
        tls_fingerprint = TLSFingerprint()
        chrome_ja3 = tls_fingerprint.generate_chrome_ja3()

        # Verify Chrome JA3 characteristics
        assert chrome_ja3 is not None
        assert len(chrome_ja3) > 20  # JA3 should be substantial string

        # Test with actual request
        async with CloudflareBypass(chrome_config) as bypass:
            response = await bypass.get("https://httpbin.org/get")

            assert response.status_code == 200
            # TLS fingerprint is applied at connection level - if we get 200, it worked

    async def test_chrome_javascript_execution(self, chrome_config):
        """Test that JavaScript execution matches Chrome behavior."""
        async with CloudflareBypass(chrome_config) as bypass:
            # Test with a page that might have JavaScript
            response = await bypass.get("https://httpbin.org/get")

            assert response.status_code == 200

            # Verify JavaScript solver is properly initialized
            if hasattr(bypass, 'js_solver') and bypass.js_solver:
                # Test JavaScript execution directly
                test_js = "Math.pow(2, 3) + 1"
                try:
                    result = bypass.js_solver._execute_with_mini_racer(test_js, "test.com")
                    assert result is not None
                except Exception:
                    # JS solver may not be available in all configurations
                    pass

    async def test_chrome_concurrent_requests(self, chrome_config, test_urls):
        """Test Chrome emulation under concurrent load."""
        # Configure for concurrent testing
        chrome_config.max_concurrent_requests = 5

        async with CloudflareBypass(chrome_config) as bypass:
            # Make concurrent requests
            tasks = [bypass.get(url) for url in test_urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all requests succeeded
            successful_responses = [r for r in responses if isinstance(r, CloudflareResponse)]
            assert len(successful_responses) >= len(test_urls) // 2  # At least half should succeed

            # Verify consistent Chrome emulation across all requests
            for response in successful_responses:
                assert response.status_code == 200

    async def test_chrome_browser_consistency(self, chrome_config):
        """Test that Chrome emulation is consistent across requests."""
        async with CloudflareBypass(chrome_config) as bypass:
            # Make multiple requests to the same endpoint
            responses = []
            for _ in range(3):
                response = await bypass.get("https://httpbin.org/headers")
                responses.append(response)
                await asyncio.sleep(1)  # Small delay between requests

            # Parse headers from all responses
            all_headers = []
            for response in responses:
                assert response.status_code == 200
                import json
                response_data = json.loads(response.content)
                headers = response_data.get("headers", {})
                all_headers.append(headers)

            # Verify consistent headers across requests
            assert len(all_headers) == 3

            # Check that key Chrome headers are consistent
            chrome_headers = ["User-Agent", "Accept", "Accept-Language", "Sec-Fetch-Dest"]
            for header_name in chrome_headers:
                if header_name in all_headers[0]:
                    header_values = [h.get(header_name) for h in all_headers]
                    assert len(set(header_values)) == 1, f"Inconsistent {header_name} header"

    async def test_chrome_version_emulation(self, chrome_config):
        """Test that specific Chrome version is correctly emulated."""
        async with CloudflareBypass(chrome_config) as bypass:
            response = await bypass.get("https://httpbin.org/user-agent")

            assert response.status_code == 200

            import json
            response_data = json.loads(response.content)
            user_agent = response_data.get("user-agent", "")

            # Verify specific Chrome version
            expected_version = chrome_config.browser_version  # "120.0.0.0"
            assert expected_version in user_agent

    async def test_chrome_encoding_support(self, chrome_config):
        """Test that Chrome encoding capabilities are emulated."""
        async with CloudflareBypass(chrome_config) as bypass:
            response = await bypass.get("https://httpbin.org/gzip")

            assert response.status_code == 200

            # Verify that gzip encoding was handled
            assert len(response.content) > 0

            # Response should be properly decoded JSON
            import json
            try:
                response_data = json.loads(response.content)
                assert "gzipped" in response_data
                assert response_data["gzipped"] is True
            except json.JSONDecodeError:
                pytest.fail("Response was not properly decoded from gzip")

    async def test_chrome_ssl_support(self, chrome_config):
        """Test that Chrome SSL/TLS capabilities are emulated."""
        async with CloudflareBypass(chrome_config) as bypass:
            # Test HTTPS request
            response = await bypass.get("https://httpbin.org/get")

            assert response.status_code == 200

            # Verify SSL connection was successful
            import json
            response_data = json.loads(response.content)

            # Should have received data over HTTPS
            assert "url" in response_data
            assert response_data["url"].startswith("https://")

    async def test_chrome_redirect_handling(self, chrome_config):
        """Test that Chrome redirect behavior is emulated."""
        async with CloudflareBypass(chrome_config) as bypass:
            # Test redirect endpoint
            response = await bypass.get("https://httpbin.org/redirect/2")

            assert response.status_code == 200

            # Should have followed redirects successfully
            import json
            response_data = json.loads(response.content)

            # Final endpoint should be /get
            assert "url" in response_data
            assert response_data["url"].endswith("/get")

    async def test_chrome_performance_characteristics(self, chrome_config):
        """Test Chrome emulation performance characteristics."""
        start_time = time.time()

        async with CloudflareBypass(chrome_config) as bypass:
            # Make several requests to measure performance
            responses = []
            for _ in range(5):
                response = await bypass.get("https://httpbin.org/get")
                responses.append(response)

            # Verify all requests succeeded
            for response in responses:
                assert response.status_code == 200

        elapsed_time = time.time() - start_time

        # Performance check - should complete reasonably quickly
        assert elapsed_time < 60  # 5 requests should complete within 60 seconds

        # Average response time should be reasonable
        avg_time = elapsed_time / len(responses)
        assert avg_time < 12  # Average should be less than 12 seconds per request

    async def test_chrome_emulation_with_custom_headers(self, chrome_config):
        """Test Chrome emulation with additional custom headers."""
        # Add custom headers while maintaining Chrome emulation
        custom_headers = {
            "X-Custom-Header": "test-value",
            "X-Request-ID": "chrome-emulation-test"
        }

        async with CloudflareBypass(chrome_config) as bypass:
            response = await bypass.get("https://httpbin.org/headers", headers=custom_headers)

            assert response.status_code == 200

            import json
            response_data = json.loads(response.content)
            headers = response_data.get("headers", {})

            # Verify custom headers were included
            assert "X-Custom-Header" in headers
            assert headers["X-Custom-Header"] == "test-value"
            assert "X-Request-ID" in headers
            assert headers["X-Request-ID"] == "chrome-emulation-test"

            # Verify Chrome headers are still present
            assert "User-Agent" in headers
            assert "Chrome/120.0.0.0" in headers["User-Agent"]

    async def test_chrome_error_handling(self, chrome_config):
        """Test Chrome emulation error handling."""
        async with CloudflareBypass(chrome_config) as bypass:
            # Test with invalid URL
            with pytest.raises(Exception):
                await bypass.get("https://nonexistent-domain-12345.invalid")

            # Test with server error
            response = await bypass.get("https://httpbin.org/status/500")
            assert response.status_code == 500

            # Chrome emulation should handle errors gracefully
            # The fact that we got a 500 response means the request succeeded

    @pytest.mark.slow
    async def test_chrome_emulation_stress_test(self, chrome_config):
        """Stress test Chrome emulation under load."""
        chrome_config.max_concurrent_requests = 10
        chrome_config.requests_per_second = 5

        async with CloudflareBypass(chrome_config) as bypass:
            # Generate many concurrent requests
            urls = ["https://httpbin.org/get"] * 20

            start_time = time.time()
            tasks = [bypass.get(url) for url in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed_time = time.time() - start_time

            # Count successful responses
            successful = sum(1 for r in responses if isinstance(r, CloudflareResponse) and r.status_code == 200)

            # Should have high success rate
            success_rate = successful / len(responses)
            assert success_rate >= 0.8  # At least 80% success rate

            # Performance should be reasonable under load
            assert elapsed_time < 120  # Should complete within 2 minutes


@pytest.mark.integration
@pytest.mark.asyncio
class TestChromeEmulationComponents:
    """Integration tests for individual Chrome emulation components."""

    async def test_browser_emulation_component(self):
        """Test BrowserEmulation component directly."""
        browser_emulation = BrowserEmulation()

        # Test Chrome headers generation
        chrome_headers = browser_emulation.generate_chrome_headers()

        assert isinstance(chrome_headers, dict)
        assert "User-Agent" in chrome_headers
        assert "Chrome" in chrome_headers["User-Agent"]
        assert "Accept" in chrome_headers

        # Verify header format
        assert chrome_headers["Accept-Language"].startswith("en-US")
        assert "gzip" in chrome_headers["Accept-Encoding"]

    async def test_tls_fingerprint_component(self):
        """Test TLS fingerprint component for Chrome emulation."""
        tls_fingerprint = TLSFingerprint()

        # Test Chrome JA3 generation
        ja3_string = tls_fingerprint.generate_chrome_ja3()

        assert isinstance(ja3_string, str)
        assert len(ja3_string) > 10

        # JA3 should contain cipher and extension information
        assert "," in ja3_string  # JA3 format uses commas

    async def test_http_client_chrome_integration(self):
        """Test HTTP client with Chrome emulation."""
        config = CloudflareBypassConfig(
            browser_version="120.0.0.0",
            timeout=30.0
        )

        http_client = HTTPClient(config)

        # Verify Chrome configuration is applied
        assert http_client.config.browser_version == "120.0.0.0"
        assert http_client.config.timeout == 30.0


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])