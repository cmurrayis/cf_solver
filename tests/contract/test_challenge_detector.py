"""Contract test for challenge detection interface.

This test validates the challenge detection interface against the API specification.
Tests MUST fail initially to follow TDD principles.
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock

# Import will fail until implementation exists - this is expected for TDD
try:
    from cloudflare_research.challenges import ChallengeDetector
    from cloudflare_research.models import Challenge, ChallengeRecord
except ImportError:
    # Expected during TDD phase - tests should fail initially
    ChallengeDetector = None
    Challenge = None
    ChallengeRecord = None


@pytest.mark.contract
@pytest.mark.asyncio
class TestChallengeDetector:
    """Contract tests for challenge detection interface."""

    @pytest.fixture
    def detector(self):
        """Create ChallengeDetector instance for testing."""
        if ChallengeDetector is None:
            pytest.skip("ChallengeDetector not implemented yet - TDD phase")
        return ChallengeDetector()

    @pytest.fixture
    def sample_html_responses(self):
        """Sample HTML responses for testing challenge detection."""
        return {
            "javascript_challenge": """<html><head><title>Just a moment...</title></head>
                <body><script>window._cf_chl_opt={...}</script></body></html>""",
            "turnstile_challenge": """<html><body>
                <div class="cf-turnstile" data-sitekey="abc123"></div></body></html>""",
            "managed_challenge": """<html><body>
                <div id="challenge-form"><h1>Checking your browser</h1></div></body></html>""",
            "rate_limit": """<html><body><h1>Rate limited</h1>
                <p>Too many requests</p></body></html>""",
            "normal_response": """<html><head><title>Normal Page</title></head>
                <body><h1>Welcome</h1><p>Normal content</p></body></html>"""
        }

    async def test_detector_class_exists(self):
        """Test that ChallengeDetector class exists."""
        assert ChallengeDetector is not None

    async def test_detect_method_exists(self, detector):
        """Test that detect() method exists and is callable."""
        assert hasattr(detector, 'detect')
        assert callable(getattr(detector, 'detect'))

    async def test_detect_javascript_challenge(self, detector, sample_html_responses):
        """Test detection of JavaScript challenge."""
        response_data = {
            "status_code": 503,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["javascript_challenge"],
            "url": "https://example.com"
        }

        # Contract: detect(response_data) -> Challenge or None
        challenge = await detector.detect(response_data)

        assert challenge is not None
        assert isinstance(challenge, Challenge)
        assert challenge.type == "javascript"
        assert challenge.url == "https://example.com"
        assert challenge.solved is False
        assert isinstance(challenge.challenge_id, str)

    async def test_detect_turnstile_challenge(self, detector, sample_html_responses):
        """Test detection of Turnstile challenge."""
        response_data = {
            "status_code": 403,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["turnstile_challenge"],
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)

        assert challenge is not None
        assert isinstance(challenge, Challenge)
        assert challenge.type == "turnstile"
        assert challenge.url == "https://example.com"
        assert challenge.solved is False

    async def test_detect_managed_challenge(self, detector, sample_html_responses):
        """Test detection of managed challenge."""
        response_data = {
            "status_code": 403,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["managed_challenge"],
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)

        assert challenge is not None
        assert isinstance(challenge, Challenge)
        assert challenge.type == "managed"
        assert challenge.url == "https://example.com"

    async def test_detect_rate_limit(self, detector, sample_html_responses):
        """Test detection of rate limiting."""
        response_data = {
            "status_code": 429,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["rate_limit"],
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)

        assert challenge is not None
        assert isinstance(challenge, Challenge)
        assert challenge.type == "rate_limit"

    async def test_detect_no_challenge(self, detector, sample_html_responses):
        """Test detection when no challenge is present."""
        response_data = {
            "status_code": 200,
            "headers": {"server": "nginx"},
            "body": sample_html_responses["normal_response"],
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)
        assert challenge is None

    async def test_detect_unknown_challenge(self, detector):
        """Test detection of unknown challenge type."""
        response_data = {
            "status_code": 403,
            "headers": {"server": "cloudflare"},
            "body": "<html><body><div>Unknown challenge format</div></body></html>",
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)

        if challenge is not None:
            assert isinstance(challenge, Challenge)
            assert challenge.type == "unknown"

    async def test_detect_invalid_input(self, detector):
        """Test detection with invalid input data."""
        # Missing required fields
        with pytest.raises((ValueError, KeyError, TypeError)):
            await detector.detect({})

        # Invalid status code
        with pytest.raises((ValueError, TypeError)):
            await detector.detect({
                "status_code": "not-a-number",
                "headers": {},
                "body": "",
                "url": "https://example.com"
            })

    async def test_detect_performance_requirement(self, detector, sample_html_responses):
        """Test that challenge detection meets performance requirements (<10ms)."""
        import time

        response_data = {
            "status_code": 503,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["javascript_challenge"],
            "url": "https://example.com"
        }

        # Measure detection time
        start_time = time.perf_counter()
        challenge = await detector.detect(response_data)
        end_time = time.perf_counter()

        detection_time_ms = (end_time - start_time) * 1000

        # Should be under 10ms as per specification
        assert detection_time_ms < 10, f"Detection took {detection_time_ms:.2f}ms, should be <10ms"
        assert challenge is not None

    async def test_challenge_structure_validation(self, detector, sample_html_responses):
        """Test that detected challenges have correct structure."""
        response_data = {
            "status_code": 503,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["javascript_challenge"],
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)

        # Validate all required Challenge fields
        assert hasattr(challenge, 'challenge_id')
        assert hasattr(challenge, 'request_id')
        assert hasattr(challenge, 'type')
        assert hasattr(challenge, 'url')
        assert hasattr(challenge, 'solved')
        assert hasattr(challenge, 'solve_duration_ms')
        assert hasattr(challenge, 'detected_at')

        # Validate types
        assert isinstance(challenge.challenge_id, str)
        assert isinstance(challenge.type, str)
        assert isinstance(challenge.url, str)
        assert isinstance(challenge.solved, bool)
        assert challenge.solve_duration_ms is None or isinstance(challenge.solve_duration_ms, int)

        # Validate enums
        valid_types = ['javascript', 'turnstile', 'managed', 'rate_limit', 'unknown']
        assert challenge.type in valid_types

    async def test_challenge_id_uniqueness(self, detector, sample_html_responses):
        """Test that challenge IDs are unique."""
        response_data = {
            "status_code": 503,
            "headers": {"server": "cloudflare"},
            "body": sample_html_responses["javascript_challenge"],
            "url": "https://example.com"
        }

        # Detect same challenge multiple times
        challenges = []
        for _ in range(3):
            challenge = await detector.detect(response_data)
            if challenge:
                challenges.append(challenge)

        # All challenge IDs should be unique
        challenge_ids = [c.challenge_id for c in challenges]
        assert len(set(challenge_ids)) == len(challenge_ids)

    async def test_detect_method_signature(self, detector):
        """Test detect() method has correct signature."""
        import inspect

        sig = inspect.signature(detector.detect)
        params = sig.parameters

        # Check required parameter
        assert 'response_data' in params

        # Check return type annotation
        return_annotation = sig.return_annotation
        assert return_annotation is not inspect.Signature.empty

    async def test_detector_configuration(self):
        """Test detector can be configured with options."""
        if ChallengeDetector is None:
            pytest.skip("ChallengeDetector not implemented yet - TDD phase")

        # Test with configuration options
        config = {
            "enable_javascript_detection": True,
            "enable_turnstile_detection": True,
            "enable_managed_detection": True,
            "detection_timeout_ms": 5000
        }

        detector = ChallengeDetector(config=config)
        assert hasattr(detector, 'detect')

    async def test_multiple_challenges_in_response(self, detector):
        """Test handling of response with multiple challenge indicators."""
        complex_response = """<html><body>
            <script>window._cf_chl_opt={...}</script>
            <div class="cf-turnstile" data-sitekey="abc123"></div>
        </body></html>"""

        response_data = {
            "status_code": 503,
            "headers": {"server": "cloudflare"},
            "body": complex_response,
            "url": "https://example.com"
        }

        challenge = await detector.detect(response_data)

        # Should detect the primary challenge type
        assert challenge is not None
        assert isinstance(challenge, Challenge)
        assert challenge.type in ['javascript', 'turnstile']

    async def test_challenge_context_preservation(self, detector, sample_html_responses):
        """Test that challenge context is preserved for solving."""
        response_data = {
            "status_code": 503,
            "headers": {
                "server": "cloudflare",
                "cf-ray": "12345678-ABC",
                "set-cookie": "cf_clearance=test123"
            },
            "body": sample_html_responses["javascript_challenge"],
            "url": "https://protected.example.com/api"
        }

        challenge = await detector.detect(response_data)

        assert challenge is not None
        # Context should be available for challenge solving
        # (Implementation details would be tested in integration tests)