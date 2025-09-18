"""
Basic Usage Example for CloudflareBypass

This example demonstrates the fundamental usage patterns of CloudflareBypass
for making HTTP requests that can bypass Cloudflare protection mechanisms.
"""

import asyncio
import logging
from typing import Optional

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.models.response import CloudflareResponse


async def basic_get_request(url: str) -> Optional[CloudflareResponse]:
    """
    Perform a basic GET request with default configuration.

    Args:
        url: Target URL to request

    Returns:
        CloudflareResponse object or None if failed
    """
    print(f"Making GET request to: {url}")

    # Create basic configuration
    config = CloudflareBypassConfig(
        timeout=30.0,
        enable_detailed_logging=True
    )

    try:
        async with CloudflareBypass(config) as bypass:
            result = await bypass.get(url)

            print(f"Status Code: {result.status_code}")
            print(f"Challenge Solved: {result.challenge_solved}")
            print(f"Response Length: {len(result.content)} bytes")
            print(f"Attempts: {result.attempts}")

            if result.timing:
                print(f"Total Time: {result.timing.total_time:.3f}s")
                print(f"DNS Time: {result.timing.dns_time:.3f}s")
                print(f"Connect Time: {result.timing.connect_time:.3f}s")
                print(f"TLS Time: {result.timing.tls_time:.3f}s")

            return result

    except Exception as e:
        print(f"Request failed: {e}")
        return None


async def basic_post_request(url: str, data: dict) -> Optional[CloudflareResponse]:
    """
    Perform a basic POST request with JSON data.

    Args:
        url: Target URL to request
        data: JSON data to send

    Returns:
        CloudflareResponse object or None if failed
    """
    print(f"Making POST request to: {url}")
    print(f"Data: {data}")

    config = CloudflareBypassConfig(
        timeout=30.0,
        enable_detailed_logging=True
    )

    try:
        async with CloudflareBypass(config) as bypass:
            result = await bypass.post(url, json_data=data)

            print(f"Status Code: {result.status_code}")
            print(f"Challenge Solved: {result.challenge_solved}")
            print(f"Response Length: {len(result.content)} bytes")

            return result

    except Exception as e:
        print(f"POST request failed: {e}")
        return None


async def request_with_headers(url: str, headers: dict) -> Optional[CloudflareResponse]:
    """
    Perform a request with custom headers.

    Args:
        url: Target URL to request
        headers: Custom headers to include

    Returns:
        CloudflareResponse object or None if failed
    """
    print(f"Making request with custom headers to: {url}")
    print(f"Headers: {headers}")

    config = CloudflareBypassConfig(
        timeout=30.0,
        enable_detailed_logging=True
    )

    try:
        async with CloudflareBypass(config) as bypass:
            result = await bypass.get(url, headers=headers)

            print(f"Status Code: {result.status_code}")
            print(f"Challenge Solved: {result.challenge_solved}")

            # Show some response headers
            print("Response Headers:")
            for key, value in list(result.headers.items())[:5]:  # Show first 5 headers
                print(f"  {key}: {value}")

            return result

    except Exception as e:
        print(f"Request with headers failed: {e}")
        return None


async def configured_bypass_example():
    """
    Example using CloudflareBypass with custom configuration.
    """
    print("=== Configured CloudflareBypass Example ===")

    # Create configuration with custom settings
    config = CloudflareBypassConfig(
        browser_version="120.0.0.0",
        timeout=45.0,
        max_concurrent_requests=5,
        requests_per_second=2.0,
        solve_javascript_challenges=True,
        solve_managed_challenges=False,  # Conservative approach
        solve_turnstile_challenges=False,  # Conservative approach
        enable_detailed_logging=True,
        enable_monitoring=True,
        enable_metrics_collection=True
    )

    test_url = "https://httpbin.org/get"

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"CloudflareBypass initialized with config:")
            print(f"  Browser Version: {config.browser_version}")
            print(f"  Timeout: {config.timeout}s")
            print(f"  Max Concurrent: {config.max_concurrent_requests}")
            print(f"  Rate Limit: {config.requests_per_second} req/s")
            print()

            # Make test request
            result = await bypass.get(test_url)

            print(f"Request completed:")
            print(f"  URL: {test_url}")
            print(f"  Status: {result.status_code}")
            print(f"  Challenge Solved: {result.challenge_solved}")
            print(f"  Attempts: {result.attempts}")

            if result.timing:
                print(f"  Timing:")
                print(f"    Total: {result.timing.total_time:.3f}s")
                print(f"    Challenge: {result.timing.challenge_time:.3f}s")

            # Show response content (first 200 chars)
            content_preview = result.content[:200]
            if len(result.content) > 200:
                content_preview += "..."
            print(f"  Response Preview: {content_preview}")

    except Exception as e:
        print(f"Configured bypass example failed: {e}")


async def multiple_requests_example():
    """
    Example showing multiple sequential requests with the same bypass instance.
    """
    print("\n=== Multiple Requests Example ===")

    config = CloudflareBypassConfig(
        timeout=30.0,
        enable_detailed_logging=False  # Reduce noise for multiple requests
    )

    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent"
    ]

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Making {len(urls)} sequential requests...")

            for i, url in enumerate(urls, 1):
                print(f"Request {i}/{len(urls)}: {url}")

                result = await bypass.get(url)
                print(f"  Status: {result.status_code}")
                print(f"  Challenge: {result.challenge_solved}")
                print(f"  Size: {len(result.content)} bytes")

                # Small delay between requests
                await asyncio.sleep(1)

            print("All requests completed successfully!")

    except Exception as e:
        print(f"Multiple requests example failed: {e}")


async def error_handling_example():
    """
    Example demonstrating error handling patterns.
    """
    print("\n=== Error Handling Example ===")

    config = CloudflareBypassConfig(
        timeout=5.0,  # Short timeout to demonstrate timeout handling
        enable_detailed_logging=True
    )

    # Test with various scenarios
    test_cases = [
        ("Valid URL", "https://httpbin.org/get"),
        ("Invalid URL", "https://nonexistent-domain-12345.com"),
        ("Timeout URL", "https://httpbin.org/delay/10"),  # Will timeout with 5s limit
    ]

    async with CloudflareBypass(config) as bypass:
        for description, url in test_cases:
            print(f"\nTesting: {description}")
            print(f"URL: {url}")

            try:
                result = await bypass.get(url)
                print(f"  ✓ Success: Status {result.status_code}")
                print(f"  Challenge Solved: {result.challenge_solved}")

            except asyncio.TimeoutError:
                print(f"  ✗ Timeout: Request exceeded {config.timeout}s")

            except Exception as e:
                print(f"  ✗ Error: {type(e).__name__}: {e}")


async def main():
    """
    Main function demonstrating various CloudflareBypass usage patterns.
    """
    # Setup logging to see detailed output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Basic Usage Examples")
    print("=" * 50)

    # Example 1: Basic GET request
    print("\n1. Basic GET Request")
    await basic_get_request("https://httpbin.org/get")

    # Example 2: POST request with JSON
    print("\n2. POST Request with JSON")
    test_data = {"test": "data", "timestamp": "2024-01-01T00:00:00Z"}
    await basic_post_request("https://httpbin.org/post", test_data)

    # Example 3: Request with custom headers
    print("\n3. Request with Custom Headers")
    custom_headers = {
        "X-Test-Header": "example-value",
        "Accept": "application/json",
        "User-Agent": "CloudflareBypass-Example/1.0"
    }
    await request_with_headers("https://httpbin.org/headers", custom_headers)

    # Example 4: Configured bypass instance
    await configured_bypass_example()

    # Example 5: Multiple requests
    await multiple_requests_example()

    # Example 6: Error handling
    await error_handling_example()

    print("\n" + "=" * 50)
    print("All examples completed!")
    print("\nNext Steps:")
    print("- Try with your own URLs")
    print("- Experiment with different configurations")
    print("- Check out concurrent_requests.py for parallel processing")
    print("- See challenge_solving.py for advanced challenge handling")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())