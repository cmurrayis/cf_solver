#!/usr/bin/env python3
"""
Simple CloudflareScraper Example

This is exactly how you would use cloudscraper, but with CloudflareScraper
for automatic Cloudflare bypass capabilities.
"""

# Instead of: import cloudscraper
import cloudflare_research as cfr

# Example 1: Basic usage (exactly like cloudscraper)
print("Example 1: Basic Usage")
print("-" * 22)

scraper = cfr.create_scraper()
response = scraper.get("https://httpbin.org/get")
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:100]}...")
scraper.close()

print()

# Example 2: Context manager (recommended)
print("Example 2: Context Manager")
print("-" * 26)

with cfr.create_scraper() as scraper:
    response = scraper.get("https://httpbin.org/ip")
    data = response.json()
    print(f"Your IP: {data['origin']}")

print()

# Example 3: One-off requests
print("Example 3: One-off Requests")
print("-" * 27)

response = cfr.get("https://httpbin.org/user-agent")
data = response.json()
print(f"User-Agent: {data['user-agent'][:50]}...")

print()

# Example 4: POST request
print("Example 4: POST Request")
print("-" * 23)

response = cfr.post("https://httpbin.org/post",
                    json={"message": "Hello from CloudflareScraper!"})
if response.ok:
    data = response.json()
    print(f"Posted message: {data['json']['message']}")

print()
print("That's it! CloudflareScraper works exactly like cloudscraper,")
print("but automatically bypasses Cloudflare protection!")