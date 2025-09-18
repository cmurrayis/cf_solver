Installation Guide
==================

This guide covers the installation and setup of CloudflareBypass Research Tool.

Requirements
------------

System Requirements
~~~~~~~~~~~~~~~~~~~

- **Python**: 3.11 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 2GB RAM (8GB+ recommended for high concurrency)
- **CPU**: Multi-core processor recommended for optimal performance

Python Dependencies
~~~~~~~~~~~~~~~~~~~

Core dependencies are automatically installed:

- **aiohttp**: HTTP client library
- **curl-cffi**: TLS fingerprinting
- **mini-racer**: JavaScript execution
- **pydantic**: Data validation
- **asyncio**: Asynchronous programming

Installation Methods
--------------------

From Source (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Clone the repository::

    git clone https://github.com/yourusername/cloudflare-bypass-research.git
    cd cloudflare-bypass-research

2. Create virtual environment::

    python -m venv venv

3. Activate virtual environment:

   **Windows**::

    venv\Scripts\activate

   **macOS/Linux**::

    source venv/bin/activate

4. Install dependencies::

    pip install -r requirements.txt

5. Verify installation::

    python -c "import cloudflare_research; print('Installation successful')"

Using pip (When Available)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
   This method will be available when the package is published to PyPI.

::

    pip install cloudflare-research

Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~

For development and testing::

    # Clone repository
    git clone https://github.com/yourusername/cloudflare-bypass-research.git
    cd cloudflare-bypass-research

    # Install in development mode
    pip install -e .

    # Install development dependencies
    pip install -r requirements-dev.txt

Docker Installation
~~~~~~~~~~~~~~~~~~~

Using Docker for isolated environments::

    # Build image
    docker build -t cloudflare-bypass .

    # Run container
    docker run -it cloudflare-bypass python -c "import cloudflare_research"

Platform-Specific Instructions
-------------------------------

Windows
~~~~~~~

1. Install Python 3.11+ from `python.org <https://python.org>`_
2. Install Visual Studio Build Tools (for curl-cffi compilation)
3. Follow the standard installation steps above

**Windows-specific notes:**

- Use PowerShell or Command Prompt
- Ensure Python is in your PATH
- May require administrator privileges for some dependencies

macOS
~~~~~

1. Install Python via Homebrew::

    brew install python@3.11

2. Install required system libraries::

    brew install curl

3. Follow the standard installation steps

**macOS-specific notes:**

- Xcode Command Line Tools may be required
- Use ``python3`` and ``pip3`` commands if needed

Linux (Ubuntu/Debian)
~~~~~~~~~~~~~~~~~~~~~~

1. Install Python and development tools::

    sudo apt update
    sudo apt install python3.11 python3.11-venv python3.11-dev
    sudo apt install build-essential libcurl4-openssl-dev

2. Follow the standard installation steps

**Linux-specific notes:**

- Development headers are required for curl-cffi
- Use package manager for system dependencies

Configuration
-------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Optional environment variables for configuration::

    # Maximum concurrent requests
    export CF_BYPASS_MAX_CONCURRENT=100

    # Default timeout (seconds)
    export CF_BYPASS_TIMEOUT=30

    # Log level
    export CF_BYPASS_LOG_LEVEL=INFO

    # Browser version for emulation
    export CF_BYPASS_BROWSER_VERSION=120.0.0.0

Configuration File
~~~~~~~~~~~~~~~~~~

Create a configuration file `config.yaml`::

    cloudflare_bypass:
      max_concurrent_requests: 100
      solve_javascript_challenges: true
      enable_tls_fingerprinting: true
      browser_version: "120.0.0.0"
      challenge_timeout: 30.0

    logging:
      level: INFO
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

Verification
------------

Test Basic Functionality
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a test script `test_installation.py`::

    import asyncio
    from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

    async def test_installation():
        config = CloudflareBypassConfig(
            max_concurrent_requests=1,
            solve_javascript_challenges=True
        )

        try:
            async with CloudflareBypass(config) as bypass:
                response = await bypass.get("https://httpbin.org/get")
                print(f"Status: {response.status_code}")
                print("Installation verified successfully!")
                return True
        except Exception as e:
            print(f"Installation test failed: {e}")
            return False

    if __name__ == "__main__":
        success = asyncio.run(test_installation())
        exit(0 if success else 1)

Run the test::

    python test_installation.py

Test Challenge Solving
~~~~~~~~~~~~~~~~~~~~~~

Test JavaScript challenge capabilities::

    python -c "
    from mini_racer import MiniRacer
    ctx = MiniRacer()
    result = ctx.eval('2 + 2')
    print(f'JavaScript execution test: {result}')
    assert result == 4
    print('JavaScript engine working correctly!')
    "

Test TLS Fingerprinting
~~~~~~~~~~~~~~~~~~~~~~~

Verify curl-cffi installation::

    python -c "
    import curl_cffi
    print(f'curl-cffi version: {curl_cffi.__version__}')
    print('TLS fingerprinting support available!')
    "

Troubleshooting
---------------

Common Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: ``ModuleNotFoundError: No module named 'curl_cffi'``

**Solution**: Install system dependencies and reinstall::

    # Linux
    sudo apt install libcurl4-openssl-dev

    # macOS
    brew install curl

    # Reinstall
    pip uninstall curl-cffi
    pip install curl-cffi

**Issue**: ``Error: Microsoft Visual C++ 14.0 is required`` (Windows)

**Solution**: Install Visual Studio Build Tools:

1. Download from Microsoft Visual Studio website
2. Install "C++ build tools" workload
3. Restart command prompt and retry installation

**Issue**: ``mini-racer`` compilation errors

**Solution**: Use pre-compiled wheels or install build dependencies::

    # Try pre-compiled wheel first
    pip install --only-binary=all mini-racer

    # If that fails, install build tools
    # Windows: Install Visual Studio Build Tools
    # Linux: sudo apt install build-essential
    # macOS: xcode-select --install

**Issue**: Permission denied errors

**Solution**: Use virtual environment or user installation::

    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate     # Windows

    # Or install for user only
    pip install --user -r requirements.txt

**Issue**: Import errors after installation

**Solution**: Check Python path and virtual environment::

    # Verify Python path
    python -c "import sys; print(sys.path)"

    # Check virtual environment
    which python  # Linux/macOS
    where python  # Windows

Performance Optimization
------------------------

System Optimization
~~~~~~~~~~~~~~~~~~~

For high-performance usage:

1. **Increase file descriptor limits** (Linux/macOS)::

    # Check current limit
    ulimit -n

    # Increase limit (add to .bashrc/.zshrc)
    ulimit -n 65536

2. **Optimize TCP settings** (Linux)::

    # Increase connection tracking
    echo 'net.netfilter.nf_conntrack_max = 1048576' >> /etc/sysctl.conf

3. **Configure swap** for high memory usage::

    # Monitor memory usage
    free -h

Python Optimization
~~~~~~~~~~~~~~~~~~~

1. **Use Python 3.11+** for optimal async performance
2. **Enable optimizations**::

    # Run with optimizations
    python -O your_script.py

3. **Configure garbage collection**::

    import gc
    gc.set_threshold(700, 10, 10)  # Tune for your workload

Next Steps
----------

After successful installation:

1. Read the :doc:`configuration` guide
2. Try the :doc:`examples`
3. Review :doc:`troubleshooting` for common issues

.. seealso::
   - :doc:`configuration` - Detailed configuration options
   - :doc:`examples` - Usage examples and tutorials
   - :doc:`troubleshooting` - Common issues and solutions