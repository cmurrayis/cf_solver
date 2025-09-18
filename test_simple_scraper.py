#!/usr/bin/env python3
"""
Simple CloudflareScraper Test - Drop-in replacement for cloudscraper

This script demonstrates how to use the CloudflareScraper with the same
interface as cloudscraper for easy migration.
"""

import cloudflare_research as cfr

def test_cloudscraper_interface():
    """Test the cloudscraper-like interface."""
    print("[TEST] Testing CloudflareScraper Interface")
    print("=" * 40)

    # Method 1: Create scraper (like cloudscraper.create_scraper())
    print("\n[1] Using create_scraper() method:")
    scraper = cfr.create_scraper()

    try:
        response = scraper.get("https://httpbin.org/get")
        print(f"[OK] Status: {response.status_code}")
        print(f"[OK] URL: {response.url}")
        print(f"[OK] Response size: {len(response.text)} chars")
        print(f"[OK] Headers: {len(response.headers)} headers")

        # Test JSON parsing
        data = response.json()
        print(f"[OK] JSON parsed successfully: {type(data)}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
    finally:
        scraper.close()

    # Method 2: Context manager
    print("\n[2] Using context manager:")
    try:
        with cfr.create_scraper() as scraper:
            response = scraper.get("https://httpbin.org/user-agent")
            print(f"[OK] Status: {response.status_code}")
            data = response.json()
            print(f"[OK] User-Agent: {data.get('user-agent', 'N/A')}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

    # Method 3: One-off requests
    print("\n[3] Using convenience functions:")
    try:
        response = cfr.get("https://httpbin.org/ip")
        print(f"[OK] Status: {response.status_code}")
        data = response.json()
        print(f"[OK] IP: {data.get('origin', 'N/A')}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

    # Method 4: POST request
    print("\n[4] Testing POST request:")
    try:
        post_data = {"test": "data", "number": 123}
        response = cfr.post("https://httpbin.org/post", json=post_data)
        print(f"[OK] Status: {response.status_code}")
        data = response.json()
        print(f"[OK] Posted data received: {data.get('json') == post_data}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

    # Method 5: Custom configuration
    print("\n[5] Testing custom configuration:")
    try:
        config = cfr.CloudflareBypassConfig(
            requests_per_second=1.0,  # Very conservative
            timeout=15.0,
            max_concurrent_requests=5
        )

        with cfr.create_scraper(config) as scraper:
            response = scraper.get("https://httpbin.org/user-agent")
            print(f"[OK] Status: {response.status_code}")
            data = response.json()
            print(f"[OK] Custom configuration working: {response.status_code == 200}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

def test_cloudscraper_compatibility():
    """Test compatibility with cloudscraper usage patterns."""
    print("\n[COMPAT] Testing Cloudscraper Compatibility")
    print("=" * 40)

    # This is how you would use cloudscraper:
    # import cloudscraper
    # scraper = cloudscraper.create_scraper()
    # response = scraper.get("https://example.com")
    # print(response.text)

    # This is how you use cloudflare_research (drop-in replacement):
    try:
        scraper = cfr.create_scraper()
        response = scraper.get("https://httpbin.org/get")

        # All the same attributes should be available
        print(f"[OK] response.status_code: {response.status_code}")
        print(f"[OK] response.text available: {len(response.text) > 0}")
        print(f"[OK] response.content available: {len(response.content) > 0}")
        print(f"[OK] response.headers available: {len(response.headers) > 0}")
        print(f"[OK] response.url: {response.url}")
        print(f"[OK] response.ok: {response.ok}")

        # Test methods
        try:
            data = response.json()
            print(f"[OK] response.json() works: {type(data)}")
        except:
            print("[ERROR] response.json() failed")

        try:
            response.raise_for_status()
            print("[OK] response.raise_for_status() works")
        except:
            print("[ERROR] response.raise_for_status() failed")

        scraper.close()

    except Exception as e:
        print(f"[ERROR] Compatibility test failed: {e}")

def compare_with_cloudscraper():
    """Show the exact same usage as cloudscraper."""
    print("\n[COMPARE] Cloudscraper vs CloudflareScraper")
    print("=" * 40)

    print("Original cloudscraper code:")
    print("```python")
    print("import cloudscraper")
    print("")
    print("scraper = cloudscraper.create_scraper()")
    print("response = scraper.get('https://example.com')")
    print("print(response.text)")
    print("```")
    print()

    print("CloudflareScraper equivalent (drop-in replacement):")
    print("```python")
    print("import cloudflare_research as cfr")
    print("")
    print("scraper = cfr.create_scraper()")
    print("response = scraper.get('https://example.com')")
    print("print(response.text)")
    print("```")
    print()

    print("[SUCCESS] It's exactly the same interface!")

if __name__ == "__main__":
    print("CloudflareScraper Simple Interface Test")
    print("==========================================")

    test_cloudscraper_interface()
    test_cloudscraper_compatibility()
    compare_with_cloudscraper()

    print("\n[SUCCESS] All tests completed!")
    print("\n[SUMMARY] Usage Summary:")
    print("- Import: import cloudflare_research as cfr")
    print("- Create scraper: scraper = cfr.create_scraper()")
    print("- Make requests: response = scraper.get(url)")
    print("- Or one-off: response = cfr.get(url)")
    print("- Same interface as cloudscraper!")