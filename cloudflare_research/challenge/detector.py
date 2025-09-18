"""Cloudflare challenge detection and classification.

Detects various types of Cloudflare challenges including JavaScript challenges,
Turnstile CAPTCHAs, managed challenges, and rate limiting responses.
"""

import re
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class ChallengeType(Enum):
    """Types of Cloudflare challenges."""
    NONE = "none"
    JAVASCRIPT = "javascript"
    TURNSTILE = "turnstile"
    MANAGED = "managed"
    RATE_LIMITED = "rate_limited"
    BOT_FIGHT = "bot_fight"
    BLOCKED = "blocked"
    FIREWALL = "firewall"
    UNKNOWN = "unknown"


@dataclass
class ChallengeInfo:
    """Information about a detected challenge."""
    challenge_type: ChallengeType
    confidence: float  # 0.0 to 1.0

    # Challenge details
    challenge_url: Optional[str] = None
    challenge_id: Optional[str] = None
    site_key: Optional[str] = None
    ray_id: Optional[str] = None

    # JavaScript challenge specific
    js_code: Optional[str] = None
    form_data: Optional[Dict[str, str]] = None
    submit_url: Optional[str] = None

    # Turnstile specific
    turnstile_action: Optional[str] = None
    turnstile_cdata: Optional[str] = None

    # Metadata
    response_headers: Dict[str, str] = None
    html_content: Optional[str] = None
    status_code: int = 200

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "challenge_type": self.challenge_type.value,
            "confidence": self.confidence,
            "challenge_url": self.challenge_url,
            "challenge_id": self.challenge_id,
            "site_key": self.site_key,
            "ray_id": self.ray_id,
            "js_code": self.js_code[:500] + "..." if self.js_code and len(self.js_code) > 500 else self.js_code,
            "form_data": self.form_data,
            "submit_url": self.submit_url,
            "turnstile_action": self.turnstile_action,
            "turnstile_cdata": self.turnstile_cdata,
            "status_code": self.status_code,
            "has_html_content": bool(self.html_content),
        }


class CloudflareDetector:
    """Detects and classifies Cloudflare challenges from HTTP responses."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for challenge detection."""

        # JavaScript challenge patterns
        self.js_challenge_patterns = {
            "challenge_form": re.compile(r'<form[^>]*id="challenge-form"[^>]*>', re.IGNORECASE),
            "cf_challenge": re.compile(r'window\._cf_chl_[a-zA-Z]+', re.IGNORECASE),
            "jschl_vc": re.compile(r'name="jschl_vc"\s+value="([^"]+)"'),
            "jschl_answer": re.compile(r'name="jschl_answer"'),
            "cf_challenge_submission": re.compile(r'var\s+[a-zA-Z_$][a-zA-Z0-9_$]*\s*=\s*document\.getElementById\(["\']challenge-form["\']'),
        }

        # Turnstile patterns
        self.turnstile_patterns = {
            "turnstile_widget": re.compile(r'cf-turnstile', re.IGNORECASE),
            "turnstile_script": re.compile(r'challenges\.cloudflare\.com/turnstile', re.IGNORECASE),
            "site_key": re.compile(r'data-sitekey=["\']([^"\']+)["\']', re.IGNORECASE),
            "turnstile_callback": re.compile(r'data-callback=["\']([^"\']+)["\']', re.IGNORECASE),
            "turnstile_action": re.compile(r'data-action=["\']([^"\']+)["\']', re.IGNORECASE),
        }

        # Managed challenge patterns
        self.managed_patterns = {
            "managed_challenge": re.compile(r'managed challenge', re.IGNORECASE),
            "checking_browser": re.compile(r'checking.*browser', re.IGNORECASE),
            "please_wait": re.compile(r'please\s+wait', re.IGNORECASE),
            "ray_id": re.compile(r'Ray ID:\s*([a-f0-9]+)', re.IGNORECASE),
        }

        # Rate limiting patterns
        self.rate_limit_patterns = {
            "rate_limited": re.compile(r'rate.*limit', re.IGNORECASE),
            "too_many_requests": re.compile(r'too\s+many\s+requests', re.IGNORECASE),
            "retry_after": re.compile(r'retry[_\s]*after', re.IGNORECASE),
        }

        # Bot fight mode patterns
        self.bot_fight_patterns = {
            "bot_fight": re.compile(r'bot\s*fight\s*mode', re.IGNORECASE),
            "suspicious_activity": re.compile(r'suspicious\s+activity', re.IGNORECASE),
            "automated_traffic": re.compile(r'automated\s+traffic', re.IGNORECASE),
        }

        # Blocked/Firewall patterns
        self.blocked_patterns = {
            "access_denied": re.compile(r'access\s+denied', re.IGNORECASE),
            "blocked": re.compile(r'blocked', re.IGNORECASE),
            "forbidden": re.compile(r'forbidden', re.IGNORECASE),
            "firewall": re.compile(r'firewall', re.IGNORECASE),
        }

        # Cloudflare server patterns
        self.cloudflare_patterns = {
            "cf_server": re.compile(r'cloudflare', re.IGNORECASE),
            "cf_ray": re.compile(r'cf-ray:\s*([a-f0-9-]+)', re.IGNORECASE),
            "cf_cache": re.compile(r'cf-cache-status', re.IGNORECASE),
        }

    def detect_challenge(self, content: str, headers: Dict[str, str] = None,
                        status_code: int = 200, url: str = "") -> ChallengeInfo:
        """Detect and classify Cloudflare challenge from response."""
        headers = headers or {}

        # First check if this is even a Cloudflare response
        if not self._is_cloudflare_response(content, headers):
            return ChallengeInfo(ChallengeType.NONE, 0.0, status_code=status_code)

        # Check for different challenge types in order of specificity
        challenge_checks = [
            self._detect_javascript_challenge,
            self._detect_turnstile_challenge,
            self._detect_managed_challenge,
            self._detect_rate_limiting,
            self._detect_bot_fight,
            self._detect_blocked_response,
        ]

        for check_func in challenge_checks:
            challenge_info = check_func(content, headers, status_code, url)
            if challenge_info.challenge_type != ChallengeType.NONE:
                return challenge_info

        # If Cloudflare response but no specific challenge detected
        if self._is_cloudflare_response(content, headers):
            return ChallengeInfo(ChallengeType.UNKNOWN, 0.3, status_code=status_code)

        return ChallengeInfo(ChallengeType.NONE, 0.0, status_code=status_code)

    def detect(self, content: str, headers: Dict[str, str] = None,
              status_code: int = 200, url: str = "") -> ChallengeInfo:
        """Alias for detect_challenge method (contract API compatibility)."""
        return self.detect_challenge(content, headers, status_code, url)

    def _is_cloudflare_response(self, content: str, headers: Dict[str, str]) -> bool:
        """Check if response is from Cloudflare."""
        # Check headers for Cloudflare indicators
        cf_headers = {
            "cf-ray", "cf-cache-status", "cf-edge-cache", "cf-request-id",
            "server", "cf-bgj", "cf-polished", "cf-apo-via"
        }

        for header_name in cf_headers:
            if header_name in headers or header_name.lower() in headers:
                if header_name == "server":
                    server_value = headers.get("server", headers.get("Server", ""))
                    if "cloudflare" in server_value.lower():
                        return True
                else:
                    return True

        # Check content for Cloudflare patterns
        if self.cloudflare_patterns["cf_server"].search(content):
            return True

        if self.cloudflare_patterns["cf_ray"].search(content):
            return True

        # Check for common Cloudflare challenge page elements
        cf_content_indicators = [
            "challenges.cloudflare.com",
            "__CF$cv$params",
            "window._cf_chl",
            "cf-wrapper",
            "cf-error-details"
        ]

        content_lower = content.lower()
        for indicator in cf_content_indicators:
            if indicator.lower() in content_lower:
                return True

        return False

    def _detect_javascript_challenge(self, content: str, headers: Dict[str, str],
                                    status_code: int, url: str) -> ChallengeInfo:
        """Detect JavaScript-based challenge."""
        confidence = 0.0
        js_code = None
        form_data = {}
        submit_url = None

        # Check for challenge form
        if self.js_challenge_patterns["challenge_form"].search(content):
            confidence += 0.4

        # Check for CF challenge variables
        if self.js_challenge_patterns["cf_challenge"].search(content):
            confidence += 0.3

        # Check for jschl_vc (challenge verification code)
        jschl_vc_match = self.js_challenge_patterns["jschl_vc"].search(content)
        if jschl_vc_match:
            confidence += 0.2
            form_data["jschl_vc"] = jschl_vc_match.group(1)

        # Check for jschl_answer field
        if self.js_challenge_patterns["jschl_answer"].search(content):
            confidence += 0.1

        if confidence >= 0.5:
            # Extract JavaScript code if present
            js_match = re.search(r'<script[^>]*>(.*?setTimeout\(.*?\).*?)</script>',
                               content, re.DOTALL | re.IGNORECASE)
            if js_match:
                js_code = js_match.group(1)

            # Extract form action URL
            form_action_match = re.search(r'<form[^>]*action="([^"]*)"[^>]*id="challenge-form"',
                                        content, re.IGNORECASE)
            if form_action_match:
                submit_url = form_action_match.group(1)
                # Make URL absolute if relative
                if submit_url.startswith("/"):
                    parsed_url = urlparse(url)
                    submit_url = f"{parsed_url.scheme}://{parsed_url.netloc}{submit_url}"

            # Extract additional form fields
            for field in ["pass", "s"]:
                field_match = re.search(rf'name="{field}"\s+value="([^"]*)"', content)
                if field_match:
                    form_data[field] = field_match.group(1)

            ray_id = self._extract_ray_id(content, headers)

            return ChallengeInfo(
                challenge_type=ChallengeType.JAVASCRIPT,
                confidence=min(confidence, 1.0),
                js_code=js_code,
                form_data=form_data,
                submit_url=submit_url,
                ray_id=ray_id,
                response_headers=headers,
                html_content=content,
                status_code=status_code
            )

        return ChallengeInfo(ChallengeType.NONE, 0.0)

    def _detect_turnstile_challenge(self, content: str, headers: Dict[str, str],
                                   status_code: int, url: str) -> ChallengeInfo:
        """Detect Turnstile CAPTCHA challenge."""
        confidence = 0.0
        site_key = None
        turnstile_action = None
        turnstile_cdata = None

        # Check for Turnstile widget
        if self.turnstile_patterns["turnstile_widget"].search(content):
            confidence += 0.4

        # Check for Turnstile script
        if self.turnstile_patterns["turnstile_script"].search(content):
            confidence += 0.3

        # Extract site key
        site_key_match = self.turnstile_patterns["site_key"].search(content)
        if site_key_match:
            confidence += 0.2
            site_key = site_key_match.group(1)

        # Extract action
        action_match = self.turnstile_patterns["turnstile_action"].search(content)
        if action_match:
            confidence += 0.1
            turnstile_action = action_match.group(1)

        # Extract cdata if present
        cdata_match = re.search(r'data-cdata=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if cdata_match:
            turnstile_cdata = cdata_match.group(1)

        if confidence >= 0.5:
            ray_id = self._extract_ray_id(content, headers)

            return ChallengeInfo(
                challenge_type=ChallengeType.TURNSTILE,
                confidence=min(confidence, 1.0),
                site_key=site_key,
                turnstile_action=turnstile_action,
                turnstile_cdata=turnstile_cdata,
                ray_id=ray_id,
                response_headers=headers,
                html_content=content,
                status_code=status_code
            )

        return ChallengeInfo(ChallengeType.NONE, 0.0)

    def _detect_managed_challenge(self, content: str, headers: Dict[str, str],
                                 status_code: int, url: str) -> ChallengeInfo:
        """Detect managed challenge (human verification)."""
        confidence = 0.0

        # Check for managed challenge indicators
        for pattern in self.managed_patterns.values():
            if pattern.search(content):
                confidence += 0.25

        if confidence >= 0.5:
            ray_id = self._extract_ray_id(content, headers)

            return ChallengeInfo(
                challenge_type=ChallengeType.MANAGED,
                confidence=min(confidence, 1.0),
                ray_id=ray_id,
                response_headers=headers,
                html_content=content,
                status_code=status_code
            )

        return ChallengeInfo(ChallengeType.NONE, 0.0)

    def _detect_rate_limiting(self, content: str, headers: Dict[str, str],
                             status_code: int, url: str) -> ChallengeInfo:
        """Detect rate limiting response."""
        confidence = 0.0

        # Status code check
        if status_code == 429:
            confidence += 0.5

        # Check headers
        if "retry-after" in headers or "Retry-After" in headers:
            confidence += 0.3

        # Check content patterns
        for pattern in self.rate_limit_patterns.values():
            if pattern.search(content):
                confidence += 0.2

        if confidence >= 0.5:
            ray_id = self._extract_ray_id(content, headers)

            return ChallengeInfo(
                challenge_type=ChallengeType.RATE_LIMITED,
                confidence=min(confidence, 1.0),
                ray_id=ray_id,
                response_headers=headers,
                html_content=content,
                status_code=status_code
            )

        return ChallengeInfo(ChallengeType.NONE, 0.0)

    def _detect_bot_fight(self, content: str, headers: Dict[str, str],
                         status_code: int, url: str) -> ChallengeInfo:
        """Detect Bot Fight Mode response."""
        confidence = 0.0

        # Check for bot fight patterns
        for pattern in self.bot_fight_patterns.values():
            if pattern.search(content):
                confidence += 0.3

        if confidence >= 0.5:
            ray_id = self._extract_ray_id(content, headers)

            return ChallengeInfo(
                challenge_type=ChallengeType.BOT_FIGHT,
                confidence=min(confidence, 1.0),
                ray_id=ray_id,
                response_headers=headers,
                html_content=content,
                status_code=status_code
            )

        return ChallengeInfo(ChallengeType.NONE, 0.0)

    def _detect_blocked_response(self, content: str, headers: Dict[str, str],
                                status_code: int, url: str) -> ChallengeInfo:
        """Detect blocked/denied access response."""
        confidence = 0.0

        # Status code checks
        if status_code in [403, 406, 410, 429, 503]:
            confidence += 0.3

        # Check content patterns
        for pattern in self.blocked_patterns.values():
            if pattern.search(content):
                confidence += 0.2

        if confidence >= 0.5:
            ray_id = self._extract_ray_id(content, headers)

            # Determine if it's firewall or general block
            challenge_type = ChallengeType.FIREWALL if self.blocked_patterns["firewall"].search(content) else ChallengeType.BLOCKED

            return ChallengeInfo(
                challenge_type=challenge_type,
                confidence=min(confidence, 1.0),
                ray_id=ray_id,
                response_headers=headers,
                html_content=content,
                status_code=status_code
            )

        return ChallengeInfo(ChallengeType.NONE, 0.0)

    def _extract_ray_id(self, content: str, headers: Dict[str, str]) -> Optional[str]:
        """Extract Cloudflare Ray ID from content or headers."""
        # Check headers first
        for header_name in ["cf-ray", "CF-RAY"]:
            if header_name in headers:
                return headers[header_name]

        # Check content
        ray_match = self.managed_patterns["ray_id"].search(content)
        if ray_match:
            return ray_match.group(1)

        # Check for CF-RAY in content
        cf_ray_match = self.cloudflare_patterns["cf_ray"].search(content)
        if cf_ray_match:
            return cf_ray_match.group(1)

        return None

    def is_challenge_response(self, content: str, headers: Dict[str, str] = None,
                             status_code: int = 200) -> bool:
        """Quick check if response contains a challenge."""
        challenge_info = self.detect_challenge(content, headers, status_code)
        return challenge_info.challenge_type != ChallengeType.NONE

    def get_challenge_severity(self, challenge_type: ChallengeType) -> int:
        """Get challenge severity level (0-5, higher is more difficult)."""
        severity_map = {
            ChallengeType.NONE: 0,
            ChallengeType.JAVASCRIPT: 2,
            ChallengeType.MANAGED: 3,
            ChallengeType.TURNSTILE: 4,
            ChallengeType.BOT_FIGHT: 4,
            ChallengeType.RATE_LIMITED: 1,
            ChallengeType.BLOCKED: 5,
            ChallengeType.FIREWALL: 5,
            ChallengeType.UNKNOWN: 2,
        }
        return severity_map.get(challenge_type, 2)


# Utility functions
def create_challenge_detector() -> CloudflareDetector:
    """Create a new challenge detector instance."""
    return CloudflareDetector()


def detect_challenge_quick(content: str, headers: Dict[str, str] = None) -> ChallengeType:
    """Quick challenge detection returning only the type."""
    detector = CloudflareDetector()
    challenge_info = detector.detect_challenge(content, headers)
    return challenge_info.challenge_type


def is_challenge_solvable(challenge_type: ChallengeType) -> bool:
    """Check if a challenge type can be automatically solved."""
    solvable_types = {
        ChallengeType.JAVASCRIPT,
        ChallengeType.RATE_LIMITED,  # Just wait
    }
    return challenge_type in solvable_types