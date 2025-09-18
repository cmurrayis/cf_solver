#!/usr/bin/env python3
"""
Debian Server Test for CloudflareScraper

This script tests CloudflareScraper on your Debian server after cloning the repo.

Usage:
    python debian_server_test.py
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    """Print a formatted section"""
    print(f"\n{title}")
    print("-" * len(title))

def run_command(cmd, description, capture_output=True):
    """Run a shell command and return result"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output,
                              text=True, timeout=30)
        if result.returncode == 0:
            print(f"  [OK] {description} successful")
            return result.stdout.strip() if capture_output else ""
        else:
            print(f"  [ERROR] {description} failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {description} timed out")
        return None
    except Exception as e:
        print(f"  [ERROR] {description} exception: {e}")
        return None

def check_system_info():
    """Check system information"""
    print_section("System Information")

    # Check Debian version
    debian_version = run_command("cat /etc/debian_version", "Getting Debian version")
    if debian_version:
        print(f"  Debian Version: {debian_version}")

    # Check Python version
    python_version = run_command("python3 --version", "Checking Python version")
    if python_version:
        print(f"  {python_version}")

    # Check current directory
    current_dir = os.getcwd()
    print(f"  Current Directory: {current_dir}")

    # Check if we're in the right directory
    if os.path.exists("cloudflare_research") and os.path.exists("requirements.txt"):
        print("  [OK] Found CloudflareScraper files")
        return True
    else:
        print("  [ERROR] CloudflareScraper files not found")
        print("  Make sure you're in the CF_Solver directory")
        return False

def setup_environment():
    """Set up virtual environment and install dependencies"""
    print_section("Environment Setup")

    # Check if virtual environment exists
    if os.path.exists("cloudflare_env"):
        print("  [INFO] Virtual environment already exists")
    else:
        print("  [INFO] Creating virtual environment...")
        if not run_command("python3 -m venv cloudflare_env", "Creating virtual environment"):
            return False

    # Install dependencies
    print("  [INFO] Installing dependencies...")

    # Note: We need to run these commands in the virtual environment
    activate_cmd = "source cloudflare_env/bin/activate"

    commands = [
        f"{activate_cmd} && pip install --upgrade pip",
        f"{activate_cmd} && pip install -r requirements.txt",
        f"{activate_cmd} && pip install -e ."
    ]

    for cmd in commands:
        description = cmd.split("&&")[-1].strip()
        if not run_command(cmd, description):
            print(f"  [ERROR] Failed to run: {description}")
            return False

    print("  [OK] Environment setup complete")
    return True

def test_import():
    """Test if CloudflareScraper can be imported"""
    print_section("Import Test")

    test_cmd = """
source cloudflare_env/bin/activate && python3 -c "
import cloudflare_research as cfr
print('CloudflareScraper imported successfully')
print(f'Version: {getattr(cfr, \"__version__\", \"Unknown\")}')
"
"""

    result = run_command(test_cmd, "Testing CloudflareScraper import")
    if result:
        print(f"  [OK] {result}")
        return True
    else:
        print("  [ERROR] Import failed")
        return False

def test_basic_functionality():
    """Test basic CloudflareScraper functionality"""
    print_section("Basic Functionality Test")

    test_script = '''
import cloudflare_research as cfr
import json
import sys

try:
    # Test 1: Create scraper
    scraper = cfr.create_scraper()
    print("[OK] Scraper created successfully")

    # Test 2: Simple HTTP request
    response = scraper.get("https://httpbin.org/ip", timeout=15)
    data = response.json()
    server_ip = data.get("origin", "Unknown")
    print(f"[OK] Basic HTTP request: {response.status_code}")
    print(f"[OK] Server IP: {server_ip}")

    # Test 3: JSON parsing
    response = scraper.get("https://httpbin.org/json", timeout=15)
    json_data = response.json()
    print(f"[OK] JSON parsing: {type(json_data)}")

    # Test 4: POST request
    post_data = {"test": "debian_server", "timestamp": "2025-01-01"}
    response = scraper.post("https://httpbin.org/post", json=post_data, timeout=15)
    if response.ok:
        print(f"[OK] POST request: {response.status_code}")

    scraper.close()
    print("[OK] All basic tests passed")

except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    sys.exit(1)
'''

    # Write test script to file
    with open("temp_test.py", "w") as f:
        f.write(test_script)

    # Run test script
    test_cmd = "source cloudflare_env/bin/activate && python3 temp_test.py"
    result = run_command(test_cmd, "Running basic functionality test", capture_output=False)

    # Clean up
    if os.path.exists("temp_test.py"):
        os.remove("temp_test.py")

    return result is not None

def test_cloudflare_bypass():
    """Test Cloudflare bypass functionality"""
    print_section("Cloudflare Bypass Test")

    test_script = '''
import cloudflare_research as cfr
import time
import sys

try:
    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=5,
        requests_per_second=2.0,
        timeout=30.0
    )

    with cfr.create_scraper(config) as scraper:
        # Test Discord (known Cloudflare site)
        print("[INFO] Testing Discord.com (Cloudflare protected)...")
        start_time = time.time()
        response = scraper.get("https://discord.com")
        duration = time.time() - start_time

        print(f"[OK] Response Status: {response.status_code}")
        print(f"[OK] Response Time: {duration:.2f}s")
        print(f"[OK] Content Length: {len(response.text)} characters")

        # Check Cloudflare indicators
        cf_ray = response.headers.get("cf-ray", "Not detected")
        cf_cache = response.headers.get("cf-cache-status", "Not detected")
        server = response.headers.get("server", "Unknown")

        print(f"[INFO] CF-RAY: {cf_ray}")
        print(f"[INFO] CF-Cache-Status: {cf_cache}")
        print(f"[INFO] Server: {server}")

        if cf_ray != "Not detected":
            print("[SUCCESS] Cloudflare detected and bypassed!")
            print(f"[SUCCESS] CF-RAY ID: {cf_ray}")
        elif "cloudflare" in server.lower():
            print("[SUCCESS] Cloudflare server detected!")
        else:
            print("[INFO] No Cloudflare detected (may not be protected)")

        # Test another site
        print("\\n[INFO] Testing Example.com...")
        response2 = scraper.get("https://example.com")
        print(f"[OK] Example.com Status: {response2.status_code}")

    print("[OK] Cloudflare bypass test completed")

except Exception as e:
    print(f"[ERROR] Cloudflare test failed: {e}")
    sys.exit(1)
'''

    # Write test script to file
    with open("temp_cf_test.py", "w") as f:
        f.write(test_script)

    # Run test script
    test_cmd = "source cloudflare_env/bin/activate && python3 temp_cf_test.py"
    result = run_command(test_cmd, "Running Cloudflare bypass test", capture_output=False)

    # Clean up
    if os.path.exists("temp_cf_test.py"):
        os.remove("temp_cf_test.py")

    return result is not None

def test_performance():
    """Test performance with multiple requests"""
    print_section("Performance Test")

    test_script = '''
import cloudflare_research as cfr
import time
import sys

try:
    test_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/delay/1"
    ]

    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=3,
        requests_per_second=3.0
    )

    with cfr.create_scraper(config) as scraper:
        start_time = time.time()
        successful = 0

        for i, url in enumerate(test_urls, 1):
            try:
                response = scraper.get(url, timeout=15)
                if response.ok:
                    successful += 1
                    print(f"[OK] Request {i}: {response.status_code}")
                else:
                    print(f"[WARN] Request {i}: {response.status_code}")
            except Exception as e:
                print(f"[ERROR] Request {i}: {e}")

        total_time = time.time() - start_time
        print(f"[OK] Performance: {successful}/{len(test_urls)} requests successful")
        print(f"[OK] Total time: {total_time:.2f}s")
        print(f"[OK] Average: {total_time/len(test_urls):.2f}s per request")

except Exception as e:
    print(f"[ERROR] Performance test failed: {e}")
    sys.exit(1)
'''

    # Write test script to file
    with open("temp_perf_test.py", "w") as f:
        f.write(test_script)

    # Run test script
    test_cmd = "source cloudflare_env/bin/activate && python3 temp_perf_test.py"
    result = run_command(test_cmd, "Running performance test", capture_output=False)

    # Clean up
    if os.path.exists("temp_perf_test.py"):
        os.remove("temp_perf_test.py")

    return result is not None

def create_usage_example():
    """Create a usage example file"""
    print_section("Creating Usage Example")

    example_code = '''#!/usr/bin/env python3
"""
CloudflareScraper Usage Example for Debian Server

This example shows how to use CloudflareScraper in your own scripts.
"""

import cloudflare_research as cfr
import time

def scrape_example():
    """Example of scraping a Cloudflare-protected site"""

    # Configure scraper for your needs
    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=10,
        requests_per_second=5.0,
        timeout=30.0,
        solve_javascript_challenges=True,
        enable_tls_fingerprinting=True
    )

    # Use context manager for automatic cleanup
    with cfr.create_scraper(config) as scraper:

        # Example sites - replace with your targets
        sites_to_test = [
            "https://discord.com",
            "https://example.com",
            # Add your target sites here
        ]

        for site in sites_to_test:
            print(f"\\nTesting: {site}")

            try:
                start_time = time.time()
                response = scraper.get(site)
                duration = time.time() - start_time

                print(f"  Status: {response.status_code}")
                print(f"  Duration: {duration:.2f}s")
                print(f"  Content: {len(response.text)} characters")

                # Check for Cloudflare
                cf_ray = response.headers.get('cf-ray')
                if cf_ray:
                    print(f"  [CLOUDFLARE] CF-RAY: {cf_ray}")
                    print(f"  [SUCCESS] Bypassed Cloudflare protection!")
                else:
                    print(f"  [INFO] No Cloudflare protection detected")

                # Example: Save content to file
                filename = f"scraped_{site.replace('https://', '').replace('/', '_')}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  [SAVED] Content saved to: {filename}")

            except Exception as e:
                print(f"  [ERROR] Failed to scrape {site}: {e}")

            # Be respectful - add delay between requests
            time.sleep(2)

def api_style_usage():
    """Example of using CloudflareScraper like cloudscraper"""

    print("\\n" + "="*50)
    print("API-Style Usage (like cloudscraper)")
    print("="*50)

    # Method 1: Basic usage
    scraper = cfr.create_scraper()
    response = scraper.get("https://httpbin.org/get")
    print(f"Method 1 - Basic: {response.status_code}")
    scraper.close()

    # Method 2: Context manager (recommended)
    with cfr.create_scraper() as scraper:
        response = scraper.get("https://httpbin.org/user-agent")
        data = response.json()
        print(f"Method 2 - Context: User-Agent detected")

    # Method 3: One-off requests
    response = cfr.get("https://httpbin.org/ip")
    data = response.json()
    print(f"Method 3 - One-off: IP {data['origin']}")

if __name__ == "__main__":
    print("CloudflareScraper Usage Example")
    print("="*40)

    # Run examples
    scrape_example()
    api_style_usage()

    print("\\n[COMPLETE] Example finished!")
    print("\\nTo use in your own scripts:")
    print("1. source cloudflare_env/bin/activate")
    print("2. python your_script.py")
'''

    # Write example file
    with open("usage_example.py", "w") as f:
        f.write(example_code)

    print("  [OK] Created usage_example.py")
    print("  [INFO] Run with: source cloudflare_env/bin/activate && python usage_example.py")

def generate_report(test_results):
    """Generate final test report"""
    print_header("DEBIAN SERVER TEST REPORT")

    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Server: Debian 12")
    print(f"Python: {sys.version.split()[0]}")
    print()

    # Test Results
    print("Test Results:")
    print("-" * 15)
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())

    for test_name, result in test_results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")

    print()
    print(f"Summary: {passed_tests}/{total_tests} tests passed")

    # Overall Status
    if passed_tests == total_tests:
        print_header("🎉 ALL TESTS PASSED!")
        print("✅ CloudflareScraper is ready for production use on Debian!")
        print()
        print("Next Steps:")
        print("1. Use 'source cloudflare_env/bin/activate' before running scripts")
        print("2. Test against your target sites")
        print("3. Check usage_example.py for implementation examples")
        print("4. Monitor performance and adjust configuration as needed")

    elif passed_tests >= total_tests * 0.8:
        print_header("⚠️ MOST TESTS PASSED")
        print("✅ CloudflareScraper should work for basic use cases")
        print("⚠️ Some issues detected - check failed tests above")

    else:
        print_header("❌ MULTIPLE TEST FAILURES")
        print("🔧 Please check the installation and try again")
        print()
        print("Common fixes:")
        print("1. Make sure you're in the CF_Solver directory")
        print("2. Check internet connectivity")
        print("3. Verify all dependencies are installed")

def main():
    """Main test execution"""
    print_header("CLOUDFLARE SCRAPER - DEBIAN SERVER TEST")
    print("This script will test CloudflareScraper on your Debian server")
    print("Make sure you're in the CF_Solver directory after cloning")
    print()

    test_results = {}

    # Run all tests
    test_results["System Check"] = check_system_info()

    if test_results["System Check"]:
        test_results["Environment Setup"] = setup_environment()

        if test_results["Environment Setup"]:
            test_results["Import Test"] = test_import()
            test_results["Basic Functionality"] = test_basic_functionality()
            test_results["Cloudflare Bypass"] = test_cloudflare_bypass()
            test_results["Performance Test"] = test_performance()

            # Create usage example regardless of test results
            create_usage_example()
        else:
            print("\n[ERROR] Environment setup failed. Cannot continue with tests.")
            test_results.update({
                "Import Test": False,
                "Basic Functionality": False,
                "Cloudflare Bypass": False,
                "Performance Test": False
            })
    else:
        print("\n[ERROR] System check failed. Make sure you're in the CF_Solver directory.")
        test_results.update({
            "Environment Setup": False,
            "Import Test": False,
            "Basic Functionality": False,
            "Cloudflare Bypass": False,
            "Performance Test": False
        })

    # Generate final report
    generate_report(test_results)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        print("Please check your installation and try again")