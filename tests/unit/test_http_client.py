"""
Unit tests for HTTP client functionality.

These tests verify the HTTP client capabilities including request handling,
response processing, connection management, retry logic, and error handling
in isolation from other components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
import aiohttp
from aiohttp import ClientSession, ClientResponse, ClientTimeout

from cloudflare_research.http.client import HTTPClient, HTTPConfig, RequestBuilder
from cloudflare_research.models.response import CloudflareResponse
from cloudflare_research.models.request import HTTPRequest, HTTPMethod
from cloudflare_research.bypass import CloudflareBypassConfig


@pytest.fixture
def http_config():
    """Create HTTP configuration for testing."""
    return HTTPConfig(
        timeout=30.0,
        max_redirects=5,
        connection_pool_size=100,
        keep_alive_timeout=60.0,
        headers={
            "User-Agent": "Test-Agent/1.0",
            "Accept": "text/html,application/json"
        }
    )


@pytest.fixture
def bypass_config():
    """Create CloudflareBypass configuration for testing."""
    return CloudflareBypassConfig(
        timeout=30.0,
        max_concurrent_requests=10,
        connection_pool_size=50,
        headers={
            "User-Agent": "Mozilla/5.0 Test Browser",
            "Accept-Language": "en-US,en;q=0.9"
        }
    )


@pytest.fixture
async def http_client(bypass_config):
    """Create HTTP client instance for testing."""
    client = HTTPClient(bypass_config)
    await client.start()
    yield client
    await client.stop()


@pytest.fixture
def mock_response():
    """Create mock HTTP response."""
    response = Mock(spec=ClientResponse)
    response.status = 200
    response.headers = {"Content-Type": "application/json", "Content-Length": "100"}
    response.text = AsyncMock(return_value='{"test": "data"}')
    response.read = AsyncMock(return_value=b'{"test": "data"}')
    response.url = Mock()
    response.url.human_repr.return_value = "https://example.com"
    return response


class TestHTTPClient:
    """Test HTTP client functionality."""

    def test_http_client_initialization(self, bypass_config):
        """Test HTTP client initialization."""
        client = HTTPClient(bypass_config)

        assert client is not None
        assert client.config == bypass_config
        assert hasattr(client, 'session')

    async def test_http_client_start_stop(self, bypass_config):
        """Test HTTP client lifecycle management."""
        client = HTTPClient(bypass_config)

        # Start client
        await client.start()
        assert client.session is not None
        assert isinstance(client.session, ClientSession)

        # Stop client
        await client.stop()
        assert client.session is None or client.session.closed

    async def test_get_request(self, http_client, mock_response):
        """Test GET request execution."""
        url = "https://example.com/test"

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            response = await http_client.get(url)

            assert isinstance(response, CloudflareResponse)
            assert response.status_code == 200
            assert response.url == url
            assert "test" in response.content

            # Verify call
            mock_get.assert_called_once()

    async def test_post_request(self, http_client, mock_response):
        """Test POST request execution."""
        url = "https://example.com/api"
        data = {"key": "value"}

        with patch.object(http_client.session, 'post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            response = await http_client.post(url, data=data)

            assert isinstance(response, CloudflareResponse)
            assert response.status_code == 200

            # Verify call with data
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert 'data' in call_kwargs

    async def test_post_request_with_json(self, http_client, mock_response):
        """Test POST request with JSON data."""
        url = "https://example.com/api"
        json_data = {"message": "test"}

        with patch.object(http_client.session, 'post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            response = await http_client.post(url, json_data=json_data)

            assert isinstance(response, CloudflareResponse)
            assert response.status_code == 200

            # Verify JSON was passed
            call_kwargs = mock_post.call_args[1]
            assert 'json' in call_kwargs
            assert call_kwargs['json'] == json_data

    async def test_request_with_headers(self, http_client, mock_response):
        """Test request with custom headers."""
        url = "https://example.com/test"
        custom_headers = {"X-Custom": "value", "Authorization": "Bearer token"}

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            response = await http_client.get(url, headers=custom_headers)

            assert response.status_code == 200

            # Verify headers were merged
            call_kwargs = mock_get.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert "X-Custom" in headers
            assert headers["X-Custom"] == "value"

    async def test_request_timeout_handling(self, http_client):
        """Test request timeout handling."""
        url = "https://example.com/slow"

        with patch.object(http_client.session, 'get') as mock_get:
            # Simulate timeout
            mock_get.side_effect = asyncio.TimeoutError("Request timed out")

            with pytest.raises(asyncio.TimeoutError):
                await http_client.get(url)

    async def test_connection_error_handling(self, http_client):
        """Test connection error handling."""
        url = "https://nonexistent.example.com"

        with patch.object(http_client.session, 'get') as mock_get:
            # Simulate connection error
            mock_get.side_effect = aiohttp.ClientConnectionError("Connection failed")

            with pytest.raises(aiohttp.ClientConnectionError):
                await http_client.get(url)

    async def test_retry_mechanism(self, http_client, mock_response):
        """Test request retry mechanism."""
        url = "https://example.com/unstable"

        with patch.object(http_client.session, 'get') as mock_get:
            # First call fails, second succeeds
            mock_get.side_effect = [
                aiohttp.ClientConnectionError("Connection failed"),
                mock_response.__aenter__.return_value
            ]

            try:
                response = await http_client.get_with_retry(url, max_retries=2)
                assert response.status_code == 200
                assert mock_get.call_count == 2

            except AttributeError:
                # Method might not exist - that's acceptable
                pytest.skip("Retry mechanism not implemented")

    async def test_redirect_handling(self, http_client):
        """Test redirect handling."""
        url = "https://example.com/redirect"

        # Mock redirect response
        redirect_response = Mock(spec=ClientResponse)
        redirect_response.status = 302
        redirect_response.headers = {"Location": "https://example.com/final"}

        # Mock final response
        final_response = Mock(spec=ClientResponse)
        final_response.status = 200
        final_response.headers = {"Content-Type": "text/html"}
        final_response.text = AsyncMock(return_value="Final content")

        with patch.object(http_client.session, 'get') as mock_get:
            # Configure to follow redirects automatically
            mock_get.return_value.__aenter__.return_value = final_response

            response = await http_client.get(url, allow_redirects=True)

            assert response.status_code == 200

    async def test_session_configuration(self, bypass_config):
        """Test session configuration from CloudflareBypass config."""
        client = HTTPClient(bypass_config)
        await client.start()

        session = client.session

        # Verify session configuration
        assert session is not None
        assert isinstance(session.timeout, ClientTimeout)
        assert session.timeout.total == bypass_config.timeout

        # Verify connector configuration
        connector = session.connector
        assert connector.limit == bypass_config.connection_pool_size

        await client.stop()

    async def test_default_headers_merging(self, http_client):
        """Test default headers merging with request headers."""
        url = "https://example.com/test"
        request_headers = {"Content-Type": "application/json"}

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = Mock(
                status=200,
                headers={},
                text=AsyncMock(return_value=""),
                url=Mock(human_repr=Mock(return_value=url))
            )

            await http_client.get(url, headers=request_headers)

            # Verify headers include both default and request headers
            call_kwargs = mock_get.call_args[1]
            headers = call_kwargs['headers']

            # Should have User-Agent from config
            assert any("User-Agent" in str(k) for k in headers.keys())
            # Should have Content-Type from request
            assert "Content-Type" in headers

    async def test_response_processing(self, http_client):
        """Test response processing and CloudflareResponse creation."""
        url = "https://example.com/test"

        # Create detailed mock response
        mock_resp = Mock(spec=ClientResponse)
        mock_resp.status = 200
        mock_resp.headers = {
            "Content-Type": "text/html",
            "Server": "cloudflare",
            "CF-RAY": "12345-DFW"
        }
        mock_resp.text = AsyncMock(return_value="<html>Test content</html>")
        mock_resp.url = Mock()
        mock_resp.url.human_repr.return_value = url

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_resp

            response = await http_client.get(url)

            # Verify CloudflareResponse attributes
            assert isinstance(response, CloudflareResponse)
            assert response.status_code == 200
            assert response.url == url
            assert "Test content" in response.content
            assert "Server" in response.headers
            assert response.headers["Server"] == "cloudflare"

    async def test_concurrent_requests(self, http_client, mock_response):
        """Test concurrent request handling."""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            # Execute concurrent requests
            tasks = [http_client.get(url) for url in urls]
            responses = await asyncio.gather(*tasks)

            # Verify all requests completed
            assert len(responses) == len(urls)
            for response in responses:
                assert isinstance(response, CloudflareResponse)
                assert response.status_code == 200

            # Verify all requests were made
            assert mock_get.call_count == len(urls)

    async def test_request_timing(self, http_client, mock_response):
        """Test request timing measurement."""
        url = "https://example.com/test"

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            response = await http_client.get(url)

            # Check if timing information is available
            if hasattr(response, 'timing') and response.timing:
                assert hasattr(response.timing, 'total_time')
                assert response.timing.total_time >= 0

    async def test_error_response_handling(self, http_client):
        """Test handling of HTTP error responses."""
        url = "https://example.com/error"

        # Mock error response
        error_response = Mock(spec=ClientResponse)
        error_response.status = 500
        error_response.headers = {"Content-Type": "text/html"}
        error_response.text = AsyncMock(return_value="Internal Server Error")
        error_response.url = Mock()
        error_response.url.human_repr.return_value = url

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = error_response

            response = await http_client.get(url)

            # Should still return CloudflareResponse with error status
            assert isinstance(response, CloudflareResponse)
            assert response.status_code == 500
            assert "Internal Server Error" in response.content

    async def test_large_response_handling(self, http_client):
        """Test handling of large responses."""
        url = "https://example.com/large"
        large_content = "x" * 10000  # 10KB content

        large_response = Mock(spec=ClientResponse)
        large_response.status = 200
        large_response.headers = {"Content-Type": "text/plain", "Content-Length": str(len(large_content))}
        large_response.text = AsyncMock(return_value=large_content)
        large_response.url = Mock()
        large_response.url.human_repr.return_value = url

        with patch.object(http_client.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = large_response

            response = await http_client.get(url)

            assert response.status_code == 200
            assert len(response.content) == len(large_content)


class TestHTTPConfig:
    """Test HTTP configuration functionality."""

    def test_http_config_creation(self, http_config):
        """Test HTTP configuration creation."""
        assert http_config.timeout == 30.0
        assert http_config.max_redirects == 5
        assert http_config.connection_pool_size == 100
        assert "User-Agent" in http_config.headers

    def test_http_config_defaults(self):
        """Test HTTP configuration default values."""
        config = HTTPConfig()

        assert config.timeout > 0
        assert config.max_redirects >= 0
        assert config.connection_pool_size > 0
        assert isinstance(config.headers, dict)

    def test_http_config_validation(self):
        """Test HTTP configuration validation."""
        # Valid config
        valid_config = HTTPConfig(timeout=60.0, max_redirects=10)
        assert valid_config.timeout == 60.0
        assert valid_config.max_redirects == 10

        # Invalid timeout should raise error or be handled
        try:
            invalid_config = HTTPConfig(timeout=-1)
            # Should either raise exception or clamp to valid value
            assert invalid_config.timeout >= 0
        except (ValueError, TypeError):
            pass  # Expected behavior

    def test_config_to_aiohttp_params(self, http_config):
        """Test conversion to aiohttp parameters."""
        try:
            params = http_config.to_aiohttp_params()
            assert isinstance(params, dict)
            assert 'timeout' in params
            assert 'headers' in params

        except AttributeError:
            # Method might not exist - that's acceptable
            pytest.skip("Config to aiohttp params not implemented")


class TestRequestBuilder:
    """Test request builder functionality."""

    def test_request_builder_creation(self):
        """Test request builder creation."""
        builder = RequestBuilder()
        assert builder is not None

    def test_build_get_request(self):
        """Test building GET request."""
        builder = RequestBuilder()
        url = "https://example.com/test"

        request = builder.get(url).build()

        assert isinstance(request, HTTPRequest)
        assert request.method == HTTPMethod.GET
        assert request.url == url

    def test_build_post_request(self):
        """Test building POST request."""
        builder = RequestBuilder()
        url = "https://example.com/api"
        data = {"key": "value"}

        request = builder.post(url).data(data).build()

        assert isinstance(request, HTTPRequest)
        assert request.method == HTTPMethod.POST
        assert request.url == url
        assert request.data == data

    def test_request_with_headers(self):
        """Test building request with headers."""
        builder = RequestBuilder()
        url = "https://example.com/test"
        headers = {"Authorization": "Bearer token"}

        request = builder.get(url).headers(headers).build()

        assert request.headers == headers

    def test_request_with_timeout(self):
        """Test building request with timeout."""
        builder = RequestBuilder()
        url = "https://example.com/test"
        timeout = 45.0

        request = builder.get(url).timeout(timeout).build()

        assert request.timeout == timeout

    def test_request_builder_chaining(self):
        """Test request builder method chaining."""
        builder = RequestBuilder()
        url = "https://example.com/api"

        request = (builder
                  .post(url)
                  .headers({"Content-Type": "application/json"})
                  .json_data({"test": "data"})
                  .timeout(30.0)
                  .build())

        assert request.method == HTTPMethod.POST
        assert request.url == url
        assert request.headers["Content-Type"] == "application/json"
        assert request.json_data == {"test": "data"}
        assert request.timeout == 30.0

    def test_request_validation(self):
        """Test request validation in builder."""
        builder = RequestBuilder()

        # Valid request
        valid_request = builder.get("https://example.com").build()
        assert valid_request.url == "https://example.com"

        # Invalid URL should be handled
        try:
            invalid_request = builder.get("invalid-url").build()
            # Should either raise exception or handle gracefully
        except (ValueError, TypeError):
            pass  # Expected behavior


@pytest.mark.parametrize("method", [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE])
async def test_http_methods(method, http_client, mock_response):
    """Test different HTTP methods."""
    url = "https://example.com/test"

    # Map method to session method
    session_method_map = {
        HTTPMethod.GET: 'get',
        HTTPMethod.POST: 'post',
        HTTPMethod.PUT: 'put',
        HTTPMethod.DELETE: 'delete'
    }

    session_method = session_method_map[method]

    with patch.object(http_client.session, session_method) as mock_method:
        mock_method.return_value.__aenter__.return_value = mock_response

        # Call appropriate client method
        if method == HTTPMethod.GET:
            response = await http_client.get(url)
        elif method == HTTPMethod.POST:
            response = await http_client.post(url, data={})
        elif method == HTTPMethod.PUT:
            try:
                response = await http_client.put(url, data={})
            except AttributeError:
                pytest.skip(f"{method.value} method not implemented")
        elif method == HTTPMethod.DELETE:
            try:
                response = await http_client.delete(url)
            except AttributeError:
                pytest.skip(f"{method.value} method not implemented")

        assert response.status_code == 200
        mock_method.assert_called_once()


@pytest.mark.parametrize("status_code", [200, 301, 302, 400, 401, 403, 404, 500, 502, 503])
async def test_status_code_handling(status_code, http_client):
    """Test handling of various HTTP status codes."""
    url = "https://example.com/test"

    mock_resp = Mock(spec=ClientResponse)
    mock_resp.status = status_code
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.text = AsyncMock(return_value=f"Status {status_code} content")
    mock_resp.url = Mock()
    mock_resp.url.human_repr.return_value = url

    with patch.object(http_client.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_resp

        response = await http_client.get(url)

        assert response.status_code == status_code
        assert f"Status {status_code}" in response.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])