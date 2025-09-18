"""Request execution commands for CloudflareBypass CLI.

Provides comprehensive commands for executing HTTP requests with various
options, batch processing, and session management.
"""

import click
import asyncio
import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import time

from ..bypass import CloudflareBypass, CloudflareBypassConfig
from ..session import SessionManager, create_session_config, create_session_manager
from ..models.test_request import TestRequest, HttpMethod
from ..utils import generate_request_id


@click.group()
def requests_group():
    """Request execution commands."""
    pass


@requests_group.command('single')
@click.option('--url', '-u', required=True, help='Target URL')
@click.option('--method', '-m', default='GET', type=click.Choice(['GET', 'POST', 'PUT', 'DELETE']),
              help='HTTP method')
@click.option('--headers', '-h', multiple=True, help='Headers in format "Name:Value"')
@click.option('--data', '-d', help='Request body data')
@click.option('--json-data', '-j', help='JSON data to send')
@click.option('--timeout', '-t', default=30, help='Request timeout in seconds')
@click.option('--proxy', '-p', help='Proxy URL (http://host:port)')
@click.option('--browser-version', default='120.0.0.0', help='Browser version to emulate')
@click.option('--solve-challenges', is_flag=True, default=True, help='Enable challenge solving')
@click.option('--output', '-o', type=click.Path(), help='Output file for response')
@click.option('--save-headers', is_flag=True, help='Save response headers')
@click.option('--follow-redirects', is_flag=True, default=True, help='Follow redirects')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def single_request(url: str, method: str, headers: tuple, data: Optional[str],
                  json_data: Optional[str], timeout: int, proxy: Optional[str],
                  browser_version: str, solve_challenges: bool, output: Optional[str],
                  save_headers: bool, follow_redirects: bool, verbose: bool) -> None:
    """Execute a single HTTP request with Cloudflare bypass."""

    async def execute():
        # Parse headers
        parsed_headers = {}
        for header in headers:
            if ':' in header:
                key, value = header.split(':', 1)
                parsed_headers[key.strip()] = value.strip()

        # Parse JSON data if provided
        request_data = data
        if json_data:
            try:
                parsed_json = json.loads(json_data)
                request_data = json.dumps(parsed_json)
                parsed_headers['Content-Type'] = 'application/json'
            except json.JSONDecodeError as e:
                click.echo(f"Invalid JSON data: {e}", err=True)
                return

        # Configure CloudflareBypass
        config = CloudflareBypassConfig(
            browser_version=browser_version,
            timeout=timeout,
            proxy_url=proxy,
            solve_javascript_challenges=solve_challenges,
            follow_redirects=follow_redirects,
            enable_detailed_logging=verbose
        )

        if verbose:
            click.echo(f"Executing {method} request to {url}")
            if parsed_headers:
                click.echo(f"Headers: {parsed_headers}")
            if request_data:
                click.echo(f"Data: {request_data[:200]}{'...' if len(request_data) > 200 else ''}")

        start_time = time.time()

        try:
            async with CloudflareBypass(config) as bypass:
                # Execute request
                if method == 'GET':
                    result = await bypass.get(url, headers=parsed_headers)
                elif method == 'POST':
                    if json_data:
                        result = await bypass.post(url, json_data=json.loads(json_data), headers=parsed_headers)
                    else:
                        result = await bypass.post(url, data=request_data, headers=parsed_headers)
                else:
                    # For other methods, use the raw HTTP client
                    result = await bypass._request(method, url, data=request_data, headers=parsed_headers)

                elapsed_time = time.time() - start_time

                # Prepare output
                output_data = {
                    "request": {
                        "url": url,
                        "method": method,
                        "headers": parsed_headers,
                        "data": request_data
                    },
                    "response": {
                        "status_code": result.status_code,
                        "headers": dict(result.headers) if save_headers else {},
                        "content_length": len(result.content),
                        "content": result.content
                    },
                    "metrics": {
                        "elapsed_time": elapsed_time,
                        "challenge_solved": result.challenge_solved,
                        "attempts": result.attempts,
                        "timing": result.timing.to_dict() if result.timing else None
                    },
                    "timestamp": datetime.now().isoformat()
                }

                # Output results
                if output:
                    with open(output, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    click.echo(f"Results saved to {output}")
                else:
                    click.echo(f"Status: {result.status_code}")
                    click.echo(f"Content-Length: {len(result.content)} bytes")
                    click.echo(f"Challenge Solved: {result.challenge_solved}")
                    click.echo(f"Elapsed Time: {elapsed_time:.3f}s")

                    if verbose or not output:
                        if save_headers:
                            click.echo("\nResponse Headers:")
                            for k, v in result.headers.items():
                                click.echo(f"  {k}: {v}")

                        click.echo(f"\nResponse Content:\n{result.content}")

        except Exception as e:
            click.echo(f"Request failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(execute())


@requests_group.command('batch')
@click.option('--input', '-i', required=True, type=click.Path(exists=True),
              help='Input file with URLs (one per line) or JSON request specifications')
@click.option('--format', '-f', default='text', type=click.Choice(['text', 'json', 'csv']),
              help='Input file format')
@click.option('--concurrency', '-c', default=10, help='Number of concurrent requests')
@click.option('--rate', '-r', default=10.0, help='Requests per second')
@click.option('--timeout', '-t', default=30, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.option('--browser-version', default='120.0.0.0', help='Browser version to emulate')
@click.option('--solve-challenges', is_flag=True, default=True, help='Enable challenge solving')
@click.option('--proxy', '-p', help='Proxy URL')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def batch_requests(input: str, format: str, concurrency: int, rate: float,
                  timeout: int, output: Optional[str], browser_version: str,
                  solve_challenges: bool, proxy: Optional[str], verbose: bool) -> None:
    """Execute multiple requests from a file."""

    async def execute_batch():
        # Load requests from input file
        requests_data = []

        try:
            with open(input, 'r') as f:
                if format == 'text':
                    # Simple text format - one URL per line
                    for line_num, line in enumerate(f, 1):
                        url = line.strip()
                        if url and not url.startswith('#'):
                            requests_data.append({
                                'id': f'req_{line_num}',
                                'url': url,
                                'method': 'GET'
                            })

                elif format == 'json':
                    # JSON format with request specifications
                    data = json.load(f)
                    if isinstance(data, list):
                        requests_data = data
                    else:
                        requests_data = [data]

                elif format == 'csv':
                    # CSV format: url,method,headers,data
                    reader = csv.DictReader(f)
                    for row_num, row in enumerate(reader, 1):
                        request_spec = {
                            'id': f'req_{row_num}',
                            'url': row['url'],
                            'method': row.get('method', 'GET')
                        }
                        if 'headers' in row and row['headers']:
                            request_spec['headers'] = json.loads(row['headers'])
                        if 'data' in row and row['data']:
                            request_spec['data'] = row['data']
                        requests_data.append(request_spec)

        except Exception as e:
            click.echo(f"Failed to load input file: {e}", err=True)
            return

        if not requests_data:
            click.echo("No requests found in input file", err=True)
            return

        click.echo(f"Loaded {len(requests_data)} requests")
        click.echo(f"Concurrency: {concurrency}, Rate: {rate} req/s")

        # Configure CloudflareBypass
        config = CloudflareBypassConfig(
            max_concurrent_requests=concurrency,
            requests_per_second=rate,
            browser_version=browser_version,
            timeout=timeout,
            proxy_url=proxy,
            solve_javascript_challenges=solve_challenges,
            enable_detailed_logging=verbose,
            enable_metrics_collection=True
        )

        results = []
        start_time = time.time()

        try:
            async with CloudflareBypass(config) as bypass:
                # Create session for batch processing
                if bypass.session_manager:
                    session_config = create_session_config(
                        name=f"Batch Requests {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        concurrency_limit=concurrency,
                        rate_limit=rate
                    )
                    session = await bypass.session_manager.create_session(session_config)
                    await session.start()

                # Process requests
                async def process_request(req_data):
                    req_id = req_data.get('id', generate_request_id())
                    url = req_data['url']
                    method = req_data.get('method', 'GET')
                    headers = req_data.get('headers', {})
                    data = req_data.get('data')

                    try:
                        if method == 'GET':
                            result = await bypass.get(url, headers=headers)
                        else:
                            result = await bypass.post(url, data=data, headers=headers)

                        return {
                            'id': req_id,
                            'url': url,
                            'method': method,
                            'status_code': result.status_code,
                            'content_length': len(result.content),
                            'challenge_solved': result.challenge_solved,
                            'attempts': result.attempts,
                            'success': True,
                            'error': None
                        }

                    except Exception as e:
                        return {
                            'id': req_id,
                            'url': url,
                            'method': method,
                            'status_code': None,
                            'content_length': 0,
                            'challenge_solved': False,
                            'attempts': 0,
                            'success': False,
                            'error': str(e)
                        }

                # Execute requests with progress reporting
                semaphore = asyncio.Semaphore(concurrency)

                async def limited_request(req_data):
                    async with semaphore:
                        return await process_request(req_data)

                # Process all requests
                click.echo("Processing requests...")
                tasks = [limited_request(req) for req in requests_data]

                # Execute with progress updates
                completed = 0
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)
                    completed += 1

                    if verbose or completed % 10 == 0:
                        progress = (completed / len(requests_data)) * 100
                        click.echo(f"Progress: {completed}/{len(requests_data)} ({progress:.1f}%)")

                # Calculate summary statistics
                total_time = time.time() - start_time
                successful = sum(1 for r in results if r['success'])
                failed = len(results) - successful
                avg_rate = len(results) / total_time if total_time > 0 else 0

                summary = {
                    'total_requests': len(results),
                    'successful': successful,
                    'failed': failed,
                    'success_rate': (successful / len(results)) * 100,
                    'total_time': total_time,
                    'avg_rate': avg_rate,
                    'results': results
                }

                # Output results
                if output:
                    with open(output, 'w') as f:
                        json.dump(summary, f, indent=2)
                    click.echo(f"Results saved to {output}")

                click.echo(f"\nBatch Execution Summary:")
                click.echo(f"Total Requests: {len(results)}")
                click.echo(f"Successful: {successful}")
                click.echo(f"Failed: {failed}")
                click.echo(f"Success Rate: {summary['success_rate']:.1f}%")
                click.echo(f"Total Time: {total_time:.1f}s")
                click.echo(f"Average Rate: {avg_rate:.1f} req/s")

                # Show failed requests if any
                if failed > 0 and verbose:
                    click.echo(f"\nFailed Requests:")
                    for result in results:
                        if not result['success']:
                            click.echo(f"  {result['id']}: {result['url']} - {result['error']}")

        except Exception as e:
            click.echo(f"Batch execution failed: {e}", err=True)
            sys.exit(1)

    asyncio.run(execute_batch())


@requests_group.command('session')
@click.option('--name', '-n', required=True, help='Session name')
@click.option('--concurrency', '-c', default=100, help='Concurrent request limit')
@click.option('--rate', '-r', default=10.0, help='Requests per second')
@click.option('--timeout', '-t', default=30, help='Default timeout')
@click.option('--browser-version', default='120.0.0.0', help='Browser version')
@click.option('--interactive', '-i', is_flag=True, help='Interactive session mode')
@click.option('--script', '-s', type=click.Path(exists=True), help='Script file to execute')
def session_mode(name: str, concurrency: int, rate: float, timeout: int,
                browser_version: str, interactive: bool, script: Optional[str]) -> None:
    """Create a managed session for multiple requests."""

    async def run_session():
        # Create session manager
        session_manager = create_session_manager()
        await session_manager.start()

        try:
            # Create session
            session_config = create_session_config(
                name=name,
                concurrency_limit=concurrency,
                rate_limit=rate,
                browser_version=browser_version
            )

            session = await session_manager.create_session(session_config)
            await session.start()

            click.echo(f"Session '{name}' created and started")
            click.echo(f"Session ID: {session.session_id}")

            if script:
                # Execute script file
                click.echo(f"Executing script: {script}")
                await execute_script_file(session, script)

            elif interactive:
                # Interactive mode
                click.echo("Entering interactive mode. Type 'help' for commands.")
                await interactive_session(session)

            else:
                # Just show session info
                click.echo("Session ready. Use --interactive or --script options to use it.")

        except Exception as e:
            click.echo(f"Session failed: {e}", err=True)
        finally:
            await session_manager.stop()

    asyncio.run(run_session())


async def execute_script_file(session, script_path: str) -> None:
    """Execute commands from a script file."""
    # This would implement script execution logic
    # For now, just placeholder
    click.echo(f"Script execution not yet implemented: {script_path}")


async def interactive_session(session) -> None:
    """Run interactive session."""
    commands = {
        'help': 'Show available commands',
        'get <url>': 'Execute GET request',
        'post <url> [data]': 'Execute POST request',
        'stats': 'Show session statistics',
        'quit': 'Exit session'
    }

    while True:
        try:
            command = input("cf> ").strip()

            if not command:
                continue

            if command == 'quit':
                break

            elif command == 'help':
                click.echo("Available commands:")
                for cmd, desc in commands.items():
                    click.echo(f"  {cmd}: {desc}")

            elif command == 'stats':
                stats = session.get_performance_stats()
                click.echo(f"Session Statistics:")
                for key, value in stats.items():
                    click.echo(f"  {key}: {value}")

            elif command.startswith('get '):
                url = command[4:].strip()
                if url:
                    result = await session.execute_request(
                        TestRequest(url=url, method=HttpMethod.GET)
                    )
                    click.echo(f"Status: {result.status_code if hasattr(result, 'status_code') else 'N/A'}")

            else:
                click.echo(f"Unknown command: {command}")

        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            click.echo(f"Error: {e}")


# Export public API
__all__ = [
    'requests_group',
]