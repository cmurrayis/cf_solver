"""ChallengeRecord model for tracking security challenges.

Represents information about security challenges encountered during testing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4


class ChallengeType(Enum):
    """Types of challenges that can be encountered."""
    JAVASCRIPT = "javascript"
    TURNSTILE = "turnstile"
    MANAGED = "managed"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


@dataclass
class ChallengeRecord:
    """
    Represents a security challenge encountered during testing.

    This entity captures all information about challenges detected and solved
    during browser emulation requests, including timing and solution data.
    """

    # Core identifiers
    challenge_id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)
    session_id: Optional[UUID] = None

    # Challenge details
    type: ChallengeType = ChallengeType.UNKNOWN
    url: str = ""
    challenge_html: Optional[str] = None
    javascript_code: Optional[str] = None

    # Solution data
    solution_data: Optional[Dict[str, Any]] = None
    cf_clearance: Optional[str] = None
    solved: bool = False
    solve_duration_ms: Optional[int] = None

    # Error handling
    error_message: Optional[str] = None

    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)
    solved_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate challenge record after initialization."""
        self._validate_url()
        self._validate_solve_duration()

    def _validate_url(self) -> None:
        """Validate challenge URL format."""
        if not self.url:
            raise ValueError("Challenge URL is required")

        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError("Challenge URL must start with http:// or https://")

    def _validate_solve_duration(self) -> None:
        """Validate solve duration."""
        if self.solve_duration_ms is not None:
            if not isinstance(self.solve_duration_ms, int):
                raise TypeError("Solve duration must be an integer")

            if self.solve_duration_ms < 0:
                raise ValueError("Solve duration must be non-negative")

    @property
    def is_solved(self) -> bool:
        """Check if challenge was successfully solved."""
        return self.solved and self.solved_at is not None

    @property
    def detection_to_solution_ms(self) -> Optional[int]:
        """Calculate time from detection to solution."""
        if self.solved_at:
            delta = self.solved_at - self.detected_at
            return int(delta.total_seconds() * 1000)
        return None

    def mark_solved(self, solution_data: Dict[str, Any],
                   cf_clearance: Optional[str] = None) -> None:
        """Mark challenge as solved with solution data."""
        self.solved = True
        self.solved_at = datetime.now()
        self.solution_data = solution_data
        self.cf_clearance = cf_clearance
        self.solve_duration_ms = self.detection_to_solution_ms

    def mark_failed(self, error_message: str) -> None:
        """Mark challenge as failed to solve."""
        self.solved = False
        self.error_message = error_message
        self.solve_duration_ms = self.detection_to_solution_ms

    def extract_javascript(self, html_content: str) -> Optional[str]:
        """Extract JavaScript code from challenge HTML."""
        # Simple extraction - would be more sophisticated in real implementation
        import re
        
        # Look for common Cloudflare challenge patterns
        patterns = [
            r'<script[^>]*>([\s\S]*?window\._cf_chl_opt[\s\S]*?)</script>',
            r'<script[^>]*>([\s\S]*?challenge[\s\S]*?)</script>',
            r'<script[^>]*data-cf-[^>]*>([\s\S]*?)</script>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                self.javascript_code = match.group(1).strip()
                return self.javascript_code
        
        return None

    def get_challenge_context(self) -> Dict[str, Any]:
        """Get challenge context for solving."""
        return {
            "challenge_id": str(self.challenge_id),
            "type": self.type.value,
            "url": self.url,
            "html": self.challenge_html,
            "javascript": self.javascript_code,
            "detected_at": self.detected_at.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert challenge record to dictionary for serialization."""
        return {
            "challenge_id": str(self.challenge_id),
            "request_id": str(self.request_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "type": self.type.value,
            "url": self.url,
            "challenge_html": self.challenge_html,
            "javascript_code": self.javascript_code,
            "solution_data": self.solution_data,
            "cf_clearance": self.cf_clearance,
            "solved": self.solved,
            "solve_duration_ms": self.solve_duration_ms,
            "error_message": self.error_message,
            "detected_at": self.detected_at.isoformat(),
            "solved_at": self.solved_at.isoformat() if self.solved_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChallengeRecord":
        """Create ChallengeRecord from dictionary."""
        # Parse timestamps
        detected_at = datetime.fromisoformat(data["detected_at"]) if data.get("detected_at") else datetime.now()
        solved_at = datetime.fromisoformat(data["solved_at"]) if data.get("solved_at") else None

        return cls(
            challenge_id=UUID(data["challenge_id"]) if data.get("challenge_id") else uuid4(),
            request_id=UUID(data["request_id"]) if data.get("request_id") else uuid4(),
            session_id=UUID(data["session_id"]) if data.get("session_id") else None,
            type=ChallengeType(data.get("type", "unknown")),
            url=data["url"],
            challenge_html=data.get("challenge_html"),
            javascript_code=data.get("javascript_code"),
            solution_data=data.get("solution_data"),
            cf_clearance=data.get("cf_clearance"),
            solved=data.get("solved", False),
            solve_duration_ms=data.get("solve_duration_ms"),
            error_message=data.get("error_message"),
            detected_at=detected_at,
            solved_at=solved_at,
        )

    @classmethod
    def create_from_response(cls, request_id: UUID, response_data: Dict[str, Any]) -> "ChallengeRecord":
        """Create challenge record from HTTP response data."""
        challenge = cls(
            request_id=request_id,
            url=response_data.get("url", ""),
            challenge_html=response_data.get("body", "")
        )
        
        # Detect challenge type from response
        challenge._detect_challenge_type(response_data)
        
        # Extract JavaScript if present
        if challenge.challenge_html:
            challenge.extract_javascript(challenge.challenge_html)
        
        return challenge

    def _detect_challenge_type(self, response_data: Dict[str, Any]) -> None:
        """Detect challenge type from response data."""
        status_code = response_data.get("status_code", 200)
        headers = response_data.get("headers", {})
        body = response_data.get("body", "")
        
        # Check for rate limiting
        if status_code == 429:
            self.type = ChallengeType.RATE_LIMIT
            return
        
        # Check for Cloudflare server header
        server = headers.get("server", "").lower()
        if "cloudflare" not in server:
            return
        
        # Check body content for challenge indicators
        body_lower = body.lower()
        
        if "window._cf_chl_opt" in body or "challenge-platform" in body_lower:
            self.type = ChallengeType.JAVASCRIPT
        elif "cf-turnstile" in body or "turnstile" in body_lower:
            self.type = ChallengeType.TURNSTILE
        elif "checking your browser" in body_lower or "challenge-form" in body_lower:
            self.type = ChallengeType.MANAGED
        elif status_code in {403, 503} and "cloudflare" in body_lower:
            self.type = ChallengeType.UNKNOWN

    def __str__(self) -> str:
        """String representation of the challenge record."""
        return (
            f"ChallengeRecord(id={str(self.challenge_id)[:8]}..., "
            f"type={self.type.value}, solved={self.solved}, "
            f"duration={self.solve_duration_ms}ms)"
        )