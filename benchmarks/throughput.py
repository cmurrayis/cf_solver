"""
Throughput Benchmark for CloudflareBypass

This benchmark measures the request throughput performance of CloudflareBypass
under various configurations and load conditions. It provides detailed metrics
on requests per second, response times, and resource utilization.
"""

import asyncio
import time
import json
import statistics
import psutil
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig


@dataclass
class ThroughputMetrics:
    """Metrics collected during throughput testing."""
    test_name: str
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    challenges_solved: int
    total_attempts: int
    cpu_usage_percent: float
    memory_usage_mb: float
    network_bytes_sent: int
    network_bytes_received: int
    error_rate: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ThroughputBenchmark:
    """Comprehensive throughput benchmark for CloudflareBypass."""

    def __init__(self):
        self.results: List[ThroughputMetrics] = []
        self.start_network_stats = None
        self.start_time = None

    def _get_network_stats(self) -> Tuple[int, int]:
        """Get current network bytes sent/received."""
        net_io = psutil.net_io_counters()
        return net_io.bytes_sent, net_io.bytes_recv

    def _get_system_stats(self) -> Tuple[float, float]:
        """Get current CPU and memory usage."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        memory_mb = (memory_info.total - memory_info.available) / 1024 / 1024
        return cpu_percent, memory_mb

    async def run_throughput_test(
        self,
        config: CloudflareBypassConfig,
        test_name: str,
        target_url: str,
        duration_seconds: int,
        warmup_seconds: int = 10
    ) -> ThroughputMetrics:
        """
        Run a throughput test for specified duration.

        Args:
            config: CloudflareBypass configuration
            test_name: Name for this test
            target_url: URL to test against
            duration_seconds: How long to run the test
            warmup_seconds: Warmup period before measuring

        Returns:
            ThroughputMetrics with detailed results
        """
        print(f"\n=== Running Throughput Test: {test_name} ===")
        print(f"Target URL: {target_url}")
        print(f"Duration: {duration_seconds}s (+ {warmup_seconds}s warmup)")
        print(f"Max Concurrent: {config.max_concurrent_requests}")
        print(f"Rate Limit: {config.requests_per_second} req/s")

        # Initialize tracking variables
        requests_completed = 0
        successful_requests = 0
        failed_requests = 0
        response_times = []
        challenges_solved = 0
        total_attempts = 0

        # Get initial system stats
        initial_net_sent, initial_net_recv = self._get_network_stats()

        try:
            async with CloudflareBypass(config) as bypass:
                print("Starting warmup period...")

                # Warmup phase
                warmup_end = time.time() + warmup_seconds
                while time.time() < warmup_end:
                    try:
                        result = await bypass.get(target_url)
                        await asyncio.sleep(0.1)  # Small delay during warmup
                    except:
                        pass

                print("Warmup complete. Starting measurement...")

                # Start measurement
                start_time = time.time()
                end_time = start_time + duration_seconds

                async def make_request():
                    """Make a single request and track metrics."""
                    nonlocal requests_completed, successful_requests, failed_requests
                    nonlocal challenges_solved, total_attempts

                    request_start = time.time()

                    try:
                        result = await bypass.get(target_url)
                        request_time = time.time() - request_start

                        requests_completed += 1
                        successful_requests += 1
                        response_times.append(request_time)

                        if result.challenge_solved:
                            challenges_solved += 1
                        total_attempts += result.attempts

                    except Exception as e:
                        request_time = time.time() - request_start
                        requests_completed += 1
                        failed_requests += 1
                        response_times.append(request_time)

                # Generate load for the specified duration
                tasks = []

                while time.time() < end_time:
                    # Create requests up to the concurrency limit
                    if len(tasks) < config.max_concurrent_requests:
                        task = asyncio.create_task(make_request())
                        tasks.append(task)

                    # Clean up completed tasks
                    tasks = [t for t in tasks if not t.done()]

                    # Respect rate limiting
                    if config.requests_per_second > 0:
                        await asyncio.sleep(1.0 / config.requests_per_second)
                    else:
                        await asyncio.sleep(0.001)  # Small yield

                # Wait for remaining tasks to complete
                print("Test duration reached. Waiting for remaining requests...")
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Calculate final metrics
                actual_duration = time.time() - start_time
                final_cpu, final_memory = self._get_system_stats()
                final_net_sent, final_net_recv = self._get_network_stats()

                # Calculate throughput
                actual_rps = requests_completed / actual_duration if actual_duration > 0 else 0

                # Calculate response time statistics
                if response_times:
                    avg_response_time = statistics.mean(response_times)
                    min_response_time = min(response_times)
                    max_response_time = max(response_times)
                    p50_response_time = statistics.median(response_times)

                    # Calculate percentiles
                    sorted_times = sorted(response_times)
                    p95_index = int(0.95 * len(sorted_times))
                    p99_index = int(0.99 * len(sorted_times))
                    p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
                    p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
                else:
                    avg_response_time = min_response_time = max_response_time = 0
                    p50_response_time = p95_response_time = p99_response_time = 0

                # Calculate error rate
                error_rate = (failed_requests / requests_completed * 100) if requests_completed > 0 else 0

                # Create metrics object
                metrics = ThroughputMetrics(
                    test_name=test_name,
                    duration=actual_duration,
                    total_requests=requests_completed,
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    requests_per_second=actual_rps,
                    avg_response_time=avg_response_time,
                    min_response_time=min_response_time,
                    max_response_time=max_response_time,
                    p50_response_time=p50_response_time,
                    p95_response_time=p95_response_time,
                    p99_response_time=p99_response_time,
                    challenges_solved=challenges_solved,
                    total_attempts=total_attempts,
                    cpu_usage_percent=final_cpu,
                    memory_usage_mb=final_memory,
                    network_bytes_sent=final_net_sent - initial_net_sent,
                    network_bytes_received=final_net_recv - initial_net_recv,
                    error_rate=error_rate,
                    timestamp=datetime.now().isoformat()
                )

                self.results.append(metrics)

                # Print immediate results
                print(f"\nTest Results:")
                print(f"  Duration: {actual_duration:.2f}s")
                print(f"  Total Requests: {requests_completed}")
                print(f"  Successful: {successful_requests}")
                print(f"  Failed: {failed_requests}")
                print(f"  RPS: {actual_rps:.2f}")
                print(f"  Avg Response Time: {avg_response_time:.3f}s")
                print(f"  P95 Response Time: {p95_response_time:.3f}s")
                print(f"  Error Rate: {error_rate:.2f}%")
                print(f"  Challenges Solved: {challenges_solved}")
                print(f"  CPU Usage: {final_cpu:.1f}%")
                print(f"  Memory Usage: {final_memory:.1f} MB")

                return metrics

        except Exception as e:
            print(f"Throughput test failed: {e}")
            raise


async def benchmark_different_concurrency_levels():
    """Benchmark throughput at different concurrency levels."""
    print("=== Concurrency Level Throughput Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 30  # 30 seconds per test

    concurrency_levels = [1, 5, 10, 25, 50, 100]
    benchmark = ThroughputBenchmark()

    for concurrency in concurrency_levels:
        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrency,
            requests_per_second=0,  # No rate limiting for max throughput
            timeout=30.0,
            solve_javascript_challenges=False,  # Disabled for throughput testing
            enable_detailed_logging=False
        )

        test_name = f"Concurrency_{concurrency}"
        await benchmark.run_throughput_test(
            config, test_name, target_url, test_duration, warmup_seconds=5
        )

        # Small delay between tests
        await asyncio.sleep(5)

    return benchmark.results


async def benchmark_rate_limiting_effects():
    """Benchmark the effects of rate limiting on throughput."""
    print("\n=== Rate Limiting Effects Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 30

    rate_limits = [0, 5, 10, 20, 50, 100]  # 0 = no limit
    benchmark = ThroughputBenchmark()

    for rate_limit in rate_limits:
        config = CloudflareBypassConfig(
            max_concurrent_requests=20,  # Fixed concurrency
            requests_per_second=rate_limit if rate_limit > 0 else 0,
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        test_name = f"RateLimit_{rate_limit}_rps" if rate_limit > 0 else "RateLimit_None"
        await benchmark.run_throughput_test(
            config, test_name, target_url, test_duration, warmup_seconds=5
        )

        await asyncio.sleep(3)

    return benchmark.results


async def benchmark_challenge_solving_impact():
    """Benchmark the impact of challenge solving on throughput."""
    print("\n=== Challenge Solving Impact Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 30

    configs = [
        (CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10,
            solve_javascript_challenges=False,
            solve_managed_challenges=False,
            solve_turnstile_challenges=False,
            enable_detailed_logging=False
        ), "No_Challenges"),

        (CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10,
            solve_javascript_challenges=True,
            solve_managed_challenges=False,
            solve_turnstile_challenges=False,
            enable_detailed_logging=False
        ), "JS_Challenges_Only"),

        (CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10,
            solve_javascript_challenges=True,
            solve_managed_challenges=True,
            solve_turnstile_challenges=True,
            enable_detailed_logging=False
        ), "All_Challenges")
    ]

    benchmark = ThroughputBenchmark()

    for config, test_name in configs:
        await benchmark.run_throughput_test(
            config, test_name, target_url, test_duration, warmup_seconds=5
        )
        await asyncio.sleep(5)

    return benchmark.results


async def benchmark_sustained_load():
    """Benchmark sustained load over a longer period."""
    print("\n=== Sustained Load Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 120  # 2 minutes

    config = CloudflareBypassConfig(
        max_concurrent_requests=50,
        requests_per_second=20,
        timeout=30.0,
        solve_javascript_challenges=False,
        enable_detailed_logging=False,
        enable_monitoring=True,
        enable_metrics_collection=True
    )

    benchmark = ThroughputBenchmark()

    await benchmark.run_throughput_test(
        config, "Sustained_Load", target_url, test_duration, warmup_seconds=10
    )

    return benchmark.results


def generate_benchmark_report(all_results: List[List[ThroughputMetrics]], report_filename: str):
    """Generate a comprehensive benchmark report."""
    print(f"\n=== Generating Benchmark Report: {report_filename} ===")

    # Flatten all results
    flattened_results = []
    for result_group in all_results:
        flattened_results.extend(result_group)

    # Create report data
    report = {
        "benchmark_summary": {
            "total_tests": len(flattened_results),
            "timestamp": datetime.now().isoformat(),
            "total_requests": sum(r.total_requests for r in flattened_results),
            "total_successful": sum(r.successful_requests for r in flattened_results),
            "overall_success_rate": sum(r.successful_requests for r in flattened_results) /
                                  sum(r.total_requests for r in flattened_results) * 100
        },
        "test_results": [result.to_dict() for result in flattened_results],
        "performance_analysis": {}
    }

    # Performance analysis
    if flattened_results:
        rps_values = [r.requests_per_second for r in flattened_results]
        response_times = [r.avg_response_time for r in flattened_results]

        report["performance_analysis"] = {
            "max_throughput": max(rps_values),
            "min_throughput": min(rps_values),
            "avg_throughput": statistics.mean(rps_values),
            "fastest_avg_response": min(response_times),
            "slowest_avg_response": max(response_times),
            "avg_response_time": statistics.mean(response_times)
        }

    # Save report
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report_filename}")

    # Print summary
    print(f"\nBenchmark Summary:")
    print(f"  Total Tests: {report['benchmark_summary']['total_tests']}")
    print(f"  Total Requests: {report['benchmark_summary']['total_requests']}")
    print(f"  Overall Success Rate: {report['benchmark_summary']['overall_success_rate']:.2f}%")

    if "performance_analysis" in report and report["performance_analysis"]:
        pa = report["performance_analysis"]
        print(f"  Max Throughput: {pa['max_throughput']:.2f} RPS")
        print(f"  Avg Throughput: {pa['avg_throughput']:.2f} RPS")
        print(f"  Fastest Response: {pa['fastest_avg_response']:.3f}s")
        print(f"  Avg Response Time: {pa['avg_response_time']:.3f}s")


async def main():
    """Main function to run all throughput benchmarks."""
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during benchmarking
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Throughput Benchmark Suite")
    print("=" * 60)
    print("This benchmark will test throughput under various conditions.")
    print("Each test includes a warmup period and sustained load measurement.")
    print("=" * 60)

    all_results = []

    try:
        # Run all benchmark suites
        print("\n🚀 Starting throughput benchmarks...")

        # Concurrency benchmark
        concurrency_results = await benchmark_different_concurrency_levels()
        all_results.append(concurrency_results)

        # Rate limiting benchmark
        rate_limit_results = await benchmark_rate_limiting_effects()
        all_results.append(rate_limit_results)

        # Challenge solving impact
        challenge_results = await benchmark_challenge_solving_impact()
        all_results.append(challenge_results)

        # Sustained load test
        sustained_results = await benchmark_sustained_load()
        all_results.append(sustained_results)

        # Generate comprehensive report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"throughput_benchmark_{timestamp}.json"
        generate_benchmark_report(all_results, report_filename)

        print(f"\n{'='*60}")
        print("🎯 All throughput benchmarks completed successfully!")
        print(f"📊 Detailed results saved to: {report_filename}")
        print(f"{'='*60}")

        print("\nKey Insights:")
        print("• Monitor requests per second (RPS) for performance")
        print("• Higher concurrency generally improves throughput")
        print("• Rate limiting helps control resource usage")
        print("• Challenge solving reduces throughput but enables access")
        print("• Sustained load testing reveals stability characteristics")

        print("\nNext Steps:")
        print("• Analyze the detailed JSON report for trends")
        print("• Test with your specific target URLs")
        print("• Adjust configurations based on results")
        print("• Run memory_usage.py to analyze resource consumption")
        print("• Use stress_test.py for extreme load scenarios")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the throughput benchmarks
    asyncio.run(main())