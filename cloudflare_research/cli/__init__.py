"""Command-line interface for CloudflareBypass research tool.

Provides comprehensive CLI commands for executing requests, benchmarking,
testing, and managing sessions with CloudflareBypass.
"""

import click
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Import CLI modules
from .requests import requests_group
from .benchmark import benchmark_group

# Import core functionality
from ..bypass import CloudflareBypass, CloudflareBypassConfig
from ..session import SessionManager, create_session_config
from ..metrics import MetricsCollector, ExportFormat


# Configure logging for CLI
def setup_logging(verbose: int = 0) -> None:
    """Setup logging based on verbosity level."""
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@click.group()
@click.option('--verbose', '-v', count=True, help='Increase verbosity (use -vv for debug)')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx: click.Context, verbose: int, config: Optional[str]) -> None:
    """CloudflareBypass - High-performance Cloudflare challenge research tool.

    A comprehensive tool for researching and testing Cloudflare protection mechanisms
    with browser emulation, challenge solving, and high-concurrency capabilities.
    """
    setup_logging(verbose)

    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store configuration
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config

    # Load configuration if provided
    if config:
        try:
            with open(config, 'r') as f:
                config_data = json.load(f)
                ctx.obj['config'] = config_data
        except Exception as e:
            click.echo(f"Error loading config file: {e}", err=True)
            sys.exit(1)
    else:
        ctx.obj['config'] = {}


@cli.command()
@click.option('--url', '-u', required=True, help='Target URL to test')
@click.option('--method', '-m', default='GET', type=click.Choice(['GET', 'POST']), help='HTTP method')
@click.option('--headers', '-h', multiple=True, help='Headers in format "Name:Value"')
@click.option('--data', '-d', help='POST data')
@click.option('--timeout', '-t', default=30, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file for response')
@click.option('--json-output', is_flag=True, help='Output response as JSON')
@click.pass_context
def request(ctx: click.Context, url: str, method: str, headers: tuple,
           data: Optional[str], timeout: int, output: Optional[str],
           json_output: bool) -> None:
    """Execute a single request with Cloudflare bypass."""

    async def execute_request():
        # Parse headers
        parsed_headers = {}
        for header in headers:
            if ':' in header:
                key, value = header.split(':', 1)
                parsed_headers[key.strip()] = value.strip()

        # Configure CloudflareBypass
        config = CloudflareBypassConfig(
            timeout=timeout,
            enable_detailed_logging=ctx.obj['verbose'] >= 2
        )

        try:
            async with CloudflareBypass(config) as bypass:
                click.echo(f"Executing {method} request to {url}")

                if method == 'GET':
                    result = await bypass.get(url, headers=parsed_headers)
                else:
                    result = await bypass.post(url, data=data, headers=parsed_headers)

                # Prepare output
                if json_output:
                    output_data = {
                        "url": url,
                        "method": method,
                        "status_code": result.status_code,
                        "headers": dict(result.headers),
                        "content": result.content,
                        "timing": result.timing.to_dict() if result.timing else None,
                        "challenge_solved": result.challenge_solved,
                        "attempts": result.attempts
                    }
                    output_text = json.dumps(output_data, indent=2)
                else:
                    output_text = f"""Request Results:
URL: {url}
Method: {method}
Status Code: {result.status_code}
Content Length: {len(result.content)} bytes
Challenge Solved: {result.challenge_solved}
Attempts: {result.attempts}

Headers:
{chr(10).join(f"  {k}: {v}" for k, v in result.headers.items())}

Response Content:
{result.content}
"""

                # Output results
                if output:
                    with open(output, 'w') as f:
                        f.write(output_text)
                    click.echo(f"Results saved to {output}")
                else:
                    click.echo(output_text)

        except Exception as e:
            click.echo(f"Request failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(execute_request())


@cli.command()
@click.option('--concurrency', '-c', default=10, help='Number of concurrent requests')
@click.option('--rate', '-r', default=10.0, help='Requests per second')
@click.option('--duration', '-d', default=60, help='Test duration in seconds')
@click.option('--url', '-u', required=True, help='Target URL')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.pass_context
def stress_test(ctx: click.Context, concurrency: int, rate: float,
               duration: int, url: str, output: Optional[str]) -> None:
    """Run a stress test against a target URL."""

    async def run_stress_test():
        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrency,
            requests_per_second=rate,
            enable_metrics_collection=True
        )

        click.echo(f"Starting stress test:")
        click.echo(f"  URL: {url}")
        click.echo(f"  Concurrency: {concurrency}")
        click.echo(f"  Rate: {rate} req/s")
        click.echo(f"  Duration: {duration}s")

        try:
            async with CloudflareBypass(config) as bypass:
                # Start metrics collection
                start_time = asyncio.get_event_loop().time()
                requests_made = 0
                successful_requests = 0
                failed_requests = 0

                async def make_request():
                    nonlocal requests_made, successful_requests, failed_requests
                    try:
                        result = await bypass.get(url)
                        requests_made += 1
                        if result.status_code == 200:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                    except Exception:
                        requests_made += 1
                        failed_requests += 1

                # Schedule requests
                tasks = []
                while asyncio.get_event_loop().time() - start_time < duration:
                    # Create batch of requests
                    batch_size = min(concurrency, int(rate))
                    for _ in range(batch_size):
                        task = asyncio.create_task(make_request())
                        tasks.append(task)

                    # Wait for rate limiting
                    await asyncio.sleep(1.0)

                    # Clean up completed tasks
                    tasks = [t for t in tasks if not t.done()]

                # Wait for remaining tasks
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Calculate results
                total_time = asyncio.get_event_loop().time() - start_time
                actual_rate = requests_made / total_time if total_time > 0 else 0
                success_rate = (successful_requests / requests_made * 100) if requests_made > 0 else 0

                results = {
                    "test_config": {
                        "url": url,
                        "concurrency": concurrency,
                        "target_rate": rate,
                        "duration": duration
                    },
                    "results": {
                        "total_requests": requests_made,
                        "successful_requests": successful_requests,
                        "failed_requests": failed_requests,
                        "success_rate_percent": success_rate,
                        "actual_rate": actual_rate,
                        "total_time": total_time
                    }
                }

                # Output results
                output_text = f"""Stress Test Results:
Total Requests: {requests_made}
Successful: {successful_requests}
Failed: {failed_requests}
Success Rate: {success_rate:.1f}%
Actual Rate: {actual_rate:.1f} req/s
Total Time: {total_time:.1f}s
"""

                if output:
                    with open(output, 'w') as f:
                        json.dump(results, f, indent=2)
                    click.echo(f"Detailed results saved to {output}")

                click.echo(output_text)

        except Exception as e:
            click.echo(f"Stress test failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(run_stress_test())


@cli.command()
@click.option('--format', '-f', default='json',
              type=click.Choice(['json', 'csv', 'prometheus']),
              help='Export format')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output file')
@click.option('--hours', default=1, help='Hours of metrics to export')
def export_metrics(format: str, output: str, hours: int) -> None:
    """Export collected metrics."""

    async def export():
        try:
            # Create metrics collector to access existing data
            collector = MetricsCollector()

            # Export metrics
            export_format = ExportFormat(format)
            exported_file = await collector.export_metrics(
                format=export_format,
                hours=hours,
                filename=output
            )

            click.echo(f"Metrics exported to {exported_file}")

        except Exception as e:
            click.echo(f"Export failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(export())


@cli.command()
@click.option('--config-file', '-c', type=click.Path(), help='Save configuration to file')
def generate_config(config_file: Optional[str]) -> None:
    """Generate a sample configuration file."""

    sample_config = {
        "browser_version": "120.0.0.0",
        "max_concurrent_requests": 1000,
        "requests_per_second": 100.0,
        "timeout": 30.0,
        "enable_monitoring": True,
        "enable_metrics_collection": True,
        "solve_javascript_challenges": True,
        "solve_managed_challenges": False,
        "solve_turnstile_challenges": False,
        "proxy_url": None,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    }

    config_json = json.dumps(sample_config, indent=2)

    if config_file:
        with open(config_file, 'w') as f:
            f.write(config_json)
        click.echo(f"Configuration saved to {config_file}")
    else:
        click.echo("Sample configuration:")
        click.echo(config_json)


@cli.command()
def version() -> None:
    """Show version information."""
    try:
        from .. import __version__
        version_str = __version__
    except ImportError:
        version_str = "unknown"

    click.echo(f"CloudflareBypass CLI version {version_str}")
    click.echo("High-performance Cloudflare challenge research tool")


# Add command groups
cli.add_command(requests_group, name='requests')
cli.add_command(benchmark_group, name='benchmark')


def main() -> None:
    """Main CLI entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()


# Export public API
__all__ = [
    'cli',
    'main',
]