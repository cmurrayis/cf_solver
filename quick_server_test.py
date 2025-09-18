#!/usr/bin/env python3
"""
Quick Server Test for CloudflareScraper

Upload this file to your server and run it to test CloudflareScraper deployment.

Usage:
    python quick_server_test.py
"""

import sys
import json
import time
from datetime import datetime

def test_server_environment():
    """Test if the server environment is ready"""
    print("CloudflareScraper Server Environment Test")
    print("=" * 45)
    print()

    # Check Python version
    print("1. Python Environment Check")
    print("-" * 30)
    print(f"   Python Version: {sys.version}")
    print(f"   Python Executable: {sys.executable}")

    if sys.version_info < (3, 11):
        print("   ❌ WARNING: Python 3.11+ recommended")
    else:
        print("   ✅ Python version OK")
    print()

    # Try to import CloudflareScraper
    print("2. CloudflareScraper Import Test")
    print("-" * 35)
    try:
        import cloudflare_research as cfr
        print("   ✅ CloudflareScraper imported successfully")
        print(f"   Version: {getattr(cfr, '__version__', 'Unknown')}")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        print("\n   INSTALLATION NEEDED:")
        print("   1. Upload your CF_Solver directory to this server")
        print("   2. cd CF_Solver")
        print("   3. pip install -r requirements.txt")
        print("   4. pip install -e .")
        return False

def run_functionality_tests():
    """Run comprehensive functionality tests"""
    import cloudflare_research as cfr

    print("3. Functionality Tests")
    print("-" * 22)

    results = []

    # Test 1: Basic scraper creation
    try:
        scraper = cfr.create_scraper()
        print("   ✅ Scraper creation: SUCCESS")
        results.append(("Scraper Creation", True, "OK"))
        scraper.close()
    except Exception as e:
        print(f"   ❌ Scraper creation: FAILED - {e}")
        results.append(("Scraper Creation", False, str(e)))
        return results

    # Test 2: Basic HTTP request
    try:
        with cfr.create_scraper() as scraper:
            response = scraper.get("https://httpbin.org/ip", timeout=10)
            data = response.json()
            server_ip = data.get('origin', 'Unknown')
            print(f"   ✅ Basic HTTP: SUCCESS (IP: {server_ip})")
            results.append(("Basic HTTP", True, f"IP: {server_ip}"))
    except Exception as e:
        print(f"   ❌ Basic HTTP: FAILED - {e}")
        results.append(("Basic HTTP", False, str(e)))

    # Test 3: JSON handling
    try:
        with cfr.create_scraper() as scraper:
            response = scraper.get("https://httpbin.org/json", timeout=10)
            data = response.json()
            print(f"   ✅ JSON parsing: SUCCESS")
            results.append(("JSON Parsing", True, "OK"))
    except Exception as e:
        print(f"   ❌ JSON parsing: FAILED - {e}")
        results.append(("JSON Parsing", False, str(e)))

    # Test 4: POST request
    try:
        with cfr.create_scraper() as scraper:
            test_data = {"server": "test", "timestamp": datetime.now().isoformat()}
            response = scraper.post("https://httpbin.org/post", json=test_data, timeout=10)
            if response.ok:
                print(f"   ✅ POST request: SUCCESS")
                results.append(("POST Request", True, "OK"))
            else:
                print(f"   ❌ POST request: FAILED - Status {response.status_code}")
                results.append(("POST Request", False, f"Status {response.status_code}"))
    except Exception as e:
        print(f"   ❌ POST request: FAILED - {e}")
        results.append(("POST Request", False, str(e)))

    # Test 5: Cloudflare detection
    try:
        with cfr.create_scraper() as scraper:
            print("   🔍 Testing Cloudflare site (discord.com)...")
            response = scraper.get("https://discord.com", timeout=15)

            # Check for Cloudflare indicators
            cf_ray = response.headers.get('cf-ray', 'Not detected')
            cf_server = response.headers.get('server', '')

            if 'cf-ray' in response.headers or 'cloudflare' in cf_server.lower():
                print(f"   ✅ Cloudflare bypass: SUCCESS (CF-RAY: {cf_ray})")
                results.append(("Cloudflare Bypass", True, f"CF-RAY: {cf_ray}"))
            else:
                print(f"   ⚠️  Cloudflare bypass: No CF detected (might not be protected)")
                results.append(("Cloudflare Detection", True, "No CF detected"))
    except Exception as e:
        print(f"   ❌ Cloudflare test: FAILED - {e}")
        results.append(("Cloudflare Test", False, str(e)))

    return results

def run_performance_test():
    """Run a simple performance test"""
    import cloudflare_research as cfr

    print("\n4. Performance Test")
    print("-" * 18)

    try:
        test_urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/get",
            "https://httpbin.org/status/200"
        ]

        start_time = time.time()
        successful_requests = 0

        with cfr.create_scraper() as scraper:
            for i, url in enumerate(test_urls, 1):
                try:
                    response = scraper.get(url, timeout=10)
                    if response.ok:
                        successful_requests += 1
                        print(f"   Request {i}: ✅ {response.status_code}")
                    else:
                        print(f"   Request {i}: ❌ {response.status_code}")
                except Exception as e:
                    print(f"   Request {i}: ❌ {e}")

        end_time = time.time()
        total_time = end_time - start_time

        print(f"   Performance: {successful_requests}/{len(test_urls)} requests successful")
        print(f"   Total time: {total_time:.2f} seconds")
        print(f"   Average: {total_time/len(test_urls):.2f} seconds per request")

        return successful_requests == len(test_urls)

    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False

def generate_report(results):
    """Generate a comprehensive test report"""
    print("\n" + "=" * 50)
    print("SERVER TEST REPORT")
    print("=" * 50)

    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Server: {sys.platform}")
    print()

    # Test results summary
    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)

    print("Test Results:")
    print("-" * 15)
    for test_name, success, details in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}: {details}")

    print()
    print(f"Summary: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ CloudflareScraper is ready for production use on this server!")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  Most tests passed - minor issues detected")
        print("✅ CloudflareScraper should work for basic use cases")
    else:
        print("❌ Multiple test failures detected")
        print("🔧 Please check installation and dependencies")

    print()
    print("Next Steps:")
    if passed_tests == total_tests:
        print("1. Deploy your CloudflareScraper applications")
        print("2. Test against your target Cloudflare-protected sites")
        print("3. Monitor performance and adjust configuration as needed")
    else:
        print("1. Check error messages above")
        print("2. Verify all dependencies are installed")
        print("3. Re-run this test after fixing issues")

def main():
    """Main test execution"""
    print("🚀 Starting CloudflareScraper Server Test")
    print("⏱️  This will take about 30-60 seconds...")
    print()

    # Step 1: Environment check
    if not test_server_environment():
        print("\n❌ Environment check failed. Please install CloudflareScraper first.")
        return

    # Step 2: Functionality tests
    print()
    results = run_functionality_tests()

    # Step 3: Performance test
    perf_success = run_performance_test()
    results.append(("Performance Test", perf_success, "Multiple requests"))

    # Step 4: Generate report
    generate_report(results)

    print("\n📋 Test completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Please check your installation and try again.")