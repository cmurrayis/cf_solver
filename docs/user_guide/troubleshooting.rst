Troubleshooting Guide
====================

This guide helps diagnose and resolve common issues with CloudflareBypass Research Tool.

Quick Diagnosis
---------------

Common Issues Checklist
~~~~~~~~~~~~~~~~~~~~~~~

Before diving into detailed troubleshooting, check these common issues:

**Installation Issues:**
- [ ] Python 3.11+ installed
- [ ] All dependencies installed correctly
- [ ] Virtual environment activated
- [ ] System dependencies available (curl, build tools)

**Configuration Issues:**
- [ ] Valid configuration parameters
- [ ] Reasonable concurrency limits
- [ ] Proper timeout values
- [ ] Valid browser version strings

**Network Issues:**
- [ ] Internet connectivity
- [ ] No proxy/firewall blocking
- [ ] Target site accessible
- [ ] DNS resolution working

**Runtime Issues:**
- [ ] Sufficient memory available
- [ ] CPU not overloaded
- [ ] File descriptor limits adequate
- [ ] No resource leaks

Installation Problems
--------------------

ModuleNotFoundError Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: ``ModuleNotFoundError: No module named 'cloudflare_research'``

**Diagnosis**::

    # Check if package is installed
    pip list | grep cloudflare

    # Check Python path
    python -c "import sys; print(sys.path)"

**Solutions**::

    # Install in current environment
    pip install -r requirements.txt

    # Use virtual environment
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate     # Windows
    pip install -r requirements.txt

curl-cffi Installation Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: ``Error: Microsoft Visual C++ 14.0 is required`` (Windows)

**Solutions**:

1. **Install Visual Studio Build Tools**::

    # Download from Microsoft
    # Install "C++ build tools" workload

2. **Use pre-compiled wheels**::

    pip install --only-binary=all curl-cffi

3. **Alternative method**::

    conda install -c conda-forge curl-cffi

**Error**: ``fatal error: curl/curl.h: No such file`` (Linux)

**Solutions**::

    # Ubuntu/Debian
    sudo apt update
    sudo apt install libcurl4-openssl-dev

    # CentOS/RHEL
    sudo yum install libcurl-devel

    # Then reinstall
    pip uninstall curl-cffi
    pip install curl-cffi

MiniRacer Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: JavaScript engine compilation errors

**Solutions**::

    # Try pre-compiled wheel
    pip install --only-binary=all mini-racer

    # Install build dependencies
    # Windows: Visual Studio Build Tools
    # Linux: build-essential
    # macOS: xcode-select --install

    # Alternative JavaScript engine
    pip install PyExecJS

Configuration Problems
---------------------

Invalid Configuration Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: ``ConfigurationError: Invalid max_concurrent_requests``

**Diagnosis**::

    from cloudflare_research import CloudflareBypassConfig

    config = CloudflareBypassConfig(max_concurrent_requests=0)  # Invalid
    validation = config.validate()
    print(validation.errors)

**Solutions**::

    # Use valid ranges
    config = CloudflareBypassConfig(
        max_concurrent_requests=10,     # Must be > 0
        requests_per_second=5.0,        # Must be > 0
        timeout=30.0,                   # Must be > 0
        challenge_timeout=30.0          # Must be > 0
    )

Memory/Resource Issues
~~~~~~~~~~~~~~~~~~~~~

**Error**: ``MemoryError`` or system slowdown

**Diagnosis**::

    import psutil
    import os

    # Check memory usage
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

    # Check file descriptors (Linux/macOS)
    print(f"Open files: {process.num_fds()}")

**Solutions**::

    # Reduce concurrency
    config = CloudflareBypassConfig(
        max_concurrent_requests=10,     # Reduce from higher value
        connection_pool_size=25         # Reduce pool size
    )

    # Increase system limits (Linux/macOS)
    ulimit -n 65536  # Increase file descriptor limit

    # Monitor and cleanup
    async with CloudflareBypass(config) as bypass:
        # Your code here
        pass  # Resources automatically cleaned up

Network and Connection Issues
----------------------------

Connection Timeout Errors
~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: ``asyncio.TimeoutError`` or connection timeouts

**Diagnosis**::

    # Test basic connectivity
    import aiohttp
    import asyncio

    async def test_connectivity():
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://httpbin.org/get", timeout=10) as resp:
                    print(f"Basic connectivity: {resp.status}")
            except Exception as e:
                print(f"Connectivity issue: {e}")

    asyncio.run(test_connectivity())

**Solutions**::

    # Increase timeouts
    config = CloudflareBypassConfig(
        timeout=60.0,           # Increase request timeout
        challenge_timeout=60.0, # Increase challenge timeout
        connection_timeout=30.0 # Increase connection timeout
    )

    # Add retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await bypass.get(url)
            break
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

DNS Resolution Issues
~~~~~~~~~~~~~~~~~~~~

**Error**: ``ClientConnectorError: Cannot connect to host``

**Diagnosis**::

    import socket

    def test_dns(hostname):
        try:
            ip = socket.gethostbyname(hostname)
            print(f"{hostname} resolves to {ip}")
            return True
        except socket.gaierror as e:
            print(f"DNS error for {hostname}: {e}")
            return False

    test_dns("example.com")

**Solutions**::

    # Use custom DNS
    import aiohttp

    connector = aiohttp.TCPConnector(
        resolver=aiohttp.AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1"])
    )

    # Or configure system DNS
    # Linux: Edit /etc/resolv.conf
    # Windows: Network settings > DNS

SSL/TLS Issues
~~~~~~~~~~~~~

**Error**: ``ClientConnectorCertificateError`` or SSL verification failures

**Diagnosis**::

    import ssl
    import socket

    def check_ssl(hostname, port=443):
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    print(f"SSL connection to {hostname}: OK")
                    print(f"Certificate: {ssock.getpeercert()['subject']}")
        except Exception as e:
            print(f"SSL error: {e}")

    check_ssl("example.com")

**Solutions**::

    # Disable SSL verification (NOT recommended for production)
    config = CloudflareBypassConfig(
        verify_ssl=False
    )

    # Use custom SSL context
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

Challenge Solving Issues
-----------------------

JavaScript Challenge Failures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: ``ChallengeError: Failed to solve JavaScript challenge``

**Diagnosis**::

    # Test JavaScript engine
    from mini_racer import MiniRacer

    try:
        ctx = MiniRacer()
        result = ctx.eval("2 + 2")
        print(f"JavaScript engine working: {result}")
    except Exception as e:
        print(f"JavaScript engine error: {e}")

**Solutions**::

    # Increase JavaScript timeout
    config = CloudflareBypassConfig(
        javascript_timeout=30.0,
        challenge_timeout=60.0
    )

    # Enable verbose logging
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Try alternative JavaScript engine
    # pip install PyExecJS

Turnstile Challenge Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: Turnstile CAPTCHA not solved

**Diagnosis**::

    # Check if Turnstile is detected
    response = await bypass.get(url)
    if "turnstile" in response.text.lower():
        print("Turnstile challenge detected")

**Solutions**::

    # Enable Turnstile solving
    config = CloudflareBypassConfig(
        solve_turnstile_challenges=True,
        challenge_timeout=60.0
    )

    # Note: Turnstile solving may require additional setup
    # Check documentation for Turnstile configuration

Challenge Detection Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: Challenges not detected properly

**Diagnosis**::

    from cloudflare_research.challenge import ChallengeDetector

    detector = ChallengeDetector()
    html_content = response.text
    challenge_type = detector.detect_challenge_type(html_content, response.headers)
    print(f"Detected challenge: {challenge_type}")

**Solutions**::

    # Enable all challenge types
    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        solve_turnstile_challenges=True,
        solve_managed_challenges=True
    )

    # Increase detection sensitivity
    # Check response content manually
    if "challenge" in response.text.lower():
        print("Challenge keywords found in response")

Performance Issues
-----------------

Slow Response Times
~~~~~~~~~~~~~~~~~~

**Error**: Requests taking too long

**Diagnosis**::

    import time

    async def measure_performance():
        start_time = time.time()
        response = await bypass.get("https://example.com")
        elapsed = time.time() - start_time
        print(f"Request took {elapsed:.2f} seconds")

**Solutions**::

    # Optimize configuration
    config = CloudflareBypassConfig(
        connection_pool_size=50,    # Increase pool size
        enable_http2=True,          # Use HTTP/2
        compression=True,           # Enable compression
        dns_cache_size=100          # Enable DNS caching
    )

    # Use connection pooling
    async with CloudflareBypass(config) as bypass:
        # Reuse the same instance for multiple requests
        for url in urls:
            response = await bypass.get(url)

Low Concurrency Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: Not achieving expected concurrency

**Diagnosis**::

    import asyncio
    import time

    async def test_concurrency():
        start_time = time.time()
        tasks = [bypass.get(f"https://httpbin.org/delay/1") for _ in range(10)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        print(f"10 concurrent requests took {elapsed:.2f} seconds")
        # Should be close to 1 second, not 10

**Solutions**::

    # Increase concurrency limits
    config = CloudflareBypassConfig(
        max_concurrent_requests=100,
        connection_pool_size=50
    )

    # Check system limits
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print(f"File descriptor limit: {soft}")

    # Increase if needed (Linux/macOS)
    # ulimit -n 65536

Memory Leaks
~~~~~~~~~~~

**Error**: Memory usage continuously increasing

**Diagnosis**::

    import psutil
    import gc

    process = psutil.Process()
    initial_memory = process.memory_info().rss

    # ... run your code ...

    gc.collect()  # Force garbage collection
    final_memory = process.memory_info().rss
    leak = (final_memory - initial_memory) / 1024 / 1024
    print(f"Memory increase: {leak:.2f} MB")

**Solutions**::

    # Properly close resources
    async with CloudflareBypass(config) as bypass:
        # Your code here
        pass  # Automatic cleanup

    # Limit session storage
    config = CloudflareBypassConfig(
        session_persistence=False,  # Disable if not needed
        cookie_jar_size=100         # Limit cookie storage
    )

    # Manual cleanup
    await bypass.close()

Rate Limiting Issues
-------------------

Getting Rate Limited
~~~~~~~~~~~~~~~~~~~

**Error**: HTTP 429 responses or rate limiting

**Diagnosis**::

    response = await bypass.get(url)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        print(f"Rate limited. Retry after: {retry_after} seconds")

**Solutions**::

    # Reduce request rate
    config = CloudflareBypassConfig(
        requests_per_second=1.0,    # Reduce from higher value
        max_concurrent_requests=5   # Reduce concurrency
    )

    # Implement backoff
    async def request_with_backoff(url):
        for attempt in range(3):
            response = await bypass.get(url)
            if response.status_code != 429:
                return response

            # Exponential backoff
            delay = 2 ** attempt
            await asyncio.sleep(delay)

        raise Exception("Rate limited after retries")

Adaptive Rate Limiting
~~~~~~~~~~~~~~~~~~~~~

**Solution**: Implement adaptive rate limiting based on responses::

    class AdaptiveRateLimiter:
        def __init__(self, initial_rate=10.0):
            self.rate = initial_rate
            self.success_count = 0
            self.total_count = 0

        async def make_request(self, bypass, url):
            # Apply current rate limit
            await asyncio.sleep(1.0 / self.rate)

            response = await bypass.get(url)
            self.total_count += 1

            if response.status_code == 429:
                # Reduce rate on rate limiting
                self.rate *= 0.5
                print(f"Rate limited. Reducing rate to {self.rate:.2f}")
            elif response.status_code < 400:
                self.success_count += 1
                # Gradually increase rate on success
                if self.success_count % 10 == 0:
                    self.rate *= 1.1

            return response

Debugging and Logging
---------------------

Enable Debug Logging
~~~~~~~~~~~~~~~~~~~~

Get detailed information about what's happening::

    import logging

    # Enable debug logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Enable specific loggers
    logging.getLogger("cloudflare_research").setLevel(logging.DEBUG)
    logging.getLogger("aiohttp").setLevel(logging.DEBUG)

Custom Logging
~~~~~~~~~~~~~

Create custom logging for your specific needs::

    import logging

    class CloudflareLogger:
        def __init__(self):
            self.logger = logging.getLogger("cloudflare_debug")
            handler = logging.FileHandler("cloudflare_debug.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

        def log_request(self, method, url, status_code, elapsed):
            self.logger.info(f"{method} {url} -> {status_code} ({elapsed:.3f}s)")

        def log_challenge(self, challenge_type, solved, solve_time):
            self.logger.info(f"Challenge {challenge_type}: {'SOLVED' if solved else 'FAILED'} ({solve_time:.3f}s)")

Response Analysis
~~~~~~~~~~~~~~~~

Analyze responses to understand issues::

    async def analyze_response(response):
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        # Check for Cloudflare indicators
        cf_ray = response.headers.get("CF-RAY")
        if cf_ray:
            print(f"CF-RAY: {cf_ray}")

        # Check for challenges
        content = response.text.lower()
        if "challenge" in content:
            print("Challenge keywords found")
        if "turnstile" in content:
            print("Turnstile detected")
        if "javascript" in content:
            print("JavaScript challenge detected")

        # Save response for analysis
        with open("response_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

Testing and Validation
---------------------

Validate Installation
~~~~~~~~~~~~~~~~~~~~~

Test that everything is working correctly::

    async def validate_installation():
        tests_passed = 0
        total_tests = 0

        # Test 1: Basic import
        total_tests += 1
        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig
            print("✓ Import test passed")
            tests_passed += 1
        except Exception as e:
            print(f"✗ Import test failed: {e}")

        # Test 2: Configuration
        total_tests += 1
        try:
            config = CloudflareBypassConfig()
            print("✓ Configuration test passed")
            tests_passed += 1
        except Exception as e:
            print(f"✗ Configuration test failed: {e}")

        # Test 3: Basic request
        total_tests += 1
        try:
            async with CloudflareBypass(config) as bypass:
                response = await bypass.get("https://httpbin.org/get")
                assert response.status_code == 200
            print("✓ Basic request test passed")
            tests_passed += 1
        except Exception as e:
            print(f"✗ Basic request test failed: {e}")

        # Test 4: JavaScript engine
        total_tests += 1
        try:
            from mini_racer import MiniRacer
            ctx = MiniRacer()
            result = ctx.eval("2 + 2")
            assert result == 4
            print("✓ JavaScript engine test passed")
            tests_passed += 1
        except Exception as e:
            print(f"✗ JavaScript engine test failed: {e}")

        print(f"\nValidation complete: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests

    success = await validate_installation()

Environment Testing
~~~~~~~~~~~~~~~~~~

Test in different environments::

    import platform
    import sys

    def print_environment_info():
        print(f"Python version: {sys.version}")
        print(f"Platform: {platform.platform()}")
        print(f"Architecture: {platform.architecture()}")

        # Check dependencies
        try:
            import aiohttp
            print(f"aiohttp version: {aiohttp.__version__}")
        except ImportError:
            print("aiohttp not installed")

        try:
            import curl_cffi
            print(f"curl-cffi version: {curl_cffi.__version__}")
        except ImportError:
            print("curl-cffi not installed")

        try:
            import mini_racer
            print("mini-racer available")
        except ImportError:
            print("mini-racer not installed")

Common Error Messages
--------------------

Error Reference
~~~~~~~~~~~~~~

Quick reference for common error messages:

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Error Message
     - Solution
   * - ``ModuleNotFoundError: No module named 'cloudflare_research'``
     - Install package: ``pip install -r requirements.txt``
   * - ``ClientConnectorError: Cannot connect to host``
     - Check network connectivity and DNS
   * - ``asyncio.TimeoutError``
     - Increase timeout values in configuration
   * - ``ChallengeError: Failed to solve JavaScript challenge``
     - Check JavaScript engine and increase timeouts
   * - ``ConfigurationError: Invalid max_concurrent_requests``
     - Use valid configuration values
   * - ``MemoryError``
     - Reduce concurrency and connection pool size
   * - ``Too many open files``
     - Increase file descriptor limit
   * - ``HTTP 429: Too Many Requests``
     - Reduce request rate and implement backoff

Getting Help
-----------

Community Support
~~~~~~~~~~~~~~~~

- **GitHub Issues**: Report bugs and get help
- **Documentation**: Comprehensive guides and examples
- **Stack Overflow**: Community Q&A (tag: cloudflare-bypass)

Professional Support
~~~~~~~~~~~~~~~~~~~

For professional support and consulting:
- Performance optimization
- Custom challenge solving
- Enterprise integration
- Security auditing

Reporting Bugs
~~~~~~~~~~~~~

When reporting issues, include:

1. **Environment information**::

    python --version
    pip list
    uname -a  # Linux/macOS
    systeminfo  # Windows

2. **Configuration used**
3. **Complete error message and stack trace**
4. **Minimal reproduction example**
5. **Expected vs actual behavior**

.. seealso::
   - :doc:`installation` - Installation guide
   - :doc:`configuration` - Configuration options
   - :doc:`examples` - Usage examples