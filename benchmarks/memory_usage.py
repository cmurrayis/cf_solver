"""
Memory Usage Benchmark for CloudflareBypass

This benchmark analyzes memory consumption patterns of CloudflareBypass
under various load conditions, tracking memory usage, garbage collection,
connection pooling, and resource efficiency.
"""

import asyncio
import time
import json
import gc
import psutil
import tracemalloc
import statistics
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig


@dataclass
class MemorySnapshot:
    """Single memory measurement snapshot."""
    timestamp: float
    rss_mb: float
    vms_mb: float
    percent: float
    python_memory_mb: float
    active_connections: int
    total_requests: int


@dataclass
class MemoryBenchmarkResult:
    """Complete memory benchmark results."""
    test_name: str
    duration: float
    initial_memory_mb: float
    peak_memory_mb: float
    final_memory_mb: float
    avg_memory_mb: float
    memory_growth_mb: float
    memory_growth_percent: float
    total_requests: int
    requests_per_mb: float
    gc_collections: int
    peak_connections: int
    avg_connections: float
    snapshots: List[MemorySnapshot]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryProfiler:
    """Memory profiling utilities."""

    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.start_time = None
        self.total_requests = 0
        self.active_connections = 0

    def start_profiling(self):
        """Start memory profiling."""
        tracemalloc.start()
        gc.collect()  # Clean start
        self.start_time = time.time()
        self.snapshots.clear()
        self.total_requests = 0

    def take_snapshot(self, active_connections: int = 0, total_requests: int = 0):
        """Take a memory snapshot."""
        if not self.start_time:
            return

        # Get system memory info
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        # Get Python memory usage
        current, peak = tracemalloc.get_traced_memory()
        python_memory_mb = current / 1024 / 1024

        snapshot = MemorySnapshot(
            timestamp=time.time() - self.start_time,
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            python_memory_mb=python_memory_mb,
            active_connections=active_connections,
            total_requests=total_requests
        )

        self.snapshots.append(snapshot)

    def stop_profiling(self) -> List[MemorySnapshot]:
        """Stop profiling and return snapshots."""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        return self.snapshots.copy()


class MemoryBenchmark:
    """Comprehensive memory usage benchmark."""

    def __init__(self):
        self.results: List[MemoryBenchmarkResult] = []

    async def run_memory_test(
        self,
        config: CloudflareBypassConfig,
        test_name: str,
        target_url: str,
        duration_seconds: int,
        snapshot_interval: float = 1.0
    ) -> MemoryBenchmarkResult:
        """
        Run memory usage test for specified duration.

        Args:
            config: CloudflareBypass configuration
            test_name: Name for this test
            target_url: URL to test against
            duration_seconds: How long to run the test
            snapshot_interval: How often to take memory snapshots

        Returns:
            MemoryBenchmarkResult with detailed analysis
        """
        print(f"\n=== Memory Test: {test_name} ===")
        print(f"Duration: {duration_seconds}s")
        print(f"Snapshot interval: {snapshot_interval}s")
        print(f"Target: {target_url}")

        profiler = MemoryProfiler()
        profiler.start_profiling()

        # Take initial snapshot
        profiler.take_snapshot(0, 0)
        initial_memory = profiler.snapshots[0].rss_mb

        total_requests = 0
        active_connections = 0
        gc_collections_start = sum(gc.get_stats()[i]['collections'] for i in range(3))

        try:
            async with CloudflareBypass(config) as bypass:
                start_time = time.time()
                end_time = start_time + duration_seconds
                last_snapshot = start_time

                async def make_requests():
                    """Continuously make requests."""
                    nonlocal total_requests, active_connections

                    while time.time() < end_time:
                        try:
                            active_connections += 1
                            result = await bypass.get(target_url)
                            total_requests += 1
                        except Exception as e:
                            pass  # Continue on errors
                        finally:
                            active_connections -= 1

                        # Respect rate limiting
                        if config.requests_per_second > 0:
                            await asyncio.sleep(1.0 / config.requests_per_second)
                        else:
                            await asyncio.sleep(0.001)

                # Start request generation
                request_task = asyncio.create_task(make_requests())

                # Memory monitoring loop
                while time.time() < end_time:
                    current_time = time.time()

                    if current_time - last_snapshot >= snapshot_interval:
                        profiler.take_snapshot(active_connections, total_requests)
                        last_snapshot = current_time

                        # Print progress
                        latest_snapshot = profiler.snapshots[-1]
                        print(f"  {latest_snapshot.timestamp:.1f}s: "
                              f"Memory {latest_snapshot.rss_mb:.1f}MB, "
                              f"Requests {total_requests}, "
                              f"Connections {active_connections}")

                    await asyncio.sleep(0.1)

                # Clean up
                request_task.cancel()
                try:
                    await request_task
                except asyncio.CancelledError:
                    pass

                # Take final snapshot
                profiler.take_snapshot(active_connections, total_requests)

        except Exception as e:
            print(f"Memory test error: {e}")
            profiler.take_snapshot(active_connections, total_requests)

        # Stop profiling and analyze results
        snapshots = profiler.stop_profiling()
        gc_collections_end = sum(gc.get_stats()[i]['collections'] for i in range(3))

        if not snapshots:
            raise ValueError("No memory snapshots collected")

        # Calculate metrics
        memory_values = [s.rss_mb for s in snapshots]
        initial_memory = memory_values[0]
        peak_memory = max(memory_values)
        final_memory = memory_values[-1]
        avg_memory = statistics.mean(memory_values)
        memory_growth = final_memory - initial_memory
        memory_growth_percent = (memory_growth / initial_memory * 100) if initial_memory > 0 else 0

        connection_values = [s.active_connections for s in snapshots]
        peak_connections = max(connection_values) if connection_values else 0
        avg_connections = statistics.mean(connection_values) if connection_values else 0

        requests_per_mb = total_requests / avg_memory if avg_memory > 0 else 0
        actual_duration = snapshots[-1].timestamp

        result = MemoryBenchmarkResult(
            test_name=test_name,
            duration=actual_duration,
            initial_memory_mb=initial_memory,
            peak_memory_mb=peak_memory,
            final_memory_mb=final_memory,
            avg_memory_mb=avg_memory,
            memory_growth_mb=memory_growth,
            memory_growth_percent=memory_growth_percent,
            total_requests=total_requests,
            requests_per_mb=requests_per_mb,
            gc_collections=gc_collections_end - gc_collections_start,
            peak_connections=peak_connections,
            avg_connections=avg_connections,
            snapshots=snapshots,
            timestamp=datetime.now().isoformat()
        )

        self.results.append(result)

        # Print summary
        print(f"\nMemory Test Results:")
        print(f"  Initial Memory: {initial_memory:.2f} MB")
        print(f"  Peak Memory: {peak_memory:.2f} MB")
        print(f"  Final Memory: {final_memory:.2f} MB")
        print(f"  Memory Growth: {memory_growth:.2f} MB ({memory_growth_percent:.1f}%)")
        print(f"  Avg Memory: {avg_memory:.2f} MB")
        print(f"  Total Requests: {total_requests}")
        print(f"  Requests per MB: {requests_per_mb:.1f}")
        print(f"  GC Collections: {gc_collections_end - gc_collections_start}")
        print(f"  Peak Connections: {peak_connections}")

        return result


async def benchmark_concurrency_memory_impact():
    """Benchmark memory usage with different concurrency levels."""
    print("=== Concurrency Memory Impact Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 60  # 1 minute per test

    concurrency_levels = [1, 5, 10, 25, 50]
    benchmark = MemoryBenchmark()

    for concurrency in concurrency_levels:
        # Force garbage collection before each test
        gc.collect()
        await asyncio.sleep(2)

        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrency,
            requests_per_second=5 * concurrency,  # Scale rate with concurrency
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        test_name = f"Concurrency_{concurrency}"
        await benchmark.run_memory_test(
            config, test_name, target_url, test_duration, snapshot_interval=2.0
        )

        # Cleanup between tests
        await asyncio.sleep(3)

    return benchmark.results


async def benchmark_sustained_load_memory():
    """Benchmark memory usage during sustained load."""
    print("\n=== Sustained Load Memory Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 300  # 5 minutes

    config = CloudflareBypassConfig(
        max_concurrent_requests=25,
        requests_per_second=15,
        timeout=30.0,
        solve_javascript_challenges=False,
        enable_detailed_logging=False,
        enable_monitoring=True
    )

    benchmark = MemoryBenchmark()

    # Force clean start
    gc.collect()
    await asyncio.sleep(3)

    await benchmark.run_memory_test(
        config, "Sustained_Load", target_url, test_duration, snapshot_interval=5.0
    )

    return benchmark.results


async def benchmark_connection_pooling_memory():
    """Benchmark memory usage of connection pooling."""
    print("\n=== Connection Pooling Memory Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 90

    configs = [
        (CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10,
            connection_pool_size=5,  # Small pool
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        ), "Small_Pool_5"),

        (CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10,
            connection_pool_size=50,  # Medium pool
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        ), "Medium_Pool_50"),

        (CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10,
            connection_pool_size=200,  # Large pool
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        ), "Large_Pool_200")
    ]

    benchmark = MemoryBenchmark()

    for config, test_name in configs:
        gc.collect()
        await asyncio.sleep(3)

        await benchmark.run_memory_test(
            config, test_name, target_url, test_duration, snapshot_interval=3.0
        )

        await asyncio.sleep(5)

    return benchmark.results


async def benchmark_challenge_solving_memory():
    """Benchmark memory usage with challenge solving enabled."""
    print("\n=== Challenge Solving Memory Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 120

    configs = [
        (CloudflareBypassConfig(
            max_concurrent_requests=10,
            requests_per_second=5,
            solve_javascript_challenges=False,
            solve_managed_challenges=False,
            solve_turnstile_challenges=False,
            enable_detailed_logging=False
        ), "No_Challenges"),

        (CloudflareBypassConfig(
            max_concurrent_requests=10,
            requests_per_second=5,
            solve_javascript_challenges=True,
            solve_managed_challenges=True,
            solve_turnstile_challenges=True,
            enable_detailed_logging=False
        ), "All_Challenges_Enabled")
    ]

    benchmark = MemoryBenchmark()

    for config, test_name in configs:
        gc.collect()
        await asyncio.sleep(3)

        await benchmark.run_memory_test(
            config, test_name, target_url, test_duration, snapshot_interval=3.0
        )

        await asyncio.sleep(5)

    return benchmark.results


async def benchmark_memory_leak_detection():
    """Long-running test to detect potential memory leaks."""
    print("\n=== Memory Leak Detection Benchmark ===")

    target_url = "https://httpbin.org/get"
    test_duration = 600  # 10 minutes

    config = CloudflareBypassConfig(
        max_concurrent_requests=15,
        requests_per_second=8,
        timeout=30.0,
        solve_javascript_challenges=False,
        enable_detailed_logging=False
    )

    benchmark = MemoryBenchmark()

    # Start with clean memory state
    gc.collect()
    await asyncio.sleep(5)

    await benchmark.run_memory_test(
        config, "Memory_Leak_Detection", target_url, test_duration, snapshot_interval=10.0
    )

    # Analyze for memory leaks
    result = benchmark.results[-1]
    leak_threshold = 50  # MB growth threshold
    growth_rate = result.memory_growth_mb / (result.duration / 60)  # MB per minute

    print(f"\nMemory Leak Analysis:")
    print(f"  Total Growth: {result.memory_growth_mb:.2f} MB")
    print(f"  Growth Rate: {growth_rate:.2f} MB/minute")
    print(f"  Growth Percentage: {result.memory_growth_percent:.1f}%")

    if result.memory_growth_mb > leak_threshold:
        print(f"  ⚠️  Potential memory leak detected (>{leak_threshold}MB growth)")
    else:
        print(f"  ✅ No significant memory leak detected")

    return benchmark.results


def analyze_memory_patterns(results: List[MemoryBenchmarkResult]):
    """Analyze memory usage patterns across all tests."""
    print(f"\n=== Memory Pattern Analysis ===")

    if not results:
        print("No results to analyze")
        return

    # Overall statistics
    total_requests = sum(r.total_requests for r in results)
    avg_memory_efficiency = statistics.mean(r.requests_per_mb for r in results if r.requests_per_mb > 0)
    avg_memory_growth = statistics.mean(r.memory_growth_percent for r in results)

    print(f"Overall Statistics:")
    print(f"  Total Tests: {len(results)}")
    print(f"  Total Requests: {total_requests}")
    print(f"  Avg Memory Efficiency: {avg_memory_efficiency:.1f} requests/MB")
    print(f"  Avg Memory Growth: {avg_memory_growth:.1f}%")

    # Find extremes
    most_efficient = max(results, key=lambda r: r.requests_per_mb)
    least_efficient = min(results, key=lambda r: r.requests_per_mb)
    highest_growth = max(results, key=lambda r: r.memory_growth_percent)
    lowest_growth = min(results, key=lambda r: r.memory_growth_percent)

    print(f"\nMemory Efficiency:")
    print(f"  Most Efficient: {most_efficient.test_name} ({most_efficient.requests_per_mb:.1f} req/MB)")
    print(f"  Least Efficient: {least_efficient.test_name} ({least_efficient.requests_per_mb:.1f} req/MB)")

    print(f"\nMemory Growth:")
    print(f"  Highest Growth: {highest_growth.test_name} ({highest_growth.memory_growth_percent:.1f}%)")
    print(f"  Lowest Growth: {lowest_growth.test_name} ({lowest_growth.memory_growth_percent:.1f}%)")

    # GC Analysis
    total_gc = sum(r.gc_collections for r in results)
    avg_gc_per_test = total_gc / len(results)
    print(f"\nGarbage Collection:")
    print(f"  Total GC Collections: {total_gc}")
    print(f"  Average per Test: {avg_gc_per_test:.1f}")


def generate_memory_report(all_results: List[List[MemoryBenchmarkResult]], report_filename: str):
    """Generate comprehensive memory usage report."""
    print(f"\n=== Generating Memory Report: {report_filename} ===")

    # Flatten results
    flattened_results = []
    for result_group in all_results:
        flattened_results.extend(result_group)

    # Create report
    report = {
        "memory_benchmark_summary": {
            "total_tests": len(flattened_results),
            "timestamp": datetime.now().isoformat(),
            "total_requests": sum(r.total_requests for r in flattened_results),
            "avg_memory_efficiency": statistics.mean(r.requests_per_mb for r in flattened_results if r.requests_per_mb > 0),
            "avg_memory_growth": statistics.mean(r.memory_growth_percent for r in flattened_results),
            "total_gc_collections": sum(r.gc_collections for r in flattened_results)
        },
        "test_results": [result.to_dict() for result in flattened_results],
        "memory_analysis": {}
    }

    # Memory analysis
    if flattened_results:
        memory_growths = [r.memory_growth_percent for r in flattened_results]
        memory_efficiencies = [r.requests_per_mb for r in flattened_results if r.requests_per_mb > 0]

        report["memory_analysis"] = {
            "max_memory_growth": max(memory_growths),
            "min_memory_growth": min(memory_growths),
            "avg_memory_growth": statistics.mean(memory_growths),
            "max_efficiency": max(memory_efficiencies) if memory_efficiencies else 0,
            "min_efficiency": min(memory_efficiencies) if memory_efficiencies else 0,
            "avg_efficiency": statistics.mean(memory_efficiencies) if memory_efficiencies else 0
        }

    # Save report
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Memory report saved to: {report_filename}")

    # Print summary
    summary = report["memory_benchmark_summary"]
    print(f"\nMemory Benchmark Summary:")
    print(f"  Tests: {summary['total_tests']}")
    print(f"  Total Requests: {summary['total_requests']}")
    print(f"  Avg Efficiency: {summary['avg_memory_efficiency']:.1f} req/MB")
    print(f"  Avg Growth: {summary['avg_memory_growth']:.1f}%")
    print(f"  GC Collections: {summary['total_gc_collections']}")


async def main():
    """Main function to run all memory benchmarks."""
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Memory Usage Benchmark Suite")
    print("=" * 65)
    print("This benchmark analyzes memory consumption under various conditions.")
    print("Tests include concurrency, sustained load, connection pooling, and leak detection.")
    print("=" * 65)

    all_results = []

    try:
        # Run all memory benchmarks
        print("\n🧠 Starting memory benchmarks...")

        # Concurrency impact on memory
        concurrency_results = await benchmark_concurrency_memory_impact()
        all_results.append(concurrency_results)

        # Sustained load memory usage
        sustained_results = await benchmark_sustained_load_memory()
        all_results.append(sustained_results)

        # Connection pooling memory impact
        pooling_results = await benchmark_connection_pooling_memory()
        all_results.append(pooling_results)

        # Challenge solving memory impact
        challenge_results = await benchmark_challenge_solving_memory()
        all_results.append(challenge_results)

        # Memory leak detection
        leak_results = await benchmark_memory_leak_detection()
        all_results.append(leak_results)

        # Analyze patterns across all tests
        flattened_results = []
        for result_group in all_results:
            flattened_results.extend(result_group)
        analyze_memory_patterns(flattened_results)

        # Generate comprehensive report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"memory_benchmark_{timestamp}.json"
        generate_memory_report(all_results, report_filename)

        print(f"\n{'='*65}")
        print("🧠 All memory benchmarks completed successfully!")
        print(f"📊 Detailed results saved to: {report_filename}")
        print(f"{'='*65}")

        print("\nMemory Optimization Tips:")
        print("• Monitor memory growth during long-running operations")
        print("• Adjust connection pool size based on memory constraints")
        print("• Consider request rate limits to manage memory usage")
        print("• Regular garbage collection can help with memory efficiency")
        print("• Challenge solving increases memory usage due to JS execution")

        print("\nNext Steps:")
        print("• Review memory patterns in the detailed JSON report")
        print("• Test with your specific usage patterns")
        print("• Monitor for memory leaks in production scenarios")
        print("• Run stress_test.py to test extreme memory conditions")

    except Exception as e:
        print(f"❌ Memory benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the memory benchmarks
    asyncio.run(main())