#!/usr/bin/env python3
"""
Test the fixed standalone CloudflareScraper
"""

import cloudflare_scraper_standalone as cfs

def test_simple_request():
    """Test a simple HTTP request"""
    print("Testing standalone CloudflareScraper...")
    print("=" * 50)

    try:
        # Test basic functionality
        print("1. Testing basic HTTP request...")
        response = cfs.get("https://httpbin.org/ip")
        data = response.json()
        print(f"✅ Success! Your IP: {data.get('origin', 'Unknown')}")

        # Test with scraper instance
        print("\n2. Testing with scraper instance...")
        with cfs.create_scraper() as scraper:
            response = scraper.get("https://httpbin.org/user-agent")
            data = response.json()
            print(f"✅ User-Agent: {data.get('user-agent', 'Unknown')[:50]}...")

        # Test POST request
        print("\n3. Testing POST request...")
        response = cfs.post("https://httpbin.org/post", json={"test": "data"})
        data = response.json()
        print(f"✅ POST successful: {data.get('json', {}).get('test', 'Failed')}")

        print("\n🎉 All tests passed! CloudflareScraper standalone is working!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_request()