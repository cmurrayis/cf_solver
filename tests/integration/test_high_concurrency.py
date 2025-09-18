"""
Integration tests for high-concurrency load testing functionality.

These tests verify that CloudflareBypass can handle high-concurrency scenarios
with proper resource management, rate limiting, and system stability under load.
"""

import pytest
import asyncio
import time
import statistics
import psutil
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.models.response import CloudflareResponse


@dataclass
class LoadTestResult:
    """Results from a load test."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration: float
    requests_per_second: float
    avg_response_time: float
    p95_response_time: float
    peak_memory_mb: float
    error_rate: float


@pytest.mark.integration
@pytest.mark.asyncio
class TestHighConcurrencyIntegration:
    """Integration tests for high-concurrency load testing."""

    @pytest.fixture
    def high_concurrency_config(self) -> CloudflareBypassConfig:
        """Create configuration for high-concurrency testing."""
        return CloudflareBypassConfig(
            max_concurrent_requests=100,
            requests_per_second=50.0,
            timeout=30.0,
            connection_pool_size=150,
            solve_javascript_challenges=False,  # Disabled for performance
            enable_detailed_logging=False,
            enable_monitoring=True,
            enable_metrics_collection=True
        )

    @pytest.fixture
    def moderate_concurrency_config(self) -> CloudflareBypassConfig:
        """Create configuration for moderate concurrency testing."""
        return CloudflareBypassConfig(
            max_concurrent_requests=25,
            requests_per_second=20.0,
            timeout=30.0,
            connection_pool_size=50,
            solve_javascript_challenges=False,
            enable_detailed_logging=False,
            enable_monitoring=True
        )

    @pytest.fixture
    def test_urls(self) -> List[str]:
        """Provide test URLs for load testing."""
        return [
            "https://httpbin.org/get",
            "https://httpbin.org/status/200",
            "https://httpbin.org/headers",
            "https://httpbin.org/json",
            "https://httpbin.org/user-agent"
        ]

    async def run_load_test(
        self,
        config: CloudflareBypassConfig,
        test_url: str,
        num_requests: int
    ) -> LoadTestResult:
        """Run a load test and return results."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        successful_requests = 0
        failed_requests = 0
        response_times = []
        peak_memory = start_memory

        async with CloudflareBypass(config) as bypass:
            async def make_request():
                """Make a single request and track metrics."""
                nonlocal successful_requests, failed_requests, peak_memory

                request_start = time.time()
                try:
                    response = await bypass.get(test_url)
                    request_time = time.time() - request_start

                    if response.status_code == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1

                    response_times.append(request_time)

                    # Track memory usage
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, current_memory)

                except Exception as e:
                    failed_requests += 1
                    request_time = time.time() - request_start
                    response_times.append(request_time)

            # Create and execute all requests
            tasks = [make_request() for _ in range(num_requests)]
            await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start_time
        total_requests = successful_requests + failed_requests

        # Calculate metrics
        requests_per_second = total_requests / duration if duration > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0

        # Calculate 95th percentile
        if response_times:
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
        else:
            p95_response_time = 0

        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        return LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            duration=duration,
            requests_per_second=requests_per_second,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            peak_memory_mb=peak_memory,
            error_rate=error_rate
        )

    async def test_moderate_concurrency_load(self, moderate_concurrency_config):
        """Test moderate concurrency load (25 concurrent requests)."""
        result = await self.run_load_test(
            moderate_concurrency_config,
            "https://httpbin.org/get",
            50  # 50 total requests
        )

        # Assertions for moderate load
        assert result.total_requests == 50
        assert result.error_rate < 10.0  # Less than 10% errors
        assert result.avg_response_time < 10.0  # Less than 10 seconds average
        assert result.requests_per_second > 1.0  # At least 1 RPS
        assert result.peak_memory_mb < 1000  # Less than 1GB memory usage

    async def test_high_concurrency_load(self, high_concurrency_config):
        """Test high concurrency load (100 concurrent requests)."""
        result = await self.run_load_test(
            high_concurrency_config,
            "https://httpbin.org/get",
            200  # 200 total requests
        )

        # Assertions for high load
        assert result.total_requests == 200
        assert result.error_rate < 20.0  # Less than 20% errors under high load
        assert result.avg_response_time < 15.0  # Less than 15 seconds average
        assert result.requests_per_second > 2.0  # At least 2 RPS
        assert result.peak_memory_mb < 2000  # Less than 2GB memory usage

    @pytest.mark.slow
    async def test_sustained_high_concurrency(self, high_concurrency_config):
        """Test sustained high concurrency over longer period."""
        # Run multiple batches to simulate sustained load
        results = []

        for batch in range(3):  # 3 batches
            print(f"Running batch {batch + 1}/3...")

            result = await self.run_load_test(
                high_concurrency_config,
                "https://httpbin.org/get",
                100  # 100 requests per batch
            )
            results.append(result)

            # Small delay between batches
            await asyncio.sleep(5)

        # Analyze sustained performance
        total_requests = sum(r.total_requests for r in results)
        total_successful = sum(r.successful_requests for r in results)
        avg_rps = statistics.mean(r.requests_per_second for r in results)
        avg_response_time = statistics.mean(r.avg_response_time for r in results)
        max_memory = max(r.peak_memory_mb for r in results)

        # Sustained load assertions
        assert total_requests == 300  # 3 batches × 100 requests
        assert (total_successful / total_requests) > 0.8  # 80% overall success rate
        assert avg_rps > 2.0  # Sustained 2+ RPS
        assert avg_response_time < 20.0  # Reasonable response times
        assert max_memory < 3000  # Memory doesn't grow excessively

    async def test_concurrency_scaling(self, test_urls):
        """Test performance scaling with different concurrency levels."""
        concurrency_levels = [5, 15, 25, 50]
        results = {}

        for concurrency in concurrency_levels:
            config = CloudflareBypassConfig(
                max_concurrent_requests=concurrency,
                requests_per_second=concurrency * 2,  # Scale rate with concurrency
                timeout=30.0,
                solve_javascript_challenges=False,
                enable_detailed_logging=False
            )

            result = await self.run_load_test(
                config,
                "https://httpbin.org/get",
                concurrency * 2  # 2 requests per concurrent connection
            )

            results[concurrency] = result
            print(f"Concurrency {concurrency}: {result.requests_per_second:.2f} RPS, "
                  f"{result.error_rate:.1f}% errors")

        # Verify scaling characteristics
        assert len(results) == len(concurrency_levels)

        # Higher concurrency should generally achieve higher RPS (up to a point)
        low_concurrency_rps = results[5].requests_per_second
        high_concurrency_rps = results[25].requests_per_second

        # Some improvement expected, but not necessarily linear
        assert high_concurrency_rps >= low_concurrency_rps * 0.8

    async def test_rate_limiting_effectiveness(self):
        """Test that rate limiting works effectively under load."""
        target_rps = 10.0
        config = CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=target_rps,
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        # Run for specific duration to test rate limiting
        start_time = time.time()
        requests_made = 0

        async with CloudflareBypass(config) as bypass:
            # Make requests for 10 seconds
            end_time = start_time + 10

            async def make_timed_requests():
                nonlocal requests_made
                while time.time() < end_time:
                    try:
                        await bypass.get("https://httpbin.org/get")
                        requests_made += 1
                    except Exception:
                        pass

            # Run concurrent request makers
            tasks = [make_timed_requests() for _ in range(5)]
            await asyncio.gather(*tasks, return_exceptions=True)

        actual_duration = time.time() - start_time
        actual_rps = requests_made / actual_duration

        # Rate limiting should keep us close to target
        # Allow some variance due to timing and overhead
        assert actual_rps <= target_rps * 1.5  # Not more than 50% over target
        assert actual_rps >= target_rps * 0.5  # Not less than 50% under target

    async def test_connection_pool_efficiency(self):
        """Test connection pool efficiency under high load."""
        # Test with different pool sizes
        pool_sizes = [10, 50, 100]
        results = {}

        for pool_size in pool_sizes:
            config = CloudflareBypassConfig(
                max_concurrent_requests=50,
                requests_per_second=25.0,
                connection_pool_size=pool_size,
                timeout=30.0,
                solve_javascript_challenges=False,
                enable_detailed_logging=False
            )

            result = await self.run_load_test(
                config,
                "https://httpbin.org/get",
                100
            )

            results[pool_size] = result
            print(f"Pool size {pool_size}: {result.avg_response_time:.3f}s avg, "
                  f"{result.error_rate:.1f}% errors")

        # Larger pools should generally perform better (to a point)
        assert len(results) == len(pool_sizes)

        # Should see some improvement with larger pools
        small_pool_time = results[10].avg_response_time
        large_pool_time = results[100].avg_response_time

        # Large pool shouldn't be significantly slower
        assert large_pool_time <= small_pool_time * 2.0

    async def test_error_handling_under_load(self):
        """Test error handling behavior under high load."""
        config = CloudflareBypassConfig(
            max_concurrent_requests=30,
            requests_per_second=20.0,
            timeout=5.0,  # Short timeout to induce some timeouts
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        # Mix of good and problematic URLs
        test_urls = [
            "https://httpbin.org/get",           # Should work
            "https://httpbin.org/delay/10",      # Will timeout with 5s timeout
            "https://httpbin.org/status/500",    # Server error
            "https://httpbin.org/get",           # Should work
        ]

        results = []
        async with CloudflareBypass(config) as bypass:
            async def test_url(url):
                try:
                    response = await bypass.get(url)
                    return {"url": url, "success": True, "status": response.status_code}
                except Exception as e:
                    return {"url": url, "success": False, "error": str(e)}

            # Make concurrent requests to different URLs
            tasks = [test_url(url) for url in test_urls * 10]  # 40 total requests
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful

        # Should handle errors gracefully
        assert len(results) == 40
        assert failed > 0  # Some should fail due to timeouts/errors
        assert successful > 0  # Some should succeed

        # System should remain stable despite errors
        error_rate = (failed / len(results)) * 100
        assert error_rate < 80  # Less than 80% errors (some URLs are designed to fail)

    async def test_memory_usage_under_load(self, high_concurrency_config):
        """Test memory usage patterns under high load."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples = []

        async def monitor_memory():
            """Monitor memory usage during the test."""
            for _ in range(20):  # Monitor for duration of test
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                await asyncio.sleep(1)

        # Start memory monitoring
        monitor_task = asyncio.create_task(monitor_memory())

        # Run load test
        result = await self.run_load_test(
            high_concurrency_config,
            "https://httpbin.org/get",
            150
        )

        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Analyze memory usage
        if memory_samples:
            peak_memory = max(memory_samples)
            avg_memory = statistics.mean(memory_samples)
            memory_growth = peak_memory - initial_memory

            # Memory usage assertions
            assert memory_growth < 1000  # Less than 1GB growth
            assert peak_memory < 3000   # Less than 3GB total

            # Memory should be relatively stable (not constantly growing)
            if len(memory_samples) > 10:
                first_half_avg = statistics.mean(memory_samples[:len(memory_samples)//2])
                second_half_avg = statistics.mean(memory_samples[len(memory_samples)//2:])
                growth_rate = (second_half_avg - first_half_avg) / first_half_avg
                assert growth_rate < 0.5  # Less than 50% growth during test

    async def test_concurrent_different_endpoints(self, test_urls):
        """Test concurrent requests to different endpoints."""
        config = CloudflareBypassConfig(
            max_concurrent_requests=25,
            requests_per_second=15.0,
            timeout=30.0,
            solve_javascript_challenges=False,
            enable_detailed_logging=False
        )

        results_by_url = {}

        async with CloudflareBypass(config) as bypass:
            async def test_endpoint(url):
                """Test a specific endpoint multiple times."""
                successes = 0
                failures = 0

                for _ in range(5):  # 5 requests per endpoint
                    try:
                        response = await bypass.get(url)
                        if response.status_code == 200:
                            successes += 1
                        else:
                            failures += 1
                    except Exception:
                        failures += 1

                return {"url": url, "successes": successes, "failures": failures}

            # Test all endpoints concurrently
            tasks = [test_endpoint(url) for url in test_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Organize results by URL
            for result in results:
                if isinstance(result, dict):
                    url = result["url"]
                    results_by_url[url] = result

        # Verify all endpoints were tested
        assert len(results_by_url) == len(test_urls)

        # Each endpoint should have reasonable success rate
        for url, result in results_by_url.items():
            total_requests = result["successes"] + result["failures"]
            success_rate = result["successes"] / total_requests if total_requests > 0 else 0

            print(f"{url}: {result['successes']}/{total_requests} success rate: {success_rate:.2f}")
            assert success_rate >= 0.6  # At least 60% success rate per endpoint

    @pytest.mark.slow
    async def test_load_test_stability(self, moderate_concurrency_config):
        """Test system stability over extended load test."""
        # Run load test for longer duration
        start_time = time.time()
        batch_results = []

        # Run 5 batches of load tests
        for batch in range(5):
            print(f"Running stability batch {batch + 1}/5...")

            result = await self.run_load_test(
                moderate_concurrency_config,
                "https://httpbin.org/get",
                30  # 30 requests per batch
            )

            batch_results.append(result)

            # Short break between batches
            await asyncio.sleep(3)

        total_duration = time.time() - start_time

        # Analyze stability
        total_requests = sum(r.total_requests for r in batch_results)
        total_successful = sum(r.successful_requests for r in batch_results)
        response_times = [r.avg_response_time for r in batch_results]
        error_rates = [r.error_rate for r in batch_results]

        # Stability assertions
        assert total_requests == 150  # 5 batches × 30 requests
        assert (total_successful / total_requests) >= 0.8  # 80% overall success
        assert total_duration < 300  # Complete within 5 minutes

        # Performance should be relatively stable across batches
        if len(response_times) > 1:
            response_time_variance = statistics.stdev(response_times)
            avg_response_time = statistics.mean(response_times)
            coefficient_of_variation = response_time_variance / avg_response_time

            # Response times shouldn't vary too wildly
            assert coefficient_of_variation < 1.0  # Less than 100% variation


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])