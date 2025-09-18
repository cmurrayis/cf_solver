"""Turnstile challenge handler for Cloudflare challenges.

Handles Cloudflare's Turnstile challenge system, which is their newer
CAPTCHA replacement that focuses on privacy and user experience.
"""

import re
import time
import json
import base64
import random
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin


@dataclass
class TurnstileChallenge:
    """Represents a Turnstile challenge."""
    site_key: str
    callback_url: str
    action: Optional[str] = None
    cdata: Optional[str] = None
    theme: str = "auto"
    size: str = "normal"
    appearance: str = "always"
    retry: str = "auto"
    language: str = "auto"
    response_field_name: str = "cf-turnstile-response"


@dataclass
class TurnstileSolution:
    """Solution to a Turnstile challenge."""
    response_token: str
    site_key: str
    callback_url: str
    form_data: Dict[str, str] = None

    def __post_init__(self):
        if self.form_data is None:
            self.form_data = {}

    def to_form_data(self) -> Dict[str, str]:
        """Convert solution to form data."""
        data = {
            "cf-turnstile-response": self.response_token,
        }

        # Add any additional form data
        data.update(self.form_data)

        return data


class TurnstileHandler:
    """Handles Cloudflare Turnstile challenges."""

    def __init__(self):
        self._compile_patterns()
        self._setup_context()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for Turnstile detection."""
        self.turnstile_patterns = {
            # Turnstile script and widget detection
            "turnstile_script": re.compile(
                r'<script[^>]*src="[^"]*challenges\.cloudflare\.com/turnstile[^"]*"[^>]*></script>',
                re.IGNORECASE
            ),
            "turnstile_widget": re.compile(
                r'<div[^>]*class="[^"]*cf-turnstile[^"]*"[^>]*>',
                re.IGNORECASE
            ),

            # Site key extraction
            "site_key": re.compile(
                r'data-sitekey="([^"]+)"',
                re.IGNORECASE
            ),
            "site_key_js": re.compile(
                r'sitekey:\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            ),

            # Callback and configuration
            "callback_url": re.compile(
                r'data-callback="([^"]+)"',
                re.IGNORECASE
            ),
            "callback_js": re.compile(
                r'callback:\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            ),

            # Additional Turnstile parameters
            "action": re.compile(
                r'data-action="([^"]+)"',
                re.IGNORECASE
            ),
            "cdata": re.compile(
                r'data-cdata="([^"]+)"',
                re.IGNORECASE
            ),
            "theme": re.compile(
                r'data-theme="([^"]+)"',
                re.IGNORECASE
            ),
            "size": re.compile(
                r'data-size="([^"]+)"',
                re.IGNORECASE
            ),

            # Response field
            "response_field": re.compile(
                r'<input[^>]*name="cf-turnstile-response"[^>]*>',
                re.IGNORECASE
            ),
        }

        # Turnstile API patterns
        self.api_patterns = {
            "api_script": re.compile(
                r'https://challenges\.cloudflare\.com/turnstile/v0/api\.js',
                re.IGNORECASE
            ),
            "render_call": re.compile(
                r'turnstile\.render\s*\(\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            ),
        }

    def _setup_context(self) -> None:
        """Setup Turnstile handling context."""
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    def detect_turnstile(self, html_content: str) -> bool:
        """Detect if page contains Turnstile challenge."""
        html_lower = html_content.lower()

        # Check for Turnstile indicators
        indicators = [
            "cf-turnstile",
            "challenges.cloudflare.com/turnstile",
            "turnstile.render",
            "data-sitekey",
        ]

        for indicator in indicators:
            if indicator in html_lower:
                return True

        # Check with regex patterns
        for pattern in self.turnstile_patterns.values():
            if pattern.search(html_content):
                return True

        return False

    def extract_challenge(self, html_content: str, url: str) -> Optional[TurnstileChallenge]:
        """Extract Turnstile challenge information from HTML."""
        if not self.detect_turnstile(html_content):
            return None

        # Extract site key
        site_key = self._extract_site_key(html_content)
        if not site_key:
            return None

        # Extract callback URL
        callback_url = self._extract_callback_url(html_content, url)

        # Extract optional parameters
        action = self._extract_parameter(html_content, "action")
        cdata = self._extract_parameter(html_content, "cdata")
        theme = self._extract_parameter(html_content, "theme") or "auto"
        size = self._extract_parameter(html_content, "size") or "normal"

        return TurnstileChallenge(
            site_key=site_key,
            callback_url=callback_url,
            action=action,
            cdata=cdata,
            theme=theme,
            size=size,
        )

    def _extract_site_key(self, html_content: str) -> Optional[str]:
        """Extract Turnstile site key."""
        # Try data-sitekey attribute
        match = self.turnstile_patterns["site_key"].search(html_content)
        if match:
            return match.group(1)

        # Try JavaScript sitekey
        match = self.turnstile_patterns["site_key_js"].search(html_content)
        if match:
            return match.group(1)

        return None

    def _extract_callback_url(self, html_content: str, base_url: str) -> str:
        """Extract callback URL."""
        # Try data-callback attribute
        match = self.turnstile_patterns["callback_url"].search(html_content)
        if match:
            callback = match.group(1)
            return urljoin(base_url, callback)

        # Try JavaScript callback
        match = self.turnstile_patterns["callback_js"].search(html_content)
        if match:
            callback = match.group(1)
            return urljoin(base_url, callback)

        # Default to current URL
        return base_url

    def _extract_parameter(self, html_content: str, param_name: str) -> Optional[str]:
        """Extract Turnstile parameter."""
        if param_name in self.turnstile_patterns:
            match = self.turnstile_patterns[param_name].search(html_content)
            if match:
                return match.group(1)
        return None

    def solve_turnstile(self, challenge: TurnstileChallenge, **kwargs) -> TurnstileSolution:
        """Solve Turnstile challenge.

        Note: This is a research implementation. In a real scenario,
        Turnstile challenges should be solved through legitimate user interaction
        or proper API integration with Cloudflare.
        """

        # Simulate solving delay (Turnstile typically takes 1-3 seconds)
        solve_delay = kwargs.get('solve_delay', random.uniform(1.5, 3.0))
        time.sleep(solve_delay)

        # Generate research response token
        # Note: This is for research purposes only
        response_token = self._generate_research_token(challenge)

        return TurnstileSolution(
            response_token=response_token,
            site_key=challenge.site_key,
            callback_url=challenge.callback_url,
            form_data=kwargs.get('form_data', {})
        )

    def solve(self, challenge, **kwargs) -> TurnstileSolution:
        """Alias for solve_turnstile method (contract API compatibility)."""
        if isinstance(challenge, TurnstileChallenge):
            return self.solve_turnstile(challenge, **kwargs)
        elif isinstance(challenge, dict):
            # Convert dict to TurnstileChallenge
            turnstile_challenge = TurnstileChallenge(
                site_key=challenge.get('site_key', ''),
                callback_url=challenge.get('callback_url', ''),
                action=challenge.get('action'),
                cdata=challenge.get('cdata'),
                theme=challenge.get('theme', 'auto'),
                size=challenge.get('size', 'normal'),
            )
            return self.solve_turnstile(turnstile_challenge, **kwargs)
        else:
            raise ValueError("Invalid challenge format for Turnstile solver")

    def _generate_research_token(self, challenge: TurnstileChallenge) -> str:
        """Generate research token for testing purposes.

        Note: This is for research and testing only.
        Real Turnstile tokens are generated by Cloudflare's servers.
        """
        # Create research token structure
        token_data = {
            "iss": "research.cloudflare.com",
            "exp": int(time.time()) + 300,  # 5 minutes
            "iat": int(time.time()),
            "sitekey": challenge.site_key,
            "action": challenge.action or "submit",
            "cdata": challenge.cdata,
            "research": True,
        }

        # Encode as base64 for research purposes
        token_json = json.dumps(token_data, separators=(',', ':'))
        token_bytes = token_json.encode('utf-8')
        research_token = base64.urlsafe_b64encode(token_bytes).decode('utf-8').rstrip('=')

        # Add research prefix
        return f"research.{research_token}"

    def verify_solution(self, solution: TurnstileSolution) -> bool:
        """Verify Turnstile solution format."""
        if not solution.response_token:
            return False

        if not solution.site_key:
            return False

        # Check if it's a research token
        if solution.response_token.startswith("research."):
            return True

        # For real tokens, basic format validation
        if len(solution.response_token) < 20:
            return False

        return True

    def get_verification_params(self, solution: TurnstileSolution) -> Dict[str, str]:
        """Get parameters for server-side verification."""
        return {
            "secret": "RESEARCH_SECRET_KEY",  # This would be your secret key
            "response": solution.response_token,
            "remoteip": "127.0.0.1",  # Optional: user's IP address
        }


# Utility functions
def create_turnstile_handler() -> TurnstileHandler:
    """Create a new Turnstile challenge handler."""
    return TurnstileHandler()


def detect_turnstile_challenge(html_content: str) -> bool:
    """Quick function to detect Turnstile challenge."""
    handler = TurnstileHandler()
    return handler.detect_turnstile(html_content)


def solve_turnstile_challenge(html_content: str, url: str, **kwargs) -> Optional[TurnstileSolution]:
    """Quick function to solve Turnstile challenge."""
    handler = TurnstileHandler()
    challenge = handler.extract_challenge(html_content, url)

    if challenge:
        return handler.solve_turnstile(challenge, **kwargs)

    return None