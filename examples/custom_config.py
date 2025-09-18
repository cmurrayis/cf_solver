"""
Custom Configuration Example for CloudflareBypass

This example demonstrates how to create and use custom configurations
for CloudflareBypass to optimize performance for specific use cases,
environments, and requirements.
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig


def create_high_performance_config() -> CloudflareBypassConfig:
    """
    Configuration optimized for high-performance scenarios.

    Best for: High-volume testing, load testing, performance benchmarks
    """
    return CloudflareBypassConfig(
        # Performance optimizations
        max_concurrent_requests=1000,
        requests_per_second=50.0,
        timeout=15.0,  # Shorter timeout for speed

        # Browser emulation
        browser_version="120.0.0.0",

        # Challenge solving - disabled for speed
        solve_javascript_challenges=False,
        solve_managed_challenges=False,
        solve_turnstile_challenges=False,

        # Connection settings
        connection_pool_size=100,
        keep_alive_timeout=30.0,

        # Minimal logging for performance
        enable_detailed_logging=False,
        enable_monitoring=True,
        enable_metrics_collection=True,

        # Custom headers for performance
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }
    )


def create_stealth_config() -> CloudflareBypassConfig:
    """
    Configuration optimized for stealth and challenge solving.

    Best for: Bypassing strict protection, research, careful testing
    """
    return CloudflareBypassConfig(
        # Conservative concurrency
        max_concurrent_requests=5,
        requests_per_second=1.0,  # Very slow to avoid detection
        timeout=120.0,  # Extended timeout for challenges

        # Browser emulation
        browser_version="119.0.0.0",  # Slightly older for better compatibility

        # Full challenge solving enabled
        solve_javascript_challenges=True,
        solve_managed_challenges=True,
        solve_turnstile_challenges=True,
        max_challenge_attempts=5,
        challenge_retry_delay=3.0,

        # Connection settings for stealth
        connection_pool_size=5,
        keep_alive_timeout=60.0,

        # Detailed logging for debugging
        enable_detailed_logging=True,
        enable_monitoring=True,
        enable_metrics_collection=True,

        # Realistic browser headers
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    )


def create_research_config() -> CloudflareBypassConfig:
    """
    Configuration optimized for research and analysis.

    Best for: Academic research, detailed analysis, metric collection
    """
    return CloudflareBypassConfig(
        # Moderate performance
        max_concurrent_requests=20,
        requests_per_second=5.0,
        timeout=60.0,

        # Browser emulation
        browser_version="120.0.0.0",

        # Selective challenge solving
        solve_javascript_challenges=True,
        solve_managed_challenges=False,  # May interfere with research
        solve_turnstile_challenges=True,
        max_challenge_attempts=3,
        challenge_retry_delay=2.0,

        # Connection settings
        connection_pool_size=20,
        keep_alive_timeout=45.0,

        # Full monitoring and metrics
        enable_detailed_logging=True,
        enable_monitoring=True,
        enable_metrics_collection=True,

        # Research-friendly headers
        headers={
            "User-Agent": "CloudflareBypass-Research/1.0 (Compatible; Research Tool)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
    )


def create_mobile_config() -> CloudflareBypassConfig:
    """
    Configuration that emulates mobile browser behavior.

    Best for: Mobile-specific testing, responsive site testing
    """
    return CloudflareBypassConfig(
        # Mobile-appropriate concurrency
        max_concurrent_requests=10,
        requests_per_second=3.0,
        timeout=45.0,

        # Mobile browser version
        browser_version="120.0.0.0",

        # Challenge solving enabled
        solve_javascript_challenges=True,
        solve_managed_challenges=True,
        solve_turnstile_challenges=True,

        # Connection settings for mobile
        connection_pool_size=10,
        keep_alive_timeout=30.0,

        # Standard monitoring
        enable_detailed_logging=False,
        enable_monitoring=True,
        enable_metrics_collection=True,

        # Mobile browser headers
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    )


def create_proxy_config(proxy_url: str) -> CloudflareBypassConfig:
    """
    Configuration for use with proxy servers.

    Args:
        proxy_url: Proxy server URL (e.g., "http://proxy.example.com:8080")

    Best for: Geo-specific testing, IP rotation, privacy
    """
    return CloudflareBypassConfig(
        # Conservative settings for proxy usage
        max_concurrent_requests=15,
        requests_per_second=2.0,
        timeout=90.0,  # Longer timeout for proxy latency

        # Proxy configuration
        proxy_url=proxy_url,

        # Browser emulation
        browser_version="120.0.0.0",

        # Challenge solving enabled
        solve_javascript_challenges=True,
        solve_managed_challenges=True,
        solve_turnstile_challenges=True,
        max_challenge_attempts=3,
        challenge_retry_delay=5.0,  # Longer delay for proxy scenarios

        # Connection settings for proxy
        connection_pool_size=15,
        keep_alive_timeout=60.0,

        # Enhanced logging for proxy debugging
        enable_detailed_logging=True,
        enable_monitoring=True,
        enable_metrics_collection=True,

        # Standard headers
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
    )


async def test_configuration(config: CloudflareBypassConfig, config_name: str, test_urls: list):
    """
    Test a configuration with multiple URLs and report performance.
    """
    print(f"\n=== Testing {config_name} Configuration ===")

    # Show configuration summary
    print(f"Configuration Summary:")
    print(f"  Max Concurrent: {config.max_concurrent_requests}")
    print(f"  Rate Limit: {config.requests_per_second} req/s")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Browser Version: {config.browser_version}")
    print(f"  JS Challenges: {config.solve_javascript_challenges}")
    print(f"  Managed Challenges: {config.solve_managed_challenges}")
    print(f"  Turnstile Challenges: {config.solve_turnstile_challenges}")
    if config.proxy_url:
        print(f"  Proxy: {config.proxy_url}")

    start_time = time.time()
    results = []

    try:
        async with CloudflareBypass(config) as bypass:
            print(f"\nExecuting {len(test_urls)} test requests...")

            for i, url in enumerate(test_urls, 1):
                request_start = time.time()

                try:
                    result = await bypass.get(url)
                    request_time = time.time() - request_start

                    print(f"  {i}/{len(test_urls)}: {url}")
                    print(f"    Status: {result.status_code}")
                    print(f"    Time: {request_time:.3f}s")
                    print(f"    Challenge: {result.challenge_solved}")

                    results.append({
                        'url': url,
                        'success': True,
                        'status_code': result.status_code,
                        'response_time': request_time,
                        'challenge_solved': result.challenge_solved,
                        'attempts': result.attempts
                    })

                except Exception as e:
                    request_time = time.time() - request_start
                    print(f"  {i}/{len(test_urls)}: {url}")
                    print(f"    FAILED: {e}")
                    print(f"    Time: {request_time:.3f}s")

                    results.append({
                        'url': url,
                        'success': False,
                        'error': str(e),
                        'response_time': request_time
                    })

                # Small delay between requests
                await asyncio.sleep(1)

    except Exception as e:
        print(f"Configuration test failed: {e}")
        return None

    # Calculate statistics
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r.get('success', False))
    avg_response_time = sum(r['response_time'] for r in results) / len(results)
    challenges_solved = sum(1 for r in results if r.get('challenge_solved', False))

    print(f"\n{config_name} Results:")
    print(f"  Total Requests: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(results) - successful}")
    print(f"  Success Rate: {(successful/len(results)*100):.1f}%")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Avg Response Time: {avg_response_time:.3f}s")
    print(f"  Challenges Solved: {challenges_solved}")

    return {
        'config_name': config_name,
        'total_requests': len(results),
        'successful': successful,
        'failed': len(results) - successful,
        'success_rate': (successful/len(results)*100),
        'total_time': total_time,
        'avg_response_time': avg_response_time,
        'challenges_solved': challenges_solved,
        'results': results
    }


async def configuration_comparison():
    """
    Compare performance of different configurations.
    """
    print("=== Configuration Performance Comparison ===")

    # Test URLs
    test_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/json"
    ]

    # Configurations to test
    configs = [
        (create_high_performance_config(), "High Performance"),
        (create_stealth_config(), "Stealth"),
        (create_research_config(), "Research"),
        (create_mobile_config(), "Mobile"),
    ]

    comparison_results = []

    for config, name in configs:
        result = await test_configuration(config, name, test_urls)
        if result:
            comparison_results.append(result)

        # Delay between configuration tests
        await asyncio.sleep(3)

    # Summary comparison
    if comparison_results:
        print(f"\n{'='*80}")
        print("CONFIGURATION COMPARISON SUMMARY")
        print(f"{'='*80}")

        print(f"{'Config':<20} {'Success Rate':<12} {'Avg Time':<10} {'Total Time':<11} {'Challenges':<10}")
        print("-" * 80)

        for result in comparison_results:
            print(f"{result['config_name']:<20} "
                  f"{result['success_rate']:<11.1f}% "
                  f"{result['avg_response_time']:<9.3f}s "
                  f"{result['total_time']:<10.2f}s "
                  f"{result['challenges_solved']:<10}")

        # Determine best configurations
        fastest_config = min(comparison_results, key=lambda x: x['avg_response_time'])
        most_reliable = max(comparison_results, key=lambda x: x['success_rate'])

        print(f"\nRecommendations:")
        print(f"  Fastest: {fastest_config['config_name']} "
              f"({fastest_config['avg_response_time']:.3f}s avg)")
        print(f"  Most Reliable: {most_reliable['config_name']} "
              f"({most_reliable['success_rate']:.1f}% success)")


async def custom_configuration_from_file():
    """
    Example of loading configuration from a JSON file.
    """
    print("\n=== Custom Configuration from File ===")

    # Create sample configuration file
    sample_config = {
        "browser_version": "119.0.0.0",
        "max_concurrent_requests": 25,
        "requests_per_second": 8.0,
        "timeout": 45.0,
        "solve_javascript_challenges": True,
        "solve_managed_challenges": False,
        "solve_turnstile_challenges": True,
        "max_challenge_attempts": 3,
        "challenge_retry_delay": 2.5,
        "enable_detailed_logging": True,
        "enable_monitoring": True,
        "enable_metrics_collection": True,
        "headers": {
            "User-Agent": "Custom-CloudflareBypass/1.0",
            "Accept": "application/json,text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9"
        }
    }

    # Save to file
    config_file = Path("custom_config.json")
    with open(config_file, 'w') as f:
        json.dump(sample_config, f, indent=2)

    print(f"Created sample configuration file: {config_file}")

    # Load configuration from file
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)

        # Create CloudflareBypassConfig from loaded data
        config = CloudflareBypassConfig(**config_data)

        print(f"Loaded configuration from file:")
        print(f"  Browser Version: {config.browser_version}")
        print(f"  Max Concurrent: {config.max_concurrent_requests}")
        print(f"  Rate Limit: {config.requests_per_second}")
        print(f"  Custom Headers: {len(config.headers) if config.headers else 0}")

        # Test the loaded configuration
        test_url = "https://httpbin.org/headers"

        async with CloudflareBypass(config) as bypass:
            result = await bypass.get(test_url)

            print(f"\nTest with loaded configuration:")
            print(f"  URL: {test_url}")
            print(f"  Status: {result.status_code}")
            print(f"  Challenge Solved: {result.challenge_solved}")
            print(f"  ✓ Configuration loaded and tested successfully!")

    except Exception as e:
        print(f"Failed to load configuration from file: {e}")
    finally:
        # Clean up
        if config_file.exists():
            config_file.unlink()
            print(f"Cleaned up configuration file: {config_file}")


async def environment_specific_configs():
    """
    Examples of configurations for different environments.
    """
    print("\n=== Environment-Specific Configurations ===")

    environments = {
        "development": CloudflareBypassConfig(
            max_concurrent_requests=5,
            requests_per_second=2.0,
            timeout=30.0,
            solve_javascript_challenges=True,
            enable_detailed_logging=True,
            enable_monitoring=True
        ),

        "testing": CloudflareBypassConfig(
            max_concurrent_requests=20,
            requests_per_second=10.0,
            timeout=20.0,
            solve_javascript_challenges=True,
            enable_detailed_logging=False,
            enable_monitoring=True,
            enable_metrics_collection=True
        ),

        "production": CloudflareBypassConfig(
            max_concurrent_requests=100,
            requests_per_second=25.0,
            timeout=15.0,
            solve_javascript_challenges=False,  # Disabled for speed
            enable_detailed_logging=False,
            enable_monitoring=True,
            enable_metrics_collection=True
        )
    }

    test_url = "https://httpbin.org/get"

    for env_name, config in environments.items():
        print(f"\n--- {env_name.upper()} Environment ---")
        print(f"Max Concurrent: {config.max_concurrent_requests}")
        print(f"Rate Limit: {config.requests_per_second} req/s")
        print(f"Timeout: {config.timeout}s")
        print(f"Detailed Logging: {config.enable_detailed_logging}")

        try:
            async with CloudflareBypass(config) as bypass:
                start_time = time.time()
                result = await bypass.get(test_url)
                elapsed = time.time() - start_time

                print(f"Test Result: Status {result.status_code}, Time {elapsed:.3f}s")

        except Exception as e:
            print(f"Environment test failed: {e}")


async def main():
    """
    Main function demonstrating various custom configuration scenarios.
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CloudflareBypass Custom Configuration Examples")
    print("=" * 70)

    # Run all configuration examples
    await configuration_comparison()
    await custom_configuration_from_file()
    await environment_specific_configs()

    print("\n" + "=" * 70)
    print("All custom configuration examples completed!")
    print("\nConfiguration Best Practices:")
    print("✓ Choose appropriate concurrency for your use case")
    print("✓ Set realistic rate limits to avoid triggering protection")
    print("✓ Use longer timeouts for challenge-heavy scenarios")
    print("✓ Enable detailed logging only during development/debugging")
    print("✓ Consider proxy configuration for geo-specific testing")
    print("✓ Use environment-specific configurations")
    print("✓ Test configurations thoroughly before production use")
    print("\nConfiguration Scenarios:")
    print("• High Performance: Fast, no challenges, high concurrency")
    print("• Stealth: Slow, full challenges, low detection risk")
    print("• Research: Balanced, metrics-focused, moderate speed")
    print("• Mobile: Mobile headers, moderate performance")
    print("• Proxy: Proxy-aware, longer timeouts, enhanced logging")
    print("\nNext Steps:")
    print("- Create configuration files for your specific needs")
    print("- Test different configurations with your target sites")
    print("- Monitor performance and adjust settings accordingly")
    print("- Consider A/B testing different configurations")


if __name__ == "__main__":
    # Run the custom configuration examples
    asyncio.run(main())