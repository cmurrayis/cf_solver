#!/usr/bin/env python3
"""
Detailed Cloudflare Bypass Analysis Tool

Provides comprehensive analysis of bypass attempts including:
- Individual request outcomes
- Cloudflare detection mechanisms triggered
- Challenge types encountered
- Solving methods used
- Success optimization strategies
"""

import asyncio
import json
import time
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import aiohttp
from dataclasses import dataclass

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.challenge import ChallengeType


@dataclass
class RequestAnalysis:
    """Detailed analysis of a single request."""
    request_id: int
    url: str
    status_code: int
    success: bool
    response_time: float
    content_length: int

    # Cloudflare detection
    is_cloudflare: bool
    cf_ray: Optional[str]
    cf_cookies: Dict[str, str]

    # Challenge analysis
    challenge_detected: bool
    challenge_type: Optional[str]
    challenge_solved: bool
    solving_method: Optional[str]
    solve_time: Optional[float]

    # Response analysis
    response_headers: Dict[str, str]
    response_snippet: str
    error_type: Optional[str]

    # Bypass analysis
    bypass_success: bool
    bypass_method: str
    recommendation: str


class DetailedBypassAnalyzer:
    """Comprehensive Cloudflare bypass analyzer."""

    def __init__(self, target_url: str):
        self.target_url = target_url
        self.analyses: List[RequestAnalysis] = []

    def log(self, message: str) -> None:
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def detect_cloudflare_protection(self, headers: Dict[str, str], body: str) -> Tuple[bool, str, Dict[str, str]]:
        """Detect Cloudflare protection mechanisms."""
        cf_indicators = {
            'server': headers.get('server', '').lower(),
            'cf_ray': headers.get('cf-ray', ''),
            'cf_cache_status': headers.get('cf-cache-status', ''),
        }

        is_cloudflare = (
            'cloudflare' in cf_indicators['server'] or
            cf_indicators['cf_ray'] or
            cf_indicators['cf_cache_status']
        )

        # Extract Cloudflare cookies
        cf_cookies = {}
        set_cookie = headers.get('set-cookie', '')
        if set_cookie:
            for cookie_part in set_cookie.split(';'):
                if '=' in cookie_part:
                    key, value = cookie_part.split('=', 1)
                    key = key.strip()
                    if key.startswith('__cf') or key.startswith('cf_'):
                        cf_cookies[key] = value.strip()

        return is_cloudflare, cf_indicators['cf_ray'], cf_cookies

    def analyze_challenge_response(self, status_code: int, headers: Dict[str, str], body: str) -> Tuple[bool, Optional[str]]:
        """Analyze if response contains a challenge and what type."""
        challenge_indicators = {
            # JavaScript challenge
            'js_challenge': any([
                'window._cf_chl_opt' in body,
                'challenge-platform' in body.lower(),
                'jschl-answer' in body.lower(),
                'cf-challenge' in body.lower()
            ]),

            # Managed challenge (human verification)
            'managed_challenge': any([
                'checking your browser' in body.lower(),
                'please wait while we check' in body.lower(),
                'verify you are human' in body.lower(),
                'ray id' in body.lower() and status_code == 403
            ]),

            # Turnstile CAPTCHA
            'turnstile': any([
                'cf-turnstile' in body.lower(),
                'turnstile' in body.lower(),
                'data-sitekey' in body.lower()
            ]),

            # Rate limiting
            'rate_limit': any([
                status_code == 429,
                'rate limit' in body.lower(),
                'too many requests' in body.lower()
            ]),

            # Bot fight mode
            'bot_fight': any([
                'bot fight mode' in body.lower(),
                'suspicious activity' in body.lower(),
                status_code == 403 and 'cloudflare' in headers.get('server', '').lower()
            ])
        }

        for challenge_type, detected in challenge_indicators.items():
            if detected:
                return True, challenge_type

        return False, None

    def determine_bypass_method(self, status_code: int, challenge_type: Optional[str], cf_cookies: Dict[str, str]) -> Tuple[str, str]:
        """Determine what bypass method was used and recommendations."""
        if status_code == 200:
            if cf_cookies:
                return "cookie_bypass", "[SUCCESS] Successfully obtained Cloudflare cookies"
            else:
                return "direct_access", "[WARNING] Success but no CF cookies (may not be protected)"

        elif status_code == 403:
            if challenge_type:
                return "challenge_detected", f"[CHALLENGE] Challenge detected: {challenge_type}"
            else:
                return "blocked", "[BLOCKED] Blocked by Cloudflare (no challenge offered)"

        elif status_code == 429:
            return "rate_limited", "[RATE_LIMIT] Rate limited - need to slow down requests"

        elif status_code == 503:
            return "service_unavailable", "[UNAVAILABLE] Service temporarily unavailable"

        else:
            return "unknown_error", f"[UNKNOWN] Unexpected status: {status_code}"

    async def analyze_request(self, bypass: CloudflareBypass, request_id: int) -> RequestAnalysis:
        """Perform detailed analysis of a single request."""
        start_time = time.time()

        try:
            # Make request through CloudflareBypass
            result = await bypass.get(self.target_url)

            response_time = time.time() - start_time
            status_code = result.status_code if hasattr(result, 'status_code') else 0
            content = result.content if hasattr(result, 'content') else ""
            headers = dict(result.headers) if hasattr(result, 'headers') else {}

            # Analyze Cloudflare protection
            is_cloudflare, cf_ray, cf_cookies = self.detect_cloudflare_protection(headers, content)

            # Analyze challenges
            challenge_detected, challenge_type = self.analyze_challenge_response(status_code, headers, content)

            # Determine bypass method and success
            bypass_method, recommendation = self.determine_bypass_method(status_code, challenge_type, cf_cookies)

            # Extract challenge solving info from result
            challenge_solved = getattr(result, 'challenge_solved', False)
            solving_method = None
            solve_time = None

            if hasattr(result, 'challenge_info'):
                solving_method = getattr(result.challenge_info, 'solving_method', None)
                solve_time = getattr(result.challenge_info, 'solve_time', None)

            analysis = RequestAnalysis(
                request_id=request_id,
                url=self.target_url,
                status_code=status_code,
                success=status_code == 200,
                response_time=response_time,
                content_length=len(content),

                is_cloudflare=is_cloudflare,
                cf_ray=cf_ray,
                cf_cookies=cf_cookies,

                challenge_detected=challenge_detected,
                challenge_type=challenge_type,
                challenge_solved=challenge_solved,
                solving_method=solving_method,
                solve_time=solve_time,

                response_headers=headers,
                response_snippet=content[:200] + "..." if len(content) > 200 else content,
                error_type=None,

                bypass_success=status_code == 200,
                bypass_method=bypass_method,
                recommendation=recommendation
            )

        except Exception as e:
            response_time = time.time() - start_time

            analysis = RequestAnalysis(
                request_id=request_id,
                url=self.target_url,
                status_code=0,
                success=False,
                response_time=response_time,
                content_length=0,

                is_cloudflare=False,
                cf_ray=None,
                cf_cookies={},

                challenge_detected=False,
                challenge_type=None,
                challenge_solved=False,
                solving_method=None,
                solve_time=None,

                response_headers={},
                response_snippet="",
                error_type=type(e).__name__,

                bypass_success=False,
                bypass_method="error",
                recommendation=f"❌ Error: {str(e)}"
            )

        return analysis

    async def run_detailed_analysis(self, concurrent_requests: int = 10) -> Dict[str, Any]:
        """Run detailed bypass analysis with specified concurrency."""
        self.log(f"Starting detailed Cloudflare bypass analysis")
        self.log(f"Target: {self.target_url}")
        self.log(f"Concurrent requests: {concurrent_requests}")
        self.log("=" * 80)

        # Configure CloudflareBypass for optimal success
        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrent_requests,
            requests_per_second=2.0,  # Conservative rate to avoid rate limiting
            browser_version="120.0.0.0",
            solve_javascript_challenges=True,
            solve_turnstile_challenges=True,
            solve_managed_challenges=False,  # Usually requires human interaction
            challenge_timeout=30.0,
            timeout=30.0,
            enable_tls_fingerprinting=True,
            ja3_randomization=True,
            enable_monitoring=True
        )

        analyses = []

        try:
            async with CloudflareBypass(config) as bypass:
                # Execute requests with detailed tracking
                for i in range(concurrent_requests):
                    self.log(f"Executing request {i+1}/{concurrent_requests}")

                    analysis = await self.analyze_request(bypass, i+1)
                    analyses.append(analysis)

                    # Print immediate results
                    self.print_request_summary(analysis)

                    # Small delay between requests to avoid aggressive rate limiting
                    await asyncio.sleep(0.5)

        except Exception as e:
            self.log(f"Analysis failed: {e}")
            return {"error": str(e)}

        # Generate comprehensive report
        report = self.generate_comprehensive_report(analyses)

        return report

    def print_request_summary(self, analysis: RequestAnalysis) -> None:
        """Print immediate summary of request analysis."""
        status_emoji = "[OK]" if analysis.success else "[FAIL]"
        cf_emoji = "[CF]" if analysis.is_cloudflare else "[DIRECT]"

        self.log(f"  {status_emoji} Request {analysis.request_id}: {analysis.status_code} "
                f"({analysis.response_time:.2f}s) {cf_emoji}")

        if analysis.cf_cookies:
            self.log(f"    [COOKIES] CF Cookies: {list(analysis.cf_cookies.keys())}")

        if analysis.challenge_detected:
            solve_emoji = "[SOLVED]" if analysis.challenge_solved else "[DETECTED]"
            self.log(f"    {solve_emoji} Challenge: {analysis.challenge_type}")

        if analysis.cf_ray:
            self.log(f"    [RAY] CF-RAY: {analysis.cf_ray}")

    def generate_comprehensive_report(self, analyses: List[RequestAnalysis]) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        total_requests = len(analyses)
        successful_requests = sum(1 for a in analyses if a.success)

        # Calculate statistics
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0

        # Cloudflare analysis
        cloudflare_requests = [a for a in analyses if a.is_cloudflare]
        cf_success_rate = (sum(1 for a in cloudflare_requests if a.success) / len(cloudflare_requests)) * 100 if cloudflare_requests else 0

        # Challenge analysis
        challenges_detected = [a for a in analyses if a.challenge_detected]
        challenges_solved = [a for a in challenges_detected if a.challenge_solved]

        # Response time analysis
        response_times = [a.response_time for a in analyses]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        # Status code breakdown
        status_breakdown = {}
        for analysis in analyses:
            status = analysis.status_code
            if status not in status_breakdown:
                status_breakdown[status] = {"count": 0, "examples": []}
            status_breakdown[status]["count"] += 1
            if len(status_breakdown[status]["examples"]) < 3:
                status_breakdown[status]["examples"].append({
                    "request_id": analysis.request_id,
                    "recommendation": analysis.recommendation
                })

        # Bypass method analysis
        bypass_methods = {}
        for analysis in analyses:
            method = analysis.bypass_method
            if method not in bypass_methods:
                bypass_methods[method] = 0
            bypass_methods[method] += 1

        # Cookie analysis
        cf_cookie_types = {}
        for analysis in analyses:
            for cookie_name in analysis.cf_cookies:
                if cookie_name not in cf_cookie_types:
                    cf_cookie_types[cookie_name] = 0
                cf_cookie_types[cookie_name] += 1

        # Generate improvement recommendations
        recommendations = self.generate_improvement_recommendations(analyses)

        report = {
            "test_summary": {
                "target_url": self.target_url,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time
            },
            "cloudflare_analysis": {
                "cloudflare_detected": len(cloudflare_requests),
                "cloudflare_success_rate": cf_success_rate,
                "cf_ray_ids": [a.cf_ray for a in cloudflare_requests if a.cf_ray],
                "cf_cookie_types": cf_cookie_types
            },
            "challenge_analysis": {
                "challenges_detected": len(challenges_detected),
                "challenges_solved": len(challenges_solved),
                "challenge_types": [a.challenge_type for a in challenges_detected],
                "solve_success_rate": (len(challenges_solved) / len(challenges_detected)) * 100 if challenges_detected else 0
            },
            "status_breakdown": status_breakdown,
            "bypass_methods": bypass_methods,
            "detailed_analyses": [
                {
                    "request_id": a.request_id,
                    "status_code": a.status_code,
                    "success": a.success,
                    "response_time": a.response_time,
                    "is_cloudflare": a.is_cloudflare,
                    "cf_ray": a.cf_ray,
                    "cf_cookies": list(a.cf_cookies.keys()),
                    "challenge_detected": a.challenge_detected,
                    "challenge_type": a.challenge_type,
                    "challenge_solved": a.challenge_solved,
                    "bypass_method": a.bypass_method,
                    "recommendation": a.recommendation
                }
                for a in analyses
            ],
            "improvement_recommendations": recommendations,
            "optimization_strategies": self.generate_optimization_strategies(analyses)
        }

        return report

    def generate_improvement_recommendations(self, analyses: List[RequestAnalysis]) -> List[str]:
        """Generate specific recommendations to improve success rate."""
        recommendations = []

        # Analyze failure patterns
        failed_requests = [a for a in analyses if not a.success]

        if not failed_requests:
            recommendations.append("[SUCCESS] Perfect success rate achieved!")
            return recommendations

        # Rate limiting detection
        rate_limited = [a for a in failed_requests if a.status_code == 429]
        if rate_limited:
            recommendations.append(f"[RATE_LIMIT] {len(rate_limited)} requests rate limited - reduce request rate")

        # 403 blocks
        blocked_403 = [a for a in failed_requests if a.status_code == 403]
        if blocked_403:
            challenges_in_403 = [a for a in blocked_403 if a.challenge_detected]
            no_challenge_403 = [a for a in blocked_403 if not a.challenge_detected]

            if challenges_in_403:
                recommendations.append(f"[CHALLENGE] {len(challenges_in_403)} requests blocked with challenges - improve challenge solving")

            if no_challenge_403:
                recommendations.append(f"[BLOCKED] {len(no_challenge_403)} requests blocked without challenges - improve fingerprinting")

        # Connection errors
        connection_errors = [a for a in failed_requests if a.status_code == 0]
        if connection_errors:
            recommendations.append(f"[CONNECTION] {len(connection_errors)} connection errors - check network/proxy settings")

        # Cookie analysis
        successful_with_cookies = [a for a in analyses if a.success and a.cf_cookies]
        successful_without_cookies = [a for a in analyses if a.success and not a.cf_cookies]

        if successful_with_cookies and successful_without_cookies:
            recommendations.append("[COOKIES] Mixed cookie presence - ensure consistent session management")

        return recommendations

    def generate_optimization_strategies(self, analyses: List[RequestAnalysis]) -> List[str]:
        """Generate specific strategies to achieve 100% success rate."""
        strategies = []

        successful_requests = [a for a in analyses if a.success]
        failed_requests = [a for a in analyses if not a.success]

        if not failed_requests:
            strategies.append("[OPTIMAL] Already at optimal performance!")
            return strategies

        # Analyze successful patterns
        if successful_requests:
            successful_methods = set(a.bypass_method for a in successful_requests)
            strategies.append(f"[SUCCESS_METHODS] Successful bypass methods: {', '.join(successful_methods)}")

            successful_with_cf = [a for a in successful_requests if a.is_cloudflare]
            if successful_with_cf:
                strategies.append(f"[CF_BYPASS] Successfully bypassed Cloudflare in {len(successful_with_cf)} cases")

        # Rate limiting mitigation
        if any(a.status_code == 429 for a in failed_requests):
            strategies.append("[RATE_LIMIT] Implement adaptive rate limiting (start at 0.5 req/s)")
            strategies.append("[BACKOFF] Add exponential backoff for rate limited requests")

        # Challenge solving improvements
        challenges_unsolved = [a for a in failed_requests if a.challenge_detected and not a.challenge_solved]
        if challenges_unsolved:
            strategies.append("[SOLVER] Improve challenge solving algorithms")
            strategies.append("[TIMEOUT] Implement challenge-specific timeout strategies")

        # Browser fingerprinting improvements
        blocks_without_challenge = [a for a in failed_requests if a.status_code == 403 and not a.challenge_detected]
        if blocks_without_challenge:
            strategies.append("[FINGERPRINT] Enhance browser fingerprinting (TLS, headers, behavior)")
            strategies.append("[TIMING] Implement request timing randomization")

        # Session persistence
        if any(a.cf_cookies for a in analyses):
            strategies.append("[SESSION] Implement session persistence across requests")
            strategies.append("[COOKIES] Reuse successful Cloudflare cookies")

        return strategies

    def print_final_report(self, report: Dict[str, Any]) -> None:
        """Print comprehensive final report."""
        summary = report["test_summary"]
        cf_analysis = report["cloudflare_analysis"]
        challenge_analysis = report["challenge_analysis"]

        self.log("\n" + "=" * 80)
        self.log("DETAILED CLOUDFLARE BYPASS ANALYSIS REPORT")
        self.log("=" * 80)

        # Test Summary
        self.log(f"\n[SUMMARY] TEST SUMMARY:")
        self.log(f"  Target URL: {summary['target_url']}")
        self.log(f"  Total Requests: {summary['total_requests']}")
        self.log(f"  Successful: {summary['successful_requests']}")
        self.log(f"  Success Rate: {summary['success_rate']:.1f}%")
        self.log(f"  Avg Response Time: {summary['avg_response_time']:.2f}s")

        # Cloudflare Analysis
        self.log(f"\n[CLOUDFLARE] CLOUDFLARE ANALYSIS:")
        self.log(f"  Cloudflare Detected: {cf_analysis['cloudflare_detected']} requests")
        self.log(f"  CF Success Rate: {cf_analysis['cloudflare_success_rate']:.1f}%")
        if cf_analysis['cf_cookie_types']:
            self.log(f"  CF Cookies Obtained: {list(cf_analysis['cf_cookie_types'].keys())}")
        if cf_analysis['cf_ray_ids']:
            self.log(f"  CF-RAY IDs: {len(cf_analysis['cf_ray_ids'])} unique")

        # Challenge Analysis
        self.log(f"\n[CHALLENGE] CHALLENGE ANALYSIS:")
        self.log(f"  Challenges Detected: {challenge_analysis['challenges_detected']}")
        self.log(f"  Challenges Solved: {challenge_analysis['challenges_solved']}")
        if challenge_analysis['challenges_detected'] > 0:
            self.log(f"  Solve Success Rate: {challenge_analysis['solve_success_rate']:.1f}%")
        if challenge_analysis['challenge_types']:
            unique_types = list(set(t for t in challenge_analysis['challenge_types'] if t))
            self.log(f"  Challenge Types: {unique_types}")

        # Status Breakdown
        self.log(f"\n[STATUS] STATUS CODE BREAKDOWN:")
        for status, info in report['status_breakdown'].items():
            self.log(f"  {status}: {info['count']} requests")
            for example in info['examples'][:2]:
                self.log(f"    - Request {example['request_id']}: {example['recommendation']}")

        # Recommendations
        self.log(f"\n[RECOMMENDATIONS] IMPROVEMENT RECOMMENDATIONS:")
        for rec in report['improvement_recommendations']:
            self.log(f"  {rec}")

        # Optimization Strategies
        self.log(f"\n[OPTIMIZATION] OPTIMIZATION STRATEGIES:")
        for strategy in report['optimization_strategies']:
            self.log(f"  {strategy}")

        # Success Achievement Guide
        current_success = summary['success_rate']
        if current_success < 95:
            self.log(f"\n[TARGET] TO ACHIEVE 100% SUCCESS:")
            self.log(f"  1. Implement adaptive rate limiting (current failures suggest rate limiting)")
            self.log(f"  2. Enhance browser fingerprinting for 403 blocks")
            self.log(f"  3. Improve challenge detection and solving algorithms")
            self.log(f"  4. Implement session persistence with CF cookies")
            self.log(f"  5. Add retry logic with exponential backoff")
        elif current_success < 100:
            self.log(f"\n[FINAL] FINAL OPTIMIZATIONS FOR 100%:")
            self.log(f"  - Fine-tune request timing and rate limiting")
            self.log(f"  - Implement cookie session reuse")
            self.log(f"  - Add intelligent retry for temporary failures")
        else:
            self.log(f"\n[PERFECT] PERFECT SUCCESS RATE ACHIEVED!")


async def main():
    """Main entry point for detailed bypass analysis."""
    target_url = "https://kick.com/api/v1/channels/adinross"
    concurrent_requests = 10

    analyzer = DetailedBypassAnalyzer(target_url)

    try:
        report = await analyzer.run_detailed_analysis(concurrent_requests)

        if "error" in report:
            analyzer.log(f"Analysis failed: {report['error']}")
            sys.exit(1)

        # Print comprehensive report
        analyzer.print_final_report(report)

        # Save detailed report
        output_file = "detailed_bypass_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        analyzer.log(f"\nDetailed analysis saved to: {output_file}")

        # Exit with success rate indicator
        success_rate = report['test_summary']['success_rate']
        if success_rate >= 95:
            analyzer.log(f"\n[EXCELLENT] {success_rate:.1f}% success rate achieved!")
            sys.exit(0)
        elif success_rate >= 80:
            analyzer.log(f"\n[GOOD] {success_rate:.1f}% success rate - optimization needed")
            sys.exit(0)
        else:
            analyzer.log(f"\n[NEEDS_WORK] {success_rate:.1f}% success rate - significant optimization required")
            sys.exit(1)

    except KeyboardInterrupt:
        analyzer.log("\nAnalysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        analyzer.log(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())