#!/usr/bin/env python3
"""
Quick test of the fixed CloudflareScraper standalone
"""

import cloudflare_scraper_standalone as cfs

# Test the user agent generation fix
def test_user_agent_generation():
    print("Testing user agent generation...")

    # Test with detailed Chrome version
    manager = cfs.BrowserFingerprintManager()
    fingerprint = manager.generate_fingerprint("124.0.6367.60")
    print(f"User Agent: {fingerprint.user_agent}")

    # Should contain the correct Chrome version
    assert "Chrome/124.0.6367.60" in fingerprint.user_agent
    print("✅ User agent generation working!")

# Test TLS fingerprint
def test_tls_fingerprint():
    print("Testing TLS fingerprint...")

    tls_manager = cfs.ChromeTLSFingerprintManager()
    fingerprint = tls_manager.get_fingerprint_by_string("124.0.6367.60")
    print(f"TLS Fingerprint: {type(fingerprint).__name__}")
    print("✅ TLS fingerprint working!")

# Test basic request
def test_basic_request():
    print("Testing basic HTTP request...")

    response = cfs.get("https://httpbin.org/ip")
    data = response.json()
    print(f"IP: {data.get('origin')}")
    print("✅ Basic request working!")

if __name__ == "__main__":
    try:
        test_user_agent_generation()
        test_tls_fingerprint()
        test_basic_request()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()