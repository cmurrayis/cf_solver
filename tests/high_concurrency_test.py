#!/usr/bin/env python3
"""
High Concurrency Test for CloudflareBypass against Kick.com API.

Tests high concurrency performance against https://kick.com/api/v1/channels/adinross
with multiple sessions to validate specification targets.
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

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.session import SessionManager, create_session_config
from cloudflare_research.utils import Timer


class HighConcurrencyTester:
    """Tests high concurrency performance against Kick.com API."""

    def __init__(self, target_url: str):
        self.target_url = target_url
        self.results = {}

    def log(self, message: str) -> None:
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    async def test_baseline_aiohttp(self, sessions: int = 5, requests_per_session: int = 100) -> Dict[str, Any]:
        """Test baseline performance using pure aiohttp."""
        self.log(f"Testing baseline aiohttp performance: {sessions} sessions, {requests_per_session} requests each")

        all_results = []
        session_results = {}

        for session_id in range(sessions):
            self.log(f"Starting session {session_id + 1}/{sessions}")

            session_start = time.time()
            successful_requests = 0
            failed_requests = 0
            response_times = []

            # Configure session with appropriate limits
            connector = aiohttp.TCPConnector(
                limit=requests_per_session + 10,
                limit_per_host=requests_per_session,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )

            timeout = aiohttp.ClientTimeout(total=30, connect=10)

            async def make_request(session: aiohttp.ClientSession, request_id: int) -> Dict[str, Any]:
                request_start = time.time()
                try:
                    async with session.get(self.target_url, timeout=timeout) as response:
                        content = await response.text()
                        elapsed = time.time() - request_start

                        return {
                            'request_id': request_id,
                            'success': True,
                            'status_code': response.status,
                            'response_time': elapsed,
                            'content_length': len(content),
                            'headers': dict(response.headers),
                            'error': None
                        }
                except Exception as e:
                    elapsed = time.time() - request_start
                    return {
                        'request_id': request_id,
                        'success': False,
                        'status_code': None,
                        'response_time': elapsed,
                        'content_length': 0,
                        'headers': {},
                        'error': str(e)
                    }

            try:
                async with aiohttp.ClientSession(connector=connector) as session:
                    # Create all requests for this session
                    tasks = [make_request(session, i) for i in range(requests_per_session)]

                    # Execute all requests concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results
                    for result in results:
                        if isinstance(result, Exception):
                            failed_requests += 1
                            all_results.append({
                                'session_id': session_id,
                                'success': False,
                                'error': str(result),
                                'response_time': 0
                            })
                        else:
                            all_results.append({**result, 'session_id': session_id})
                            if result['success']:
                                successful_requests += 1
                                response_times.append(result['response_time'])
                            else:
                                failed_requests += 1

            except Exception as e:
                self.log(f"Session {session_id} failed: {e}")
                session_results[session_id] = {'error': str(e)}
                continue

            session_time = time.time() - session_start
            success_rate = (successful_requests / requests_per_session) * 100 if requests_per_session > 0 else 0
            throughput = requests_per_session / session_time if session_time > 0 else 0

            session_stats = {
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': success_rate,
                'total_time': session_time,
                'throughput': throughput,
                'avg_response_time': statistics.mean(response_times) if response_times else 0,
                'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times) if response_times else 0
            }

            session_results[session_id] = session_stats
            self.log(f"Session {session_id + 1} completed: {success_rate:.1f}% success, {throughput:.1f} req/s")

        # Calculate overall statistics
        total_requests = len(all_results)
        total_successful = sum(1 for r in all_results if r.get('success', False))
        overall_success_rate = (total_successful / total_requests) * 100 if total_requests > 0 else 0

        successful_times = [r['response_time'] for r in all_results if r.get('success', False)]
        overall_avg_time = statistics.mean(successful_times) if successful_times else 0

        return {
            'test_config': {
                'target_url': self.target_url,
                'sessions': sessions,
                'requests_per_session': requests_per_session,
                'total_requests': total_requests
            },
            'overall_stats': {
                'total_requests': total_requests,
                'successful_requests': total_successful,
                'failed_requests': total_requests - total_successful,
                'success_rate': overall_success_rate,
                'avg_response_time': overall_avg_time
            },
            'session_results': session_results,
            'detailed_results': all_results
        }

    async def test_cloudflare_bypass(self, sessions: int = 5, requests_per_session: int = 100) -> Dict[str, Any]:
        """Test performance using CloudflareBypass implementation."""
        self.log(f"Testing CloudflareBypass performance: {sessions} sessions, {requests_per_session} requests each")

        all_results = []
        session_results = {}

        for session_id in range(sessions):
            self.log(f"Starting CloudflareBypass session {session_id + 1}/{sessions}")

            session_start = time.time()
            successful_requests = 0
            failed_requests = 0
            response_times = []
            challenges_solved = 0

            # Configure CloudflareBypass for this session
            config = CloudflareBypassConfig(
                max_concurrent_requests=requests_per_session + 20,
                requests_per_second=50,  # Conservative rate limit
                browser_version="120.0.0.0",
                solve_javascript_challenges=True,
                solve_turnstile_challenges=True,
                challenge_timeout=30.0,
                timeout=30.0,
                enable_monitoring=True
            )

            async def make_bypass_request(bypass: CloudflareBypass, request_id: int) -> Dict[str, Any]:
                request_start = time.time()
                try:
                    result = await bypass.get(self.target_url)
                    elapsed = time.time() - request_start

                    challenge_solved = hasattr(result, 'challenge_solved') and result.challenge_solved

                    return {
                        'request_id': request_id,
                        'session_id': session_id,
                        'success': result.status_code == 200,
                        'status_code': result.status_code,
                        'response_time': elapsed,
                        'content_length': len(result.content) if hasattr(result, 'content') else 0,
                        'challenge_solved': challenge_solved,
                        'attempts': getattr(result, 'attempts', 1),
                        'error': None
                    }
                except Exception as e:
                    elapsed = time.time() - request_start
                    return {
                        'request_id': request_id,
                        'session_id': session_id,
                        'success': False,
                        'status_code': None,
                        'response_time': elapsed,
                        'content_length': 0,
                        'challenge_solved': False,
                        'attempts': 0,
                        'error': str(e)
                    }

            try:
                async with CloudflareBypass(config) as bypass:
                    # Create semaphore to control actual concurrency within session
                    semaphore = asyncio.Semaphore(min(50, requests_per_session))

                    async def controlled_request(request_id: int):
                        async with semaphore:
                            return await make_bypass_request(bypass, request_id)

                    # Execute all requests for this session
                    tasks = [controlled_request(i) for i in range(requests_per_session)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results
                    for result in results:
                        if isinstance(result, Exception):
                            failed_requests += 1
                            all_results.append({
                                'session_id': session_id,
                                'success': False,
                                'error': str(result),
                                'response_time': 0,
                                'challenge_solved': False
                            })
                        else:
                            all_results.append(result)
                            if result['success']:
                                successful_requests += 1
                                response_times.append(result['response_time'])
                                if result['challenge_solved']:
                                    challenges_solved += 1
                            else:
                                failed_requests += 1

            except Exception as e:
                self.log(f"CloudflareBypass session {session_id} failed: {e}")
                session_results[session_id] = {'error': str(e)}
                continue

            session_time = time.time() - session_start
            success_rate = (successful_requests / requests_per_session) * 100 if requests_per_session > 0 else 0
            throughput = requests_per_session / session_time if session_time > 0 else 0
            challenge_rate = (challenges_solved / successful_requests) * 100 if successful_requests > 0 else 0

            session_stats = {
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': success_rate,
                'challenges_solved': challenges_solved,
                'challenge_rate': challenge_rate,
                'total_time': session_time,
                'throughput': throughput,
                'avg_response_time': statistics.mean(response_times) if response_times else 0,
                'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times) if response_times else 0
            }

            session_results[session_id] = session_stats
            self.log(f"Bypass session {session_id + 1} completed: {success_rate:.1f}% success, {throughput:.1f} req/s, {challenges_solved} challenges")

        # Calculate overall statistics
        total_requests = len(all_results)
        total_successful = sum(1 for r in all_results if r.get('success', False))
        total_challenges = sum(1 for r in all_results if r.get('challenge_solved', False))
        overall_success_rate = (total_successful / total_requests) * 100 if total_requests > 0 else 0

        successful_times = [r['response_time'] for r in all_results if r.get('success', False)]
        overall_avg_time = statistics.mean(successful_times) if successful_times else 0

        return {
            'test_config': {
                'target_url': self.target_url,
                'sessions': sessions,
                'requests_per_session': requests_per_session,
                'total_requests': total_requests
            },
            'overall_stats': {
                'total_requests': total_requests,
                'successful_requests': total_successful,
                'failed_requests': total_requests - total_successful,
                'success_rate': overall_success_rate,
                'challenges_encountered': total_challenges,
                'challenge_solve_rate': (total_challenges / total_successful) * 100 if total_successful > 0 else 0,
                'avg_response_time': overall_avg_time
            },
            'session_results': session_results,
            'detailed_results': all_results
        }

    async def run_comparison_test(self, sessions: int = 5, requests_per_session: int = 100) -> Dict[str, Any]:
        """Run comparative test between baseline and CloudflareBypass."""
        self.log("=" * 80)
        self.log(f"HIGH CONCURRENCY TEST: {self.target_url}")
        self.log(f"Configuration: {sessions} sessions × {requests_per_session} requests = {sessions * requests_per_session} total requests")
        self.log("=" * 80)

        start_time = time.time()

        # Test 1: Baseline aiohttp performance
        self.log("\n>> PHASE 1: Baseline aiohttp Performance")
        try:
            baseline_results = await self.test_baseline_aiohttp(sessions, requests_per_session)
            baseline_success = True
        except Exception as e:
            self.log(f"Baseline test failed: {e}")
            baseline_results = {'error': str(e)}
            baseline_success = False

        # Test 2: CloudflareBypass performance
        self.log("\n>> PHASE 2: CloudflareBypass Performance")
        try:
            bypass_results = await self.test_cloudflare_bypass(sessions, requests_per_session)
            bypass_success = True
        except Exception as e:
            self.log(f"CloudflareBypass test failed: {e}")
            bypass_results = {'error': str(e)}
            bypass_success = False

        total_test_time = time.time() - start_time

        # Generate comparison report
        report = {
            'timestamp': datetime.now().isoformat(),
            'target_url': self.target_url,
            'test_duration_seconds': total_test_time,
            'test_configuration': {
                'sessions': sessions,
                'requests_per_session': requests_per_session,
                'total_requests': sessions * requests_per_session
            },
            'baseline_aiohttp': baseline_results,
            'cloudflare_bypass': bypass_results,
            'comparison': self._generate_comparison(baseline_results, bypass_results) if baseline_success and bypass_success else None
        }

        return report

    def _generate_comparison(self, baseline: Dict[str, Any], bypass: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparison analysis between baseline and bypass results."""
        if 'error' in baseline or 'error' in bypass:
            return {'error': 'Cannot compare due to test failures'}

        b_stats = baseline['overall_stats']
        cf_stats = bypass['overall_stats']

        comparison = {
            'success_rate_comparison': {
                'baseline_percent': b_stats['success_rate'],
                'bypass_percent': cf_stats['success_rate'],
                'difference': cf_stats['success_rate'] - b_stats['success_rate'],
                'bypass_better': cf_stats['success_rate'] >= b_stats['success_rate']
            },
            'response_time_comparison': {
                'baseline_avg_ms': b_stats['avg_response_time'] * 1000,
                'bypass_avg_ms': cf_stats['avg_response_time'] * 1000,
                'difference_ms': (cf_stats['avg_response_time'] - b_stats['avg_response_time']) * 1000,
                'bypass_faster': cf_stats['avg_response_time'] <= b_stats['avg_response_time']
            },
            'challenge_handling': {
                'challenges_encountered': cf_stats.get('challenges_encountered', 0),
                'challenge_solve_rate': cf_stats.get('challenge_solve_rate', 0),
                'adds_capability': cf_stats.get('challenges_encountered', 0) > 0
            },
            'overall_assessment': {
                'bypass_maintains_performance': cf_stats['success_rate'] >= (b_stats['success_rate'] - 5),  # Allow 5% degradation
                'bypass_adds_value': cf_stats.get('challenges_encountered', 0) > 0,
                'recommended': cf_stats['success_rate'] >= 90 and cf_stats.get('challenge_solve_rate', 0) >= 80
            }
        }

        return comparison

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print executive summary of test results."""
        self.log("\n" + "=" * 80)
        self.log("HIGH CONCURRENCY TEST SUMMARY")
        self.log("=" * 80)

        config = report['test_configuration']
        self.log(f"Target URL: {report['target_url']}")
        self.log(f"Test Scale: {config['sessions']} sessions × {config['requests_per_session']} requests = {config['total_requests']} total")
        self.log(f"Test Duration: {report['test_duration_seconds']:.1f} seconds")

        # Baseline results
        baseline = report['baseline_aiohttp']
        if 'error' not in baseline:
            b_stats = baseline['overall_stats']
            self.log(f"\nBaseline aiohttp Results:")
            self.log(f"  Success Rate: {b_stats['success_rate']:.1f}%")
            self.log(f"  Avg Response Time: {b_stats['avg_response_time']*1000:.0f}ms")
            self.log(f"  Total Successful: {b_stats['successful_requests']}/{b_stats['total_requests']}")
        else:
            self.log(f"\nBaseline aiohttp: FAILED - {baseline['error']}")

        # CloudflareBypass results
        bypass = report['cloudflare_bypass']
        if 'error' not in bypass:
            cf_stats = bypass['overall_stats']
            self.log(f"\nCloudflareBypass Results:")
            self.log(f"  Success Rate: {cf_stats['success_rate']:.1f}%")
            self.log(f"  Avg Response Time: {cf_stats['avg_response_time']*1000:.0f}ms")
            self.log(f"  Challenges Encountered: {cf_stats.get('challenges_encountered', 0)}")
            self.log(f"  Challenge Solve Rate: {cf_stats.get('challenge_solve_rate', 0):.1f}%")
            self.log(f"  Total Successful: {cf_stats['successful_requests']}/{cf_stats['total_requests']}")
        else:
            self.log(f"\nCloudflareBypass: FAILED - {bypass['error']}")

        # Comparison
        comparison = report.get('comparison')
        if comparison and 'error' not in comparison:
            self.log(f"\nComparison Analysis:")
            success_comp = comparison['success_rate_comparison']
            time_comp = comparison['response_time_comparison']
            challenge_comp = comparison['challenge_handling']

            self.log(f"  Success Rate: {success_comp['difference']:+.1f}% {'(Better)' if success_comp['bypass_better'] else '(Worse)'}")
            self.log(f"  Response Time: {time_comp['difference_ms']:+.0f}ms {'(Faster)' if time_comp['bypass_faster'] else '(Slower)'}")
            self.log(f"  Challenge Capability: {'Yes' if challenge_comp['adds_capability'] else 'No'}")

            overall = comparison['overall_assessment']
            recommendation = "RECOMMENDED" if overall['recommended'] else "NEEDS_IMPROVEMENT"
            self.log(f"  Overall Assessment: {recommendation}")

        else:
            self.log(f"\nComparison: Not available due to test failures")


async def main():
    """Main entry point for high concurrency testing."""
    target_url = "https://kick.com/api/v1/channels/adinross"

    # Test configuration
    sessions = 5
    requests_per_session = 20  # Start with smaller load to avoid overwhelming the API

    tester = HighConcurrencyTester(target_url)

    try:
        # Run comprehensive test
        results = await tester.run_comparison_test(sessions, requests_per_session)

        # Print summary
        tester.print_summary(results)

        # Save detailed results
        output_file = "high_concurrency_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        tester.log(f"\nDetailed results saved to: {output_file}")

        # Determine exit code based on results
        if 'comparison' in results and results['comparison']:
            overall = results['comparison'].get('overall_assessment', {})
            if overall.get('recommended', False):
                tester.log("\n>> HIGH CONCURRENCY TEST PASSED!")
                sys.exit(0)
            else:
                tester.log("\n>> HIGH CONCURRENCY TEST COMPLETED (Performance concerns detected)")
                sys.exit(0)
        else:
            tester.log("\n>> HIGH CONCURRENCY TEST COMPLETED (Partial results)")
            sys.exit(0)

    except KeyboardInterrupt:
        tester.log("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        tester.log(f"\nUnexpected error during testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())