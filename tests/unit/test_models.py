"""
Unit tests for CloudflareBypass data models and validation.

Tests model validation, serialization, and data integrity for all core data structures.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from cloudflare_research.models import (
    BrowserConfig,
    ProxyConfig,
    RequestTiming,
    TestRequest,
    TestSession,
    ChallengeRecord,
    PerformanceMetrics,
    TestConfiguration,
    RequestStatus,
    HttpMethod,
    SessionStatus,
    ChallengeType,
    MetricType,
    RequestResult,
    BatchRequestResult,
    BatchSummary,
    Session,
    Challenge
)


class TestBrowserConfig:
    """Test BrowserConfig model validation and behavior."""

    def test_valid_browser_config_creation(self):
        """Test creating valid BrowserConfig instances."""
        config = BrowserConfig(
            version="120.0.0.0",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport_width=1920,
            viewport_height=1080,
            timezone="America/New_York",
            language="en-US",
            platform="Win32"
        )

        assert config.version == "120.0.0.0"
        assert config.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.timezone == "America/New_York"
        assert config.language == "en-US"
        assert config.platform == "Win32"

    def test_browser_config_defaults(self):
        """Test BrowserConfig default values."""
        config = BrowserConfig()

        assert config.version == "124.0.0.0"
        assert config.user_agent is None
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.timezone == "America/New_York"
        assert config.language == "en-US"
        assert config.platform == "Win32"

    def test_browser_config_custom_values(self):
        """Test BrowserConfig with custom values."""
        config = BrowserConfig(
            version="119.0.0.0",
            viewport_width=1366,
            viewport_height=768,
            timezone="UTC",
            language="de-DE",
            platform="Linux"
        )

        assert config.version == "119.0.0.0"
        assert config.viewport_width == 1366
        assert config.viewport_height == 768
        assert config.timezone == "UTC"
        assert config.language == "de-DE"
        assert config.platform == "Linux"


class TestProxyConfig:
    """Test ProxyConfig model validation and behavior."""

    def test_valid_proxy_config_creation(self):
        """Test creating valid ProxyConfig instances."""
        config = ProxyConfig(
            type="http",
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass"
        )

        assert config.type == "http"
        assert config.host == "proxy.example.com"
        assert config.port == 8080
        assert config.username == "user"
        assert config.password == "pass"

    def test_proxy_config_without_auth(self):
        """Test ProxyConfig without authentication."""
        config = ProxyConfig(
            type="socks5",
            host="proxy.test.com",
            port=1080
        )

        assert config.type == "socks5"
        assert config.host == "proxy.test.com"
        assert config.port == 1080
        assert config.username is None
        assert config.password is None

    def test_proxy_config_different_types(self):
        """Test different proxy types."""
        types = ["http", "https", "socks4", "socks5"]

        for proxy_type in types:
            config = ProxyConfig(
                type=proxy_type,
                host="proxy.example.com",
                port=8080
            )
            assert config.type == proxy_type


class TestRequestTiming:
    """Test RequestTiming model validation and behavior."""

    def test_valid_request_timing_creation(self):
        """Test creating valid RequestTiming instances."""
        timing = RequestTiming(
            dns_resolution_ms=50,
            tcp_connection_ms=100,
            tls_handshake_ms=150,
            request_sent_ms=10,
            response_received_ms=200,
            total_duration_ms=510
        )

        assert timing.dns_resolution_ms == 50
        assert timing.tcp_connection_ms == 100
        assert timing.tls_handshake_ms == 150
        assert timing.request_sent_ms == 10
        assert timing.response_received_ms == 200
        assert timing.total_duration_ms == 510

    def test_request_timing_defaults(self):
        """Test RequestTiming default values."""
        timing = RequestTiming()

        assert timing.dns_resolution_ms == 0
        assert timing.tcp_connection_ms == 0
        assert timing.tls_handshake_ms == 0
        assert timing.request_sent_ms == 0
        assert timing.response_received_ms == 0
        assert timing.total_duration_ms == 0


class TestTestRequest:
    """Test TestRequest model validation and behavior."""

    def test_valid_test_request_creation(self):
        """Test creating valid TestRequest instances."""
        request = TestRequest(
            url="https://example.com",
            method=HttpMethod.GET,
            headers={"User-Agent": "Test Browser"},
            timeout=30
        )

        assert request.url == "https://example.com"
        assert request.method == HttpMethod.GET
        assert request.headers["User-Agent"] == "Test Browser"
        assert request.timeout == 30
        assert request.status == RequestStatus.CREATED
        assert isinstance(request.request_id, UUID)

    def test_test_request_validation_empty_url(self):
        """Test validation fails for empty URL."""
        with pytest.raises(ValueError, match="URL is required"):
            TestRequest(url="")

    def test_test_request_validation_invalid_url_scheme(self):
        """Test validation fails for invalid URL scheme."""
        with pytest.raises(ValueError, match="URL must start with http:// or https://"):
            TestRequest(url="ftp://example.com")

    def test_test_request_validation_invalid_timeout(self):
        """Test validation fails for invalid timeout."""
        with pytest.raises(ValueError, match="Timeout must be between 1 and 300 seconds"):
            TestRequest(url="https://example.com", timeout=0)

        with pytest.raises(ValueError, match="Timeout must be between 1 and 300 seconds"):
            TestRequest(url="https://example.com", timeout=500)

    def test_test_request_validation_invalid_headers(self):
        """Test validation fails for invalid headers."""
        with pytest.raises(TypeError, match="Headers must be a dictionary"):
            TestRequest(url="https://example.com", headers="invalid")

        with pytest.raises(TypeError, match="Header keys and values must be strings"):
            TestRequest(url="https://example.com", headers={123: "value"})

    def test_test_request_is_completed_property(self):
        """Test is_completed property."""
        request = TestRequest(url="https://example.com")

        assert not request.is_completed

        request.status = RequestStatus.COMPLETED
        assert request.is_completed

        request.status = RequestStatus.FAILED
        assert request.is_completed

        request.status = RequestStatus.TIMEOUT
        assert request.is_completed

    def test_test_request_is_successful_property(self):
        """Test is_successful property."""
        request = TestRequest(url="https://example.com")

        assert not request.is_successful

        request.status = RequestStatus.COMPLETED
        request.status_code = 200
        assert request.is_successful

        request.status_code = 404
        assert not request.is_successful

    def test_test_request_duration_calculation(self):
        """Test duration calculation."""
        request = TestRequest(url="https://example.com")

        assert request.duration_ms is None

        request.started_at = datetime.now()
        request.completed_at = request.started_at + timedelta(milliseconds=1500)

        duration = request.duration_ms
        assert duration >= 1500
        assert duration < 1600  # Allow for some variance

    def test_test_request_execution_lifecycle(self):
        """Test request execution lifecycle methods."""
        request = TestRequest(url="https://example.com")

        # Start execution
        request.start_execution()
        assert request.status == RequestStatus.EXECUTING
        assert request.started_at is not None

        # Mark completed
        timing = RequestTiming(total_duration_ms=1000)
        request.mark_completed(200, {"Content-Type": "text/html"}, "response body", timing)

        assert request.status == RequestStatus.COMPLETED
        assert request.status_code == 200
        assert request.response_headers["Content-Type"] == "text/html"
        assert request.response_body == "response body"
        assert request.timing.total_duration_ms == 1000
        assert request.completed_at is not None

    def test_test_request_mark_failed(self):
        """Test marking request as failed."""
        request = TestRequest(url="https://example.com")

        request.mark_failed("Connection timeout")

        assert request.status == RequestStatus.FAILED
        assert request.error_message == "Connection timeout"
        assert request.completed_at is not None

    def test_test_request_mark_timeout(self):
        """Test marking request as timed out."""
        request = TestRequest(url="https://example.com", timeout=30)

        request.mark_timeout()

        assert request.status == RequestStatus.TIMEOUT
        assert request.error_message == "Request timed out after 30 seconds"
        assert request.completed_at is not None

    def test_test_request_serialization(self):
        """Test TestRequest serialization."""
        request = TestRequest(
            url="https://api.example.com",
            method=HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body='{"test": "data"}',
            timeout=60
        )

        data = request.to_dict()

        assert data["url"] == "https://api.example.com"
        assert data["method"] == "POST"
        assert data["headers"]["Content-Type"] == "application/json"
        assert data["body"] == '{"test": "data"}'
        assert data["timeout"] == 60
        assert data["status"] == "created"

    def test_test_request_deserialization(self):
        """Test TestRequest deserialization."""
        data = {
            "request_id": str(uuid4()),
            "url": "https://test.example.com",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "timeout": 45,
            "status": "completed",
            "status_code": 200,
            "created_at": datetime.now().isoformat()
        }

        request = TestRequest.from_dict(data)

        assert request.url == "https://test.example.com"
        assert request.method == HttpMethod.GET
        assert request.headers["Accept"] == "application/json"
        assert request.timeout == 45
        assert request.status == RequestStatus.COMPLETED
        assert request.status_code == 200


class TestChallengeRecord:
    """Test ChallengeRecord model validation and behavior."""

    def test_valid_challenge_record_creation(self):
        """Test creating valid ChallengeRecord instances."""
        challenge = ChallengeRecord(
            request_id=uuid4(),
            type=ChallengeType.JAVASCRIPT,
            url="https://example.com/challenge",
            challenge_html="<html>Challenge content</html>"
        )

        assert isinstance(challenge.challenge_id, UUID)
        assert isinstance(challenge.request_id, UUID)
        assert challenge.type == ChallengeType.JAVASCRIPT
        assert challenge.url == "https://example.com/challenge"
        assert challenge.challenge_html == "<html>Challenge content</html>"
        assert not challenge.solved
        assert challenge.solved_at is None

    def test_challenge_record_validation_empty_url(self):
        """Test validation fails for empty URL."""
        with pytest.raises(ValueError, match="Challenge URL is required"):
            ChallengeRecord(url="")

    def test_challenge_record_validation_invalid_url_scheme(self):
        """Test validation fails for invalid URL scheme."""
        with pytest.raises(ValueError, match="Challenge URL must start with http:// or https://"):
            ChallengeRecord(url="ftp://example.com")

    def test_challenge_record_validation_negative_duration(self):
        """Test validation fails for negative solve duration."""
        with pytest.raises(ValueError, match="Solve duration must be non-negative"):
            ChallengeRecord(
                url="https://example.com",
                solve_duration_ms=-100
            )

    def test_challenge_record_is_solved_property(self):
        """Test is_solved property."""
        challenge = ChallengeRecord(url="https://example.com")

        assert not challenge.is_solved

        challenge.solved = True
        assert not challenge.is_solved  # Still needs solved_at

        challenge.solved_at = datetime.now()
        assert challenge.is_solved

    def test_challenge_record_mark_solved(self):
        """Test marking challenge as solved."""
        challenge = ChallengeRecord(url="https://example.com")

        solution_data = {"cf_clearance": "test_token"}
        challenge.mark_solved(solution_data, "cf_clearance_value")

        assert challenge.solved
        assert challenge.solved_at is not None
        assert challenge.solution_data == solution_data
        assert challenge.cf_clearance == "cf_clearance_value"
        assert challenge.solve_duration_ms is not None

    def test_challenge_record_mark_failed(self):
        """Test marking challenge as failed."""
        challenge = ChallengeRecord(url="https://example.com")

        challenge.mark_failed("Timeout during solving")

        assert not challenge.solved
        assert challenge.error_message == "Timeout during solving"
        # For failed challenges without solved_at, solve_duration_ms is None
        assert challenge.solve_duration_ms is None

    def test_challenge_record_javascript_extraction(self):
        """Test JavaScript extraction from HTML."""
        html_content = """
        <html>
            <script>
                window._cf_chl_opt = {
                    cvId: "2",
                    cType: "managed",
                    cNounce: "12345"
                };
            </script>
        </html>
        """

        challenge = ChallengeRecord(url="https://example.com")
        extracted_js = challenge.extract_javascript(html_content)

        assert extracted_js is not None
        assert "window._cf_chl_opt" in extracted_js
        assert challenge.javascript_code == extracted_js

    def test_challenge_record_challenge_context(self):
        """Test challenge context generation."""
        challenge = ChallengeRecord(
            url="https://example.com",
            type=ChallengeType.TURNSTILE,
            challenge_html="<html>Test</html>",
            javascript_code="console.log('test');"
        )

        context = challenge.get_challenge_context()

        assert context["type"] == "turnstile"
        assert context["url"] == "https://example.com"
        assert context["html"] == "<html>Test</html>"
        assert context["javascript"] == "console.log('test');"
        assert "challenge_id" in context
        assert "detected_at" in context

    def test_challenge_record_type_detection(self):
        """Test challenge type detection from response."""
        # Test JavaScript challenge detection
        response_data = {
            "status_code": 403,
            "headers": {"server": "cloudflare"},
            "body": "<html><script>window._cf_chl_opt = {};</script></html>",
            "url": "https://example.com"
        }

        challenge = ChallengeRecord.create_from_response(uuid4(), response_data)
        assert challenge.type == ChallengeType.JAVASCRIPT

        # Test Turnstile detection
        response_data["body"] = "<html><div class='cf-turnstile'></div></html>"
        challenge = ChallengeRecord.create_from_response(uuid4(), response_data)
        assert challenge.type == ChallengeType.TURNSTILE

        # Test rate limit detection
        response_data["status_code"] = 429
        challenge = ChallengeRecord.create_from_response(uuid4(), response_data)
        assert challenge.type == ChallengeType.RATE_LIMIT

    def test_challenge_record_serialization(self):
        """Test ChallengeRecord serialization."""
        challenge = ChallengeRecord(
            url="https://challenge.example.com",
            type=ChallengeType.MANAGED,
            challenge_html="<html>Challenge</html>",
            solved=True,
            solve_duration_ms=2500
        )

        data = challenge.to_dict()

        assert data["url"] == "https://challenge.example.com"
        assert data["type"] == "managed"
        assert data["challenge_html"] == "<html>Challenge</html>"
        assert data["solved"] is True
        assert data["solve_duration_ms"] == 2500


class TestRequestResult:
    """Test RequestResult API response model."""

    def test_valid_request_result_creation(self):
        """Test creating valid RequestResult instances."""
        timing = RequestTiming(total_duration_ms=1500)
        result = RequestResult(
            request_id="req_12345",
            url="https://api.example.com",
            status_code=200,
            headers={"Content-Type": "application/json"},
            body='{"success": true}',
            timing=timing,
            success=True
        )

        assert result.request_id == "req_12345"
        assert result.url == "https://api.example.com"
        assert result.status_code == 200
        assert result.headers["Content-Type"] == "application/json"
        assert result.body == '{"success": true}'
        assert result.timing.total_duration_ms == 1500
        assert result.success is True

    def test_request_result_with_challenge(self):
        """Test RequestResult with challenge information."""
        challenge = Challenge(
            challenge_id="ch_123",
            request_id="req_123",
            type="javascript",
            url="https://example.com",
            solved=True,
            solve_duration_ms=2000
        )

        timing = RequestTiming()
        result = RequestResult(
            request_id="req_123",
            url="https://example.com",
            status_code=200,
            headers={},
            body="success",
            timing=timing,
            success=True,
            challenge=challenge
        )

        assert result.challenge is not None
        assert result.challenge.challenge_id == "ch_123"
        assert result.challenge.solved is True
        assert result.challenge.solve_duration_ms == 2000

    def test_request_result_with_error(self):
        """Test RequestResult with error information."""
        timing = RequestTiming()
        result = RequestResult(
            request_id="req_error",
            url="https://timeout.example.com",
            status_code=0,
            headers={},
            body="",
            timing=timing,
            success=False,
            error="Connection timeout"
        )

        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.status_code == 0


class TestBatchRequestResult:
    """Test BatchRequestResult API response model."""

    def test_valid_batch_result_creation(self):
        """Test creating valid BatchRequestResult instances."""
        summary = BatchSummary(
            duration_ms=5000,
            requests_per_second=20.0,
            success_rate=0.95,
            challenges_encountered=5,
            challenge_solve_rate=1.0
        )

        results = [
            RequestResult("req_1", "https://example.com", 200, {}, "ok", RequestTiming(), True),
            RequestResult("req_2", "https://example.com", 200, {}, "ok", RequestTiming(), True)
        ]

        batch_result = BatchRequestResult(
            session_id="sess_123",
            total_requests=100,
            completed_requests=95,
            failed_requests=5,
            results=results,
            summary=summary
        )

        assert batch_result.session_id == "sess_123"
        assert batch_result.total_requests == 100
        assert batch_result.completed_requests == 95
        assert batch_result.failed_requests == 5
        assert len(batch_result.results) == 2
        assert batch_result.summary.success_rate == 0.95


class TestSession:
    """Test Session API response model."""

    def test_valid_session_creation(self):
        """Test creating valid Session instances."""
        config = {
            "browser_version": "120.0.0.0",
            "concurrency_limit": 10,
            "rate_limit": 5.0,
            "default_timeout": 30
        }

        stats = {
            "total_requests": 150,
            "completed_requests": 140,
            "failed_requests": 10,
            "challenges_encountered": 20
        }

        session = Session(
            session_id="sess_abc123",
            name="Test Session",
            status="running",
            config=config,
            stats=stats,
            created_at="2024-01-01T12:00:00",
            started_at="2024-01-01T12:00:30",
            completed_at=None
        )

        assert session.session_id == "sess_abc123"
        assert session.name == "Test Session"
        assert session.status == "running"
        assert session.config["browser_version"] == "120.0.0.0"
        assert session.stats["total_requests"] == 150
        assert session.completed_at is None


class TestChallenge:
    """Test Challenge API response model."""

    def test_valid_challenge_creation(self):
        """Test creating valid Challenge instances."""
        challenge = Challenge(
            challenge_id="ch_xyz789",
            request_id="req_123",
            type="turnstile",
            url="https://example.com/challenge",
            solved=True,
            solve_duration_ms=3000,
            detected_at="2024-01-01T12:00:00",
            solved_at="2024-01-01T12:00:03"
        )

        assert challenge.challenge_id == "ch_xyz789"
        assert challenge.request_id == "req_123"
        assert challenge.type == "turnstile"
        assert challenge.url == "https://example.com/challenge"
        assert challenge.solved is True
        assert challenge.solve_duration_ms == 3000

    def test_challenge_failed_scenario(self):
        """Test Challenge with failed solving."""
        challenge = Challenge(
            challenge_id="ch_failed",
            request_id="req_456",
            type="javascript",
            url="https://example.com/challenge",
            solved=False,
            error_message="Timeout during challenge solving",
            detected_at="2024-01-01T12:00:00"
        )

        assert challenge.solved is False
        assert challenge.error_message == "Timeout during challenge solving"
        assert challenge.solved_at is None


class TestModelIntegration:
    """Test integration between different models."""

    def test_test_request_with_browser_config(self):
        """Test TestRequest integration with BrowserConfig."""
        browser_config = BrowserConfig(
            version="119.0.0.0",
            user_agent="Custom Browser",
            viewport_width=1366,
            viewport_height=768
        )

        request = TestRequest(
            url="https://example.com",
            browser_config=browser_config
        )

        assert request.browser_config.version == "119.0.0.0"
        assert request.browser_config.user_agent == "Custom Browser"
        assert request.browser_config.viewport_width == 1366

    def test_test_request_with_proxy_config(self):
        """Test TestRequest integration with ProxyConfig."""
        proxy_config = ProxyConfig(
            type="socks5",
            host="proxy.example.com",
            port=1080,
            username="proxyuser",
            password="proxypass"
        )

        request = TestRequest(
            url="https://example.com",
            proxy_config=proxy_config
        )

        assert request.proxy_config.type == "socks5"
        assert request.proxy_config.host == "proxy.example.com"
        assert request.proxy_config.username == "proxyuser"

    def test_challenge_record_with_request_id(self):
        """Test ChallengeRecord integration with TestRequest."""
        request = TestRequest(url="https://example.com")

        challenge = ChallengeRecord(
            request_id=request.request_id,
            url=request.url,
            type=ChallengeType.JAVASCRIPT
        )

        assert challenge.request_id == request.request_id
        assert challenge.url == request.url

    def test_model_conversion_functions(self):
        """Test model conversion utility functions."""
        from cloudflare_research.models import (
            test_request_to_request_result,
            challenge_record_to_challenge
        )

        # Create test request
        request = TestRequest(url="https://example.com")
        request.mark_completed(200, {"Content-Type": "text/html"}, "success", RequestTiming())

        # Convert to API response model
        result = test_request_to_request_result(request)

        assert result.request_id == str(request.request_id)
        assert result.url == request.url
        assert result.status_code == 200
        assert result.success is True

        # Test challenge conversion
        challenge_record = ChallengeRecord(
            url="https://example.com/challenge",
            type=ChallengeType.TURNSTILE
        )
        challenge_record.mark_solved({"token": "test_token"})

        challenge = challenge_record_to_challenge(challenge_record)

        assert challenge.challenge_id == str(challenge_record.challenge_id)
        assert challenge.type == "turnstile"
        assert challenge.solved is True


class TestModelValidation:
    """Test model validation and edge cases."""

    def test_enum_validation(self):
        """Test enum value validation."""
        # Valid enum values
        request = TestRequest(url="https://example.com", method=HttpMethod.POST)
        assert request.method == HttpMethod.POST

        challenge = ChallengeRecord(url="https://example.com", type=ChallengeType.MANAGED)
        assert challenge.type == ChallengeType.MANAGED

        # Test enum string conversion
        assert HttpMethod.GET.value == "GET"
        assert ChallengeType.JAVASCRIPT.value == "javascript"

    def test_uuid_handling(self):
        """Test UUID generation and validation."""
        request1 = TestRequest(url="https://example.com")
        request2 = TestRequest(url="https://example.com")

        # Each request should have unique ID
        assert request1.request_id != request2.request_id
        assert isinstance(request1.request_id, UUID)
        assert isinstance(request2.request_id, UUID)

    def test_datetime_handling(self):
        """Test datetime field handling."""
        request = TestRequest(url="https://example.com")

        # created_at should be set automatically
        assert isinstance(request.created_at, datetime)
        assert request.started_at is None
        assert request.completed_at is None

        # Test execution lifecycle timestamps
        request.start_execution()
        assert request.started_at is not None
        assert request.started_at > request.created_at

        request.mark_completed(200, {}, "success", RequestTiming())
        assert request.completed_at is not None
        assert request.completed_at >= request.started_at

    def test_optional_field_handling(self):
        """Test handling of optional fields."""
        # Test minimal request creation
        request = TestRequest(url="https://example.com")

        assert request.session_id is None
        assert request.body is None
        assert request.proxy_config is None
        assert request.status_code is None
        assert request.response_body is None
        assert request.error_message is None

    def test_data_serialization_round_trip(self):
        """Test complete serialization and deserialization."""
        # Create complex request with all fields
        browser_config = BrowserConfig(version="120.0.0.0", user_agent="Test")
        proxy_config = ProxyConfig(type="http", host="proxy.com", port=8080)

        original_request = TestRequest(
            url="https://example.com",
            method=HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body='{"test": "data"}',
            browser_config=browser_config,
            proxy_config=proxy_config,
            timeout=60
        )

        # Serialize to dict
        data = original_request.to_dict()

        # Deserialize back
        restored_request = TestRequest.from_dict(data)

        # Verify all fields match
        assert restored_request.url == original_request.url
        assert restored_request.method == original_request.method
        assert restored_request.headers == original_request.headers
        assert restored_request.body == original_request.body
        assert restored_request.timeout == original_request.timeout
        assert restored_request.browser_config.version == original_request.browser_config.version
        assert restored_request.proxy_config.host == original_request.proxy_config.host


if __name__ == "__main__":
    pytest.main([__file__, "-v"])