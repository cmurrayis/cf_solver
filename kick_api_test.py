#!/usr/bin/env python3
"""
Simple Kick.com API Test Script

Tests CloudflareScraper with Kick.com API endpoint to fetch adinross channel data.
"""

import cloudflare_research as cfr
import json

def test_kick_api():
    """Test Kick.com API endpoint"""
    print("CloudflareScraper - Kick.com API Test")
    print("=" * 40)

    url = "https://kick.com/api/v1/channels/adinross"
    print(f"Target URL: {url}")
    print()

    try:
        # Create scraper with moderate settings
        config = cfr.CloudflareBypassConfig(
            max_concurrent_requests=5,
            requests_per_second=2.0,
            timeout=30.0
        )

        with cfr.create_scraper(config) as scraper:
            print("Fetching data...")
            response = scraper.get(url)

            print(f"Status Code: {response.status_code}")
            print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
            print(f"Content Length: {len(response.text)} characters")

            # Check for Cloudflare protection
            cf_ray = response.headers.get('cf-ray')
            cf_cache = response.headers.get('cf-cache-status')
            server = response.headers.get('server', '').lower()

            if cf_ray:
                print(f"🛡️ Cloudflare detected - CF-RAY: {cf_ray}")
            if cf_cache:
                print(f"🛡️ CF-Cache-Status: {cf_cache}")
            if 'cloudflare' in server:
                print(f"🛡️ Cloudflare server detected")

            print()

            if response.status_code == 200:
                print("✅ SUCCESS: Data retrieved!")
                print()
                print("Response Content:")
                print("-" * 50)

                # Try to parse as JSON
                try:
                    data = response.json()
                    # Pretty print JSON with indentation
                    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                    print(formatted_json)

                    # Show some key information if available
                    print()
                    print("Key Information:")
                    print("-" * 20)
                    if isinstance(data, dict):
                        if 'user' in data:
                            user = data['user']
                            print(f"Username: {user.get('username', 'N/A')}")
                            print(f"Followers: {user.get('followers_count', 'N/A')}")
                        if 'is_live' in data:
                            print(f"Live Status: {data.get('is_live', 'N/A')}")
                        if 'category' in data:
                            category = data.get('category', {})
                            if isinstance(category, dict):
                                print(f"Category: {category.get('name', 'N/A')}")

                except json.JSONDecodeError:
                    # If not JSON, show raw content (truncated)
                    print("Raw content (first 1000 characters):")
                    print(response.text[:1000])
                    if len(response.text) > 1000:
                        print("... (truncated)")

            else:
                print(f"❌ ERROR: HTTP {response.status_code}")
                print("Response content:")
                print(response.text[:500])

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kick_api()