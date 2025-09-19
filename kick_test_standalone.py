#!/usr/bin/env python3
"""
Kick.com API Test - Using Standalone CloudflareScraper

This script tests the standalone CloudflareScraper module with Kick.com API.
Only requires the single cloudflare_scraper_standalone.py file.
"""

import cloudflare_scraper_standalone as cfr
import json

def test_kick_api():
    """Test Kick.com API with standalone scraper"""
    print("Kick.com API Test - Standalone Scraper")
    print("=" * 45)

    url = "https://kick.com/api/v1/channels/adinross"
    print(f"Target: {url}")
    print()

    try:
        # Simple one-liner approach
        print("Method 1: One-liner...")
        response = cfr.get(url)
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Content: {len(response.text)} chars")

        # Context manager approach
        print("\nMethod 2: Context manager...")
        with cfr.create_scraper() as scraper:
            response = scraper.get(url)

            # Show response details
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Content Type: {response.headers.get('content-type', 'Unknown')}")

            # Check Cloudflare
            cf_ray = response.headers.get('cf-ray')
            if cf_ray:
                print(f"🛡️ Cloudflare CF-RAY: {cf_ray}")
            else:
                print("ℹ️ No Cloudflare detected")

            if response.ok:
                print("\n📄 Response Data:")
                print("-" * 30)

                try:
                    # Parse JSON response
                    data = response.json()

                    # Pretty print with indentation
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    print(formatted)

                    # Extract key info
                    print("\n🔍 Key Information:")
                    print("-" * 20)

                    if isinstance(data, dict):
                        # User info
                        if 'user' in data:
                            user = data['user']
                            print(f"Username: {user.get('username', 'N/A')}")
                            print(f"Followers: {user.get('followers_count', 'N/A')}")
                            print(f"Bio: {user.get('bio', 'N/A')[:100]}...")

                        # Channel info
                        if 'is_live' in data:
                            live = data.get('is_live', False)
                            print(f"Currently Live: {live}")

                        if 'category' in data and data['category']:
                            category = data['category']
                            if isinstance(category, dict):
                                print(f"Category: {category.get('name', 'N/A')}")

                        # Recent stream info
                        if 'livestream' in data and data['livestream']:
                            stream = data['livestream']
                            if isinstance(stream, dict):
                                print(f"Stream Title: {stream.get('session_title', 'N/A')}")
                                print(f"Viewers: {stream.get('viewer_count', 'N/A')}")

                except json.JSONDecodeError:
                    print("⚠️ Response is not valid JSON")
                    print("Raw content (first 500 chars):")
                    print(response.text[:500])
            else:
                print(f"❌ HTTP Error: {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kick_api()