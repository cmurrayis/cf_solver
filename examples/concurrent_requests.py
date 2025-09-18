"""
Concurrent Requests Example for CloudflareBypass

This example demonstrates how to make multiple concurrent HTTP requests
efficiently using CloudflareBypass with proper concurrency control,
rate limiting, and resource management.
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.models.response import CloudflareResponse


@dataclass
class RequestResult:
    """Result of a single request in a batch."""
    url: str
    status_code: Optional[int]
    success: bool
    error: Optional[str]
    response_time: float
    challenge_solved: bool
    attempts: int
    content_length: int


async def simple_concurrent_requests():
    """
    Basic example of making multiple concurrent requests.
    """
    print("=== Simple Concurrent Requests ===")

    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/json",
    ]

    config = CloudflareBypassConfig(
        max_concurrent_requests=3,  # Limit concurrent requests
        timeout=30.0,
        enable_detailed_logging=True
    )

    start_time = time.time()

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Making {len(urls)} concurrent requests...")

            # Create tasks for all requests
            tasks = [bypass.get(url) for url in urls]

            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful = 0
            failed = 0

            for i, (url, result) in enumerate(zip(urls, results), 1):
                if isinstance(result, Exception):
                    print(f"Request {i}: {url} - FAILED: {result}")
                    failed += 1
                else:
                    print(f"Request {i}: {url} - SUCCESS: {result.status_code}")
                    print(f"  Challenge Solved: {result.challenge_solved}")
                    print(f"  Content Length: {len(result.content)} bytes")
                    successful += 1

            elapsed = time.time() - start_time
            print(f"\nResults: {successful} successful, {failed} failed")
            print(f"Total time: {elapsed:.2f}s")
            print(f"Average time per request: {elapsed/len(urls):.2f}s")

    except Exception as e:
        print(f"Concurrent requests failed: {e}")


async def controlled_concurrent_requests():
    """
    Example with controlled concurrency using semaphore and rate limiting.
    """
    print("\n=== Controlled Concurrent Requests ===")

    # Generate more URLs for testing
    base_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/json",
        "https://httpbin.org/uuid",
        "https://httpbin.org/ip",
        "https://httpbin.org/anything",
    ]

    # Create test URLs with parameters
    urls = []
    for i in range(15):  # Create 15 requests
        base_url = base_urls[i % len(base_urls)]
        if "?" in base_url:
            url = f"{base_url}&test_param={i}"
        else:
            url = f"{base_url}?test_param={i}"
        urls.append(url)

    config = CloudflareBypassConfig(
        max_concurrent_requests=5,  # Allow up to 5 concurrent requests
        requests_per_second=3.0,    # Rate limit to 3 requests per second
        timeout=30.0,
        enable_detailed_logging=False  # Reduce noise
    )

    start_time = time.time()

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Making {len(urls)} requests with controlled concurrency...")
            print(f"Max concurrent: {config.max_concurrent_requests}")
            print(f"Rate limit: {config.requests_per_second} req/s")

            results = []

            async def make_request_with_tracking(url: str, request_id: int) -> RequestResult:
                """Make a single request and track the result."""
                request_start = time.time()

                try:
                    result = await bypass.get(url)
                    request_time = time.time() - request_start

                    return RequestResult(
                        url=url,
                        status_code=result.status_code,
                        success=True,
                        error=None,
                        response_time=request_time,
                        challenge_solved=result.challenge_solved,
                        attempts=result.attempts,
                        content_length=len(result.content)
                    )

                except Exception as e:
                    request_time = time.time() - request_start
                    return RequestResult(
                        url=url,
                        status_code=None,
                        success=False,
                        error=str(e),
                        response_time=request_time,
                        challenge_solved=False,
                        attempts=0,
                        content_length=0
                    )

            # Create tasks with tracking
            tasks = [
                make_request_with_tracking(url, i)
                for i, url in enumerate(urls, 1)
            ]

            # Execute with progress reporting
            completed = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                completed += 1

                progress = (completed / len(tasks)) * 100
                print(f"Progress: {completed}/{len(tasks)} ({progress:.1f}%) - "
                      f"Last: {result.url} - "
                      f"{'SUCCESS' if result.success else 'FAILED'}")

            # Calculate statistics
            elapsed = time.time() - start_time
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            avg_response_time = sum(r.response_time for r in results) / len(results)
            actual_rate = len(results) / elapsed

            print(f"\nFinal Results:")
            print(f"Total Requests: {len(results)}")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Success Rate: {(successful/len(results)*100):.1f}%")
            print(f"Total Time: {elapsed:.2f}s")
            print(f"Average Response Time: {avg_response_time:.2f}s")
            print(f"Actual Rate: {actual_rate:.2f} req/s")
            print(f"Target Rate: {config.requests_per_second} req/s")

            # Show challenge statistics
            challenges_solved = sum(1 for r in results if r.challenge_solved)
            if challenges_solved > 0:
                print(f"Challenges Solved: {challenges_solved}")

    except Exception as e:
        print(f"Controlled concurrent requests failed: {e}")


async def batch_processing_example():
    """
    Example of processing requests in batches for better resource control.
    """
    print("\n=== Batch Processing Example ===")

    # Create a larger set of URLs
    urls = []
    for i in range(25):  # 25 total requests
        urls.append(f"https://httpbin.org/delay/{i%3}")  # Vary delay: 0, 1, 2 seconds

    batch_size = 5
    config = CloudflareBypassConfig(
        max_concurrent_requests=batch_size,
        timeout=30.0,
        enable_detailed_logging=False
    )

    start_time = time.time()

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"Processing {len(urls)} URLs in batches of {batch_size}...")

            all_results = []
            batches = [urls[i:i+batch_size] for i in range(0, len(urls), batch_size)]

            for batch_num, batch_urls in enumerate(batches, 1):
                print(f"\nProcessing batch {batch_num}/{len(batches)} "
                      f"({len(batch_urls)} requests)...")

                batch_start = time.time()

                # Process batch concurrently
                tasks = [bypass.get(url) for url in batch_urls]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process batch results
                batch_successful = 0
                for url, result in zip(batch_urls, batch_results):
                    if isinstance(result, Exception):
                        print(f"  FAILED: {url} - {result}")
                    else:
                        print(f"  SUCCESS: {url} - Status {result.status_code}")
                        batch_successful += 1

                batch_time = time.time() - batch_start
                print(f"  Batch completed in {batch_time:.2f}s "
                      f"({batch_successful}/{len(batch_urls)} successful)")

                all_results.extend(batch_results)

                # Optional delay between batches
                if batch_num < len(batches):
                    await asyncio.sleep(1)

            # Final statistics
            elapsed = time.time() - start_time
            successful = sum(1 for r in all_results if not isinstance(r, Exception))
            failed = len(all_results) - successful

            print(f"\nBatch Processing Summary:")
            print(f"Total Requests: {len(all_results)}")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Success Rate: {(successful/len(all_results)*100):.1f}%")
            print(f"Total Time: {elapsed:.2f}s")
            print(f"Average Rate: {len(all_results)/elapsed:.2f} req/s")

    except Exception as e:
        print(f"Batch processing failed: {e}")


async def concurrent_different_methods():
    """
    Example of making concurrent requests with different HTTP methods.
    """
    print("\n=== Concurrent Different Methods Example ===")

    config = CloudflareBypassConfig(
        max_concurrent_requests=4,
        timeout=30.0,
        enable_detailed_logging=True
    )

    try:
        async with CloudflareBypass(config) as bypass:
            print("Making concurrent requests with different HTTP methods...")

            # Define different types of requests
            async def get_request():
                return await bypass.get("https://httpbin.org/get")

            async def post_request():
                return await bypass.post(
                    "https://httpbin.org/post",
                    json_data={"test": "concurrent_post", "timestamp": time.time()}
                )

            async def get_with_headers():
                return await bypass.get(
                    "https://httpbin.org/headers",
                    headers={"X-Test": "concurrent-headers"}
                )

            async def get_with_params():
                return await bypass.get("https://httpbin.org/get?concurrent=true&test=params")

            # Execute all different request types concurrently
            tasks = [
                ("GET", get_request()),
                ("POST", post_request()),
                ("GET with Headers", get_with_headers()),
                ("GET with Params", get_with_params()),
            ]

            start_time = time.time()
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            elapsed = time.time() - start_time

            # Process results
            for (method, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    print(f"{method}: FAILED - {result}")
                else:
                    print(f"{method}: SUCCESS - Status {result.status_code}")
                    print(f"  Challenge Solved: {result.challenge_solved}")
                    print(f"  Content Length: {len(result.content)} bytes")

            print(f"\nAll requests completed in {elapsed:.2f}s")

    except Exception as e:
        print(f"Concurrent different methods failed: {e}")


async def performance_comparison():
    """
    Compare performance between sequential and concurrent requests.
    """
    print("\n=== Performance Comparison ===")

    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/json",
    ]

    config = CloudflareBypassConfig(
        max_concurrent_requests=len(urls),
        timeout=30.0,
        enable_detailed_logging=False
    )

    try:
        async with CloudflareBypass(config) as bypass:
            # Sequential requests
            print("Testing sequential requests...")
            sequential_start = time.time()

            for url in urls:
                result = await bypass.get(url)
                print(f"  Sequential: {url} - {result.status_code}")

            sequential_time = time.time() - sequential_start

            # Small delay between tests
            await asyncio.sleep(2)

            # Concurrent requests
            print("\nTesting concurrent requests...")
            concurrent_start = time.time()

            tasks = [bypass.get(url) for url in urls]
            results = await asyncio.gather(*tasks)

            for url, result in zip(urls, results):
                print(f"  Concurrent: {url} - {result.status_code}")

            concurrent_time = time.time() - concurrent_start

            # Performance comparison
            print(f"\nPerformance Comparison:")
            print(f"Sequential Time: {sequential_time:.2f}s")
            print(f"Concurrent Time: {concurrent_time:.2f}s")
            print(f"Speed Improvement: {sequential_time/concurrent_time:.2f}x faster")
            print(f"Time Saved: {sequential_time-concurrent_time:.2f}s")

    except Exception as e:
        print(f"Performance comparison failed: {e}")


async def main():
    """
    Main function demonstrating various concurrent request patterns.
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Concurrent Requests Examples")
    print("=" * 60)

    # Run all examples
    await simple_concurrent_requests()
    await controlled_concurrent_requests()
    await batch_processing_example()
    await concurrent_different_methods()
    await performance_comparison()

    print("\n" + "=" * 60)
    print("All concurrent examples completed!")
    print("\nKey Takeaways:")
    print("- Use max_concurrent_requests to control resource usage")
    print("- Rate limiting prevents overwhelming target servers")
    print("- Batch processing helps with large request volumes")
    print("- Concurrent requests can significantly improve performance")
    print("- Always handle exceptions properly in concurrent scenarios")
    print("\nNext Steps:")
    print("- Try with your own URLs and different concurrency levels")
    print("- Experiment with rate limiting for different scenarios")
    print("- Check out challenge_solving.py for advanced features")


if __name__ == "__main__":
    # Run the concurrent examples
    asyncio.run(main())