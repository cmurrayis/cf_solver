"""Benchmark and testing commands for CloudflareBypass CLI.

Provides comprehensive benchmarking tools for performance testing,
load testing, and challenge solving capability assessment.
"""

import click
import asyncio
import json
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys

from ..bypass import CloudflareBypass, CloudflareBypassConfig
from ..session import SessionManager, create_session_config
from ..metrics import MetricsCollector, ExportFormat
from ..utils import Timer, generate_request_id


@click.group()
def benchmark_group():
    """Benchmark and testing commands."""
    pass


@benchmark_group.command('performance')
@click.option('--url', '-u', required=True, help='Target URL for performance testing')
@click.option('--requests', '-n', default=100, help='Number of requests to execute')
@click.option('--concurrency', '-c', default=10, help='Number of concurrent requests')
@click.option('--warmup', '-w', default=5, help='Number of warmup requests')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--browser-version', default='120.0.0.0', help='Browser version to emulate')
@click.option('--solve-challenges', is_flag=True, default=True, help='Enable challenge solving')
@click.option('--detailed', '-d', is_flag=True, help='Include detailed timing breakdown')
def performance_test(url: str, requests: int, concurrency: int, warmup: int,
                    output: Optional[str], browser_version: str, solve_challenges: bool,
                    detailed: bool) -> None:
    """Run performance benchmark against a target URL."""

    async def run_benchmark():
        click.echo(f"Performance Benchmark")
        click.echo(f"Target URL: {url}")
        click.echo(f"Total Requests: {requests}")
        click.echo(f"Concurrency: {concurrency}")
        click.echo(f"Warmup Requests: {warmup}")
        click.echo("-" * 50)

        # Configure CloudflareBypass
        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrency,
            browser_version=browser_version,
            solve_javascript_challenges=solve_challenges,
            enable_metrics_collection=True,
            enable_monitoring=True
        )

        timing_data = []
        error_count = 0
        challenge_count = 0

        try:
            async with CloudflareBypass(config) as bypass:
                # Warmup phase
                if warmup > 0:
                    click.echo(f"Warming up with {warmup} requests...")
                    for i in range(warmup):
                        try:
                            await bypass.get(url)
                        except Exception:
                            pass

                click.echo("Starting benchmark...")

                # Benchmark phase
                semaphore = asyncio.Semaphore(concurrency)

                async def timed_request(request_id: int):
                    async with semaphore:
                        timer = Timer()
                        timer.start()

                        try:
                            result = await bypass.get(url)
                            elapsed = timer.stop()

                            return {
                                'request_id': request_id,
                                'elapsed_time': elapsed,
                                'status_code': result.status_code,
                                'content_length': len(result.content),
                                'challenge_solved': result.challenge_solved,
                                'attempts': result.attempts,
                                'success': True,
                                'error': None
                            }
                        except Exception as e:
                            elapsed = timer.stop()
                            return {
                                'request_id': request_id,
                                'elapsed_time': elapsed,
                                'status_code': None,
                                'content_length': 0,
                                'challenge_solved': False,
                                'attempts': 0,
                                'success': False,
                                'error': str(e)
                            }

                # Execute benchmark
                start_time = time.time()
                tasks = [timed_request(i) for i in range(requests)]

                completed = 0
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    timing_data.append(result)
                    completed += 1

                    if result['success']:
                        if result['challenge_solved']:
                            challenge_count += 1
                    else:
                        error_count += 1

                    # Progress update
                    if completed % max(1, requests // 10) == 0:
                        progress = (completed / requests) * 100
                        click.echo(f"Progress: {completed}/{requests} ({progress:.1f}%)")

                total_time = time.time() - start_time

                # Calculate statistics
                successful_requests = [r for r in timing_data if r['success']]
                if successful_requests:
                    response_times = [r['elapsed_time'] for r in successful_requests]

                    stats = {
                        'total_requests': requests,
                        'successful_requests': len(successful_requests),
                        'failed_requests': error_count,
                        'success_rate': (len(successful_requests) / requests) * 100,
                        'challenges_encountered': challenge_count,
                        'challenge_rate': (challenge_count / len(successful_requests)) * 100 if successful_requests else 0,
                        'total_time': total_time,
                        'requests_per_second': requests / total_time,
                        'response_times': {
                            'min': min(response_times),
                            'max': max(response_times),
                            'mean': statistics.mean(response_times),
                            'median': statistics.median(response_times),
                            'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
                            'p99': statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times),
                            'std_dev': statistics.stdev(response_times) if len(response_times) > 1 else 0
                        },
                        'detailed_results': timing_data if detailed else []
                    }
                else:
                    stats = {
                        'total_requests': requests,
                        'successful_requests': 0,
                        'failed_requests': error_count,
                        'success_rate': 0,
                        'error': 'All requests failed'
                    }

                # Output results
                if output:
                    with open(output, 'w') as f:
                        json.dump(stats, f, indent=2)
                    click.echo(f"Detailed results saved to {output}")

                # Display summary
                click.echo(f"\nBenchmark Results:")
                click.echo(f"Total Requests: {stats['total_requests']}")
                click.echo(f"Successful: {stats['successful_requests']}")
                click.echo(f"Failed: {stats['failed_requests']}")
                click.echo(f"Success Rate: {stats['success_rate']:.1f}%")

                if 'response_times' in stats:
                    rt = stats['response_times']
                    click.echo(f"Challenges Encountered: {stats['challenges_encountered']}")
                    click.echo(f"Challenge Rate: {stats['challenge_rate']:.1f}%")
                    click.echo(f"Total Time: {stats['total_time']:.2f}s")
                    click.echo(f"Requests/sec: {stats['requests_per_second']:.2f}")
                    click.echo(f"\nResponse Times:")
                    click.echo(f"  Min: {rt['min']:.3f}s")
                    click.echo(f"  Max: {rt['max']:.3f}s")
                    click.echo(f"  Mean: {rt['mean']:.3f}s")
                    click.echo(f"  Median: {rt['median']:.3f}s")
                    click.echo(f"  95th percentile: {rt['p95']:.3f}s")
                    click.echo(f"  99th percentile: {rt['p99']:.3f}s")
                    click.echo(f"  Std Dev: {rt['std_dev']:.3f}s")

        except Exception as e:
            click.echo(f"Benchmark failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(run_benchmark())


@benchmark_group.command('load')
@click.option('--url', '-u', required=True, help='Target URL for load testing')
@click.option('--duration', '-d', default=60, help='Test duration in seconds')
@click.option('--ramp-up', '-r', default=10, help='Ramp-up time in seconds')
@click.option('--max-concurrency', '-c', default=100, help='Maximum concurrent users')
@click.option('--target-rate', default=50.0, help='Target requests per second')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--real-time', is_flag=True, help='Show real-time statistics')
def load_test(url: str, duration: int, ramp_up: int, max_concurrency: int,
             target_rate: float, output: Optional[str], real_time: bool) -> None:
    """Run load test with gradual ramp-up."""

    async def run_load_test():
        click.echo(f"Load Test Configuration:")
        click.echo(f"Target URL: {url}")
        click.echo(f"Duration: {duration}s")
        click.echo(f"Ramp-up: {ramp_up}s")
        click.echo(f"Max Concurrency: {max_concurrency}")
        click.echo(f"Target Rate: {target_rate} req/s")
        click.echo("-" * 50)

        config = CloudflareBypassConfig(
            max_concurrent_requests=max_concurrency * 2,
            requests_per_second=target_rate * 2,
            enable_metrics_collection=True,
            enable_monitoring=True
        )

        test_results = []
        start_time = time.time()

        try:
            async with CloudflareBypass(config) as bypass:
                # Shared state
                active_requests = 0
                total_requests = 0
                successful_requests = 0
                failed_requests = 0

                async def make_request():
                    nonlocal active_requests, total_requests, successful_requests, failed_requests

                    active_requests += 1
                    total_requests += 1
                    request_start = time.time()

                    try:
                        result = await bypass.get(url)
                        elapsed = time.time() - request_start
                        successful_requests += 1

                        test_results.append({
                            'timestamp': request_start,
                            'elapsed_time': elapsed,
                            'status_code': result.status_code,
                            'challenge_solved': result.challenge_solved,
                            'success': True
                        })

                    except Exception as e:
                        elapsed = time.time() - request_start
                        failed_requests += 1

                        test_results.append({
                            'timestamp': request_start,
                            'elapsed_time': elapsed,
                            'status_code': None,
                            'challenge_solved': False,
                            'success': False,
                            'error': str(e)
                        })

                    finally:
                        active_requests -= 1

                # Ramp-up phase
                current_concurrency = 1
                concurrency_step = max_concurrency / (ramp_up * 10)  # Increase every 0.1s during ramp-up

                # Main test loop
                test_end_time = start_time + ramp_up + duration
                last_stats_time = start_time

                while time.time() < test_end_time:
                    current_time = time.time()

                    # Adjust concurrency during ramp-up
                    if current_time < start_time + ramp_up:
                        target_concurrency = min(max_concurrency, int((current_time - start_time) * concurrency_step))
                        current_concurrency = max(1, target_concurrency)
                    else:
                        current_concurrency = max_concurrency

                    # Launch requests up to current concurrency limit
                    while active_requests < current_concurrency:
                        asyncio.create_task(make_request())

                    # Real-time statistics
                    if real_time and current_time - last_stats_time >= 5.0:
                        elapsed = current_time - start_time
                        rate = total_requests / elapsed if elapsed > 0 else 0
                        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

                        click.echo(f"[{elapsed:.0f}s] Active: {active_requests}, "
                                 f"Total: {total_requests}, Rate: {rate:.1f} req/s, "
                                 f"Success: {success_rate:.1f}%")
                        last_stats_time = current_time

                    await asyncio.sleep(0.1)

                # Wait for remaining requests
                while active_requests > 0:
                    await asyncio.sleep(0.1)

                # Calculate final statistics
                total_test_time = time.time() - start_time
                overall_rate = total_requests / total_test_time if total_test_time > 0 else 0
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

                # Response time statistics
                successful_results = [r for r in test_results if r['success']]
                if successful_results:
                    response_times = [r['elapsed_time'] for r in successful_results]
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
                else:
                    avg_response_time = 0
                    p95_response_time = 0

                # Challenge statistics
                challenges_solved = sum(1 for r in successful_results if r['challenge_solved'])

                final_stats = {
                    'test_config': {
                        'url': url,
                        'duration': duration,
                        'ramp_up': ramp_up,
                        'max_concurrency': max_concurrency,
                        'target_rate': target_rate
                    },
                    'results': {
                        'total_requests': total_requests,
                        'successful_requests': successful_requests,
                        'failed_requests': failed_requests,
                        'success_rate': success_rate,
                        'challenges_solved': challenges_solved,
                        'overall_rate': overall_rate,
                        'avg_response_time': avg_response_time,
                        'p95_response_time': p95_response_time,
                        'total_test_time': total_test_time
                    },
                    'detailed_results': test_results
                }

                # Output results
                if output:
                    with open(output, 'w') as f:
                        json.dump(final_stats, f, indent=2)
                    click.echo(f"Detailed results saved to {output}")

                click.echo(f"\nLoad Test Results:")
                click.echo(f"Total Requests: {total_requests}")
                click.echo(f"Successful: {successful_requests}")
                click.echo(f"Failed: {failed_requests}")
                click.echo(f"Success Rate: {success_rate:.1f}%")
                click.echo(f"Challenges Solved: {challenges_solved}")
                click.echo(f"Overall Rate: {overall_rate:.1f} req/s")
                click.echo(f"Avg Response Time: {avg_response_time:.3f}s")
                click.echo(f"95th Percentile: {p95_response_time:.3f}s")
                click.echo(f"Total Test Time: {total_test_time:.1f}s")

        except Exception as e:
            click.echo(f"Load test failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(run_load_test())


@benchmark_group.command('challenge')
@click.option('--url', '-u', required=True, help='URL known to present challenges')
@click.option('--attempts', '-n', default=50, help='Number of challenge solving attempts')
@click.option('--browser-versions', '-b', multiple=True,
              help='Browser versions to test (can specify multiple)')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--timeout', '-t', default=30, help='Challenge solving timeout')
def challenge_test(url: str, attempts: int, browser_versions: tuple,
                  output: Optional[str], timeout: int) -> None:
    """Test challenge solving capabilities and success rates."""

    async def run_challenge_test():
        if not browser_versions:
            browser_versions_list = ['120.0.0.0', '119.0.0.0', '121.0.0.0']
        else:
            browser_versions_list = list(browser_versions)

        click.echo(f"Challenge Solving Test")
        click.echo(f"Target URL: {url}")
        click.echo(f"Attempts per version: {attempts}")
        click.echo(f"Browser versions: {', '.join(browser_versions_list)}")
        click.echo("-" * 50)

        all_results = {}

        for browser_version in browser_versions_list:
            click.echo(f"\nTesting with browser version {browser_version}...")

            config = CloudflareBypassConfig(
                browser_version=browser_version,
                solve_javascript_challenges=True,
                challenge_timeout=timeout,
                enable_metrics_collection=True
            )

            version_results = []
            successful_solves = 0
            total_solve_time = 0

            try:
                async with CloudflareBypass(config) as bypass:
                    for attempt in range(attempts):
                        timer = Timer()
                        timer.start()

                        try:
                            result = await bypass.get(url)
                            solve_time = timer.stop()
                            total_solve_time += solve_time

                            if result.challenge_solved:
                                successful_solves += 1

                            version_results.append({
                                'attempt': attempt + 1,
                                'success': result.status_code == 200,
                                'challenge_encountered': result.challenge_solved,
                                'solve_time': solve_time,
                                'attempts': result.attempts,
                                'status_code': result.status_code
                            })

                        except Exception as e:
                            solve_time = timer.stop()
                            version_results.append({
                                'attempt': attempt + 1,
                                'success': False,
                                'challenge_encountered': False,
                                'solve_time': solve_time,
                                'attempts': 0,
                                'status_code': None,
                                'error': str(e)
                            })

                        # Progress indicator
                        if (attempt + 1) % 10 == 0:
                            progress = ((attempt + 1) / attempts) * 100
                            click.echo(f"  Progress: {attempt + 1}/{attempts} ({progress:.0f}%)")

                # Calculate statistics for this version
                success_rate = (successful_solves / attempts) * 100
                avg_solve_time = total_solve_time / attempts if attempts > 0 else 0

                solve_times = [r['solve_time'] for r in version_results if r['challenge_encountered']]
                if solve_times:
                    min_solve_time = min(solve_times)
                    max_solve_time = max(solve_times)
                else:
                    min_solve_time = max_solve_time = 0

                all_results[browser_version] = {
                    'attempts': attempts,
                    'successful_solves': successful_solves,
                    'success_rate': success_rate,
                    'avg_solve_time': avg_solve_time,
                    'min_solve_time': min_solve_time,
                    'max_solve_time': max_solve_time,
                    'detailed_results': version_results
                }

                click.echo(f"  Results: {successful_solves}/{attempts} successful ({success_rate:.1f}%)")
                click.echo(f"  Avg solve time: {avg_solve_time:.3f}s")

            except Exception as e:
                click.echo(f"  Error testing version {browser_version}: {e}")
                all_results[browser_version] = {'error': str(e)}

        # Output final results
        if output:
            with open(output, 'w') as f:
                json.dump(all_results, f, indent=2)
            click.echo(f"\nDetailed results saved to {output}")

        # Summary
        click.echo(f"\nChallenge Test Summary:")
        for version, results in all_results.items():
            if 'error' not in results:
                click.echo(f"  {version}: {results['success_rate']:.1f}% success rate, "
                         f"{results['avg_solve_time']:.3f}s avg time")
            else:
                click.echo(f"  {version}: ERROR - {results['error']}")

    asyncio.run(run_challenge_test())


@benchmark_group.command('compare')
@click.option('--config1', '-c1', required=True, type=click.Path(exists=True),
              help='First configuration file')
@click.option('--config2', '-c2', required=True, type=click.Path(exists=True),
              help='Second configuration file')
@click.option('--url', '-u', required=True, help='Target URL for comparison')
@click.option('--requests', '-n', default=50, help='Number of requests per configuration')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
def compare_configs(config1: str, config2: str, url: str, requests: int,
                   output: Optional[str]) -> None:
    """Compare performance between two different configurations."""

    async def run_comparison():
        click.echo(f"Configuration Comparison Test")
        click.echo(f"Target URL: {url}")
        click.echo(f"Requests per config: {requests}")
        click.echo(f"Config 1: {config1}")
        click.echo(f"Config 2: {config2}")
        click.echo("-" * 50)

        # Load configurations
        try:
            with open(config1, 'r') as f:
                config1_data = json.load(f)
            with open(config2, 'r') as f:
                config2_data = json.load(f)
        except Exception as e:
            click.echo(f"Error loading configuration files: {e}", err=True)
            return

        results = {}

        for config_name, config_data in [("Config 1", config1_data), ("Config 2", config2_data)]:
            click.echo(f"\nTesting {config_name}...")

            # Create CloudflareBypass config from JSON
            bypass_config = CloudflareBypassConfig(**config_data)

            timing_data = []
            successful = 0
            challenges_solved = 0

            try:
                async with CloudflareBypass(bypass_config) as bypass:
                    for i in range(requests):
                        timer = Timer()
                        timer.start()

                        try:
                            result = await bypass.get(url)
                            elapsed = timer.stop()

                            if result.status_code == 200:
                                successful += 1
                            if result.challenge_solved:
                                challenges_solved += 1

                            timing_data.append(elapsed)

                        except Exception:
                            timer.stop()

                        if (i + 1) % 10 == 0:
                            progress = ((i + 1) / requests) * 100
                            click.echo(f"  Progress: {i + 1}/{requests} ({progress:.0f}%)")

                # Calculate statistics
                if timing_data:
                    avg_time = statistics.mean(timing_data)
                    min_time = min(timing_data)
                    max_time = max(timing_data)
                    p95_time = statistics.quantiles(timing_data, n=20)[18] if len(timing_data) >= 20 else max_time
                else:
                    avg_time = min_time = max_time = p95_time = 0

                results[config_name] = {
                    'config_file': config1 if config_name == "Config 1" else config2,
                    'config_data': config_data,
                    'total_requests': requests,
                    'successful_requests': successful,
                    'success_rate': (successful / requests) * 100,
                    'challenges_solved': challenges_solved,
                    'avg_response_time': avg_time,
                    'min_response_time': min_time,
                    'max_response_time': max_time,
                    'p95_response_time': p95_time,
                    'timing_data': timing_data
                }

                click.echo(f"  Success rate: {results[config_name]['success_rate']:.1f}%")
                click.echo(f"  Avg response time: {avg_time:.3f}s")
                click.echo(f"  Challenges solved: {challenges_solved}")

            except Exception as e:
                click.echo(f"  Error: {e}")
                results[config_name] = {'error': str(e)}

        # Output comparison
        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
            click.echo(f"\nDetailed results saved to {output}")

        # Summary comparison
        click.echo(f"\nComparison Summary:")
        if "Config 1" in results and "Config 2" in results:
            c1 = results["Config 1"]
            c2 = results["Config 2"]

            if 'error' not in c1 and 'error' not in c2:
                click.echo(f"Success Rate: {c1['success_rate']:.1f}% vs {c2['success_rate']:.1f}%")
                click.echo(f"Avg Response Time: {c1['avg_response_time']:.3f}s vs {c2['avg_response_time']:.3f}s")
                click.echo(f"Challenges Solved: {c1['challenges_solved']} vs {c2['challenges_solved']}")

                # Determine winner
                if c1['success_rate'] > c2['success_rate']:
                    click.echo("Winner: Config 1 (higher success rate)")
                elif c2['success_rate'] > c1['success_rate']:
                    click.echo("Winner: Config 2 (higher success rate)")
                elif c1['avg_response_time'] < c2['avg_response_time']:
                    click.echo("Winner: Config 1 (faster response time)")
                elif c2['avg_response_time'] < c1['avg_response_time']:
                    click.echo("Winner: Config 2 (faster response time)")
                else:
                    click.echo("Result: Tie")

    asyncio.run(run_comparison())


# Export public API
__all__ = [
    'benchmark_group',
]