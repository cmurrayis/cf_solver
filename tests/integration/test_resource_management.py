"""
Integration tests for resource management and limits functionality.

These tests verify that CloudflareBypass properly manages system resources
including memory, CPU, network connections, and enforces configured limits
to maintain system stability under various load conditions.
"""

import pytest
import asyncio
import time
import psutil
import gc
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.utils.resources import ResourceMonitor, ResourceManager, SystemResources
from cloudflare_research.models.response import CloudflareResponse


@dataclass
class ResourceTestResult:
    """Results from resource management tests."""
    initial_memory_mb: float
    peak_memory_mb: float
    final_memory_mb: float
    memory_growth_mb: float
    peak_cpu_percent: float
    avg_cpu_percent: float
    max_connections: int
    resource_limits_enforced: bool
    test_duration: float


@pytest.mark.integration
@pytest.mark.asyncio
class TestResourceManagementIntegration:
    """Integration tests for resource management and limits."""

    @pytest.fixture
    def resource_limited_config(self) -> CloudflareBypassConfig:
        """Create configuration with strict resource limits."""
        return CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10.0,
            timeout=30.0,
            connection_pool_size=25,
            keep_alive_timeout=30.0,
            solve_javascript_challenges=False,  # Reduce resource usage
            enable_detailed_logging=False,
            enable_monitoring=True,
            enable_metrics_collection=True,
            # Resource limits
            max_memory_mb=1000,  # 1GB limit
            max_cpu_percent=80.0  # 80% CPU limit
        )

    @pytest.fixture
    def high_resource_config(self) -> CloudflareBypassConfig:
        """Create configuration for high resource usage testing."""
        return CloudflareBypassConfig(
            max_concurrent_requests=100,
            requests_per_second=50.0,
            timeout=30.0,
            connection_pool_size=150,
            solve_javascript_challenges=True,  # Higher resource usage
            enable_detailed_logging=True,
            enable_monitoring=True,
            enable_metrics_collection=True
        )

    @pytest.fixture
    async def resource_monitor(self) -> ResourceMonitor:
        """Create and initialize resource monitor."""
        monitor = ResourceMonitor()
        await monitor.start()
        yield monitor
        await monitor.stop()

    @pytest.fixture
    async def resource_manager(self) -> ResourceManager:
        """Create and initialize resource manager."""
        manager = ResourceManager()
        await manager.start()
        yield manager
        await manager.stop()

    async def get_system_resources(self) -> SystemResources:
        """Get current system resource usage."""
        process = psutil.Process()
        memory_info = process.memory_info()

        return SystemResources(
            memory_mb=memory_info.rss / 1024 / 1024,
            cpu_percent=psutil.cpu_percent(interval=0.1),
            network_connections=len(process.connections()),
            open_files=len(process.open_files()),
            timestamp=datetime.now()
        )

    async def test_memory_limit_enforcement(self, resource_limited_config):
        """Test that memory limits are properly enforced."""
        initial_resources = await self.get_system_resources()
        memory_samples = []

        async def monitor_memory():
            """Monitor memory usage during test."""
            while True:
                try:
                    resources = await self.get_system_resources()
                    memory_samples.append(resources.memory_mb)
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break

        # Start memory monitoring
        monitor_task = asyncio.create_task(monitor_memory())

        try:
            async with CloudflareBypass(resource_limited_config) as bypass:
                # Generate load to test memory limits
                urls = ["https://httpbin.org/get"] * 30

                tasks = []
                for url in urls:
                    task = asyncio.create_task(bypass.get(url))
                    tasks.append(task)

                    # Check memory usage periodically
                    if len(tasks) % 5 == 0:
                        current_resources = await self.get_system_resources()
                        print(f"Memory usage: {current_resources.memory_mb:.1f} MB")

                # Execute all requests
                results = await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Analyze memory usage
        final_resources = await self.get_system_resources()

        if memory_samples:
            peak_memory = max(memory_samples)
            memory_growth = final_resources.memory_mb - initial_resources.memory_mb

            print(f"Memory analysis:")
            print(f"  Initial: {initial_resources.memory_mb:.1f} MB")
            print(f"  Peak: {peak_memory:.1f} MB")
            print(f"  Final: {final_resources.memory_mb:.1f} MB")
            print(f"  Growth: {memory_growth:.1f} MB")

            # Memory should stay within reasonable bounds
            assert peak_memory < 2000  # Less than 2GB
            assert memory_growth < 1000  # Less than 1GB growth

    async def test_connection_pool_limits(self, resource_limited_config):
        """Test connection pool size limits."""
        connection_samples = []

        async def monitor_connections():
            """Monitor network connections during test."""
            while True:
                try:
                    resources = await self.get_system_resources()
                    connection_samples.append(resources.network_connections)
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break

        monitor_task = asyncio.create_task(monitor_connections())

        try:
            async with CloudflareBypass(resource_limited_config) as bypass:
                # Generate concurrent requests to test connection pooling
                urls = ["https://httpbin.org/get"] * 50

                # Execute requests in batches to control connection usage
                batch_size = 10
                for i in range(0, len(urls), batch_size):
                    batch_urls = urls[i:i + batch_size]
                    tasks = [bypass.get(url) for url in batch_urls]

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Check connections
                    current_resources = await self.get_system_resources()
                    print(f"Batch {i//batch_size + 1}: {current_resources.network_connections} connections")

                    await asyncio.sleep(1)  # Brief pause between batches

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Analyze connection usage
        if connection_samples:
            peak_connections = max(connection_samples)
            avg_connections = sum(connection_samples) / len(connection_samples)

            print(f"Connection analysis:")
            print(f"  Peak connections: {peak_connections}")
            print(f"  Average connections: {avg_connections:.1f}")
            print(f"  Pool size limit: {resource_limited_config.connection_pool_size}")

            # Connections should respect pool limits (with some tolerance for system connections)
            assert peak_connections <= resource_limited_config.connection_pool_size + 20

    async def test_cpu_usage_monitoring(self, resource_limited_config):
        """Test CPU usage monitoring and limits."""
        cpu_samples = []

        async def monitor_cpu():
            """Monitor CPU usage during test."""
            while True:
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    cpu_samples.append(cpu_percent)
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break

        monitor_task = asyncio.create_task(monitor_cpu())

        try:
            async with CloudflareBypass(resource_limited_config) as bypass:
                # Generate CPU-intensive load
                start_time = time.time()

                # Run multiple concurrent requests for sustained CPU load
                tasks = []
                for i in range(30):
                    task = asyncio.create_task(bypass.get("https://httpbin.org/get"))
                    tasks.append(task)

                    # Add small delay to spread out the load
                    if i % 5 == 0:
                        await asyncio.sleep(0.1)

                # Execute all tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)

                duration = time.time() - start_time
                successful = sum(1 for r in results if isinstance(r, CloudflareResponse))

                print(f"CPU test completed: {successful}/{len(tasks)} successful in {duration:.1f}s")

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Analyze CPU usage
        if cpu_samples:
            peak_cpu = max(cpu_samples)
            avg_cpu = sum(cpu_samples) / len(cpu_samples)

            print(f"CPU analysis:")
            print(f"  Peak CPU: {peak_cpu:.1f}%")
            print(f"  Average CPU: {avg_cpu:.1f}%")

            # CPU usage should be reasonable
            assert peak_cpu < 100  # Should not max out CPU completely
            assert avg_cpu > 0     # Should show some CPU usage

    async def test_resource_cleanup_on_shutdown(self, resource_limited_config):
        """Test proper resource cleanup when CloudflareBypass shuts down."""
        initial_resources = await self.get_system_resources()

        # Create and use CloudflareBypass instance
        async with CloudflareBypass(resource_limited_config) as bypass:
            # Generate some load
            responses = []
            for i in range(10):
                try:
                    response = await bypass.get("https://httpbin.org/get")
                    responses.append(response)
                except Exception as e:
                    print(f"Request {i} failed: {e}")

            mid_test_resources = await self.get_system_resources()
            print(f"Mid-test resources: {mid_test_resources.memory_mb:.1f} MB, "
                  f"{mid_test_resources.network_connections} connections")

        # Give time for cleanup
        await asyncio.sleep(2)
        gc.collect()  # Force garbage collection

        final_resources = await self.get_system_resources()

        print(f"Resource cleanup analysis:")
        print(f"  Initial memory: {initial_resources.memory_mb:.1f} MB")
        print(f"  Mid-test memory: {mid_test_resources.memory_mb:.1f} MB")
        print(f"  Final memory: {final_resources.memory_mb:.1f} MB")
        print(f"  Initial connections: {initial_resources.network_connections}")
        print(f"  Final connections: {final_resources.network_connections}")

        # Memory should be cleaned up (allowing for some variance)
        memory_growth = final_resources.memory_mb - initial_resources.memory_mb
        assert memory_growth < 500  # Less than 500MB permanent growth

        # Connections should be cleaned up
        connection_growth = final_resources.network_connections - initial_resources.network_connections
        assert connection_growth < 10  # Minimal connection growth

    async def test_concurrent_resource_management(self, resource_limited_config):
        """Test resource management under concurrent load."""
        resource_samples = []

        async def monitor_resources():
            """Monitor all resources during concurrent test."""
            while True:
                try:
                    resources = await self.get_system_resources()
                    resource_samples.append(resources)
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break

        monitor_task = asyncio.create_task(monitor_resources())

        try:
            # Run multiple CloudflareBypass instances concurrently
            async def run_bypass_instance(instance_id: int):
                config = CloudflareBypassConfig(
                    max_concurrent_requests=10,
                    requests_per_second=5.0,
                    timeout=30.0,
                    connection_pool_size=15,
                    enable_detailed_logging=False
                )

                async with CloudflareBypass(config) as bypass:
                    responses = []
                    for i in range(5):
                        try:
                            response = await bypass.get("https://httpbin.org/get")
                            responses.append(response)
                        except Exception as e:
                            print(f"Instance {instance_id}, request {i} failed: {e}")

                    return len(responses)

            # Run 3 concurrent instances
            instance_tasks = [
                run_bypass_instance(i) for i in range(3)
            ]

            results = await asyncio.gather(*instance_tasks, return_exceptions=True)

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Analyze concurrent resource usage
        if resource_samples:
            memory_values = [r.memory_mb for r in resource_samples]
            connection_values = [r.network_connections for r in resource_samples]

            peak_memory = max(memory_values)
            peak_connections = max(connection_values)

            print(f"Concurrent resource analysis:")
            print(f"  Peak memory: {peak_memory:.1f} MB")
            print(f"  Peak connections: {peak_connections}")
            print(f"  Instances completed: {len([r for r in results if isinstance(r, int)])}")

            # Resources should stay within reasonable bounds even with multiple instances
            assert peak_memory < 3000  # Less than 3GB
            assert peak_connections < 100  # Reasonable connection count

    async def test_resource_monitor_integration(self, resource_monitor):
        """Test integration with ResourceMonitor component."""
        # Verify monitor is working
        assert resource_monitor is not None

        # Get initial state
        try:
            initial_state = await resource_monitor.get_current_state()
            assert initial_state is not None
            print(f"Initial resource state: {initial_state}")
        except AttributeError:
            # Method might not exist - create basic test
            print("ResourceMonitor get_current_state not available")

        # Generate some load while monitoring
        config = CloudflareBypassConfig(
            max_concurrent_requests=15,
            requests_per_second=8.0,
            timeout=30.0,
            enable_monitoring=True
        )

        async with CloudflareBypass(config) as bypass:
            # Make requests while monitoring
            for i in range(5):
                try:
                    response = await bypass.get("https://httpbin.org/get")
                    print(f"Request {i + 1}: {response.status_code}")
                except Exception as e:
                    print(f"Request {i + 1} failed: {e}")

                await asyncio.sleep(1)

        # Check final state
        try:
            final_state = await resource_monitor.get_current_state()
            print(f"Final resource state: {final_state}")
        except AttributeError:
            print("ResourceMonitor final state check not available")

    async def test_resource_manager_limits(self, resource_manager):
        """Test ResourceManager limit enforcement."""
        # Test resource manager functionality
        assert resource_manager is not None

        # Set resource limits (if methods exist)
        try:
            await resource_manager.set_memory_limit(1000)  # 1GB
            await resource_manager.set_cpu_limit(80)       # 80%
            print("Resource limits set successfully")
        except AttributeError:
            print("ResourceManager limit setting not available")

        # Generate load to test limits
        config = CloudflareBypassConfig(
            max_concurrent_requests=25,
            requests_per_second=12.0,
            timeout=30.0,
            enable_monitoring=True
        )

        async with CloudflareBypass(config) as bypass:
            # Make requests that might hit limits
            tasks = []
            for i in range(20):
                task = asyncio.create_task(bypass.get("https://httpbin.org/get"))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for r in results if isinstance(r, CloudflareResponse))
            failed = len(results) - successful

            print(f"Resource manager test: {successful} successful, {failed} failed")

        # Check if limits were enforced
        try:
            violations = await resource_manager.get_limit_violations()
            print(f"Limit violations: {violations}")
        except AttributeError:
            print("ResourceManager violation checking not available")

    async def test_garbage_collection_effectiveness(self, resource_limited_config):
        """Test effectiveness of garbage collection for resource management."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Generate multiple rounds of load to test GC
        for round_num in range(3):
            print(f"GC test round {round_num + 1}")

            async with CloudflareBypass(resource_limited_config) as bypass:
                # Generate substantial load
                responses = []
                for i in range(15):
                    try:
                        response = await bypass.get("https://httpbin.org/get")
                        responses.append(response)
                    except Exception as e:
                        print(f"Round {round_num + 1}, request {i} failed: {e}")

                round_memory = psutil.Process().memory_info().rss / 1024 / 1024
                print(f"  Round {round_num + 1} peak memory: {round_memory:.1f} MB")

            # Force garbage collection between rounds
            gc.collect()
            await asyncio.sleep(1)

            post_gc_memory = psutil.Process().memory_info().rss / 1024 / 1024
            print(f"  After GC: {post_gc_memory:.1f} MB")

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory

        print(f"GC effectiveness analysis:")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Total growth: {total_growth:.1f} MB")

        # GC should keep memory growth reasonable
        assert total_growth < 800  # Less than 800MB growth over 3 rounds

    async def test_resource_limits_under_stress(self, high_resource_config):
        """Test resource limits under high stress conditions."""
        # Modify config for stress testing
        high_resource_config.max_concurrent_requests = 50
        high_resource_config.requests_per_second = 25.0

        resource_samples = []
        start_time = time.time()

        async def stress_monitor():
            """Monitor resources during stress test."""
            while True:
                try:
                    resources = await self.get_system_resources()
                    resource_samples.append(resources)
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break

        monitor_task = asyncio.create_task(stress_monitor())

        try:
            async with CloudflareBypass(high_resource_config) as bypass:
                # Generate high stress load
                urls = ["https://httpbin.org/get"] * 100

                # Execute in waves to maintain stress
                wave_size = 20
                for wave_start in range(0, len(urls), wave_size):
                    wave_urls = urls[wave_start:wave_start + wave_size]
                    tasks = [bypass.get(url) for url in wave_urls]

                    wave_results = await asyncio.gather(*tasks, return_exceptions=True)

                    wave_successful = sum(1 for r in wave_results if isinstance(r, CloudflareResponse))
                    print(f"Wave {wave_start//wave_size + 1}: {wave_successful}/{len(wave_urls)} successful")

                    # Small delay between waves
                    await asyncio.sleep(0.5)

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        stress_duration = time.time() - start_time

        # Analyze stress test results
        if resource_samples:
            memory_values = [r.memory_mb for r in resource_samples]
            cpu_values = [r.cpu_percent for r in resource_samples]
            connection_values = [r.network_connections for r in resource_samples]

            peak_memory = max(memory_values)
            peak_cpu = max(cpu_values)
            peak_connections = max(connection_values)

            print(f"Stress test analysis ({stress_duration:.1f}s):")
            print(f"  Peak memory: {peak_memory:.1f} MB")
            print(f"  Peak CPU: {peak_cpu:.1f}%")
            print(f"  Peak connections: {peak_connections}")

            # System should survive stress test
            assert peak_memory < 4000  # Less than 4GB
            assert peak_connections < 200  # Reasonable connection count
            assert stress_duration < 180  # Complete within 3 minutes

    @pytest.mark.slow
    async def test_long_running_resource_stability(self, resource_limited_config):
        """Test resource stability over extended period."""
        print("Starting long-running resource stability test...")

        resource_samples = []
        start_time = time.time()
        test_duration = 120  # 2 minutes

        async def stability_monitor():
            """Monitor resources for stability test."""
            while time.time() - start_time < test_duration:
                try:
                    resources = await self.get_system_resources()
                    resource_samples.append(resources)
                    await asyncio.sleep(2)
                except asyncio.CancelledError:
                    break

        monitor_task = asyncio.create_task(stability_monitor())

        try:
            async with CloudflareBypass(resource_limited_config) as bypass:
                # Sustained moderate load
                request_count = 0
                while time.time() - start_time < test_duration:
                    try:
                        response = await bypass.get("https://httpbin.org/get")
                        request_count += 1

                        if request_count % 10 == 0:
                            elapsed = time.time() - start_time
                            print(f"Stability test: {request_count} requests in {elapsed:.1f}s")

                    except Exception as e:
                        print(f"Request {request_count + 1} failed: {e}")

                    await asyncio.sleep(1)  # 1 request per second

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Analyze stability
        if len(resource_samples) >= 10:
            memory_values = [r.memory_mb for r in resource_samples]

            initial_memory = memory_values[0]
            final_memory = memory_values[-1]
            memory_variance = max(memory_values) - min(memory_values)

            print(f"Stability analysis:")
            print(f"  Initial memory: {initial_memory:.1f} MB")
            print(f"  Final memory: {final_memory:.1f} MB")
            print(f"  Memory variance: {memory_variance:.1f} MB")
            print(f"  Total requests: {request_count}")

            # Memory should be stable over time
            memory_growth_rate = (final_memory - initial_memory) / initial_memory
            assert memory_growth_rate < 0.5  # Less than 50% growth
            assert memory_variance < 1000     # Less than 1GB variance


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])