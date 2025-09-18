"""Challenge handling module for Cloudflare challenges.

This module provides comprehensive challenge detection, solving, and handling
for various types of Cloudflare protection mechanisms.
"""

from .detector import (
    ChallengeType,
    ChallengeInfo,
    CloudflareDetector,
    create_challenge_detector,
    detect_challenge_quick,
    is_challenge_solvable,
)

from .solver import (
    ChallengeSolution,
    JSChallengeSolver,
    create_js_solver,
    solve_js_challenge,
)

from .handler import (
    ChallengeResult,
    ChallengeConfig,
    ChallengeHandler,
    create_challenge_handler,
    create_default_config,
    create_aggressive_config,
    create_conservative_config,
)

from .turnstile import (
    TurnstileChallenge,
    TurnstileSolution,
    TurnstileHandler,
    create_turnstile_handler,
    detect_turnstile_challenge,
    solve_turnstile_challenge,
)

from .parser import (
    FormField,
    ParsedScript,
    ParsedForm,
    ChallengeMetadata,
    ChallengeParser,
    create_challenge_parser,
    parse_challenge_response,
    extract_form_data,
    detect_challenge_type,
)

# Challenge type constants
SOLVABLE_CHALLENGES = {
    ChallengeType.JAVASCRIPT,
    ChallengeType.RATE_LIMITED,
}

UNSOLVABLE_CHALLENGES = {
    ChallengeType.MANAGED,
    ChallengeType.TURNSTILE,
    ChallengeType.BOT_FIGHT,
    ChallengeType.BLOCKED,
    ChallengeType.FIREWALL,
}

# Default configuration presets
DEFAULT_CHALLENGE_CONFIG = ChallengeConfig()

FAST_CONFIG = ChallengeConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=10.0,
    backoff_factor=1.5,
    randomize_delays=False,
)

THOROUGH_CONFIG = ChallengeConfig(
    max_attempts=5,
    base_delay=6.0,
    max_delay=120.0,
    backoff_factor=3.0,
    rate_limit_max_wait=900.0,  # 15 minutes
    randomize_delays=True,
)

# Challenge severity mapping
CHALLENGE_SEVERITY = {
    ChallengeType.NONE: 0,
    ChallengeType.RATE_LIMITED: 1,
    ChallengeType.JAVASCRIPT: 2,
    ChallengeType.UNKNOWN: 2,
    ChallengeType.MANAGED: 3,
    ChallengeType.TURNSTILE: 4,
    ChallengeType.BOT_FIGHT: 4,
    ChallengeType.BLOCKED: 5,
    ChallengeType.FIREWALL: 5,
}


class ChallengeManager:
    """High-level manager for all challenge-related operations."""

    def __init__(self, config: ChallengeConfig = None):
        self.config = config or DEFAULT_CHALLENGE_CONFIG
        self.detector = create_challenge_detector()
        self.handler = create_challenge_handler(self.config)

    async def process_response(self, response_content: str, response_headers: dict,
                             status_code: int, request_url: str, http_client) -> ChallengeResult:
        """Process a response and handle any challenges found."""
        return await self.handler.handle_challenge(
            response_content, response_headers, status_code, request_url, http_client
        )

    async def handle_challenge(self, response_content: str, response_headers: dict,
                             status_code: int, request_url: str, http_client) -> ChallengeResult:
        """Handle challenges found in a response (alias for process_response)."""
        return await self.process_response(
            response_content, response_headers, status_code, request_url, http_client
        )

    def detect_challenge_type(self, response_content: str, response_headers: dict = None,
                            status_code: int = 200) -> ChallengeType:
        """Detect challenge type from response."""
        challenge_info = self.detector.detect_challenge(
            response_content, response_headers, status_code
        )
        return challenge_info.challenge_type

    def is_response_challenging(self, response_content: str, response_headers: dict = None,
                              status_code: int = 200) -> bool:
        """Check if response contains a challenge."""
        return self.detector.is_challenge_response(response_content, response_headers, status_code)

    def can_solve_challenge(self, challenge_type: ChallengeType) -> bool:
        """Check if a challenge type can be automatically solved."""
        return challenge_type in SOLVABLE_CHALLENGES

    def get_challenge_severity(self, challenge_type: ChallengeType) -> int:
        """Get severity level of a challenge type (0-5)."""
        return CHALLENGE_SEVERITY.get(challenge_type, 2)

    def get_stats(self) -> dict:
        """Get challenge handling statistics."""
        return self.handler.get_stats()

    def reset_stats(self) -> None:
        """Reset challenge handling statistics."""
        self.handler.reset_stats()


def create_challenge_manager(config: ChallengeConfig = None) -> ChallengeManager:
    """Create a new challenge manager instance."""
    return ChallengeManager(config)


def analyze_challenge_response(response_content: str, response_headers: dict = None,
                             status_code: int = 200, url: str = "") -> dict:
    """Analyze a response for challenge information."""
    detector = create_challenge_detector()
    challenge_info = detector.detect_challenge(response_content, response_headers, status_code, url)

    return {
        "has_challenge": challenge_info.challenge_type != ChallengeType.NONE,
        "challenge_type": challenge_info.challenge_type.value,
        "confidence": challenge_info.confidence,
        "solvable": challenge_info.challenge_type in SOLVABLE_CHALLENGES,
        "severity": CHALLENGE_SEVERITY.get(challenge_info.challenge_type, 2),
        "ray_id": challenge_info.ray_id,
        "details": challenge_info.to_dict(),
    }


def get_challenge_recommendations(challenge_type: ChallengeType) -> dict:
    """Get recommendations for handling a specific challenge type."""
    recommendations = {
        ChallengeType.NONE: {
            "action": "continue",
            "description": "No challenge detected, proceed normally",
            "estimated_time": 0,
        },
        ChallengeType.JAVASCRIPT: {
            "action": "solve_automatically",
            "description": "JavaScript challenge can be solved automatically",
            "estimated_time": 5,
            "config_suggestions": {
                "base_delay": 4.0,
                "max_attempts": 3,
            }
        },
        ChallengeType.RATE_LIMITED: {
            "action": "wait_and_retry",
            "description": "Wait for rate limit cooldown and retry",
            "estimated_time": 30,
            "config_suggestions": {
                "rate_limit_max_wait": 300.0,
            }
        },
        ChallengeType.MANAGED: {
            "action": "manual_intervention",
            "description": "Requires human verification - manual intervention needed",
            "estimated_time": 60,
        },
        ChallengeType.TURNSTILE: {
            "action": "captcha_service",
            "description": "Requires CAPTCHA solving service or user interaction",
            "estimated_time": 30,
        },
        ChallengeType.BOT_FIGHT: {
            "action": "improve_fingerprint",
            "description": "Improve browser fingerprinting and behavior simulation",
            "estimated_time": 0,
        },
        ChallengeType.BLOCKED: {
            "action": "change_approach",
            "description": "Access blocked - may need different IP/approach",
            "estimated_time": 0,
        },
        ChallengeType.FIREWALL: {
            "action": "check_firewall_rules",
            "description": "Firewall block - check request patterns and headers",
            "estimated_time": 0,
        },
        ChallengeType.UNKNOWN: {
            "action": "investigate",
            "description": "Unknown challenge type - requires investigation",
            "estimated_time": 30,
        },
    }

    return recommendations.get(challenge_type, recommendations[ChallengeType.UNKNOWN])


# Utility functions for common challenge scenarios
async def quick_challenge_check(response_content: str, response_headers: dict = None,
                              status_code: int = 200) -> bool:
    """Quick check if response has a challenge."""
    detector = create_challenge_detector()
    return detector.is_challenge_response(response_content, response_headers, status_code)


async def solve_challenge_if_present(response_content: str, response_headers: dict,
                                   status_code: int, request_url: str, http_client,
                                   config: ChallengeConfig = None) -> ChallengeResult:
    """Convenience function to detect and solve challenge if present."""
    handler = create_challenge_handler(config)
    return await handler.handle_challenge(
        response_content, response_headers, status_code, request_url, http_client
    )


# Aliases for contract test compatibility
ChallengeDetector = CloudflareDetector
JavaScriptSolver = JSChallengeSolver

# Export public API
__all__ = [
    # Enums
    "ChallengeType",

    # Classes
    "ChallengeInfo",
    "ChallengeSolution",
    "ChallengeResult",
    "ChallengeConfig",
    "CloudflareDetector",
    "JSChallengeSolver",
    "ChallengeDetector",  # Alias for contract tests
    "JavaScriptSolver",   # Alias for contract tests
    "ChallengeHandler",
    "ChallengeManager",
    "TurnstileChallenge",
    "TurnstileSolution",
    "TurnstileHandler",
    "FormField",
    "ParsedScript",
    "ParsedForm",
    "ChallengeMetadata",
    "ChallengeParser",

    # Factory functions
    "create_challenge_detector",
    "create_js_solver",
    "create_challenge_handler",
    "create_challenge_manager",
    "create_default_config",
    "create_aggressive_config",
    "create_conservative_config",
    "create_turnstile_handler",
    "create_challenge_parser",

    # Utility functions
    "detect_challenge_quick",
    "is_challenge_solvable",
    "solve_js_challenge",
    "analyze_challenge_response",
    "get_challenge_recommendations",
    "quick_challenge_check",
    "solve_challenge_if_present",
    "detect_turnstile_challenge",
    "solve_turnstile_challenge",
    "parse_challenge_response",
    "extract_form_data",
    "detect_challenge_type",

    # Constants
    "SOLVABLE_CHALLENGES",
    "UNSOLVABLE_CHALLENGES",
    "CHALLENGE_SEVERITY",
    "DEFAULT_CHALLENGE_CONFIG",
    "FAST_CONFIG",
    "THOROUGH_CONFIG",
]