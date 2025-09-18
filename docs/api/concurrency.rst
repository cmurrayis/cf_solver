Concurrency Management
======================

The concurrency module provides advanced concurrency control, rate limiting, and performance monitoring for high-scale operations.

.. currentmodule:: cloudflare_research.concurrency

Concurrency Manager
-------------------

.. automodule:: cloudflare_research.concurrency.manager
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ConcurrencyManager
   :members:
   :undoc-members:
   :show-inheritance:

   Manages concurrent request execution with intelligent throttling.

.. automethod:: ConcurrencyManager.execute_concurrent
.. automethod:: ConcurrencyManager.add_task
.. automethod:: ConcurrencyManager.wait_for_completion
.. automethod:: ConcurrencyManager.get_statistics

Rate Limiting
-------------

.. automodule:: cloudflare_research.concurrency.rate_limiter
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: RateLimiter
   :members:
   :undoc-members:
   :show-inheritance:

   Implements adaptive rate limiting to prevent overwhelming target servers.

.. automethod:: RateLimiter.acquire
.. automethod:: RateLimiter.release
.. automethod:: RateLimiter.adjust_rate
.. automethod:: RateLimiter.get_current_rate

Performance Monitoring
----------------------

.. automodule:: cloudflare_research.concurrency.monitor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: PerformanceMonitor
   :members:
   :undoc-members:
   :show-inheritance:

   Monitors performance metrics and provides optimization recommendations.

.. automethod:: PerformanceMonitor.record_request
.. automethod:: PerformanceMonitor.get_metrics
.. automethod:: PerformanceMonitor.get_recommendations
.. automethod:: PerformanceMonitor.export_metrics

Task Management
---------------

.. autoclass:: Task
   :members:
   :undoc-members:
   :show-inheritance:

   Represents a single concurrent task with metadata and execution tracking.

.. autoclass:: TaskResult
   :members:
   :undoc-members:
   :show-inheritance:

   Contains the result of a completed task including performance metrics.

.. autoclass:: TaskQueue
   :members:
   :undoc-members:
   :show-inheritance:

   Manages a queue of tasks with priority and scheduling support.

Configuration
-------------

.. autoclass:: ConcurrencyConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration options for concurrency behavior.

.. autoclass:: RateLimitConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration for rate limiting behavior.

Error Handling
--------------

.. autoclass:: ConcurrencyError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: RateLimitExceeded
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TaskTimeout
   :members:
   :undoc-members:
   :show-inheritance:

Example Usage
-------------

Basic Concurrency Control::

    config = ConcurrencyConfig(
        max_concurrent_requests=100,
        max_requests_per_second=10.0
    )

    manager = ConcurrencyManager(config)

    # Add tasks to execute
    urls = ["https://example.com/1", "https://example.com/2"]
    for url in urls:
        task = Task(url=url, method="GET")
        manager.add_task(task)

    # Execute all tasks concurrently
    results = await manager.execute_concurrent()

    print(f"Completed {len(results)} requests")

Rate Limiting::

    rate_limiter = RateLimiter(requests_per_second=5.0)

    for i in range(20):
        async with rate_limiter:
            # This will automatically rate limit to 5 requests per second
            response = await client.get(f"https://example.com/{i}")

Adaptive Rate Limiting::

    rate_limiter = RateLimiter(
        initial_rate=10.0,
        adaptive=True,
        backoff_factor=0.5
    )

    for url in urls:
        try:
            async with rate_limiter:
                response = await client.get(url)
                if response.status_code == 429:  # Rate limited
                    rate_limiter.adjust_rate(0.5)  # Reduce rate by 50%
        except Exception as e:
            rate_limiter.adjust_rate(0.8)  # Reduce rate on errors

Performance Monitoring::

    monitor = PerformanceMonitor()

    async def make_request(url):
        start_time = time.time()
        try:
            response = await client.get(url)
            success = response.status_code < 400
        except Exception:
            success = False

        elapsed = time.time() - start_time
        monitor.record_request(url, elapsed, success)
        return response

    # Make requests and collect metrics
    await asyncio.gather(*[make_request(url) for url in urls])

    # Get performance metrics
    metrics = monitor.get_metrics()
    print(f"Success rate: {metrics.success_rate:.2%}")
    print(f"Average response time: {metrics.avg_response_time:.3f}s")

    # Get optimization recommendations
    recommendations = monitor.get_recommendations()
    for rec in recommendations:
        print(f"Recommendation: {rec}")

High-Scale Execution::

    config = ConcurrencyConfig(
        max_concurrent_requests=1000,
        max_requests_per_second=50.0,
        enable_monitoring=True,
        adaptive_rate_limiting=True
    )

    manager = ConcurrencyManager(config)
    monitor = PerformanceMonitor()

    # Generate large number of tasks
    tasks = []
    for i in range(10000):
        task = Task(
            url=f"https://example.com/item/{i}",
            method="GET",
            priority=1 if i < 1000 else 2  # High priority for first 1000
        )
        tasks.append(task)

    # Execute with automatic scaling
    results = await manager.execute_concurrent(tasks)

    # Analyze results
    successful = sum(1 for r in results if r.success)
    print(f"Success rate: {successful/len(results):.2%}")

    # Export metrics for analysis
    metrics_data = monitor.export_metrics("json")
    with open("performance_metrics.json", "w") as f:
        f.write(metrics_data)

.. seealso::
   :doc:`../user_guide/configuration` for detailed concurrency configuration options.