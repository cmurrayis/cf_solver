"""
Challenge Solving Example for CloudflareBypass

This example demonstrates how to configure and use CloudflareBypass
to handle various types of Cloudflare challenges including JavaScript
challenges, Turnstile, and managed challenges.
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.models.response import CloudflareResponse
from cloudflare_research.challenge.solver import JavaScriptSolver
from cloudflare_research.challenge.turnstile import TurnstileHandler


async def basic_challenge_solving():
    """
    Basic example of challenge solving with default configuration.
    """
    print("=== Basic Challenge Solving ===")

    # Configure with all challenge solving enabled
    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        solve_managed_challenges=True,
        solve_turnstile_challenges=True,
        timeout=60.0,  # Longer timeout for challenge solving
        enable_detailed_logging=True,
        enable_monitoring=True
    )

    # Note: Using httpbin for demonstration as it doesn't have Cloudflare protection
    # In real scenarios, you would use actual Cloudflare-protected sites
    test_url = "https://httpbin.org/get"

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Testing challenge solving capabilities...")
            print(f"Target URL: {test_url}")
            print(f"Configuration:")
            print(f"  JavaScript Challenges: {config.solve_javascript_challenges}")
            print(f"  Managed Challenges: {config.solve_managed_challenges}")
            print(f"  Turnstile Challenges: {config.solve_turnstile_challenges}")
            print(f"  Timeout: {config.timeout}s")

            start_time = time.time()
            result = await bypass.get(test_url)
            elapsed = time.time() - start_time

            print(f"\nRequest Results:")
            print(f"  Status Code: {result.status_code}")
            print(f"  Challenge Solved: {result.challenge_solved}")
            print(f"  Attempts: {result.attempts}")
            print(f"  Total Time: {elapsed:.3f}s")

            if result.timing:
                print(f"  Timing Breakdown:")
                print(f"    DNS: {result.timing.dns_time:.3f}s")
                print(f"    Connect: {result.timing.connect_time:.3f}s")
                print(f"    TLS: {result.timing.tls_time:.3f}s")
                print(f"    Challenge: {result.timing.challenge_time:.3f}s")
                print(f"    Response: {result.timing.response_time:.3f}s")

            print(f"  Response Length: {len(result.content)} bytes")

    except Exception as e:
        print(f"Basic challenge solving failed: {e}")


async def javascript_challenge_example():
    """
    Example specifically for JavaScript challenge handling.
    """
    print("\n=== JavaScript Challenge Example ===")

    # Configuration optimized for JavaScript challenges
    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        solve_managed_challenges=False,  # Focus on JS only
        solve_turnstile_challenges=False,
        browser_version="120.0.0.0",
        timeout=45.0,
        enable_detailed_logging=True
    )

    # Test multiple URLs that might have different JS challenges
    test_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent"
    ]

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Testing JavaScript challenge solving...")

            for i, url in enumerate(test_urls, 1):
                print(f"\nTest {i}/{len(test_urls)}: {url}")

                start_time = time.time()
                result = await bypass.get(url)
                elapsed = time.time() - start_time

                print(f"  Status: {result.status_code}")
                print(f"  Challenge Solved: {result.challenge_solved}")
                print(f"  Attempts: {result.attempts}")
                print(f"  Time: {elapsed:.3f}s")

                if result.challenge_solved:
                    print(f"  ✓ JavaScript challenge successfully solved!")
                    if result.timing and result.timing.challenge_time > 0:
                        print(f"  Challenge solving took: {result.timing.challenge_time:.3f}s")

                # Small delay between requests
                await asyncio.sleep(2)

    except Exception as e:
        print(f"JavaScript challenge example failed: {e}")


async def turnstile_challenge_example():
    """
    Example for Turnstile challenge handling.
    """
    print("\n=== Turnstile Challenge Example ===")

    # Configuration for Turnstile challenges
    config = CloudflareBypassConfig(
        solve_javascript_challenges=False,
        solve_managed_challenges=False,
        solve_turnstile_challenges=True,  # Focus on Turnstile
        timeout=60.0,  # Turnstile can take longer
        enable_detailed_logging=True
    )

    # Note: This is a demonstration - actual Turnstile challenges require real protected sites
    test_url = "https://httpbin.org/get"

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Testing Turnstile challenge solving...")
            print(f"Target: {test_url}")

            # Create Turnstile handler for demonstration
            turnstile_handler = TurnstileHandler()
            print(f"Turnstile handler initialized: {turnstile_handler.__class__.__name__}")

            start_time = time.time()
            result = await bypass.get(test_url)
            elapsed = time.time() - start_time

            print(f"\nTurnstile Test Results:")
            print(f"  Status: {result.status_code}")
            print(f"  Challenge Solved: {result.challenge_solved}")
            print(f"  Attempts: {result.attempts}")
            print(f"  Time: {elapsed:.3f}s")

            if result.challenge_solved:
                print(f"  ✓ Turnstile challenge handling demonstrated!")

    except Exception as e:
        print(f"Turnstile challenge example failed: {e}")


async def comprehensive_challenge_handling():
    """
    Example with all challenge types enabled for comprehensive protection.
    """
    print("\n=== Comprehensive Challenge Handling ===")

    # Full configuration with all challenge types
    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        solve_managed_challenges=True,
        solve_turnstile_challenges=True,
        browser_version="120.0.0.0",
        timeout=90.0,  # Extended timeout for complex challenges
        max_challenge_attempts=5,  # Allow multiple attempts
        enable_detailed_logging=True,
        enable_monitoring=True,
        enable_metrics_collection=True
    )

    test_scenarios = [
        ("Basic Request", "https://httpbin.org/get"),
        ("With Headers", "https://httpbin.org/headers"),
        ("POST Request", "https://httpbin.org/post"),
        ("JSON Response", "https://httpbin.org/json"),
    ]

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Testing comprehensive challenge handling...")
            print(f"Configuration Summary:")
            print(f"  All Challenge Types: Enabled")
            print(f"  Max Attempts: {config.max_challenge_attempts}")
            print(f"  Timeout: {config.timeout}s")
            print(f"  Browser Version: {config.browser_version}")

            results = []

            for scenario_name, url in test_scenarios:
                print(f"\n--- {scenario_name} ---")
                print(f"URL: {url}")

                start_time = time.time()

                try:
                    if "post" in url.lower():
                        # For POST requests, send some test data
                        test_data = {
                            "test": "comprehensive_challenge",
                            "timestamp": time.time(),
                            "scenario": scenario_name
                        }
                        result = await bypass.post(url, json_data=test_data)
                    else:
                        result = await bypass.get(url)

                    elapsed = time.time() - start_time

                    print(f"✓ SUCCESS: Status {result.status_code}")
                    print(f"  Challenge Solved: {result.challenge_solved}")
                    print(f"  Attempts: {result.attempts}")
                    print(f"  Response Time: {elapsed:.3f}s")
                    print(f"  Content Length: {len(result.content)} bytes")

                    if result.timing:
                        timing_details = []
                        if result.timing.challenge_time > 0:
                            timing_details.append(f"Challenge: {result.timing.challenge_time:.3f}s")
                        if result.timing.dns_time > 0:
                            timing_details.append(f"DNS: {result.timing.dns_time:.3f}s")
                        if result.timing.connect_time > 0:
                            timing_details.append(f"Connect: {result.timing.connect_time:.3f}s")

                        if timing_details:
                            print(f"  Timing: {', '.join(timing_details)}")

                    results.append({
                        'scenario': scenario_name,
                        'success': True,
                        'status_code': result.status_code,
                        'challenge_solved': result.challenge_solved,
                        'attempts': result.attempts,
                        'response_time': elapsed
                    })

                except Exception as e:
                    elapsed = time.time() - start_time
                    print(f"✗ FAILED: {e}")
                    results.append({
                        'scenario': scenario_name,
                        'success': False,
                        'error': str(e),
                        'response_time': elapsed
                    })

                # Delay between scenarios
                await asyncio.sleep(3)

            # Summary statistics
            successful = sum(1 for r in results if r.get('success', False))
            total_time = sum(r['response_time'] for r in results)
            challenges_solved = sum(1 for r in results if r.get('challenge_solved', False))

            print(f"\n=== Comprehensive Test Summary ===")
            print(f"Total Scenarios: {len(results)}")
            print(f"Successful: {successful}")
            print(f"Failed: {len(results) - successful}")
            print(f"Success Rate: {(successful/len(results)*100):.1f}%")
            print(f"Total Time: {total_time:.2f}s")
            print(f"Average Time per Request: {total_time/len(results):.2f}s")
            print(f"Challenges Solved: {challenges_solved}")

    except Exception as e:
        print(f"Comprehensive challenge handling failed: {e}")


async def challenge_retry_example():
    """
    Example demonstrating challenge retry mechanisms.
    """
    print("\n=== Challenge Retry Example ===")

    # Configuration with specific retry settings
    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        max_challenge_attempts=3,  # Allow up to 3 attempts
        challenge_retry_delay=2.0,  # 2 second delay between retries
        timeout=30.0,
        enable_detailed_logging=True
    )

    test_url = "https://httpbin.org/status/503"  # This will return 503, simulating a challenge scenario

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Testing challenge retry mechanisms...")
            print(f"Max Attempts: {config.max_challenge_attempts}")
            print(f"Retry Delay: {config.challenge_retry_delay}s")
            print(f"Target: {test_url}")

            start_time = time.time()

            try:
                result = await bypass.get(test_url)
                elapsed = time.time() - start_time

                print(f"\nRetry Test Results:")
                print(f"  Status: {result.status_code}")
                print(f"  Challenge Solved: {result.challenge_solved}")
                print(f"  Attempts Made: {result.attempts}")
                print(f"  Total Time: {elapsed:.3f}s")

                if result.attempts > 1:
                    avg_time_per_attempt = elapsed / result.attempts
                    print(f"  Average Time per Attempt: {avg_time_per_attempt:.3f}s")

            except Exception as e:
                elapsed = time.time() - start_time
                print(f"\nRetry Test Failed: {e}")
                print(f"  Time before failure: {elapsed:.3f}s")

    except Exception as e:
        print(f"Challenge retry example failed: {e}")


async def custom_challenge_configuration():
    """
    Example showing custom challenge solver configuration.
    """
    print("\n=== Custom Challenge Configuration ===")

    # Create custom configuration for specific challenge types
    config = CloudflareBypassConfig(
        solve_javascript_challenges=True,
        solve_managed_challenges=False,  # Disable managed challenges
        solve_turnstile_challenges=True,
        browser_version="119.0.0.0",  # Specific browser version
        timeout=45.0,
        max_challenge_attempts=2,
        challenge_retry_delay=1.5,
        enable_detailed_logging=True,

        # Custom headers that might help with challenge solving
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    test_url = "https://httpbin.org/headers"

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Testing custom challenge configuration...")
            print(f"Browser Version: {config.browser_version}")
            print(f"JavaScript Challenges: {config.solve_javascript_challenges}")
            print(f"Managed Challenges: {config.solve_managed_challenges}")
            print(f"Turnstile Challenges: {config.solve_turnstile_challenges}")
            print(f"Custom Headers: {len(config.headers) if config.headers else 0} headers")

            result = await bypass.get(test_url)

            print(f"\nCustom Configuration Results:")
            print(f"  Status: {result.status_code}")
            print(f"  Challenge Solved: {result.challenge_solved}")
            print(f"  Attempts: {result.attempts}")

            # Show that our custom headers were sent
            if result.status_code == 200:
                print(f"  ✓ Request successful with custom configuration")
                print(f"  Response length: {len(result.content)} bytes")

    except Exception as e:
        print(f"Custom challenge configuration failed: {e}")


async def main():
    """
    Main function demonstrating various challenge solving scenarios.
    """
    # Setup detailed logging to see challenge solving in action
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Challenge Solving Examples")
    print("=" * 65)
    print("Note: These examples use httpbin.org for demonstration.")
    print("In real scenarios, use actual Cloudflare-protected sites.")
    print("=" * 65)

    # Run all challenge solving examples
    await basic_challenge_solving()
    await javascript_challenge_example()
    await turnstile_challenge_example()
    await comprehensive_challenge_handling()
    await challenge_retry_example()
    await custom_challenge_configuration()

    print("\n" + "=" * 65)
    print("All challenge solving examples completed!")
    print("\nKey Challenge Solving Features:")
    print("✓ JavaScript Challenge Solving with PyMiniRacer")
    print("✓ Turnstile Challenge Detection and Handling")
    print("✓ Managed Challenge Support")
    print("✓ Configurable Retry Mechanisms")
    print("✓ Custom Browser Fingerprinting")
    print("✓ Detailed Timing and Metrics")
    print("\nConfiguration Tips:")
    print("- Increase timeout for complex challenges")
    print("- Adjust max_challenge_attempts based on site behavior")
    print("- Use appropriate browser_version for target sites")
    print("- Enable detailed logging for debugging")
    print("- Consider rate limiting to avoid triggering more challenges")
    print("\nNext Steps:")
    print("- Test with real Cloudflare-protected sites")
    print("- Experiment with different browser versions")
    print("- Monitor challenge success rates and adjust configuration")
    print("- Check out custom_config.py for advanced configuration options")


if __name__ == "__main__":
    # Run the challenge solving examples
    asyncio.run(main())