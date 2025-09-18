Command Line Interface
======================

The CLI module provides command-line tools for testing, benchmarking, and analyzing CloudflareBypass performance.

.. currentmodule:: cloudflare_research.cli

Main CLI Interface
------------------

.. automodule:: cloudflare_research.cli.__main__
   :members:
   :undoc-members:
   :show-inheritance:

The main CLI entry point provides several commands:

.. program:: cloudflare-research

.. option:: --version

   Show version information

.. option:: --help

   Show help message

.. option:: --config <path>

   Use custom configuration file

Available Commands
------------------

request
~~~~~~~

Make individual requests for testing::

    cloudflare-research request https://example.com

.. automodule:: cloudflare_research.cli.requests
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: RequestCommand
   :members:
   :undoc-members:
   :show-inheritance:

benchmark
~~~~~~~~~

Run performance benchmarks::

    cloudflare-research benchmark https://example.com --concurrency 100

.. automodule:: cloudflare_research.cli.benchmark
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BenchmarkCommand
   :members:
   :undoc-members:
   :show-inheritance:

CLI Configuration
-----------------

.. autoclass:: CLIConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration class for CLI behavior.

Output Formatting
-----------------

.. autoclass:: OutputFormatter
   :members:
   :undoc-members:
   :show-inheritance:

   Formats CLI output in various formats.

.. automethod:: OutputFormatter.format_json
.. automethod:: OutputFormatter.format_table
.. automethod:: OutputFormatter.format_summary

Progress Reporting
------------------

.. autoclass:: ProgressReporter
   :members:
   :undoc-members:
   :show-inheritance:

   Provides progress bars and status updates for long-running operations.

.. automethod:: ProgressReporter.start_progress
.. automethod:: ProgressReporter.update_progress
.. automethod:: ProgressReporter.finish_progress

Command Examples
----------------

Single Request
~~~~~~~~~~~~~~

Test a single URL::

    # Basic request
    cloudflare-research request https://example.com

    # With custom headers
    cloudflare-research request https://example.com \
        --header "User-Agent: Custom Agent" \
        --header "Authorization: Bearer token123"

    # Save response to file
    cloudflare-research request https://example.com \
        --output response.html

    # JSON output
    cloudflare-research request https://example.com \
        --format json

Performance Benchmark
~~~~~~~~~~~~~~~~~~~~~

Run concurrency tests::

    # Basic benchmark
    cloudflare-research benchmark https://example.com \
        --concurrency 50 \
        --duration 60

    # Multiple concurrency levels
    cloudflare-research benchmark https://example.com \
        --concurrency 10,50,100,500 \
        --requests 1000

    # With detailed reporting
    cloudflare-research benchmark https://example.com \
        --concurrency 100 \
        --report detailed \
        --output benchmark_results.json

Challenge Analysis
~~~~~~~~~~~~~~~~~~

Analyze challenge behavior::

    # Test challenge detection
    cloudflare-research analyze-challenges https://protected-site.com \
        --samples 20 \
        --output challenge_analysis.json

    # Specific challenge types
    cloudflare-research analyze-challenges https://protected-site.com \
        --challenge-types javascript,turnstile \
        --verbose

Configuration Examples
----------------------

Configuration File
~~~~~~~~~~~~~~~~~~

Create a configuration file `config.yaml`::

    cloudflare_bypass:
      max_concurrent_requests: 100
      solve_javascript_challenges: true
      enable_tls_fingerprinting: true
      browser_version: "120.0.0.0"

    cli:
      default_format: json
      show_progress: true
      log_level: INFO

Use configuration::

    cloudflare-research --config config.yaml benchmark https://example.com

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set configuration via environment::

    export CF_BYPASS_MAX_CONCURRENT=200
    export CF_BYPASS_SOLVE_JS=true
    export CF_BYPASS_LOG_LEVEL=DEBUG

    cloudflare-research benchmark https://example.com

Advanced Usage
--------------

Batch Processing
~~~~~~~~~~~~~~~~

Process multiple URLs from file::

    # Create urls.txt with one URL per line
    echo "https://example1.com" > urls.txt
    echo "https://example2.com" >> urls.txt

    # Process all URLs
    cloudflare-research batch-process urls.txt \
        --concurrency 10 \
        --output results/

Pipeline Integration
~~~~~~~~~~~~~~~~~~~

Use in CI/CD pipelines::

    #!/bin/bash
    # test_cloudflare_protection.sh

    # Test protection effectiveness
    result=$(cloudflare-research request https://my-protected-site.com \
        --format json \
        --timeout 30)

    # Check if Cloudflare is active
    if echo "$result" | jq -r '.cloudflare_detected' | grep -q "true"; then
        echo "Cloudflare protection is active"
        exit 0
    else
        echo "WARNING: Cloudflare protection not detected"
        exit 1
    fi

Monitoring Integration
~~~~~~~~~~~~~~~~~~~~~

Continuous monitoring::

    # Run continuous monitoring
    cloudflare-research monitor https://critical-site.com \
        --interval 300 \
        --alert-on-failure \
        --webhook https://alerts.example.com/webhook

    # Export metrics to monitoring system
    cloudflare-research benchmark https://site.com \
        --export-prometheus \
        --prometheus-gateway localhost:9091

Scripting Examples
------------------

Bash Integration
~~~~~~~~~~~~~~~~

.. code-block:: bash

    #!/bin/bash

    # Function to test site availability
    test_site() {
        local url=$1
        local result

        result=$(cloudflare-research request "$url" \
            --format json \
            --timeout 10 2>/dev/null)

        if [ $? -eq 0 ]; then
            local status=$(echo "$result" | jq -r '.status_code')
            local cf_detected=$(echo "$result" | jq -r '.cloudflare_detected')

            echo "URL: $url - Status: $status - CF: $cf_detected"
        else
            echo "URL: $url - FAILED"
        fi
    }

    # Test multiple sites
    while IFS= read -r url; do
        test_site "$url"
    done < urls.txt

Python Integration
~~~~~~~~~~~~~~~~~

.. code-block:: python

    import subprocess
    import json
    from typing import Dict, Any

    def run_bypass_test(url: str, concurrency: int = 10) -> Dict[str, Any]:
        """Run CloudflareBypass test via CLI."""
        cmd = [
            "cloudflare-research", "benchmark", url,
            "--concurrency", str(concurrency),
            "--format", "json"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            raise RuntimeError(f"Test failed: {result.stderr}")

    # Use in Python script
    results = run_bypass_test("https://example.com", concurrency=50)
    print(f"Success rate: {results['success_rate']:.2%}")

Error Handling
--------------

Common CLI error scenarios and handling:

.. autoclass:: CLIError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ConfigurationError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: NetworkError
   :members:
   :undoc-members:
   :show-inheritance:

Exit Codes
~~~~~~~~~~

Standard exit codes:

- **0**: Success
- **1**: General error
- **2**: Configuration error
- **3**: Network error
- **4**: Challenge solving failed
- **5**: Rate limit exceeded

.. seealso::
   :doc:`../user_guide/troubleshooting` for CLI troubleshooting guides.