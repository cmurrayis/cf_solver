"""Data models for the Cloudflare Research module.

This module provides all data models and type definitions for browser emulation
and Cloudflare challenge research functionality.
"""

from typing import Union, Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime

# Import all models
from .test_request import (
    TestRequest,
    RequestStatus,
    HttpMethod,
    BrowserConfig,
    ProxyConfig,
    RequestTiming,
)

from .test_session import (
    TestSession,
    SessionStatus,
    SessionStats,
    SessionConfig,
)

from .challenge_record import (
    ChallengeRecord,
    ChallengeType,
)

from .performance_metrics import (
    PerformanceMetrics,
    MetricType,
)

from .test_configuration import (
    TestConfiguration,
    BrowserProfile,
    TLSProfile,
    HeadersProfile,
    ProxySettings,
    RateLimits,
    ChallengeSettings,
)

# Type aliases for common patterns
RequestID = UUID
SessionID = UUID
ChallengeID = UUID
MetricsID = UUID
ConfigID = UUID

# API response models for contract compliance
class RequestResult:
    """Result of a single request execution."""

    def __init__(self, request_id: str, url: str, status_code: int,
                 headers: Dict[str, str], body: str, timing: RequestTiming,
                 success: bool, challenge: Optional['Challenge'] = None,
                 error: Optional[str] = None):
        self.request_id = request_id
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.timing = timing
        self.success = success
        self.challenge = challenge
        self.error = error


class BatchRequestResult:
    """Result of batch request execution."""

    def __init__(self, session_id: str, total_requests: int,
                 completed_requests: int, failed_requests: int,
                 results: List[RequestResult], summary: 'BatchSummary'):
        self.session_id = session_id
        self.total_requests = total_requests
        self.completed_requests = completed_requests
        self.failed_requests = failed_requests
        self.results = results
        self.summary = summary


class BatchSummary:
    """Summary statistics for batch request execution."""

    def __init__(self, duration_ms: int, requests_per_second: float,
                 success_rate: float, challenges_encountered: int,
                 challenge_solve_rate: float):
        self.duration_ms = duration_ms
        self.requests_per_second = requests_per_second
        self.success_rate = success_rate
        self.challenges_encountered = challenges_encountered
        self.challenge_solve_rate = challenge_solve_rate


class Session:
    """Session information for API responses."""

    def __init__(self, session_id: str, name: str, status: str,
                 config: Dict[str, Any], stats: Dict[str, Any],
                 created_at: str, started_at: Optional[str] = None,
                 completed_at: Optional[str] = None):
        self.session_id = session_id
        self.name = name
        self.status = status
        self.config = config
        self.stats = stats
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at


class Challenge:
    """Challenge information for API responses."""

    def __init__(self, challenge_id: str, request_id: str, type: str,
                 url: str, solved: bool, solve_duration_ms: Optional[int] = None,
                 error_message: Optional[str] = None, detected_at: Optional[str] = None,
                 solved_at: Optional[str] = None):
        self.challenge_id = challenge_id
        self.request_id = request_id
        self.type = type
        self.url = url
        self.solved = solved
        self.solve_duration_ms = solve_duration_ms
        self.error_message = error_message
        self.detected_at = detected_at
        self.solved_at = solved_at


# Utility functions for model conversion
def test_request_to_request_result(test_request: TestRequest) -> RequestResult:
    """Convert TestRequest to RequestResult for API responses."""
    challenge = None
    if hasattr(test_request, 'challenge') and test_request.challenge:
        challenge = Challenge(
            challenge_id=str(test_request.challenge.challenge_id),
            request_id=str(test_request.request_id),
            type=test_request.challenge.type.value,
            url=test_request.challenge.url,
            solved=test_request.challenge.solved,
            solve_duration_ms=test_request.challenge.solve_duration_ms,
            error_message=test_request.challenge.error_message,
            detected_at=test_request.challenge.detected_at.isoformat() if test_request.challenge.detected_at else None,
            solved_at=test_request.challenge.solved_at.isoformat() if test_request.challenge.solved_at else None,
        )

    return RequestResult(
        request_id=str(test_request.request_id),
        url=test_request.url,
        status_code=test_request.status_code or 0,
        headers=test_request.response_headers,
        body=test_request.response_body or "",
        timing=test_request.timing,
        success=test_request.is_successful,
        challenge=challenge,
        error=test_request.error_message,
    )


def test_session_to_session(test_session: TestSession) -> Session:
    """Convert TestSession to Session for API responses."""
    return Session(
        session_id=str(test_session.session_id),
        name=test_session.config.name,
        status=test_session.status.value,
        config={
            "browser_version": test_session.config.browser_version,
            "concurrency_limit": test_session.config.concurrency_limit,
            "rate_limit": test_session.config.rate_limit,
            "default_timeout": test_session.config.default_timeout,
        },
        stats={
            "total_requests": test_session.stats.total_requests,
            "completed_requests": test_session.stats.completed_requests,
            "failed_requests": test_session.stats.failed_requests,
            "challenges_encountered": test_session.stats.challenges_encountered,
        },
        created_at=test_session.created_at.isoformat(),
        started_at=test_session.started_at.isoformat() if test_session.started_at else None,
        completed_at=test_session.completed_at.isoformat() if test_session.completed_at else None,
    )


def challenge_record_to_challenge(challenge_record: ChallengeRecord) -> Challenge:
    """Convert ChallengeRecord to Challenge for API responses."""
    return Challenge(
        challenge_id=str(challenge_record.challenge_id),
        request_id=str(challenge_record.request_id),
        type=challenge_record.type.value,
        url=challenge_record.url,
        solved=challenge_record.solved,
        solve_duration_ms=challenge_record.solve_duration_ms,
        error_message=challenge_record.error_message,
        detected_at=challenge_record.detected_at.isoformat(),
        solved_at=challenge_record.solved_at.isoformat() if challenge_record.solved_at else None,
    )


# Export all public classes and types
__all__ = [
    # Core models
    "TestRequest", "TestSession", "ChallengeRecord", "PerformanceMetrics", "TestConfiguration",

    # Enums
    "RequestStatus", "HttpMethod", "SessionStatus", "ChallengeType", "MetricType",
    "BrowserProfile", "TLSProfile",

    # Configuration classes
    "BrowserConfig", "ProxyConfig", "SessionConfig", "SessionStats",
    "HeadersProfile", "ProxySettings", "RateLimits", "ChallengeSettings",

    # Timing and metrics
    "RequestTiming",

    # API response models
    "RequestResult", "BatchRequestResult", "BatchSummary", "Session", "Challenge",

    # Type aliases
    "RequestID", "SessionID", "ChallengeID", "MetricsID", "ConfigID",

    # Utility functions
    "test_request_to_request_result", "test_session_to_session", "challenge_record_to_challenge",
]


# Version info
__version__ = "1.0.0"
__author__ = "CF Solver Research"
__description__ = "Data models for high-performance browser emulation research"