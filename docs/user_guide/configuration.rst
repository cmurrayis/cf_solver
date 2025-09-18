Configuration Guide
===================

This guide covers all configuration options for CloudflareBypass Research Tool.

Configuration Overview
----------------------

CloudflareBypass uses a hierarchical configuration system:

1. **Default values** - Built-in safe defaults
2. **Configuration files** - YAML/JSON configuration files
3. **Environment variables** - Runtime environment configuration
4. **Code parameters** - Direct configuration in code

Configuration priority (highest to lowest):
Code parameters → Environment variables → Configuration files → Defaults

Basic Configuration
-------------------

Minimal Configuration
~~~~~~~~~~~~~~~~~~~~~

The simplest configuration for getting started::

    from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

    config = CloudflareBypassConfig()
    async with CloudflareBypass(config) as bypass:
        response = await bypass.get("https://example.com")

Production Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Recommended configuration for production use::

    config = CloudflareBypassConfig(
        # Core settings
        max_concurrent_requests=100,
        requests_per_second=10.0,
        timeout=30.0,

        # Challenge solving
        solve_javascript_challenges=True,
        solve_turnstile_challenges=True,
        challenge_timeout=30.0,

        # Browser emulation
        enable_tls_fingerprinting=True,
        browser_version="120.0.0.0",
        randomize_headers=True,

        # Performance
        enable_monitoring=True,
        connection_pool_size=50
    )

Core Configuration Options
--------------------------

Request Handling
~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``max_concurrent_requests``
     - ``10``
     - Maximum concurrent requests
   * - ``requests_per_second``
     - ``5.0``
     - Rate limiting (requests per second)
   * - ``timeout``
     - ``30.0``
     - Request timeout in seconds
   * - ``max_redirects``
     - ``10``
     - Maximum number of redirects to follow
   * - ``retry_attempts``
     - ``3``
     - Number of retry attempts on failure

Example::

    config = CloudflareBypassConfig(
        max_concurrent_requests=500,
        requests_per_second=25.0,
        timeout=60.0,
        retry_attempts=5
    )

Challenge Solving
~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``solve_javascript_challenges``
     - ``True``
     - Enable JavaScript challenge solving
   * - ``solve_turnstile_challenges``
     - ``True``
     - Enable Turnstile CAPTCHA solving
   * - ``solve_managed_challenges``
     - ``True``
     - Enable managed challenge handling
   * - ``challenge_timeout``
     - ``30.0``
     - Timeout for challenge solving
   * - ``javascript_timeout``
     - ``10.0``
     - Timeout for JavaScript execution

Example::

    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        solve_turnstile_challenges=False,  # Disable if not needed
        challenge_timeout=45.0
    )

Browser Emulation
~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``enable_tls_fingerprinting``
     - ``True``
     - Enable TLS fingerprint randomization
   * - ``browser_version``
     - ``"120.0.0.0"``
     - Browser version to emulate
   * - ``user_agent``
     - ``None``
     - Custom User-Agent (auto-generated if None)
   * - ``randomize_headers``
     - ``True``
     - Randomize HTTP headers
   * - ``ja3_randomization``
     - ``True``
     - Enable JA3 fingerprint randomization

Example::

    config = CloudflareBypassConfig(
        browser_version="121.0.0.0",
        user_agent="Custom Research Bot 1.0",
        randomize_headers=False,  # Use consistent headers
        ja3_randomization=True
    )

Advanced Configuration
----------------------

Session Management
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``session_persistence``
     - ``True``
     - Enable session state persistence
   * - ``cookie_jar_size``
     - ``1000``
     - Maximum cookies to store
   * - ``session_timeout``
     - ``3600``
     - Session timeout in seconds
   * - ``persistent_sessions``
     - ``False``
     - Save sessions to disk

Example::

    config = CloudflareBypassConfig(
        session_persistence=True,
        persistent_sessions=True,
        session_timeout=7200  # 2 hours
    )

Performance Tuning
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``connection_pool_size``
     - ``25``
     - HTTP connection pool size
   * - ``dns_cache_size``
     - ``100``
     - DNS resolution cache size
   * - ``enable_http2``
     - ``True``
     - Enable HTTP/2 protocol
   * - ``compression``
     - ``True``
     - Enable response compression
   * - ``keep_alive``
     - ``True``
     - Enable connection keep-alive

Example::

    config = CloudflareBypassConfig(
        connection_pool_size=100,
        enable_http2=True,
        compression=True,
        dns_cache_size=500
    )

Monitoring and Logging
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``enable_monitoring``
     - ``False``
     - Enable performance monitoring
   * - ``log_level``
     - ``"INFO"``
     - Logging level
   * - ``metrics_export``
     - ``None``
     - Metrics export format
   * - ``detailed_logging``
     - ``False``
     - Enable detailed request logging

Example::

    config = CloudflareBypassConfig(
        enable_monitoring=True,
        log_level="DEBUG",
        detailed_logging=True,
        metrics_export="json"
    )

Configuration Files
-------------------

YAML Configuration
~~~~~~~~~~~~~~~~~~

Create ``config.yaml``::

    cloudflare_bypass:
      # Core settings
      max_concurrent_requests: 200
      requests_per_second: 15.0
      timeout: 45.0

      # Challenge solving
      solve_javascript_challenges: true
      solve_turnstile_challenges: true
      challenge_timeout: 30.0

      # Browser emulation
      enable_tls_fingerprinting: true
      browser_version: "120.0.0.0"
      randomize_headers: true

      # Performance
      connection_pool_size: 75
      enable_http2: true

    logging:
      level: INFO
      format: "%(asctime)s - %(levelname)s - %(message)s"

Load configuration::

    import yaml
    from cloudflare_research import CloudflareBypassConfig

    with open("config.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    config = CloudflareBypassConfig(**config_data["cloudflare_bypass"])

JSON Configuration
~~~~~~~~~~~~~~~~~~

Create ``config.json``::

    {
      "cloudflare_bypass": {
        "max_concurrent_requests": 200,
        "requests_per_second": 15.0,
        "solve_javascript_challenges": true,
        "enable_tls_fingerprinting": true,
        "browser_version": "120.0.0.0"
      }
    }

Load configuration::

    import json
    from cloudflare_research import CloudflareBypassConfig

    with open("config.json", "r") as f:
        config_data = json.load(f)

    config = CloudflareBypassConfig(**config_data["cloudflare_bypass"])

Environment Variables
---------------------

All configuration options can be set via environment variables using the prefix ``CF_BYPASS_``:

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Environment Variable
     - Configuration Parameter
   * - ``CF_BYPASS_MAX_CONCURRENT``
     - ``max_concurrent_requests``
   * - ``CF_BYPASS_RATE_LIMIT``
     - ``requests_per_second``
   * - ``CF_BYPASS_TIMEOUT``
     - ``timeout``
   * - ``CF_BYPASS_BROWSER_VERSION``
     - ``browser_version``
   * - ``CF_BYPASS_LOG_LEVEL``
     - ``log_level``

Example usage::

    # Set environment variables
    export CF_BYPASS_MAX_CONCURRENT=500
    export CF_BYPASS_RATE_LIMIT=20.0
    export CF_BYPASS_BROWSER_VERSION="121.0.0.0"

    # Configuration automatically uses environment values
    config = CloudflareBypassConfig()  # Uses env vars

Use Case Configurations
-----------------------

High-Performance Testing
~~~~~~~~~~~~~~~~~~~~~~~~

Configuration optimized for maximum throughput::

    config = CloudflareBypassConfig(
        max_concurrent_requests=1000,
        requests_per_second=100.0,
        timeout=10.0,
        connection_pool_size=200,
        enable_http2=True,
        compression=True,
        retry_attempts=1,  # Faster failure
        challenge_timeout=15.0
    )

Research and Analysis
~~~~~~~~~~~~~~~~~~~~~

Configuration for detailed research with comprehensive logging::

    config = CloudflareBypassConfig(
        max_concurrent_requests=50,
        requests_per_second=5.0,
        enable_monitoring=True,
        detailed_logging=True,
        log_level="DEBUG",
        session_persistence=True,
        persistent_sessions=True,
        solve_javascript_challenges=True,
        solve_turnstile_challenges=True
    )

Stealth Mode
~~~~~~~~~~~~

Configuration for minimal detection::

    config = CloudflareBypassConfig(
        max_concurrent_requests=10,
        requests_per_second=2.0,
        randomize_headers=True,
        ja3_randomization=True,
        browser_version="120.0.0.0",
        user_agent=None,  # Auto-generate realistic UA
        enable_tls_fingerprinting=True,
        timeout=30.0
    )

Load Testing
~~~~~~~~~~~~

Configuration for stress testing protected endpoints::

    config = CloudflareBypassConfig(
        max_concurrent_requests=2000,
        requests_per_second=500.0,
        timeout=5.0,
        retry_attempts=0,  # No retries for pure load
        connection_pool_size=500,
        enable_monitoring=True,
        metrics_export="prometheus"
    )

Browser-Specific Configurations
-------------------------------

Chrome Emulation
~~~~~~~~~~~~~~~~

Accurate Chrome browser emulation::

    config = CloudflareBypassConfig(
        browser_version="120.0.0.0",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        enable_tls_fingerprinting=True,
        randomize_headers=False  # Use consistent Chrome headers
    )

Firefox Emulation
~~~~~~~~~~~~~~~~~

Firefox browser emulation::

    config = CloudflareBypassConfig(
        browser_version="121.0.0",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        enable_tls_fingerprinting=True,
        ja3_randomization=False  # Use Firefox-specific JA3
    )

Mobile Browser Emulation
~~~~~~~~~~~~~~~~~~~~~~~

Mobile Chrome emulation::

    config = CloudflareBypassConfig(
        browser_version="120.0.0.0",
        user_agent="Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        randomize_headers=True,
        enable_tls_fingerprinting=True
    )

Configuration Validation
------------------------

Validate Configuration
~~~~~~~~~~~~~~~~~~~~~~

Check configuration before use::

    config = CloudflareBypassConfig(
        max_concurrent_requests=1000,
        requests_per_second=50.0
    )

    # Validate configuration
    validation_result = config.validate()
    if not validation_result.is_valid:
        for error in validation_result.errors:
            print(f"Configuration error: {error}")

Configuration Merging
~~~~~~~~~~~~~~~~~~~~~

Merge multiple configurations::

    # Base configuration
    base_config = CloudflareBypassConfig(
        max_concurrent_requests=100,
        solve_javascript_challenges=True
    )

    # Override specific settings
    override_config = CloudflareBypassConfig(
        max_concurrent_requests=500,
        timeout=60.0
    )

    # Merge configurations (override takes precedence)
    merged_config = base_config.merge(override_config)

Dynamic Configuration
~~~~~~~~~~~~~~~~~~~~~

Update configuration at runtime::

    bypass = CloudflareBypass(config)

    # Update rate limiting based on server response
    if response.status_code == 429:  # Rate limited
        new_rate = bypass.config.requests_per_second * 0.5
        bypass.update_config(requests_per_second=new_rate)

Best Practices
--------------

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~

1. **Start Conservative**: Begin with low concurrency and increase gradually
2. **Monitor Resources**: Watch CPU, memory, and network usage
3. **Tune Rate Limits**: Adjust based on target server capacity
4. **Use Connection Pooling**: Enable for better performance
5. **Profile Your Workload**: Test different configurations

Security Considerations
~~~~~~~~~~~~~~~~~~~~~~

1. **Respect Rate Limits**: Don't overwhelm target servers
2. **Use Realistic Settings**: Avoid configurations that look like attacks
3. **Rotate Fingerprints**: Enable randomization for research
4. **Monitor Detection**: Watch for blocking or CAPTCHAs
5. **Follow Terms of Service**: Ensure compliance with target site policies

Troubleshooting Configuration
-----------------------------

Common Issues
~~~~~~~~~~~~~

**Issue**: High memory usage

**Solution**: Reduce concurrent requests or connection pool size::

    config = CloudflareBypassConfig(
        max_concurrent_requests=50,  # Reduce from 500
        connection_pool_size=25      # Reduce pool size
    )

**Issue**: Slow performance

**Solution**: Increase concurrency and enable optimizations::

    config = CloudflareBypassConfig(
        max_concurrent_requests=200,
        enable_http2=True,
        compression=True,
        connection_pool_size=100
    )

**Issue**: Challenge solving failures

**Solution**: Increase timeouts and enable all solvers::

    config = CloudflareBypassConfig(
        challenge_timeout=60.0,
        javascript_timeout=30.0,
        solve_javascript_challenges=True,
        solve_turnstile_challenges=True
    )

Configuration Testing
~~~~~~~~~~~~~~~~~~~~~

Test your configuration before production use::

    async def test_config(config):
        async with CloudflareBypass(config) as bypass:
            # Test basic functionality
            response = await bypass.get("https://httpbin.org/get")
            assert response.status_code == 200

            # Test challenge handling (if available)
            # response = await bypass.get("https://challenge-site.com")

            print("Configuration test passed!")

    asyncio.run(test_config(your_config))

.. seealso::
   - :doc:`installation` - Installation requirements
   - :doc:`examples` - Configuration examples in context
   - :doc:`troubleshooting` - Troubleshooting configuration issues