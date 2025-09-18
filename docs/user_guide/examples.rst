Usage Examples
==============

This guide provides practical examples for using CloudflareBypass Research Tool in various scenarios.

Basic Usage Examples
--------------------

Simple Request
~~~~~~~~~~~~~~

Make a basic request to a Cloudflare-protected site::

    import asyncio
    from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

    async def simple_request():
        config = CloudflareBypassConfig()

        async with CloudflareBypass(config) as bypass:
            response = await bypass.get("https://example.com")

            print(f"Status: {response.status_code}")
            print(f"Success: {response.success}")
            print(f"Cloudflare detected: {response.is_cloudflare_protected()}")

            if response.is_cloudflare_protected():
                cf_ray = response.get_cf_ray()
                print(f"CF-RAY: {cf_ray}")

    asyncio.run(simple_request())

Request with Custom Headers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add custom headers to your requests::

    async def request_with_headers():
        config = CloudflareBypassConfig()

        async with CloudflareBypass(config) as bypass:
            headers = {
                "Authorization": "Bearer your-token",
                "X-Custom-Header": "custom-value"
            }

            response = await bypass.get(
                "https://api.example.com/data",
                headers=headers
            )

            print(f"Response: {response.status_code}")

    asyncio.run(request_with_headers())

POST Request with Data
~~~~~~~~~~~~~~~~~~~~~

Send POST requests with JSON data::

    import json

    async def post_request():
        config = CloudflareBypassConfig()

        async with CloudflareBypass(config) as bypass:
            data = {
                "username": "test_user",
                "action": "research_test"
            }

            response = await bypass.post(
                "https://api.example.com/submit",
                json=data,
                headers={"Content-Type": "application/json"}
            )

            result = await response.json()
            print(f"Response: {result}")

    asyncio.run(post_request())

Concurrent Requests
-------------------

Basic Concurrency
~~~~~~~~~~~~~~~~~

Make multiple concurrent requests::

    async def concurrent_requests():
        config = CloudflareBypassConfig(
            max_concurrent_requests=10
        )

        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://example.com/page4",
            "https://example.com/page5"
        ]

        async with CloudflareBypass(config) as bypass:
            # Create tasks for all URLs
            tasks = [bypass.get(url) for url in urls]

            # Execute concurrently
            responses = await asyncio.gather(*tasks)

            # Process results
            for i, response in enumerate(responses):
                print(f"URL {i+1}: {response.status_code}")

    asyncio.run(concurrent_requests())

High-Concurrency Example
~~~~~~~~~~~~~~~~~~~~~~~~

Handle large numbers of concurrent requests::

    async def high_concurrency_example():
        config = CloudflareBypassConfig(
            max_concurrent_requests=100,
            requests_per_second=20.0
        )

        # Generate many URLs
        urls = [f"https://example.com/item/{i}" for i in range(500)]

        async with CloudflareBypass(config) as bypass:
            successful = 0
            failed = 0

            # Process in batches
            batch_size = 50
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]
                tasks = [bypass.get(url) for url in batch]

                try:
                    responses = await asyncio.gather(*tasks, return_exceptions=True)

                    for response in responses:
                        if isinstance(response, Exception):
                            failed += 1
                        elif response.status_code < 400:
                            successful += 1
                        else:
                            failed += 1

                except Exception as e:
                    print(f"Batch error: {e}")
                    failed += batch_size

                print(f"Processed {i + len(batch)}/{len(urls)} URLs")

            print(f"Results: {successful} successful, {failed} failed")

    asyncio.run(high_concurrency_example())

Challenge Handling Examples
---------------------------

JavaScript Challenge
~~~~~~~~~~~~~~~~~~~~

Handle JavaScript challenges automatically::

    async def javascript_challenge_example():
        config = CloudflareBypassConfig(
            solve_javascript_challenges=True,
            challenge_timeout=30.0
        )

        async with CloudflareBypass(config) as bypass:
            # This URL has JavaScript challenges
            response = await bypass.get("https://protected-site.com")

            if response.success:
                print("JavaScript challenge solved successfully!")
                print(f"Final status: {response.status_code}")
            else:
                print("Failed to solve JavaScript challenge")

    asyncio.run(javascript_challenge_example())

Multiple Challenge Types
~~~~~~~~~~~~~~~~~~~~~~~

Handle various challenge types::

    async def multi_challenge_example():
        config = CloudflareBypassConfig(
            solve_javascript_challenges=True,
            solve_turnstile_challenges=True,
            solve_managed_challenges=True,
            challenge_timeout=45.0
        )

        test_urls = [
            "https://site-with-js-challenge.com",
            "https://site-with-turnstile.com",
            "https://site-with-managed-challenge.com"
        ]

        async with CloudflareBypass(config) as bypass:
            for url in test_urls:
                try:
                    response = await bypass.get(url)

                    print(f"URL: {url}")
                    print(f"Status: {response.status_code}")
                    print(f"Challenge solved: {response.success}")
                    print("---")

                except Exception as e:
                    print(f"Error with {url}: {e}")

    asyncio.run(multi_challenge_example())

Session Management Examples
--------------------------

Persistent Sessions
~~~~~~~~~~~~~~~~~~

Maintain session state across requests::

    async def session_example():
        config = CloudflareBypassConfig(
            session_persistence=True
        )

        async with CloudflareBypass(config) as bypass:
            # First request establishes session
            login_response = await bypass.post(
                "https://example.com/login",
                json={"username": "research", "password": "test"}
            )

            if login_response.status_code == 200:
                print("Login successful")

                # Subsequent requests use the same session
                data_response = await bypass.get("https://example.com/api/user-data")
                print(f"Data request: {data_response.status_code}")

                # Session cookies are automatically maintained
                profile_response = await bypass.get("https://example.com/profile")
                print(f"Profile request: {profile_response.status_code}")

    asyncio.run(session_example())

Multiple Sessions
~~~~~~~~~~~~~~~~

Manage multiple independent sessions::

    from cloudflare_research.session import SessionManager

    async def multi_session_example():
        session_manager = SessionManager()

        # Create sessions for different users
        user_sessions = {}
        for user_id in ["user1", "user2", "user3"]:
            session = await session_manager.create_session(user_id)
            user_sessions[user_id] = session

        # Use different sessions concurrently
        async def user_workflow(user_id, session):
            response = await session.make_request(
                "GET",
                f"https://example.com/user/{user_id}/data"
            )
            return response.status_code

        # Execute workflows concurrently
        tasks = [
            user_workflow(user_id, session)
            for user_id, session in user_sessions.items()
        ]

        results = await asyncio.gather(*tasks)

        for user_id, status in zip(user_sessions.keys(), results):
            print(f"{user_id}: {status}")

        # Clean up sessions
        for user_id in user_sessions:
            await session_manager.close_session(user_id)

    asyncio.run(multi_session_example())

Performance Testing Examples
---------------------------

Load Testing
~~~~~~~~~~~~

Perform load testing on protected endpoints::

    async def load_test_example():
        config = CloudflareBypassConfig(
            max_concurrent_requests=200,
            requests_per_second=50.0,
            enable_monitoring=True
        )

        target_url = "https://your-test-site.com/api/endpoint"
        duration_seconds = 60
        total_requests = 0
        successful_requests = 0

        async with CloudflareBypass(config) as bypass:
            start_time = time.time()

            while time.time() - start_time < duration_seconds:
                # Make batch of requests
                batch_size = 20
                tasks = [bypass.get(target_url) for _ in range(batch_size)]

                try:
                    responses = await asyncio.gather(*tasks, return_exceptions=True)

                    for response in responses:
                        total_requests += 1
                        if not isinstance(response, Exception) and response.status_code < 400:
                            successful_requests += 1

                except Exception as e:
                    print(f"Batch error: {e}")
                    total_requests += batch_size

                # Small delay between batches
                await asyncio.sleep(0.1)

            success_rate = (successful_requests / total_requests) * 100
            rps = total_requests / duration_seconds

            print(f"Load test results:")
            print(f"Duration: {duration_seconds}s")
            print(f"Total requests: {total_requests}")
            print(f"Successful: {successful_requests}")
            print(f"Success rate: {success_rate:.2f}%")
            print(f"Requests per second: {rps:.2f}")

    asyncio.run(load_test_example())

Benchmark Comparison
~~~~~~~~~~~~~~~~~~~

Compare CloudflareBypass vs standard HTTP client::

    import aiohttp
    import time

    async def benchmark_comparison():
        test_url = "https://cloudflare-protected-site.com"
        request_count = 50

        # Test with CloudflareBypass
        config = CloudflareBypassConfig(max_concurrent_requests=10)

        async with CloudflareBypass(config) as bypass:
            start_time = time.time()
            cf_tasks = [bypass.get(test_url) for _ in range(request_count)]
            cf_responses = await asyncio.gather(*cf_tasks, return_exceptions=True)
            cf_duration = time.time() - start_time

            cf_successful = sum(
                1 for r in cf_responses
                if not isinstance(r, Exception) and r.status_code < 400
            )

        # Test with standard aiohttp
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            http_tasks = [session.get(test_url) for _ in range(request_count)]
            http_responses = await asyncio.gather(*http_tasks, return_exceptions=True)
            http_duration = time.time() - start_time

            http_successful = sum(
                1 for r in http_responses
                if not isinstance(r, Exception) and r.status < 400
            )

        print("Benchmark Results:")
        print(f"CloudflareBypass: {cf_successful}/{request_count} successful in {cf_duration:.2f}s")
        print(f"Standard HTTP: {http_successful}/{request_count} successful in {http_duration:.2f}s")

    asyncio.run(benchmark_comparison())

Monitoring and Metrics Examples
------------------------------

Real-time Monitoring
~~~~~~~~~~~~~~~~~~~~

Monitor performance in real-time::

    from cloudflare_research.metrics import MetricsCollector, PerformanceMonitor

    async def monitoring_example():
        config = CloudflareBypassConfig(
            enable_monitoring=True,
            max_concurrent_requests=50
        )

        collector = MetricsCollector()
        monitor = PerformanceMonitor()

        # Set up alert thresholds
        monitor.set_alert_thresholds(
            max_response_time=5.0,
            min_success_rate=0.90
        )

        async with CloudflareBypass(config) as bypass:
            # Start monitoring
            await monitor.start_monitoring()

            # Make requests with monitoring
            for i in range(100):
                try:
                    response = await bypass.get(f"https://example.com/item/{i}")

                    # Record metrics
                    collector.record_request(
                        url=response.url,
                        status_code=response.status_code,
                        response_time=response.elapsed.total_seconds(),
                        success=response.status_code < 400
                    )

                    # Check for alerts
                    if i % 10 == 0:
                        alerts = monitor.check_thresholds()
                        for alert in alerts:
                            print(f"ALERT: {alert}")

                        # Get current metrics
                        live_metrics = monitor.get_live_metrics()
                        print(f"Current RPS: {live_metrics.requests_per_second:.2f}")
                        print(f"Success rate: {live_metrics.success_rate:.2%}")

                except Exception as e:
                    print(f"Request {i} failed: {e}")

            await monitor.stop_monitoring()

    asyncio.run(monitoring_example())

Metrics Export
~~~~~~~~~~~~~

Export metrics to different formats::

    from cloudflare_research.metrics import MetricsExporter

    async def metrics_export_example():
        collector = MetricsCollector()

        # ... make requests and collect metrics ...

        exporter = MetricsExporter(collector)

        # Export to JSON
        json_data = exporter.export_json()
        with open("metrics.json", "w") as f:
            f.write(json_data)

        # Export to CSV
        csv_data = exporter.export_csv()
        with open("metrics.csv", "w") as f:
            f.write(csv_data)

        # Export to Prometheus format
        prometheus_data = exporter.export_prometheus()
        print("Prometheus metrics:")
        print(prometheus_data)

CLI Examples
-----------

Command Line Usage
~~~~~~~~~~~~~~~~~

Use the CLI for testing and automation::

    # Single request test
    cloudflare-research request https://example.com --format json

    # Concurrency benchmark
    cloudflare-research benchmark https://example.com \
        --concurrency 50 \
        --duration 60 \
        --output benchmark_results.json

    # Challenge analysis
    cloudflare-research analyze-challenges https://protected-site.com \
        --samples 10 \
        --verbose

Scripting Integration
~~~~~~~~~~~~~~~~~~~~

Integrate with shell scripts::

    #!/bin/bash

    # Test multiple sites
    sites=(
        "https://site1.example.com"
        "https://site2.example.com"
        "https://site3.example.com"
    )

    for site in "${sites[@]}"; do
        echo "Testing $site..."

        result=$(cloudflare-research request "$site" --format json --timeout 30)
        status=$(echo "$result" | jq -r '.status_code')
        cf_detected=$(echo "$result" | jq -r '.cloudflare_detected')

        echo "  Status: $status, Cloudflare: $cf_detected"
    done

Error Handling Examples
----------------------

Comprehensive Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Handle various error scenarios::

    from cloudflare_research.exceptions import (
        CloudflareBypassError,
        ChallengeError,
        RateLimitError,
        ConfigurationError
    )

    async def error_handling_example():
        config = CloudflareBypassConfig()

        async with CloudflareBypass(config) as bypass:
            urls_to_test = [
                "https://valid-site.com",
                "https://challenge-site.com",
                "https://rate-limited-site.com",
                "https://invalid-domain-xyz123.com"
            ]

            for url in urls_to_test:
                try:
                    response = await bypass.get(url)
                    print(f"✓ {url}: {response.status_code}")

                except ChallengeError as e:
                    print(f"✗ Challenge failed for {url}: {e}")

                except RateLimitError as e:
                    print(f"⚠ Rate limited for {url}: {e}")
                    # Wait before continuing
                    await asyncio.sleep(60)

                except CloudflareBypassError as e:
                    print(f"✗ Bypass error for {url}: {e}")

                except Exception as e:
                    print(f"✗ Unexpected error for {url}: {e}")

    asyncio.run(error_handling_example())

Retry Logic
~~~~~~~~~~

Implement custom retry logic::

    async def retry_example():
        config = CloudflareBypassConfig()

        async with CloudflareBypass(config) as bypass:
            url = "https://occasionally-failing-site.com"
            max_retries = 3
            retry_delay = 2.0

            for attempt in range(max_retries + 1):
                try:
                    response = await bypass.get(url)

                    if response.status_code < 400:
                        print(f"Success on attempt {attempt + 1}")
                        break
                    else:
                        print(f"HTTP {response.status_code} on attempt {attempt + 1}")

                except Exception as e:
                    print(f"Error on attempt {attempt + 1}: {e}")

                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print("All retry attempts failed")

    asyncio.run(retry_example())

Custom Configuration Examples
----------------------------

Environment-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure using environment variables::

    import os

    def create_config_from_env():
        config = CloudflareBypassConfig(
            max_concurrent_requests=int(os.getenv("CF_MAX_CONCURRENT", "10")),
            requests_per_second=float(os.getenv("CF_RATE_LIMIT", "5.0")),
            browser_version=os.getenv("CF_BROWSER_VERSION", "120.0.0.0"),
            solve_javascript_challenges=os.getenv("CF_SOLVE_JS", "true").lower() == "true"
        )
        return config

    async def env_config_example():
        # Set environment variables
        os.environ["CF_MAX_CONCURRENT"] = "50"
        os.environ["CF_RATE_LIMIT"] = "10.0"
        os.environ["CF_BROWSER_VERSION"] = "121.0.0.0"

        config = create_config_from_env()

        async with CloudflareBypass(config) as bypass:
            response = await bypass.get("https://example.com")
            print(f"Response: {response.status_code}")

    asyncio.run(env_config_example())

Dynamic Configuration
~~~~~~~~~~~~~~~~~~~~~

Adjust configuration based on runtime conditions::

    async def dynamic_config_example():
        # Start with conservative settings
        config = CloudflareBypassConfig(
            max_concurrent_requests=10,
            requests_per_second=2.0
        )

        async with CloudflareBypass(config) as bypass:
            # Test current performance
            test_start = time.time()
            test_tasks = [bypass.get("https://example.com") for _ in range(10)]
            test_responses = await asyncio.gather(*test_tasks, return_exceptions=True)
            test_duration = time.time() - test_start

            successful = sum(
                1 for r in test_responses
                if not isinstance(r, Exception) and r.status_code < 400
            )

            success_rate = successful / len(test_responses)

            # Adjust configuration based on results
            if success_rate > 0.95 and test_duration < 5.0:
                # Performance is good, increase concurrency
                bypass.update_config(
                    max_concurrent_requests=50,
                    requests_per_second=10.0
                )
                print("Increased concurrency settings")

            elif success_rate < 0.80:
                # Too many failures, reduce load
                bypass.update_config(
                    max_concurrent_requests=5,
                    requests_per_second=1.0
                )
                print("Reduced concurrency settings")

            # Continue with adjusted settings
            for i in range(50):
                response = await bypass.get(f"https://example.com/item/{i}")
                print(f"Request {i}: {response.status_code}")

    asyncio.run(dynamic_config_example())

.. seealso::
   - :doc:`configuration` - Detailed configuration options
   - :doc:`troubleshooting` - Troubleshooting common issues
   - :doc:`../api/bypass` - API documentation for CloudflareBypass