Testing Guide
=============

This guide covers testing strategies, frameworks, and best practices for CloudflareBypass development.

Testing Architecture
--------------------

Test Structure
~~~~~~~~~~~~~

The testing suite follows a hierarchical structure:

.. code-block:: text

    tests/
    ├── unit/                   # Unit tests for individual components
    │   ├── test_bypass.py      # Core bypass functionality
    │   ├── test_challenge.py   # Challenge system tests
    │   ├── test_browser.py     # Browser emulation tests
    │   ├── test_http.py        # HTTP client tests
    │   ├── test_session.py     # Session management tests
    │   └── test_models.py      # Data model tests
    ├── integration/            # Integration tests
    │   ├── test_end_to_end.py  # Complete workflow tests
    │   ├── test_concurrency.py # Concurrency system tests
    │   └── test_performance.py # Performance validation
    ├── contract/               # Contract tests against real endpoints
    │   ├── test_cloudflare.py  # Cloudflare-protected sites
    │   └── test_challenges.py  # Challenge solving validation
    ├── fixtures/               # Test data and fixtures
    │   ├── html_samples/       # Sample HTML responses
    │   ├── challenge_data/     # Challenge test data
    │   └── config_samples/     # Configuration examples
    └── tools/                  # Testing utilities
        ├── mock_server.py      # Mock Cloudflare server
        ├── challenge_generator.py # Generate test challenges
        └── performance_harness.py # Performance testing

Test Categories
~~~~~~~~~~~~~~

**Unit Tests**: Test individual components in isolation
- Fast execution (< 1 second per test)
- No external dependencies
- High code coverage
- Mocked dependencies

**Integration Tests**: Test component interactions
- Moderate execution time (< 30 seconds per test)
- Limited external dependencies
- Real component integration
- Controlled environment

**Contract Tests**: Test against real endpoints
- Longer execution time (< 5 minutes per test)
- Real network dependencies
- Actual Cloudflare interaction
- Rate limited execution

**Performance Tests**: Validate performance characteristics
- Variable execution time
- Resource intensive
- Scalability validation
- Benchmarking

Running Tests
------------

Basic Test Execution
~~~~~~~~~~~~~~~~~~~

Run all tests::

    # Run all tests
    python -m pytest

    # Run with coverage
    python -m pytest --cov=cloudflare_research

    # Run specific test category
    python -m pytest tests/unit/
    python -m pytest tests/integration/
    python -m pytest tests/contract/

Test Configuration
~~~~~~~~~~~~~~~~~

Configure test execution with pytest.ini::

    [tool:pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    addopts =
        --strict-markers
        --strict-config
        --verbose
        --tb=short
        --cov=cloudflare_research
        --cov-report=term-missing
        --cov-report=html
        --cov-fail-under=90

Environment Variables
~~~~~~~~~~~~~~~~~~~~

Configure tests with environment variables::

    # Test execution control
    export PYTEST_TIMEOUT=300
    export PYTEST_WORKERS=4

    # Contract test configuration
    export CF_TEST_ENDPOINTS="https://example.com,https://test.com"
    export CF_TEST_RATE_LIMIT="1.0"

    # Performance test configuration
    export CF_PERF_MAX_CONCURRENT=100
    export CF_PERF_DURATION=60

Unit Testing
-----------

Core Component Tests
~~~~~~~~~~~~~~~~~~~

Test the main CloudflareBypass class::

    import pytest
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

    class TestCloudflareBypass:
        @pytest.fixture
        def config(self):
            return CloudflareBypassConfig(
                max_concurrent_requests=10,
                solve_javascript_challenges=True
            )

        @pytest.fixture
        def mock_http_client(self):
            client = AsyncMock()
            client.get.return_value = MagicMock(
                status_code=200,
                headers={},
                text="<html>Success</html>"
            )
            return client

        @pytest.mark.asyncio
        async def test_get_request(self, config, mock_http_client):
            bypass = CloudflareBypass(config)
            bypass.http_client = mock_http_client

            response = await bypass.get("https://example.com")

            assert response.status_code == 200
            mock_http_client.get.assert_called_once()

        @pytest.mark.asyncio
        async def test_context_manager(self, config):
            async with CloudflareBypass(config) as bypass:
                assert bypass is not None
                assert bypass.http_client is not None

Challenge System Tests
~~~~~~~~~~~~~~~~~~~~~

Test challenge detection and solving::

    from cloudflare_research.challenge import ChallengeDetector, ChallengeType

    class TestChallengeDetector:
        @pytest.fixture
        def detector(self):
            return ChallengeDetector()

        def test_detect_javascript_challenge(self, detector):
            html = """
            <html>
                <script>window._cf_chl_opt = {cvId: '2', cType: 'managed'};</script>
            </html>
            """
            headers = {"Server": "cloudflare"}

            challenge_type = detector.detect_challenge_type(html, headers)
            assert challenge_type == ChallengeType.JAVASCRIPT

        def test_detect_turnstile_challenge(self, detector):
            html = """
            <html>
                <div class="cf-turnstile" data-sitekey="0x4AAA"></div>
            </html>
            """
            headers = {"Server": "cloudflare"}

            challenge_type = detector.detect_challenge_type(html, headers)
            assert challenge_type == ChallengeType.TURNSTILE

        def test_no_challenge_detected(self, detector):
            html = "<html><body>Normal content</body></html>"
            headers = {}

            challenge_type = detector.detect_challenge_type(html, headers)
            assert challenge_type == ChallengeType.NONE

Browser Emulation Tests
~~~~~~~~~~~~~~~~~~~~~~

Test browser fingerprinting and header generation::

    from cloudflare_research.browser import TLSFingerprint, HeaderGenerator

    class TestBrowserEmulation:
        def test_tls_fingerprint_generation(self):
            fingerprint = TLSFingerprint()
            ja3 = fingerprint.generate_ja3_fingerprint("chrome_120")

            assert isinstance(ja3, str)
            assert len(ja3) > 0
            assert "," in ja3  # JA3 format includes commas

        def test_header_generation(self):
            generator = HeaderGenerator("chrome", "120.0.0.0")
            headers = generator.generate_headers("https://example.com")

            assert "User-Agent" in headers
            assert "Accept" in headers
            assert "chrome" in headers["User-Agent"].lower()

        def test_randomized_headers(self):
            generator = HeaderGenerator("chrome", "120.0.0.0")

            headers1 = generator.generate_headers("https://example.com", randomize=True)
            headers2 = generator.generate_headers("https://example.com", randomize=True)

            # Some headers should differ between calls
            assert headers1["User-Agent"] == headers2["User-Agent"]  # Browser should be same
            # But some random elements may differ

Mock Testing
-----------

Mock HTTP Responses
~~~~~~~~~~~~~~~~~~

Create realistic mock responses for testing::

    import pytest
    from unittest.mock import AsyncMock, MagicMock

    @pytest.fixture
    def mock_cloudflare_response():
        response = MagicMock()
        response.status_code = 200
        response.headers = {
            "Server": "cloudflare",
            "CF-RAY": "test-ray-id",
            "Set-Cookie": "__cf_bm=test-cookie; path=/; expires=..."
        }
        response.text = """
        <html>
            <head><title>Protected Site</title></head>
            <body>Content successfully loaded</body>
        </html>
        """
        return response

    @pytest.fixture
    def mock_javascript_challenge_response():
        response = MagicMock()
        response.status_code = 503
        response.headers = {"Server": "cloudflare"}
        response.text = """
        <html>
            <script>
                window._cf_chl_opt = {
                    cvId: '2',
                    cType: 'managed',
                    cNounce: 'test-nonce',
                    cRay: 'test-ray',
                    cHash: 'test-hash'
                };
                // Challenge JavaScript code here
            </script>
        </html>
        """
        return response

Mock Server
~~~~~~~~~~

Create a mock Cloudflare server for controlled testing::

    from aiohttp import web
    import json

    class MockCloudflareServer:
        def __init__(self):
            self.app = web.Application()
            self.setup_routes()
            self.challenge_count = 0

        def setup_routes(self):
            self.app.router.add_get("/", self.handle_root)
            self.app.router.add_get("/challenge", self.handle_challenge)
            self.app.router.add_post("/submit", self.handle_submit)

        async def handle_root(self, request):
            # Return normal response or challenge based on logic
            if self.should_challenge(request):
                return await self.serve_challenge()
            else:
                return web.Response(
                    text="<html><body>Success</body></html>",
                    headers={"CF-RAY": "mock-ray-123"}
                )

        async def handle_challenge(self, request):
            return await self.serve_challenge()

        async def serve_challenge(self):
            self.challenge_count += 1
            challenge_html = """
            <html>
                <script>
                    window._cf_chl_opt = {
                        cvId: '2',
                        cType: 'managed',
                        cRay: 'mock-ray-challenge'
                    };
                    // Mock challenge code
                    setTimeout(function() {
                        window.location.href = '/success';
                    }, 1000);
                </script>
            </html>
            """
            return web.Response(
                text=challenge_html,
                status=503,
                headers={"Server": "cloudflare"}
            )

        async def handle_submit(self, request):
            # Validate challenge solution
            data = await request.json()
            if "solution" in data:
                return web.Response(
                    text='{"success": true}',
                    headers={"Content-Type": "application/json"}
                )
            else:
                return web.Response(
                    text='{"success": false}',
                    status=400
                )

        def should_challenge(self, request):
            # Logic to determine when to present challenges
            user_agent = request.headers.get("User-Agent", "")
            return "bot" in user_agent.lower() or self.challenge_count < 1

Integration Testing
------------------

End-to-End Workflow Tests
~~~~~~~~~~~~~~~~~~~~~~~~

Test complete workflows from request to response::

    import pytest
    import asyncio
    from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

    class TestEndToEndWorkflow:
        @pytest.mark.asyncio
        async def test_successful_request_flow(self):
            config = CloudflareBypassConfig(
                max_concurrent_requests=5,
                solve_javascript_challenges=True
            )

            async with CloudflareBypass(config) as bypass:
                response = await bypass.get("https://httpbin.org/get")

                assert response.status_code == 200
                assert response.success
                # Verify the complete request/response cycle

        @pytest.mark.asyncio
        async def test_challenge_solving_flow(self, mock_server):
            # Start mock server with challenges
            server_url = await mock_server.start()

            config = CloudflareBypassConfig(
                solve_javascript_challenges=True,
                challenge_timeout=30.0
            )

            async with CloudflareBypass(config) as bypass:
                response = await bypass.get(f"{server_url}/challenge")

                # Should solve challenge and get final response
                assert response.status_code == 200
                assert response.success

Concurrency Testing
~~~~~~~~~~~~~~~~~~

Test concurrent request handling::

    class TestConcurrency:
        @pytest.mark.asyncio
        async def test_concurrent_requests(self):
            config = CloudflareBypassConfig(
                max_concurrent_requests=20
            )

            urls = [f"https://httpbin.org/delay/1" for _ in range(10)]

            async with CloudflareBypass(config) as bypass:
                start_time = time.time()

                tasks = [bypass.get(url) for url in urls]
                responses = await asyncio.gather(*tasks)

                elapsed = time.time() - start_time

                # Should complete in roughly 1 second (concurrent), not 10
                assert elapsed < 3.0
                assert all(r.status_code == 200 for r in responses)

        @pytest.mark.asyncio
        async def test_rate_limiting(self):
            config = CloudflareBypassConfig(
                max_concurrent_requests=10,
                requests_per_second=5.0
            )

            async with CloudflareBypass(config) as bypass:
                start_time = time.time()

                # Make 10 requests with 5 RPS limit
                tasks = [bypass.get("https://httpbin.org/get") for _ in range(10)]
                await asyncio.gather(*tasks)

                elapsed = time.time() - start_time

                # Should take at least 2 seconds with 5 RPS limit
                assert elapsed >= 1.8  # Allow some variance

Contract Testing
---------------

Real Endpoint Testing
~~~~~~~~~~~~~~~~~~~~

Test against actual Cloudflare-protected sites::

    import pytest
    import os

    @pytest.mark.contract
    class TestCloudflareContract:
        @pytest.fixture
        def test_endpoints(self):
            endpoints = os.getenv("CF_TEST_ENDPOINTS", "").split(",")
            return [url.strip() for url in endpoints if url.strip()]

        @pytest.mark.asyncio
        async def test_cloudflare_detection(self, test_endpoints):
            if not test_endpoints:
                pytest.skip("No test endpoints configured")

            config = CloudflareBypassConfig()

            for endpoint in test_endpoints:
                async with CloudflareBypass(config) as bypass:
                    response = await bypass.get(endpoint)

                    # Should detect Cloudflare if present
                    if response.is_cloudflare_protected():
                        assert response.get_cf_ray() is not None

        @pytest.mark.asyncio
        async def test_challenge_solving_success_rate(self, test_endpoints):
            if not test_endpoints:
                pytest.skip("No test endpoints configured")

            config = CloudflareBypassConfig(
                solve_javascript_challenges=True,
                challenge_timeout=30.0
            )

            successful = 0
            total = 0

            for endpoint in test_endpoints:
                for _ in range(5):  # Test 5 times per endpoint
                    async with CloudflareBypass(config) as bypass:
                        try:
                            response = await bypass.get(endpoint)
                            if response.status_code < 400:
                                successful += 1
                        except Exception:
                            pass  # Count as failure
                        total += 1

                        # Rate limit between requests
                        await asyncio.sleep(2)

            success_rate = successful / total if total > 0 else 0
            assert success_rate >= 0.80, f"Success rate {success_rate:.2%} below 80%"

Performance Testing
------------------

Load Testing
~~~~~~~~~~~

Test performance under load::

    import time
    import statistics

    class TestPerformance:
        @pytest.mark.performance
        @pytest.mark.asyncio
        async def test_response_time_performance(self):
            config = CloudflareBypassConfig(
                max_concurrent_requests=50
            )

            response_times = []

            async with CloudflareBypass(config) as bypass:
                for _ in range(100):
                    start_time = time.time()
                    response = await bypass.get("https://httpbin.org/get")
                    elapsed = time.time() - start_time

                    if response.status_code == 200:
                        response_times.append(elapsed)

            # Performance assertions
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]

            assert avg_time < 2.0, f"Average response time {avg_time:.3f}s too high"
            assert p95_time < 5.0, f"P95 response time {p95_time:.3f}s too high"

        @pytest.mark.performance
        @pytest.mark.asyncio
        async def test_memory_usage(self):
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss

            config = CloudflareBypassConfig(
                max_concurrent_requests=100
            )

            async with CloudflareBypass(config) as bypass:
                # Make many requests
                tasks = [bypass.get("https://httpbin.org/get") for _ in range(200)]
                await asyncio.gather(*tasks)

            final_memory = process.memory_info().rss
            memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

            # Memory increase should be reasonable
            assert memory_increase < 100, f"Memory increase {memory_increase:.2f}MB too high"

Stress Testing
~~~~~~~~~~~~~

Test system limits and failure modes::

    class TestStressTesting:
        @pytest.mark.stress
        @pytest.mark.asyncio
        async def test_high_concurrency_limits(self):
            config = CloudflareBypassConfig(
                max_concurrent_requests=1000,
                requests_per_second=100.0
            )

            try:
                async with CloudflareBypass(config) as bypass:
                    # Test with very high concurrency
                    tasks = [bypass.get("https://httpbin.org/get") for _ in range(500)]
                    responses = await asyncio.gather(*tasks, return_exceptions=True)

                    successful = sum(
                        1 for r in responses
                        if not isinstance(r, Exception) and r.status_code == 200
                    )

                    # Should handle high load gracefully
                    success_rate = successful / len(responses)
                    assert success_rate >= 0.80

            except Exception as e:
                # Should fail gracefully, not crash
                assert "graceful" in str(e).lower() or "limit" in str(e).lower()

Continuous Integration
---------------------

GitHub Actions Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure automated testing in CI/CD::

    # .github/workflows/test.yml
    name: Tests

    on: [push, pull_request]

    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: [3.11, 3.12]

        steps:
        - uses: actions/checkout@v4

        - name: Set up Python ${{ matrix.python-version }}
          uses: actions/setup-python@v4
          with:
            python-version: ${{ matrix.python-version }}

        - name: Install system dependencies
          run: |
            sudo apt-get update
            sudo apt-get install -y libcurl4-openssl-dev

        - name: Install dependencies
          run: |
            python -m pip install --upgrade pip
            pip install -r requirements.txt
            pip install -r requirements-test.txt

        - name: Run unit tests
          run: pytest tests/unit/ --cov=cloudflare_research

        - name: Run integration tests
          run: pytest tests/integration/

        - name: Run contract tests
          run: pytest tests/contract/ -m "not slow"
          env:
            CF_TEST_ENDPOINTS: "https://httpbin.org"

Test Data Management
-------------------

Fixtures and Test Data
~~~~~~~~~~~~~~~~~~~~~

Organize test data effectively::

    # tests/fixtures/challenge_samples.py
    JAVASCRIPT_CHALLENGE_HTML = """
    <html>
        <script>
            window._cf_chl_opt = {
                cvId: '2',
                cType: 'managed',
                cNounce: 'sample-nonce'
            };
        </script>
    </html>
    """

    TURNSTILE_CHALLENGE_HTML = """
    <html>
        <div class="cf-turnstile" data-sitekey="sample-key"></div>
    </html>
    """

    NORMAL_RESPONSE_HTML = """
    <html>
        <head><title>Normal Page</title></head>
        <body>Regular content</body>
    </html>
    """

Test Configuration
~~~~~~~~~~~~~~~~~

Separate test configurations::

    # tests/config/test_config.py
    from cloudflare_research import CloudflareBypassConfig

    TEST_CONFIG = CloudflareBypassConfig(
        max_concurrent_requests=5,
        requests_per_second=2.0,
        timeout=10.0,
        solve_javascript_challenges=True,
        enable_monitoring=False
    )

    PERFORMANCE_TEST_CONFIG = CloudflareBypassConfig(
        max_concurrent_requests=100,
        requests_per_second=50.0,
        timeout=5.0,
        enable_monitoring=True
    )

Coverage and Quality
-------------------

Code Coverage
~~~~~~~~~~~~

Maintain high code coverage::

    # Run with coverage reporting
    pytest --cov=cloudflare_research --cov-report=html --cov-report=term

    # Coverage configuration in pyproject.toml
    [tool.coverage.run]
    source = ["cloudflare_research"]
    omit = [
        "*/tests/*",
        "*/test_*.py",
        "setup.py"
    ]

    [tool.coverage.report]
    exclude_lines = [
        "pragma: no cover",
        "def __repr__",
        "raise AssertionError",
        "raise NotImplementedError"
    ]

Quality Checks
~~~~~~~~~~~~~

Integrate quality checks in testing::

    # Run linting
    flake8 cloudflare_research/
    black --check cloudflare_research/
    mypy cloudflare_research/

    # Security scanning
    bandit -r cloudflare_research/

    # Complexity analysis
    radon cc cloudflare_research/ -a

Best Practices
-------------

Test Organization
~~~~~~~~~~~~~~~~

1. **Keep tests simple and focused**
2. **Use descriptive test names**
3. **Organize tests by functionality**
4. **Maintain test independence**
5. **Use appropriate test doubles**

Performance Testing
~~~~~~~~~~~~~~~~~~

1. **Test on realistic data**
2. **Monitor resource usage**
3. **Set performance baselines**
4. **Test failure scenarios**
5. **Use statistical analysis**

Continuous Improvement
~~~~~~~~~~~~~~~~~~~~~

1. **Regular test review**
2. **Update test data**
3. **Monitor test reliability**
4. **Improve test coverage**
5. **Optimize test execution**

.. seealso::
   - :doc:`architecture` - System architecture overview
   - :doc:`contributing` - Contributing guidelines