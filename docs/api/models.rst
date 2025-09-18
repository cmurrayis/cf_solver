Data Models
===========

The models module defines core data structures and validation for the CloudflareBypass system.

.. currentmodule:: cloudflare_research.models

Challenge Models
----------------

.. automodule:: cloudflare_research.models.challenge_record
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ChallengeRecord
   :members:
   :undoc-members:
   :show-inheritance:

   Records information about detected and solved challenges.

.. automethod:: ChallengeRecord.from_response
.. automethod:: ChallengeRecord.to_dict
.. automethod:: ChallengeRecord.is_expired

Performance Models
------------------

.. automodule:: cloudflare_research.models.performance_metrics
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: PerformanceMetrics
   :members:
   :undoc-members:
   :show-inheritance:

   Tracks performance metrics for requests and operations.

.. automethod:: PerformanceMetrics.record_request
.. automethod:: PerformanceMetrics.get_summary
.. automethod:: PerformanceMetrics.export_data

.. autoclass:: RequestMetrics
   :members:
   :undoc-members:
   :show-inheritance:

   Metrics for individual requests.

.. autoclass:: ConcurrencyMetrics
   :members:
   :undoc-members:
   :show-inheritance:

   Metrics for concurrent operations.

Test Models
-----------

.. automodule:: cloudflare_research.models.test_configuration
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TestConfiguration
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration for test scenarios and validation.

.. automethod:: TestConfiguration.validate
.. automethod:: TestConfiguration.to_dict
.. automethod:: TestConfiguration.from_dict

.. automodule:: cloudflare_research.models.test_request
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TestRequest
   :members:
   :undoc-members:
   :show-inheritance:

   Represents a test request with expected outcomes.

.. automethod:: TestRequest.execute
.. automethod:: TestRequest.validate_response
.. automethod:: TestRequest.get_metrics

.. automodule:: cloudflare_research.models.test_session
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TestSession
   :members:
   :undoc-members:
   :show-inheritance:

   Manages a complete test session with multiple requests.

.. automethod:: TestSession.add_request
.. automethod:: TestSession.execute_all
.. automethod:: TestSession.get_results
.. automethod:: TestSession.export_report

Response Models
---------------

.. autoclass:: CloudflareResponse
   :members:
   :undoc-members:
   :show-inheritance:

   Enhanced response object with Cloudflare-specific analysis.

.. automethod:: CloudflareResponse.analyze_protection
.. automethod:: CloudflareResponse.extract_challenge
.. automethod:: CloudflareResponse.get_cf_data

Configuration Models
--------------------

.. autoclass:: CloudflareBypassConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Main configuration class for CloudflareBypass behavior.

.. automethod:: CloudflareBypassConfig.validate
.. automethod:: CloudflareBypassConfig.merge
.. automethod:: CloudflareBypassConfig.to_dict

.. autoclass:: BrowserConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration for browser emulation.

.. autoclass:: ChallengeConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration for challenge solving behavior.

Error Models
------------

.. autoclass:: CloudflareBypassError
   :members:
   :undoc-members:
   :show-inheritance:

   Base exception for CloudflareBypass errors.

.. autoclass:: ChallengeError
   :members:
   :undoc-members:
   :show-inheritance:

   Raised when challenge solving fails.

.. autoclass:: ConfigurationError
   :members:
   :undoc-members:
   :show-inheritance:

   Raised when configuration is invalid.

.. autoclass:: RateLimitError
   :members:
   :undoc-members:
   :show-inheritance:

   Raised when rate limits are exceeded.

Validation
----------

.. autofunction:: validate_url
.. autofunction:: validate_headers
.. autofunction:: validate_timeout
.. autofunction:: validate_concurrency_config

Example Usage
-------------

Working with Challenge Records::

    record = ChallengeRecord(
        type="javascript",
        detected_at=datetime.now(),
        solved=True,
        solution_time=2.5,
        metadata={"difficulty": "medium"}
    )

    # Convert to dictionary for serialization
    data = record.to_dict()

    # Check if challenge is still valid
    if not record.is_expired():
        print("Challenge solution still valid")

Performance Tracking::

    metrics = PerformanceMetrics()

    # Record individual requests
    metrics.record_request(
        url="https://example.com",
        response_time=1.2,
        status_code=200,
        success=True
    )

    # Get performance summary
    summary = metrics.get_summary()
    print(f"Average response time: {summary.avg_response_time:.3f}s")
    print(f"Success rate: {summary.success_rate:.2%}")

Test Configuration::

    config = TestConfiguration(
        target_urls=["https://example1.com", "https://example2.com"],
        concurrency_levels=[10, 50, 100],
        test_duration_seconds=300,
        expected_success_rate=0.95
    )

    # Validate configuration
    if config.validate():
        print("Configuration is valid")

    # Export for sharing
    config_dict = config.to_dict()

Test Session Execution::

    session = TestSession("load_test_1")

    # Add test requests
    for i in range(100):
        request = TestRequest(
            url=f"https://example.com/api/{i}",
            method="GET",
            expected_status=200
        )
        session.add_request(request)

    # Execute all requests
    results = await session.execute_all()

    # Generate report
    report = session.export_report("json")
    with open("test_results.json", "w") as f:
        f.write(report)

Configuration Management::

    # Create base configuration
    base_config = CloudflareBypassConfig(
        max_concurrent_requests=100,
        solve_javascript_challenges=True
    )

    # Create specialized configuration
    high_perf_config = CloudflareBypassConfig(
        max_concurrent_requests=1000,
        requests_per_second=50.0
    )

    # Merge configurations
    merged = base_config.merge(high_perf_config)

    # Validate merged configuration
    if merged.validate():
        print("Merged configuration is valid")

Error Handling::

    try:
        bypass = CloudflareBypass(invalid_config)
    except ConfigurationError as e:
        print(f"Configuration error: {e}")

    try:
        result = await bypass.get("https://example.com")
    except ChallengeError as e:
        print(f"Challenge solving failed: {e}")
    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}")

.. seealso::
   :doc:`../user_guide/configuration` for detailed model configuration examples.