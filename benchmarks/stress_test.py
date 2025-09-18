"""
Concurrency Stress Test for CloudflareBypass

This stress test pushes CloudflareBypass to its limits with extreme concurrency,
high request rates, and sustained load to identify breaking points, resource
limits, and system stability under maximum stress conditions.
"""

import asyncio
import time
import json
import psutil
import statistics
import logging
import signal
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig


@dataclass
class StressTestResult:
    """Results from a stress test scenario."""
    test_name: str
    duration: float
    target_concurrency: int
    actual_peak_concurrency: int
    target_rps: float
    actual_avg_rps: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    peak_memory_mb: float
    avg_cpu_percent: float
    peak_cpu_percent: float
    network_errors: int
    timeout_errors: int
    connection_errors: int
    challenge_errors: int
    system_overload: bool
    breaking_point_reached: bool
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemMonitor:
    """Real-time system resource monitoring."""

    def __init__(self):
        self.cpu_samples = []
        self.memory_samples = []
        self.monitoring = False

    async def start_monitoring(self, interval: float = 1.0):
        """Start system monitoring."""
        self.monitoring = True
        self.cpu_samples.clear()
        self.memory_samples.clear()

        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self.cpu_samples.append(cpu_percent)

                # Memory usage
                memory_info = psutil.virtual_memory()
                memory_mb = (memory_info.total - memory_info.available) / 1024 / 1024
                self.memory_samples.append(memory_mb)

                await asyncio.sleep(interval)

            except Exception:
                break

    def stop_monitoring(self):
        """Stop system monitoring."""
        self.monitoring = False

    def get_stats(self) -> Tuple[float, float, float, float]:
        """Get monitoring statistics."""
        if not self.cpu_samples or not self.memory_samples:
            return 0, 0, 0, 0

        avg_cpu = statistics.mean(self.cpu_samples)
        peak_cpu = max(self.cpu_samples)
        avg_memory = statistics.mean(self.memory_samples)
        peak_memory = max(self.memory_samples)

        return avg_cpu, peak_cpu, avg_memory, peak_memory


class ConcurrencyStressTest:
    """Comprehensive concurrency stress testing framework."""

    def __init__(self):
        self.results: List[StressTestResult] = []
        self.running = True
        self.emergency_stop = False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\n⚠️  Signal {signum} received. Initiating emergency stop...")
            self.emergency_stop = True
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run_stress_test(
        self,
        config: CloudflareBypassConfig,
        test_name: str,
        target_url: str,
        duration_seconds: int,
        ramp_up_seconds: int = 30
    ) -> StressTestResult:
        """
        Run a comprehensive stress test.

        Args:
            config: CloudflareBypass configuration
            test_name: Name for this stress test
            target_url: URL to stress test
            duration_seconds: How long to run at full stress
            ramp_up_seconds: Time to ramp up to full load

        Returns:
            StressTestResult with detailed metrics
        """
        print(f"\n🔥 Stress Test: {test_name}")
        print(f"Target URL: {target_url}")
        print(f"Target Concurrency: {config.max_concurrent_requests}")
        print(f"Target RPS: {config.requests_per_second}")
        print(f"Duration: {duration_seconds}s (+ {ramp_up_seconds}s ramp-up)")

        # Initialize tracking variables
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        response_times = []
        active_tasks = []
        peak_concurrency = 0

        # Error categorization
        network_errors = 0
        timeout_errors = 0
        connection_errors = 0
        challenge_errors = 0

        # System monitoring
        monitor = SystemMonitor()
        monitor_task = asyncio.create_task(monitor.start_monitoring(0.5))

        start_time = time.time()
        ramp_end_time = start_time + ramp_up_seconds
        test_end_time = ramp_end_time + duration_seconds

        try:
            async with CloudflareBypass(config) as bypass:
                print("🚀 Starting stress test...")

                async def make_stress_request():
                    """Make a single stress test request."""
                    nonlocal total_requests, successful_requests, failed_requests
                    nonlocal network_errors, timeout_errors, connection_errors, challenge_errors

                    request_start = time.time()

                    try:
                        result = await bypass.get(target_url)
                        request_time = time.time() - request_start

                        total_requests += 1
                        successful_requests += 1
                        response_times.append(request_time)

                    except asyncio.TimeoutError:
                        total_requests += 1
                        failed_requests += 1
                        timeout_errors += 1
                        response_times.append(time.time() - request_start)

                    except ConnectionError:
                        total_requests += 1
                        failed_requests += 1
                        connection_errors += 1
                        response_times.append(time.time() - request_start)

                    except Exception as e:
                        total_requests += 1
                        failed_requests += 1
                        error_str = str(e).lower()

                        if 'network' in error_str or 'connection' in error_str:
                            network_errors += 1
                        elif 'challenge' in error_str or 'cloudflare' in error_str:
                            challenge_errors += 1
                        else:
                            network_errors += 1  # Default category

                        response_times.append(time.time() - request_start)

                # Main stress test loop
                last_report = start_time
                report_interval = 10  # Report every 10 seconds

                while time.time() < test_end_time and self.running and not self.emergency_stop:
                    current_time = time.time()

                    # Calculate current target concurrency (ramp up)
                    if current_time < ramp_end_time:
                        ramp_progress = (current_time - start_time) / ramp_up_seconds
                        current_target_concurrency = int(config.max_concurrent_requests * ramp_progress)
                    else:
                        current_target_concurrency = config.max_concurrent_requests

                    # Maintain target concurrency
                    active_tasks = [t for t in active_tasks if not t.done()]
                    current_concurrency = len(active_tasks)

                    if current_concurrency < current_target_concurrency:
                        # Add more tasks
                        tasks_to_add = current_target_concurrency - current_concurrency
                        for _ in range(min(tasks_to_add, 50)):  # Limit burst creation
                            task = asyncio.create_task(make_stress_request())
                            active_tasks.append(task)

                    # Update peak concurrency tracking
                    peak_concurrency = max(peak_concurrency, len(active_tasks))

                    # Progress reporting
                    if current_time - last_report >= report_interval:
                        elapsed = current_time - start_time
                        current_rps = total_requests / elapsed if elapsed > 0 else 0
                        current_error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

                        print(f"  {elapsed:.0f}s: "
                              f"Requests: {total_requests}, "
                              f"Active: {len(active_tasks)}, "
                              f"RPS: {current_rps:.1f}, "
                              f"Errors: {current_error_rate:.1f}%")

                        last_report = current_time

                        # Check for system overload
                        if len(active_tasks) == 0 and current_target_concurrency > 0:
                            print("⚠️  Warning: No active tasks despite target concurrency > 0")

                    # Rate limiting and yield
                    if config.requests_per_second > 0:
                        await asyncio.sleep(min(0.1, 1.0 / config.requests_per_second))
                    else:
                        await asyncio.sleep(0.001)  # Small yield

                # Test completed, wait for remaining requests
                print("📊 Test duration reached. Waiting for remaining requests...")

                if active_tasks:
                    # Wait up to 30 seconds for remaining requests
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*active_tasks, return_exceptions=True),
                            timeout=30
                        )
                    except asyncio.TimeoutError:
                        print("⚠️  Some requests didn't complete within timeout")

        except Exception as e:
            print(f"❌ Stress test error: {e}")

        finally:
            # Stop monitoring
            monitor.stop_monitoring()
            await monitor_task

        # Calculate final metrics
        actual_duration = time.time() - start_time
        avg_cpu, peak_cpu, avg_memory, peak_memory = monitor.get_stats()

        actual_rps = total_requests / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        # Response time statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
            p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0

        # Determine if breaking point was reached
        breaking_point_reached = (
            error_rate > 50 or  # More than 50% errors
            peak_cpu > 95 or    # CPU maxed out
            actual_rps < (config.requests_per_second * 0.1) or  # Much lower than target
            self.emergency_stop
        )

        system_overload = peak_cpu > 90 or peak_memory > 8000  # 8GB threshold

        result = StressTestResult(
            test_name=test_name,
            duration=actual_duration,
            target_concurrency=config.max_concurrent_requests,
            actual_peak_concurrency=peak_concurrency,
            target_rps=config.requests_per_second,
            actual_avg_rps=actual_rps,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            error_rate=error_rate,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            peak_memory_mb=peak_memory,
            avg_cpu_percent=avg_cpu,
            peak_cpu_percent=peak_cpu,
            network_errors=network_errors,
            timeout_errors=timeout_errors,
            connection_errors=connection_errors,
            challenge_errors=challenge_errors,
            system_overload=system_overload,
            breaking_point_reached=breaking_point_reached,
            timestamp=datetime.now().isoformat()
        )

        self.results.append(result)

        # Print summary
        print(f"\n📊 Stress Test Results:")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Total Requests: {total_requests}")
        print(f"  Success Rate: {((successful_requests/total_requests)*100):.1f}%")
        print(f"  Actual RPS: {actual_rps:.1f} (target: {config.requests_per_second})")
        print(f"  Peak Concurrency: {peak_concurrency} (target: {config.max_concurrent_requests})")
        print(f"  Avg Response Time: {avg_response_time:.3f}s")
        print(f"  P95 Response Time: {p95_response_time:.3f}s")
        print(f"  Peak CPU: {peak_cpu:.1f}%")
        print(f"  Peak Memory: {peak_memory:.1f} MB")
        print(f"  Error Breakdown:")
        print(f"    Network: {network_errors}")
        print(f"    Timeout: {timeout_errors}")
        print(f"    Connection: {connection_errors}")
        print(f"    Challenge: {challenge_errors}")

        if breaking_point_reached:
            print(f"  🔥 Breaking point reached!")
        if system_overload:
            print(f"  ⚠️  System overload detected!")

        return result


async def stress_test_concurrency_limits():
    """Test concurrency limits to find breaking points."""
    print("=== Concurrency Limits Stress Test ===")

    target_url = "https://httpbin.org/get"
    test_duration = 60  # 1 minute per test

    # Progressive concurrency levels
    concurrency_levels = [10, 25, 50, 100, 200, 500, 1000]
    stress_tester = ConcurrencyStressTest()
    stress_tester.setup_signal_handlers()

    for concurrency in concurrency_levels:
        if not stress_tester.running:
            break

        print(f"\n🧪 Testing concurrency level: {concurrency}")

        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrency,
            requests_per_second=0,  # No rate limiting for max stress
            timeout=15.0,  # Shorter timeout for stress testing
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        try:
            result = await stress_tester.run_stress_test(
                config, f"Concurrency_Stress_{concurrency}", target_url, test_duration, ramp_up_seconds=15
            )

            # Check if we should stop (breaking point reached)
            if result.breaking_point_reached:
                print(f"🛑 Breaking point reached at concurrency {concurrency}")
                break

            # Brief recovery period
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ Concurrency test failed at level {concurrency}: {e}")
            break

    return stress_tester.results


async def stress_test_sustained_extreme_load():
    """Test sustained extreme load over extended period."""
    print("\n=== Sustained Extreme Load Stress Test ===")

    target_url = "https://httpbin.org/get"
    test_duration = 300  # 5 minutes of extreme load

    config = CloudflareBypassConfig(
        max_concurrent_requests=100,
        requests_per_second=50,
        timeout=20.0,
        solve_javascript_challenges=False,
        enable_detailed_logging=False,
        enable_monitoring=True
    )

    stress_tester = ConcurrencyStressTest()
    stress_tester.setup_signal_handlers()

    await stress_tester.run_stress_test(
        config, "Sustained_Extreme_Load", target_url, test_duration, ramp_up_seconds=30
    )

    return stress_tester.results


async def stress_test_rate_limit_breaking_point():
    """Test rate limit breaking points."""
    print("\n=== Rate Limit Breaking Point Stress Test ===")

    target_url = "https://httpbin.org/get"
    test_duration = 45

    # Progressive rate limits
    rate_limits = [10, 25, 50, 100, 200, 500, 1000]
    stress_tester = ConcurrencyStressTest()
    stress_tester.setup_signal_handlers()

    for rate_limit in rate_limits:
        if not stress_tester.running:
            break

        print(f"\n🧪 Testing rate limit: {rate_limit} RPS")

        config = CloudflareBypassConfig(
            max_concurrent_requests=50,  # Fixed concurrency
            requests_per_second=rate_limit,
            timeout=15.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        try:
            result = await stress_tester.run_stress_test(
                config, f"Rate_Stress_{rate_limit}_RPS", target_url, test_duration, ramp_up_seconds=10
            )

            if result.breaking_point_reached:
                print(f"🛑 Breaking point reached at {rate_limit} RPS")
                break

            await asyncio.sleep(5)

        except Exception as e:
            print(f"❌ Rate limit test failed at {rate_limit} RPS: {e}")
            break

    return stress_tester.results


async def stress_test_memory_pressure():
    """Test behavior under memory pressure."""
    print("\n=== Memory Pressure Stress Test ===")

    target_url = "https://httpbin.org/get"
    test_duration = 120

    # Configuration designed to use more memory
    config = CloudflareBypassConfig(
        max_concurrent_requests=200,
        requests_per_second=75,
        connection_pool_size=500,  # Large connection pool
        timeout=30.0,
        solve_javascript_challenges=True,  # Uses more memory
        enable_detailed_logging=False,
        enable_monitoring=True,
        enable_metrics_collection=True
    )

    stress_tester = ConcurrencyStressTest()
    stress_tester.setup_signal_handlers()

    await stress_tester.run_stress_test(
        config, "Memory_Pressure", target_url, test_duration, ramp_up_seconds=20
    )

    return stress_tester.results


async def stress_test_error_resilience():
    """Test resilience to errors and failures."""
    print("\n=== Error Resilience Stress Test ===")

    # Mix of good and bad URLs to induce errors
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/500",  # Server error
        "https://httpbin.org/delay/10",    # Timeout
        "https://nonexistent-domain-12345.com",  # DNS error
        "https://httpbin.org/status/404",  # Not found
    ]

    test_duration = 90
    stress_tester = ConcurrencyStressTest()
    stress_tester.setup_signal_handlers()

    config = CloudflareBypassConfig(
        max_concurrent_requests=50,
        requests_per_second=20,
        timeout=5.0,  # Short timeout to induce timeouts
        solve_javascript_challenges=False,
        enable_detailed_logging=False
    )

    # Test each URL type
    for i, url in enumerate(urls[:3]):  # Test first 3 to avoid too many errors
        if not stress_tester.running:
            break

        test_name = f"Error_Resilience_{i+1}"
        print(f"\n🧪 Testing error resilience with: {url}")

        await stress_tester.run_stress_test(
            config, test_name, url, test_duration // 3, ramp_up_seconds=5
        )

        await asyncio.sleep(3)

    return stress_tester.results


def analyze_stress_test_results(all_results: List[List[StressTestResult]]):
    """Analyze stress test results to identify patterns and limits."""
    print(f"\n🔍 Stress Test Analysis")

    # Flatten results
    flattened_results = []
    for result_group in all_results:
        flattened_results.extend(result_group)

    if not flattened_results:
        print("No results to analyze")
        return

    # Overall statistics
    total_tests = len(flattened_results)
    tests_with_breaking_points = sum(1 for r in flattened_results if r.breaking_point_reached)
    tests_with_overload = sum(1 for r in flattened_results if r.system_overload)

    print(f"Overall Statistics:")
    print(f"  Total Stress Tests: {total_tests}")
    print(f"  Breaking Points Reached: {tests_with_breaking_points}")
    print(f"  System Overloads: {tests_with_overload}")

    # Performance limits
    max_successful_rps = max(r.actual_avg_rps for r in flattened_results if r.error_rate < 10)
    max_concurrency = max(r.actual_peak_concurrency for r in flattened_results if r.error_rate < 10)

    print(f"\nPerformance Limits (with <10% error rate):")
    print(f"  Max Sustainable RPS: {max_successful_rps:.1f}")
    print(f"  Max Sustainable Concurrency: {max_concurrency}")

    # Resource usage
    peak_memory = max(r.peak_memory_mb for r in flattened_results)
    peak_cpu = max(r.peak_cpu_percent for r in flattened_results)

    print(f"\nResource Usage:")
    print(f"  Peak Memory Usage: {peak_memory:.1f} MB")
    print(f"  Peak CPU Usage: {peak_cpu:.1f}%")

    # Error analysis
    total_requests = sum(r.total_requests for r in flattened_results)
    total_errors = sum(r.failed_requests for r in flattened_results)
    overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

    print(f"\nError Analysis:")
    print(f"  Total Requests: {total_requests}")
    print(f"  Total Errors: {total_errors}")
    print(f"  Overall Error Rate: {overall_error_rate:.2f}%")


def generate_stress_test_report(all_results: List[List[StressTestResult]], report_filename: str):
    """Generate comprehensive stress test report."""
    print(f"\n📊 Generating Stress Test Report: {report_filename}")

    # Flatten results
    flattened_results = []
    for result_group in all_results:
        flattened_results.extend(result_group)

    # Create report
    report = {
        "stress_test_summary": {
            "total_tests": len(flattened_results),
            "timestamp": datetime.now().isoformat(),
            "breaking_points_reached": sum(1 for r in flattened_results if r.breaking_point_reached),
            "system_overloads": sum(1 for r in flattened_results if r.system_overload),
            "total_requests": sum(r.total_requests for r in flattened_results),
            "total_errors": sum(r.failed_requests for r in flattened_results),
            "overall_error_rate": (sum(r.failed_requests for r in flattened_results) /
                                 sum(r.total_requests for r in flattened_results) * 100)
                                 if sum(r.total_requests for r in flattened_results) > 0 else 0
        },
        "test_results": [result.to_dict() for result in flattened_results],
        "performance_limits": {},
        "recommendations": []
    }

    # Calculate performance limits
    successful_tests = [r for r in flattened_results if r.error_rate < 10]
    if successful_tests:
        report["performance_limits"] = {
            "max_sustainable_rps": max(r.actual_avg_rps for r in successful_tests),
            "max_sustainable_concurrency": max(r.actual_peak_concurrency for r in successful_tests),
            "peak_memory_mb": max(r.peak_memory_mb for r in flattened_results),
            "peak_cpu_percent": max(r.peak_cpu_percent for r in flattened_results)
        }

    # Generate recommendations
    recommendations = []

    # Based on breaking points
    breaking_point_tests = [r for r in flattened_results if r.breaking_point_reached]
    if breaking_point_tests:
        min_breaking_concurrency = min(r.target_concurrency for r in breaking_point_tests)
        recommendations.append(f"Avoid concurrency above {min_breaking_concurrency} to prevent breaking points")

    # Based on error rates
    high_error_tests = [r for r in flattened_results if r.error_rate > 20]
    if high_error_tests:
        recommendations.append("Monitor error rates closely during high-load scenarios")

    # Based on resource usage
    high_memory_tests = [r for r in flattened_results if r.peak_memory_mb > 4000]
    if high_memory_tests:
        recommendations.append("Consider memory limits when scaling beyond 4GB usage")

    report["recommendations"] = recommendations

    # Save report
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Stress test report saved to: {report_filename}")


async def main():
    """Main function to run all stress tests."""
    # Setup logging
    logging.basicConfig(
        level=logging.ERROR,  # Minimal logging during stress tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Concurrency Stress Test Suite")
    print("=" * 70)
    print("⚠️  WARNING: This test suite will push your system to its limits!")
    print("It may consume significant CPU, memory, and network resources.")
    print("Monitor your system closely and use Ctrl+C for emergency stop.")
    print("=" * 70)

    # Confirm before proceeding
    try:
        response = input("Proceed with stress testing? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Stress testing cancelled.")
            return
    except KeyboardInterrupt:
        print("\nStress testing cancelled.")
        return

    all_results = []

    try:
        print("\n🔥 Starting stress test suite...")

        # Concurrency limits
        print("\n1️⃣  Testing concurrency limits...")
        concurrency_results = await stress_test_concurrency_limits()
        all_results.append(concurrency_results)

        # Sustained extreme load
        print("\n2️⃣  Testing sustained extreme load...")
        sustained_results = await stress_test_sustained_extreme_load()
        all_results.append(sustained_results)

        # Rate limit breaking points
        print("\n3️⃣  Testing rate limit breaking points...")
        rate_results = await stress_test_rate_limit_breaking_point()
        all_results.append(rate_results)

        # Memory pressure
        print("\n4️⃣  Testing memory pressure...")
        memory_results = await stress_test_memory_pressure()
        all_results.append(memory_results)

        # Error resilience
        print("\n5️⃣  Testing error resilience...")
        error_results = await stress_test_error_resilience()
        all_results.append(error_results)

        # Analyze all results
        analyze_stress_test_results(all_results)

        # Generate comprehensive report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"stress_test_report_{timestamp}.json"
        generate_stress_test_report(all_results, report_filename)

        print(f"\n{'='*70}")
        print("🎯 Stress test suite completed!")
        print(f"📊 Detailed results saved to: {report_filename}")
        print(f"{'='*70}")

        print("\nStress Test Insights:")
        print("🔍 Use the report to identify your system's performance limits")
        print("⚡ Optimize configurations based on breaking point analysis")
        print("📈 Monitor resource usage patterns during high-load scenarios")
        print("🛡️  Implement circuit breakers based on error rate thresholds")
        print("🎛️  Adjust concurrency and rate limits based on test results")

    except KeyboardInterrupt:
        print("\n🛑 Stress testing interrupted by user")
    except Exception as e:
        print(f"❌ Stress testing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the stress tests
    asyncio.run(main())