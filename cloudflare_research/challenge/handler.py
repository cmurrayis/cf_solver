"""Challenge handling orchestrator for Cloudflare challenges.

Coordinates challenge detection, solving, and response handling across
different challenge types with retry logic and error handling.
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin

from .detector import CloudflareDetector, ChallengeType, ChallengeInfo
from .solver import JSChallengeSolver, ChallengeSolution


@dataclass
class ChallengeResult:
    """Result of challenge handling attempt."""
    success: bool
    challenge_type: ChallengeType
    solution: Optional[ChallengeSolution] = None
    error: Optional[str] = None
    attempts: int = 0
    total_time: float = 0.0
    bypass_response: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "challenge_type": self.challenge_type.value,
            "solution": self.solution.to_form_data() if self.solution else None,
            "error": self.error,
            "attempts": self.attempts,
            "total_time": self.total_time,
            "has_response": self.bypass_response is not None,
        }


@dataclass
class ChallengeConfig:
    """Configuration for challenge handling."""
    max_attempts: int = 3
    base_delay: float = 4.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay
    backoff_factor: float = 2.0
    js_execution_timeout: float = 10.0
    solve_javascript: bool = True
    solve_managed: bool = False  # Requires human intervention
    solve_turnstile: bool = False  # Requires CAPTCHA solving
    handle_rate_limits: bool = True
    rate_limit_max_wait: float = 300.0  # 5 minutes
    enable_retries: bool = True
    randomize_delays: bool = True


class ChallengeHandler:
    """Orchestrates Cloudflare challenge detection and solving."""

    def __init__(self, config: ChallengeConfig = None):
        self.config = config or ChallengeConfig()
        self.detector = CloudflareDetector()
        self.js_solver = JSChallengeSolver()

        # Challenge handling stats
        self._stats = {
            "total_challenges": 0,
            "successful_solves": 0,
            "failed_solves": 0,
            "by_type": {challenge_type.value: 0 for challenge_type in ChallengeType},
        }

    async def handle_challenge(self, response_content: str, response_headers: Dict[str, str],
                              status_code: int, request_url: str,
                              http_client: Any) -> ChallengeResult:
        """Handle a Cloudflare challenge response."""

        start_time = time.time()
        self._stats["total_challenges"] += 1

        # Detect challenge type
        challenge_info = self.detector.detect_challenge(
            response_content, response_headers, status_code, request_url
        )

        self._stats["by_type"][challenge_info.challenge_type.value] += 1

        # Handle different challenge types
        if challenge_info.challenge_type == ChallengeType.NONE:
            return ChallengeResult(
                success=True,
                challenge_type=ChallengeType.NONE,
                total_time=time.time() - start_time
            )

        # Try to solve the challenge
        result = await self._solve_challenge(challenge_info, request_url, http_client)
        result.total_time = time.time() - start_time

        if result.success:
            self._stats["successful_solves"] += 1
        else:
            self._stats["failed_solves"] += 1

        return result

    async def _solve_challenge(self, challenge_info: ChallengeInfo,
                              request_url: str, http_client: Any) -> ChallengeResult:
        """Solve a specific challenge type."""

        challenge_type = challenge_info.challenge_type

        # Route to appropriate solver
        if challenge_type == ChallengeType.JAVASCRIPT and self.config.solve_javascript:
            return await self._solve_javascript_challenge(challenge_info, request_url, http_client)

        elif challenge_type == ChallengeType.RATE_LIMITED and self.config.handle_rate_limits:
            return await self._handle_rate_limit(challenge_info, request_url, http_client)

        elif challenge_type == ChallengeType.MANAGED and self.config.solve_managed:
            return await self._handle_managed_challenge(challenge_info, request_url, http_client)

        elif challenge_type == ChallengeType.TURNSTILE and self.config.solve_turnstile:
            return await self._handle_turnstile_challenge(challenge_info, request_url, http_client)

        else:
            return ChallengeResult(
                success=False,
                challenge_type=challenge_type,
                error=f"Challenge type {challenge_type.value} not supported or disabled"
            )

    async def _solve_javascript_challenge(self, challenge_info: ChallengeInfo,
                                        request_url: str, http_client: Any) -> ChallengeResult:
        """Solve JavaScript-based challenge."""

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                # Wait for challenge delay (usually 4-5 seconds)
                challenge_delay = self._calculate_challenge_delay()
                await asyncio.sleep(challenge_delay)

                # Solve the JavaScript challenge
                solution = self.js_solver.solve_challenge(
                    challenge_info.html_content,
                    request_url,
                    int(challenge_delay * 1000)
                )

                # Build submit URL
                if solution.submit_url:
                    submit_url = urljoin(request_url, solution.submit_url)
                else:
                    submit_url = request_url

                # Submit solution
                form_data = solution.to_form_data()
                response = await http_client.post(
                    submit_url,
                    data=form_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": request_url,
                    }
                )

                # Check if solution worked
                if not self._is_challenge_response(response):
                    return ChallengeResult(
                        success=True,
                        challenge_type=ChallengeType.JAVASCRIPT,
                        solution=solution,
                        attempts=attempt,
                        bypass_response=response
                    )

                # If still challenged, wait and retry
                if attempt < self.config.max_attempts:
                    backoff_delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(backoff_delay)

            except Exception as e:
                if attempt == self.config.max_attempts:
                    return ChallengeResult(
                        success=False,
                        challenge_type=ChallengeType.JAVASCRIPT,
                        error=f"JavaScript challenge solving failed: {str(e)}",
                        attempts=attempt
                    )

                # Wait before retry
                backoff_delay = self._calculate_backoff_delay(attempt)
                await asyncio.sleep(backoff_delay)

        return ChallengeResult(
            success=False,
            challenge_type=ChallengeType.JAVASCRIPT,
            error="Maximum attempts exceeded for JavaScript challenge",
            attempts=self.config.max_attempts
        )

    async def _handle_rate_limit(self, challenge_info: ChallengeInfo,
                                request_url: str, http_client: Any) -> ChallengeResult:
        """Handle rate limiting by waiting."""

        # Extract retry-after header if present
        retry_after = None
        if challenge_info.response_headers:
            retry_after = challenge_info.response_headers.get("retry-after") or \
                         challenge_info.response_headers.get("Retry-After")

        # Calculate wait time
        if retry_after:
            try:
                wait_time = float(retry_after)
            except ValueError:
                wait_time = self.config.base_delay
        else:
            # Use exponential backoff
            wait_time = self.config.base_delay

        wait_time = min(wait_time, self.config.rate_limit_max_wait)

        # Add some randomization to avoid thundering herd
        if self.config.randomize_delays:
            jitter = random.uniform(0.5, 1.5)
            wait_time *= jitter

        # Wait
        await asyncio.sleep(wait_time)

        # Retry original request
        try:
            response = await http_client.get(request_url)

            if not self._is_challenge_response(response):
                return ChallengeResult(
                    success=True,
                    challenge_type=ChallengeType.RATE_LIMITED,
                    attempts=1,
                    bypass_response=response
                )
            else:
                return ChallengeResult(
                    success=False,
                    challenge_type=ChallengeType.RATE_LIMITED,
                    error="Still rate limited after waiting",
                    attempts=1
                )

        except Exception as e:
            return ChallengeResult(
                success=False,
                challenge_type=ChallengeType.RATE_LIMITED,
                error=f"Rate limit retry failed: {str(e)}",
                attempts=1
            )

    async def _handle_managed_challenge(self, challenge_info: ChallengeInfo,
                                       request_url: str, http_client: Any) -> ChallengeResult:
        """Handle managed challenge (usually requires human intervention)."""

        # Managed challenges typically require user interaction
        # For now, we'll wait and retry once in case it's temporary
        wait_time = self.config.base_delay * 2
        await asyncio.sleep(wait_time)

        try:
            response = await http_client.get(request_url)

            if not self._is_challenge_response(response):
                return ChallengeResult(
                    success=True,
                    challenge_type=ChallengeType.MANAGED,
                    attempts=1,
                    bypass_response=response
                )
            else:
                return ChallengeResult(
                    success=False,
                    challenge_type=ChallengeType.MANAGED,
                    error="Managed challenge requires human intervention",
                    attempts=1
                )

        except Exception as e:
            return ChallengeResult(
                success=False,
                challenge_type=ChallengeType.MANAGED,
                error=f"Managed challenge retry failed: {str(e)}",
                attempts=1
            )

    async def _handle_turnstile_challenge(self, challenge_info: ChallengeInfo,
                                         request_url: str, http_client: Any) -> ChallengeResult:
        """Handle Turnstile CAPTCHA challenge."""

        # Turnstile requires CAPTCHA solving service or user interaction
        # This is a placeholder - real implementation would integrate with
        # CAPTCHA solving services or provide callback for user interaction

        return ChallengeResult(
            success=False,
            challenge_type=ChallengeType.TURNSTILE,
            error="Turnstile CAPTCHA solving not implemented",
            attempts=0
        )

    def _is_challenge_response(self, response: Any) -> bool:
        """Check if response is still a challenge."""
        try:
            content = getattr(response, 'text', '') or getattr(response, 'content', '')
            headers = getattr(response, 'headers', {})
            status_code = getattr(response, 'status_code', 200)

            return self.detector.is_challenge_response(content, headers, status_code)
        except Exception:
            return False

    def _calculate_challenge_delay(self) -> float:
        """Calculate delay before solving challenge."""
        delay = self.config.base_delay

        if self.config.randomize_delays:
            # Add some randomization (±20%)
            jitter = random.uniform(0.8, 1.2)
            delay *= jitter

        return delay

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay for retries."""
        delay = self.config.base_delay * (self.config.backoff_factor ** (attempt - 1))
        delay = min(delay, self.config.max_delay)

        if self.config.randomize_delays:
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0.5, 1.5)
            delay *= jitter

        return delay

    def get_stats(self) -> Dict[str, Any]:
        """Get challenge handling statistics."""
        stats = self._stats.copy()

        # Add derived stats
        total = self._stats["total_challenges"]
        if total > 0:
            stats["success_rate"] = self._stats["successful_solves"] / total
            stats["failure_rate"] = self._stats["failed_solves"] / total
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """Reset challenge handling statistics."""
        self._stats = {
            "total_challenges": 0,
            "successful_solves": 0,
            "failed_solves": 0,
            "by_type": {challenge_type.value: 0 for challenge_type in ChallengeType},
        }

    async def test_challenge_solving(self, test_url: str, http_client: Any) -> Dict[str, Any]:
        """Test challenge solving capabilities."""
        test_results = {
            "test_url": test_url,
            "challenges_encountered": [],
            "total_attempts": 0,
            "successful_solves": 0,
            "errors": [],
        }

        try:
            # Make initial request
            response = await http_client.get(test_url)
            content = getattr(response, 'text', '') or getattr(response, 'content', '')
            headers = getattr(response, 'headers', {})
            status_code = getattr(response, 'status_code', 200)

            # Check for challenges
            challenge_info = self.detector.detect_challenge(content, headers, status_code, test_url)

            if challenge_info.challenge_type != ChallengeType.NONE:
                test_results["challenges_encountered"].append(challenge_info.challenge_type.value)
                test_results["total_attempts"] += 1

                # Attempt to solve
                result = await self.handle_challenge(
                    content, headers, status_code, test_url, http_client
                )

                if result.success:
                    test_results["successful_solves"] += 1
                else:
                    test_results["errors"].append(result.error)

        except Exception as e:
            test_results["errors"].append(str(e))

        return test_results


# Utility functions
def create_challenge_handler(config: ChallengeConfig = None) -> ChallengeHandler:
    """Create a new challenge handler instance."""
    return ChallengeHandler(config)


def create_default_config() -> ChallengeConfig:
    """Create default challenge handling configuration."""
    return ChallengeConfig()


def create_aggressive_config() -> ChallengeConfig:
    """Create aggressive challenge handling configuration."""
    return ChallengeConfig(
        max_attempts=5,
        base_delay=6.0,
        max_delay=60.0,
        backoff_factor=2.5,
        solve_javascript=True,
        handle_rate_limits=True,
        rate_limit_max_wait=600.0,  # 10 minutes
    )


def create_conservative_config() -> ChallengeConfig:
    """Create conservative challenge handling configuration."""
    return ChallengeConfig(
        max_attempts=2,
        base_delay=3.0,
        max_delay=15.0,
        backoff_factor=1.5,
        solve_javascript=True,
        handle_rate_limits=True,
        rate_limit_max_wait=120.0,  # 2 minutes
    )