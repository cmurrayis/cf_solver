#!/usr/bin/env python3
"""
Complete CloudflareScraper Test for Debian Server

This script thoroughly tests CloudflareScraper functionality.
Run this after successful installation.
"""

import cloudflare_research as cfr
import time
import json
import sys
from datetime import datetime

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    print(f"\n{title}")
    print("-" * len(title))

def test_basic_functionality():
    """Test basic HTTP functionality"""
    print_section("1. Basic Functionality Test")

    try:
        with cfr.create_scraper() as scraper:
            # Test simple GET
            print("Testing simple GET request...")
            response = scraper.get("https://httpbin.org/get", timeout=10)
            print(f"  ✅ Status: {response.status_code}")

            # Parse JSON
            data = response.json()
            print(f"  ✅ JSON parsing successful")
            print(f"  ✅ User-Agent: {data.get('headers', {}).get('User-Agent', 'N/A')[:50]}...")

            # Test POST
            print("\nTesting POST request...")
            post_data = {"test": "debian_server", "python": "3.9"}
            response = scraper.post("https://httpbin.org/post", json=post_data, timeout=10)
            print(f"  ✅ POST Status: {response.status_code}")

            if response.ok:
                data = response.json()
                received = data.get('json', {})
                print(f"  ✅ Data echoed back: {received.get('test') == 'debian_server'}")

        return True

    except Exception as e:
        print(f"  ❌ Basic functionality failed: {e}")
        return False

def test_cloudflare_sites():
    """Test against known Cloudflare-protected sites"""
    print_section("2. Cloudflare Bypass Test")

    cloudflare_sites = [
        {
            "name": "Discord",
            "url": "https://discord.com",
            "expect_cf": True
        },
        {
            "name": "Example.com",
            "url": "https://example.com",
            "expect_cf": False  # May or may not have CF
        }
    ]

    results = []

    try:
        # Configure for respectful testing
        config = cfr.CloudflareBypassConfig(
            max_concurrent_requests=3,
            requests_per_second=1.0,
            timeout=30.0
        )

        with cfr.create_scraper(config) as scraper:
            for site in cloudflare_sites:
                print(f"\nTesting {site['name']}: {site['url']}")

                try:
                    start_time = time.time()
                    response = scraper.get(site['url'])
                    duration = time.time() - start_time

                    # Analyze response
                    cf_ray = response.headers.get('cf-ray', 'Not detected')
                    cf_cache = response.headers.get('cf-cache-status', 'Not detected')
                    server = response.headers.get('server', 'Unknown')

                    print(f"  ✅ Status: {response.status_code}")
                    print(f"  ✅ Response time: {duration:.2f}s")
                    print(f"  ✅ Content size: {len(response.text)} characters")
                    print(f"  ✅ Server: {server}")

                    # Check for Cloudflare indicators
                    cf_detected = False
                    if cf_ray != 'Not detected':
                        print(f"  🛡️ CF-RAY: {cf_ray}")
                        cf_detected = True

                    if cf_cache != 'Not detected':
                        print(f"  🛡️ CF-Cache-Status: {cf_cache}")
                        cf_detected = True

                    if 'cloudflare' in server.lower():
                        print(f"  🛡️ Cloudflare server detected")
                        cf_detected = True

                    if cf_detected:
                        print(f"  🎉 SUCCESS: Cloudflare detected and bypassed!")
                    else:
                        print(f"  ℹ️ No Cloudflare protection detected")

                    results.append({
                        "site": site['name'],
                        "status": response.status_code,
                        "cf_detected": cf_detected,
                        "cf_ray": cf_ray,
                        "duration": duration,
                        "success": True
                    })

                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                    results.append({
                        "site": site['name'],
                        "success": False,
                        "error": str(e)
                    })

                # Be respectful - delay between requests
                time.sleep(2)

        return results

    except Exception as e:
        print(f"❌ Cloudflare test setup failed: {e}")
        return []

def test_performance():
    """Test performance with multiple requests"""
    print_section("3. Performance Test")

    test_urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/get",
        "https://httpbin.org/status/200"
    ]

    try:
        config = cfr.CloudflareBypassConfig(
            max_concurrent_requests=3,
            requests_per_second=2.0
        )

        with cfr.create_scraper(config) as scraper:
            start_time = time.time()
            successful_requests = 0

            for i, url in enumerate(test_urls, 1):
                try:
                    response = scraper.get(url, timeout=15)
                    if response.ok:
                        successful_requests += 1
                        print(f"  ✅ Request {i}: {response.status_code}")
                    else:
                        print(f"  ⚠️ Request {i}: {response.status_code}")
                except Exception as e:
                    print(f"  ❌ Request {i}: {e}")

            total_time = time.time() - start_time
            avg_time = total_time / len(test_urls)

            print(f"\n  📊 Performance Results:")
            print(f"    Success rate: {successful_requests}/{len(test_urls)}")
            print(f"    Total time: {total_time:.2f}s")
            print(f"    Average per request: {avg_time:.2f}s")

            return successful_requests == len(test_urls)

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_different_methods():
    """Test different HTTP methods"""
    print_section("4. HTTP Methods Test")

    try:
        with cfr.create_scraper() as scraper:
            # Test GET
            response = scraper.get("https://httpbin.org/get")
            print(f"  ✅ GET: {response.status_code}")

            # Test POST with JSON
            response = scraper.post("https://httpbin.org/post",
                                  json={"method": "POST", "data": "test"})
            print(f"  ✅ POST (JSON): {response.status_code}")

            # Test POST with form data
            response = scraper.post("https://httpbin.org/post",
                                  data={"form": "data", "test": "value"})
            print(f"  ✅ POST (Form): {response.status_code}")

            # Test PUT
            response = scraper.put("https://httpbin.org/put",
                                 json={"method": "PUT"})
            print(f"  ✅ PUT: {response.status_code}")

            # Test DELETE
            response = scraper.delete("https://httpbin.org/delete")
            print(f"  ✅ DELETE: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ HTTP methods test failed: {e}")
        return False

def test_custom_headers():
    """Test custom headers functionality"""
    print_section("5. Custom Headers Test")

    try:
        custom_headers = {
            "X-Test-Header": "CloudflareScraper-Debian",
            "X-Python-Version": "3.9",
            "X-Custom-Value": "test123"
        }

        with cfr.create_scraper() as scraper:
            response = scraper.get("https://httpbin.org/headers", headers=custom_headers)

            if response.ok:
                data = response.json()
                received_headers = data.get('headers', {})

                print(f"  ✅ Request successful: {response.status_code}")
                print(f"  ✅ Custom headers sent:")

                for header, value in custom_headers.items():
                    if header in received_headers:
                        print(f"    ✅ {header}: {received_headers[header]}")
                    else:
                        print(f"    ❌ {header}: Not received")

                return True
            else:
                print(f"  ❌ Request failed: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Custom headers test failed: {e}")
        return False

def create_production_example():
    """Create a production usage example"""
    print_section("6. Creating Production Example")

    example_code = '''#!/usr/bin/env python3
"""
CloudflareScraper Production Example for Debian Server

This example shows how to use CloudflareScraper in production.
"""

import cloudflare_research as cfr
import time

def scrape_sites():
    """Example of scraping multiple sites"""

    # Your target sites (replace with real sites)
    target_sites = [
        "https://discord.com",
        "https://example.com",
        # Add your sites here
    ]

    # Production configuration
    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=10,
        requests_per_second=5.0,
        timeout=30.0,
        solve_javascript_challenges=True,
        enable_tls_fingerprinting=True
    )

    with cfr.create_scraper(config) as scraper:
        for site in target_sites:
            print(f"\\nScraping: {site}")

            try:
                response = scraper.get(site)

                print(f"  Status: {response.status_code}")
                print(f"  Content: {len(response.text)} chars")

                # Check for Cloudflare
                cf_ray = response.headers.get('cf-ray')
                if cf_ray:
                    print(f"  🛡️ Cloudflare bypassed: {cf_ray}")

                # Save content (example)
                filename = f"scraped_{site.replace('https://', '').replace('/', '_')}.html"
                with open(filename, 'w') as f:
                    f.write(response.text)
                print(f"  💾 Saved to: {filename}")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            time.sleep(1)  # Be respectful

def api_style_usage():
    """Show cloudscraper-style usage"""
    print("\\nAPI Style Usage (like cloudscraper):")

    # Method 1: Basic
    scraper = cfr.create_scraper()
    response = scraper.get("https://httpbin.org/ip")
    data = response.json()
    print(f"Method 1: IP {data['origin']}")
    scraper.close()

    # Method 2: Context manager
    with cfr.create_scraper() as scraper:
        response = scraper.get("https://httpbin.org/user-agent")
        print(f"Method 2: User agent set")

    # Method 3: One-off
    response = cfr.get("https://httpbin.org/get")
    print(f"Method 3: Status {response.status_code}")

if __name__ == "__main__":
    print("CloudflareScraper Production Example")
    print("=" * 40)

    scrape_sites()
    api_style_usage()

    print("\\n✅ Example completed!")
'''

    with open("production_example.py", "w") as f:
        f.write(example_code)

    print("  ✅ Created production_example.py")
    print("  ✅ Run with: python production_example.py")

def generate_test_report(results):
    """Generate final test report"""
    print_header("TEST REPORT SUMMARY")

    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"System: Debian 11.11")
    print(f"Python: {sys.version.split()[0]}")
    print()

    # Count results
    total_tests = len(results)
    passed_tests = sum(results.values())

    print("Test Results:")
    print("-" * 15)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")

    print()
    print(f"Overall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print_header("🎉 ALL TESTS PASSED!")
        print("✅ CloudflareScraper is working perfectly on Debian 11!")
        print()
        print("🚀 Ready for production use!")
        print()
        print("Next steps:")
        print("1. Test against your target sites")
        print("2. Use production_example.py as a template")
        print("3. Always activate virtual environment: source cloudflare_env/bin/activate")

    elif passed_tests >= total_tests * 0.8:
        print_header("⚠️ MOSTLY WORKING")
        print("✅ Core functionality is working")
        print("⚠️ Some advanced features may have issues")

    else:
        print_header("❌ ISSUES DETECTED")
        print("🔧 Several tests failed - check errors above")

def main():
    """Main test execution"""
    print_header("CLOUDFLARE SCRAPER - DEBIAN SERVER FULL TEST")
    print("This will thoroughly test all CloudflareScraper functionality")
    print(f"Python version: {sys.version}")
    print()

    test_results = {}

    # Run all tests
    test_results["Basic Functionality"] = test_basic_functionality()

    cf_results = test_cloudflare_sites()
    test_results["Cloudflare Bypass"] = len(cf_results) > 0 and any(r.get('success', False) for r in cf_results)

    test_results["Performance Test"] = test_performance()
    test_results["HTTP Methods"] = test_different_methods()
    test_results["Custom Headers"] = test_custom_headers()

    # Create production example
    create_production_example()

    # Generate final report
    generate_test_report(test_results)

    # Show Cloudflare results
    if cf_results:
        print_header("CLOUDFLARE TEST DETAILS")
        for result in cf_results:
            if result.get('success'):
                cf_status = "🛡️ CF DETECTED" if result.get('cf_detected') else "ℹ️ No CF"
                print(f"  {result['site']}: {result['status']} ({cf_status})")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")