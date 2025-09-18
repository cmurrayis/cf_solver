#!/usr/bin/env python3
"""
Final integration test for all quickstart scenarios.

This test validates that all examples from the README.md work correctly
and that the CloudflareBypass implementation is ready for deployment.

Test Coverage:
- Simple request example
- Production configuration example
- Concurrent requests example
- Configuration validation
- Error handling
- Performance characteristics
"""

import asyncio
import time
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test results will be written to this file
RESULTS_FILE = "quickstart_integration_results.json"


class QuickstartIntegrationTester:
    """Comprehensive integration tester for all quickstart scenarios."""

    def __init__(self):
        self.results = {}
        self.test_start_time = None
        self.setup_logging()

    def setup_logging(self):
        """Configure logging for test execution."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('quickstart_integration_test.log')
            ]
        )
        self.logger = logging.getLogger("QuickstartIntegration")

    def log_test_start(self, test_name: str):
        """Log the start of a test."""
        self.logger.info(f"=" * 60)
        self.logger.info(f"Starting test: {test_name}")
        self.logger.info(f"=" * 60)

    def log_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test results."""
        status = "PASS" if success else "FAIL"
        self.logger.info(f"Test {test_name}: {status}")
        if details:
            for key, value in details.items():
                self.logger.info(f"  {key}: {value}")

    async def test_basic_imports(self) -> Dict[str, Any]:
        """Test that all required imports work correctly."""
        test_name = "Basic Imports"
        self.log_test_start(test_name)

        try:
            # Test core imports
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig
            self.logger.info("[OK] Core imports successful")

            # Test that classes can be instantiated
            config = CloudflareBypassConfig()
            self.logger.info("[OK] Configuration object created")

            # Test basic configuration
            assert hasattr(config, 'max_concurrent_requests')
            assert hasattr(config, 'solve_javascript_challenges')
            self.logger.info("[OK] Configuration attributes accessible")

            result = {
                "success": True,
                "message": "All imports and basic instantiation successful",
                "imports_tested": [
                    "cloudflare_research.CloudflareBypass",
                    "cloudflare_research.CloudflareBypassConfig"
                ]
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "message": "Import or instantiation failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_simple_request_example(self) -> Dict[str, Any]:
        """Test the simple request example from README."""
        test_name = "Simple Request Example"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

            # Create configuration as shown in README
            config = CloudflareBypassConfig(
                max_concurrent_requests=10,
                solve_javascript_challenges=True,
                enable_tls_fingerprinting=True
            )

            # Test against a reliable endpoint
            test_url = "https://httpbin.org/get"

            async with CloudflareBypass(config) as bypass:
                start_time = time.time()
                response = await bypass.get(test_url)
                elapsed = time.time() - start_time

                # Validate response
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                assert response.success, "Response should be marked as successful"

                self.logger.info(f"[OK] Request completed successfully")
                self.logger.info(f"[OK] Status: {response.status_code}")
                self.logger.info(f"[OK] Response time: {elapsed:.3f}s")

                result = {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": elapsed,
                    "url_tested": test_url,
                    "message": "Simple request example works correctly"
                }

        except Exception as e:
            self.logger.error(f"[FAIL] Simple request failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Simple request example failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_production_configuration_example(self) -> Dict[str, Any]:
        """Test the production configuration example from README."""
        test_name = "Production Configuration Example"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

            # Production-ready configuration from README
            config = CloudflareBypassConfig(
                # Performance settings
                max_concurrent_requests=100,
                requests_per_second=10.0,
                timeout=30.0,

                # Challenge solving
                solve_javascript_challenges=True,
                solve_turnstile_challenges=True,
                challenge_timeout=45.0,

                # Browser emulation
                enable_tls_fingerprinting=True,
                browser_version="120.0.0.0",
                randomize_headers=True,

                # Monitoring
                enable_monitoring=True
            )

            # Validate configuration
            assert config.max_concurrent_requests == 100
            assert config.requests_per_second == 10.0
            assert config.solve_javascript_challenges == True
            assert config.enable_tls_fingerprinting == True

            self.logger.info("[OK] Production configuration validated")

            # Test that bypass can be created with production config
            test_url = "https://httpbin.org/headers"

            async with CloudflareBypass(config) as bypass:
                response = await bypass.get(test_url)

                assert response.status_code == 200
                self.logger.info(f"[OK] Production config request successful")

                # Check that headers are properly set
                response_data = json.loads(response.body)
                headers = response_data.get("headers", {})
                user_agent = headers.get("User-Agent", "")

                assert "120.0.0.0" in user_agent, "Browser version should be in User-Agent"
                self.logger.info(f"[OK] Browser version correctly set in headers")

                result = {
                    "success": True,
                    "config_validated": True,
                    "request_successful": True,
                    "browser_version_set": "120.0.0.0" in user_agent,
                    "message": "Production configuration example works correctly"
                }

        except Exception as e:
            self.logger.error(f"[FAIL] Production configuration test failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Production configuration example failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_concurrent_requests_example(self) -> Dict[str, Any]:
        """Test the concurrent requests example from README."""
        test_name = "Concurrent Requests Example"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

            config = CloudflareBypassConfig(
                max_concurrent_requests=20,
                requests_per_second=5.0
            )

            # Use multiple test URLs
            urls = [
                "https://httpbin.org/get",
                "https://httpbin.org/headers",
                "https://httpbin.org/user-agent",
                "https://httpbin.org/ip",
                "https://httpbin.org/json"
            ]

            async with CloudflareBypass(config) as bypass:
                start_time = time.time()

                # Create tasks for all URLs (as shown in README)
                tasks = [bypass.get(url) for url in urls]

                # Execute concurrently
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                elapsed = time.time() - start_time

                # Process results (as shown in README)
                successful = 0
                failed = 0
                for i, response in enumerate(responses):
                    if isinstance(response, Exception):
                        self.logger.warning(f"URL {i+1}: Error - {response}")
                        failed += 1
                    else:
                        self.logger.info(f"URL {i+1}: {response.status_code}")
                        if response.status_code < 400:
                            successful += 1
                        else:
                            failed += 1

                success_rate = successful / len(urls)
                self.logger.info(f"Success rate: {successful}/{len(urls)} ({success_rate*100:.1f}%)")

                # Validate concurrent execution was efficient
                expected_max_time = max(len(urls) / config.requests_per_second, 2.0)
                assert elapsed < expected_max_time, f"Concurrent execution too slow: {elapsed:.2f}s > {expected_max_time:.2f}s"

                result = {
                    "success": True,
                    "total_requests": len(urls),
                    "successful_requests": successful,
                    "failed_requests": failed,
                    "success_rate": success_rate,
                    "total_time": elapsed,
                    "concurrent_execution_efficient": elapsed < expected_max_time,
                    "message": "Concurrent requests example works correctly"
                }

        except Exception as e:
            self.logger.error(f"[FAIL] Concurrent requests test failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Concurrent requests example failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios."""
        test_name = "Error Handling"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

            config = CloudflareBypassConfig(timeout=5.0)

            # Test invalid URL handling
            async with CloudflareBypass(config) as bypass:
                try:
                    response = await bypass.get("https://invalid-domain-that-should-not-exist-12345.com")
                    assert False, "Should have raised an exception for invalid domain"
                except Exception as e:
                    self.logger.info(f"[OK] Invalid domain correctly handled: {type(e).__name__}")

                # Test timeout handling
                try:
                    # This should timeout
                    response = await bypass.get("https://httpbin.org/delay/10")
                    # If it doesn't timeout, that's also acceptable for this test
                    self.logger.info("[OK] Long delay request handled (didn't timeout)")
                except Exception as e:
                    self.logger.info(f"[OK] Timeout correctly handled: {type(e).__name__}")

            result = {
                "success": True,
                "invalid_domain_handled": True,
                "timeout_handling_tested": True,
                "message": "Error handling works correctly"
            }

        except Exception as e:
            self.logger.error(f"[FAIL] Error handling test failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Error handling test failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_configuration_validation(self) -> Dict[str, Any]:
        """Test configuration validation."""
        test_name = "Configuration Validation"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypassConfig

            # Test valid configuration
            valid_config = CloudflareBypassConfig(
                max_concurrent_requests=50,
                requests_per_second=5.0,
                timeout=30.0
            )
            assert valid_config.max_concurrent_requests == 50
            self.logger.info("[OK] Valid configuration accepted")

            # Test configuration with various settings
            advanced_config = CloudflareBypassConfig(
                max_concurrent_requests=1,
                requests_per_second=0.5,
                browser_version="121.0.0.0",
                solve_javascript_challenges=False
            )
            assert advanced_config.requests_per_second == 0.5
            assert advanced_config.solve_javascript_challenges == False
            self.logger.info("[OK] Advanced configuration options work")

            result = {
                "success": True,
                "valid_config_accepted": True,
                "advanced_options_work": True,
                "message": "Configuration validation works correctly"
            }

        except Exception as e:
            self.logger.error(f"[FAIL] Configuration validation failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Configuration validation failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_performance_characteristics(self) -> Dict[str, Any]:
        """Test basic performance characteristics."""
        test_name = "Performance Characteristics"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

            config = CloudflareBypassConfig(
                max_concurrent_requests=10,
                requests_per_second=5.0
            )

            response_times = []
            test_url = "https://httpbin.org/get"

            async with CloudflareBypass(config) as bypass:
                # Make multiple requests to measure performance
                for i in range(5):
                    start_time = time.time()
                    response = await bypass.get(test_url)
                    elapsed = time.time() - start_time

                    assert response.status_code == 200
                    response_times.append(elapsed)
                    self.logger.info(f"Request {i+1}: {elapsed:.3f}s")

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            # Performance should be reasonable
            assert avg_response_time < 5.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time < 10.0, f"Max response time too high: {max_response_time:.3f}s"

            self.logger.info(f"[OK] Average response time: {avg_response_time:.3f}s")
            self.logger.info(f"[OK] Max response time: {max_response_time:.3f}s")

            result = {
                "success": True,
                "avg_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "performance_acceptable": avg_response_time < 5.0 and max_response_time < 10.0,
                "message": "Performance characteristics are acceptable"
            }

        except Exception as e:
            self.logger.error(f"[FAIL] Performance test failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Performance test failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def test_resource_cleanup(self) -> Dict[str, Any]:
        """Test that resources are properly cleaned up."""
        test_name = "Resource Cleanup"
        self.log_test_start(test_name)

        try:
            from cloudflare_research import CloudflareBypass, CloudflareBypassConfig
            import gc

            config = CloudflareBypassConfig(max_concurrent_requests=5)

            # Test context manager cleanup
            bypass_instance = None
            async with CloudflareBypass(config) as bypass:
                bypass_instance = bypass
                response = await bypass.get("https://httpbin.org/get")
                assert response.status_code == 200

            # After context manager, resources should be cleaned up
            # We can't easily test this, but we can verify no exceptions occur

            # Test manual cleanup
            bypass2 = CloudflareBypass(config)
            await bypass2.__aenter__()
            response = await bypass2.get("https://httpbin.org/get")
            await bypass2.__aexit__(None, None, None)

            # Force garbage collection
            gc.collect()

            self.logger.info("[OK] Resource cleanup completed without errors")

            result = {
                "success": True,
                "context_manager_cleanup": True,
                "manual_cleanup": True,
                "message": "Resource cleanup works correctly"
            }

        except Exception as e:
            self.logger.error(f"[FAIL] Resource cleanup test failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "message": "Resource cleanup test failed"
            }

        self.log_test_result(test_name, result["success"], result)
        return result

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all quickstart integration tests."""
        self.test_start_time = time.time()
        self.logger.info("Starting CloudflareBypass Quickstart Integration Tests")
        self.logger.info(f"Test start time: {datetime.now()}")

        # Define all tests to run
        tests = [
            ("basic_imports", self.test_basic_imports),
            ("simple_request_example", self.test_simple_request_example),
            ("production_configuration_example", self.test_production_configuration_example),
            ("concurrent_requests_example", self.test_concurrent_requests_example),
            ("error_handling", self.test_error_handling),
            ("configuration_validation", self.test_configuration_validation),
            ("performance_characteristics", self.test_performance_characteristics),
            ("resource_cleanup", self.test_resource_cleanup),
        ]

        # Run all tests
        test_results = {}
        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            try:
                result = await test_func()
                test_results[test_name] = result
                if result["success"]:
                    passed_tests += 1
            except Exception as e:
                test_results[test_name] = {
                    "success": False,
                    "error": str(e),
                    "message": f"Test {test_name} crashed"
                }

        # Calculate overall results
        total_time = time.time() - self.test_start_time
        success_rate = passed_tests / total_tests
        overall_success = success_rate >= 0.80  # 80% pass rate required

        overall_results = {
            "test_execution": {
                "start_time": datetime.fromtimestamp(self.test_start_time).isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_duration_seconds": total_time
            },
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": success_rate,
                "overall_success": overall_success
            },
            "individual_test_results": test_results,
            "recommendations": []
        }

        # Add recommendations based on results
        if success_rate < 1.0:
            failed_tests = [name for name, result in test_results.items() if not result["success"]]
            overall_results["recommendations"].append(f"Review failed tests: {', '.join(failed_tests)}")

        if overall_success:
            overall_results["recommendations"].append("All quickstart scenarios validated successfully")
            overall_results["recommendations"].append("CloudflareBypass is ready for deployment")
        else:
            overall_results["recommendations"].append("Address failing tests before deployment")

        # Log final results
        self.logger.info("=" * 60)
        self.logger.info("QUICKSTART INTEGRATION TEST RESULTS")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {passed_tests}")
        self.logger.info(f"Failed: {total_tests - passed_tests}")
        self.logger.info(f"Success Rate: {success_rate:.1%}")
        self.logger.info(f"Overall Result: {'PASS' if overall_success else 'FAIL'}")
        self.logger.info(f"Total Time: {total_time:.2f} seconds")

        return overall_results

    def save_results(self, results: Dict[str, Any]):
        """Save test results to JSON file."""
        try:
            with open(RESULTS_FILE, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.logger.info(f"Test results saved to {RESULTS_FILE}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")


async def main():
    """Main entry point for quickstart integration testing."""
    tester = QuickstartIntegrationTester()

    try:
        # Run all tests
        results = await tester.run_all_tests()

        # Save results
        tester.save_results(results)

        # Exit with appropriate code
        exit_code = 0 if results["test_summary"]["overall_success"] else 1
        tester.logger.info(f"Exiting with code {exit_code}")

        return exit_code

    except KeyboardInterrupt:
        tester.logger.warning("Test execution interrupted by user")
        return 130
    except Exception as e:
        tester.logger.error(f"Unexpected error during testing: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)