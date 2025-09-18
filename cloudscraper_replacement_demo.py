#!/usr/bin/env python3
"""
CloudflareScraper Demo - Drop-in replacement for cloudscraper

This script demonstrates how CloudflareScraper works as a perfect
drop-in replacement for cloudscraper with the exact same API.
"""

import cloudflare_research as cfr

def main():
    print("CloudflareScraper - Drop-in Replacement for cloudscraper")
    print("=" * 55)
    print()

    # Method 1: Basic usage (exact cloudscraper syntax)
    print("Method 1: Basic scraper usage")
    print("-" * 30)

    scraper = cfr.create_scraper()
    response = scraper.get("https://httpbin.org/get")

    print(f"Status: {response.status_code}")
    print(f"Response size: {len(response.text)} characters")
    print(f"Headers received: {len(response.headers)}")

    # Parse JSON response
    data = response.json()
    print(f"User-Agent sent: {data.get('headers', {}).get('User-Agent', 'N/A')[:50]}...")

    scraper.close()
    print()

    # Method 2: Context manager (recommended)
    print("Method 2: Using context manager")
    print("-" * 35)

    with cfr.create_scraper() as scraper:
        # GET request
        response = scraper.get("https://httpbin.org/ip")
        data = response.json()
        print(f"Your IP: {data.get('origin', 'Unknown')}")

        # POST request with JSON data
        post_data = {"message": "Hello from CloudflareScraper!", "timestamp": "2025-01-01"}
        response = scraper.post("https://httpbin.org/post", json=post_data)

        if response.ok:
            data = response.json()
            received = data.get('json', {})
            print(f"POST successful: {received.get('message', 'No message')}")
        else:
            print(f"POST failed: {response.status_code}")

    print()

    # Method 3: One-off requests (super simple)
    print("Method 3: One-off requests")
    print("-" * 30)

    # Single GET request
    response = cfr.get("https://httpbin.org/user-agent")
    data = response.json()
    user_agent = data.get('user-agent', 'Unknown')
    print(f"Detected User-Agent: {user_agent[:60]}...")

    # Single POST request
    response = cfr.post("https://httpbin.org/post",
                        json={"test": "CloudflareScraper working!"})
    print(f"POST Status: {response.status_code}")
    print()

    # Method 4: Advanced configuration
    print("Method 4: Custom configuration")
    print("-" * 35)

    # Create custom configuration
    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=10,      # Conservative limit
        requests_per_second=2.0,         # Respectful rate limiting
        timeout=15.0,                    # Custom timeout
        solve_javascript_challenges=True, # Enable JS challenge solving
        enable_tls_fingerprinting=True   # Advanced browser emulation
    )

    with cfr.create_scraper(config) as scraper:
        response = scraper.get("https://httpbin.org/delay/2")  # 2 second delay
        print(f"Delayed request completed: {response.status_code}")
        print(f"URL: {response.url}")

    print()

    # Method 5: Error handling (just like requests/cloudscraper)
    print("Method 5: Error handling")
    print("-" * 25)

    try:
        with cfr.create_scraper() as scraper:
            response = scraper.get("https://httpbin.org/status/404")
            print(f"Status: {response.status_code}")
            print(f"OK: {response.ok}")

            # This would raise an exception for 4xx/5xx status codes
            # response.raise_for_status()  # Uncomment to see error handling

    except Exception as e:
        print(f"Error handled: {e}")

    print()
    print("Summary: CloudflareScraper Usage")
    print("=" * 35)
    print("[OK] Exact same API as cloudscraper")
    print("[OK] Drop-in replacement - just change import")
    print("[OK] Automatic Cloudflare bypass")
    print("[OK] Advanced browser emulation")
    print("[OK] JavaScript challenge solving")
    print("[OK] Context manager support")
    print("[OK] One-off convenience functions")
    print("[OK] Custom configuration options")
    print()
    print("Migration from cloudscraper:")
    print("  OLD: import cloudscraper")
    print("  NEW: import cloudflare_research as cfr")
    print()
    print("  OLD: scraper = cloudscraper.create_scraper()")
    print("  NEW: scraper = cfr.create_scraper()")
    print()
    print("Everything else stays exactly the same!")

if __name__ == "__main__":
    main()