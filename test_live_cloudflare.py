#!/usr/bin/env python3
"""
Live Cloudflare Testing Script

This script tests the CloudflareBypass tool against real Cloudflare-protected sites
following ethical guidelines and responsible disclosure practices.

Usage:
    python test_live_cloudflare.py

Requirements:
    - Only test sites you own or have explicit permission to test
    - Follow rate limiting and be respectful of target systems
    - Report any findings responsibly
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
from cloudflare_research import CloudflareBypass, CloudflareBypassConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CloudflareTest")

class LiveCloudflareTestSuite:
    """Comprehensive test suite for live Cloudflare testing."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

        # Ethical testing configuration
        self.config = CloudflareBypassConfig(
            max_concurrent_requests=1,      # Single request at a time
            requests_per_second=0.2,        # Very conservative rate
            timeout=30.0,                   # Reasonable timeout
            enable_javascript_challenges=True,
            enable_turnstile_solving=True,
            challenge_timeout=60.0,
            browser_version="120.0.0.0",
            randomize_headers=True,
            user_agent="CloudflareResearch/1.0 (Educational Testing; +https://github.com/yourusername/CF_Solver)"
        )

    async def test_site(self, url: str, test_name: str, expected_behavior: str = None) -> Dict[str, Any]:
        """Test a single site and return detailed results."""

        logger.info(f"🧪 Testing: {test_name}")
        logger.info(f"🌐 URL: {url}")

        result = {
            "test_name": test_name,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "expected_behavior": expected_behavior
        }

        try:
            async with CloudflareBypass(self.config) as bypass:
                start_time = time.time()
                response = await bypass.get(url)
                duration = time.time() - start_time

                # Analyze response
                cloudflare_detected = self._detect_cloudflare(response.headers)
                challenge_indicators = self._detect_challenge_type(response)

                result.update({
                    "success": True,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 3),
                    "cloudflare_detected": cloudflare_detected,
                    "challenge_indicators": challenge_indicators,
                    "response_size": len(response.body),
                    "headers": dict(response.headers),
                    "cloudflare_ray": response.headers.get("cf-ray"),
                    "server": response.headers.get("server"),
                })

                logger.info(f"✅ Status: {response.status_code}")
                logger.info(f"⏱️  Duration: {duration:.2f}s")
                if cloudflare_detected:
                    logger.info(f"☁️  Cloudflare Ray: {response.headers.get('cf-ray', 'N/A')}")

                # Check for challenge solving
                if challenge_indicators:
                    logger.info(f"🧩 Challenge detected: {', '.join(challenge_indicators)}")
                    if response.status_code == 200:
                        logger.info("🎉 Challenge successfully solved!")
                        result["challenge_solved"] = True
                    else:
                        logger.warning("⚠️  Challenge not solved")
                        result["challenge_solved"] = False

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            result.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })

        self.results.append(result)
        return result

    def _detect_cloudflare(self, headers: Dict[str, str]) -> bool:
        """Detect if the response came through Cloudflare."""
        cloudflare_indicators = [
            "cf-ray", "cf-cache-status", "cf-request-id",
            "server" in headers and "cloudflare" in headers["server"].lower()
        ]
        return any(cloudflare_indicators)

    def _detect_challenge_type(self, response) -> List[str]:
        """Detect what type of challenge was encountered."""
        indicators = []

        # Check status codes
        if response.status_code == 403:
            indicators.append("403_forbidden")
        elif response.status_code == 503:
            indicators.append("503_service_unavailable")

        # Check response body for challenge indicators
        body_lower = response.body.lower()
        if "challenge" in body_lower:
            indicators.append("challenge_page")
        if "javascript" in body_lower and "enable" in body_lower:
            indicators.append("javascript_challenge")
        if "turnstile" in body_lower:
            indicators.append("turnstile_challenge")
        if "checking your browser" in body_lower:
            indicators.append("browser_check")

        return indicators

    async def run_basic_tests(self):
        """Run basic functionality tests."""
        logger.info("🚀 Starting Basic Cloudflare Tests")
        logger.info("=" * 50)

        basic_tests = [
            ("https://httpbin.org/get", "Control Test (No Cloudflare)", "Should work normally"),
            ("https://httpbin.org/status/403", "403 Status Test", "Should handle 403 responses"),
            ("https://httpbin.org/delay/3", "Timeout Test", "Should handle delays"),
        ]

        for url, name, expected in basic_tests:
            await self.test_site(url, name, expected)
            await asyncio.sleep(2)  # Respectful delay

    async def run_cloudflare_tests(self):
        """Run tests against known Cloudflare-protected sites."""
        logger.info("\n🌩️ Starting Cloudflare-Protected Site Tests")
        logger.info("=" * 50)

        # IMPORTANT: Only test sites you have permission to test
        # These are examples - replace with sites you own or have permission to test
        cloudflare_tests = [
            ("https://discord.com", "Discord Main Page", "May trigger bot detection"),
            ("https://example.com", "Example.com", "Basic Cloudflare protection"),
            # Add your own test sites here
        ]

        for url, name, expected in cloudflare_tests:
            await self.test_site(url, name, expected)
            await asyncio.sleep(5)  # Longer delay for external sites

    async def run_challenge_tests(self):
        """Run specific challenge detection tests."""
        logger.info("\n🧩 Starting Challenge Detection Tests")
        logger.info("=" * 50)

        # Test with different configurations that might trigger challenges
        challenge_configs = [
            {
                "name": "Suspicious User Agent Test",
                "config_override": {"user_agent": "bot/1.0"},
                "url": "https://httpbin.org/user-agent"
            },
            {
                "name": "High Request Rate Test",
                "config_override": {"requests_per_second": 5.0},
                "url": "https://httpbin.org/get"
            }
        ]

        for test_config in challenge_configs:
            # Create modified config for this test
            config = CloudflareBypassConfig(**{
                **self.config.__dict__,
                **test_config["config_override"]
            })

            logger.info(f"🎯 {test_config['name']}")
            try:
                async with CloudflareBypass(config) as bypass:
                    response = await bypass.get(test_config["url"])
                    logger.info(f"✅ {test_config['name']}: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ {test_config['name']}: {e}")

            await asyncio.sleep(3)

    def generate_comprehensive_report(self):
        """Generate a detailed test report."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        # Calculate statistics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get("success", False))
        cloudflare_detections = sum(1 for r in self.results if r.get("cloudflare_detected", False))
        challenges_solved = sum(1 for r in self.results if r.get("challenge_solved", False))

        print("\n" + "="*60)
        print("📊 COMPREHENSIVE CLOUDFLARE BYPASS TEST REPORT")
        print("="*60)
        print(f"🕐 Test Duration: {duration}")
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests} ({(successful_tests/total_tests)*100:.1f}%)")
        print(f"☁️  Cloudflare Detected: {cloudflare_detections}")
        print(f"🧩 Challenges Solved: {challenges_solved}")

        # Detailed breakdown
        print("\n📋 DETAILED RESULTS:")
        print("-" * 40)
        for result in self.results:
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"{status} {result['test_name']}")
            if result.get("cloudflare_detected"):
                print(f"    ☁️  Cloudflare Ray: {result.get('cloudflare_ray', 'N/A')}")
            if result.get("challenge_indicators"):
                print(f"    🧩 Challenges: {', '.join(result['challenge_indicators'])}")
            if not result.get("success"):
                print(f"    ❌ Error: {result.get('error', 'Unknown')}")
            print()

        # Save detailed results
        report_filename = f"cloudflare_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, "w") as f:
            json.dump({
                "test_summary": {
                    "start_time": self.start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": (successful_tests/total_tests)*100,
                    "cloudflare_detections": cloudflare_detections,
                    "challenges_solved": challenges_solved
                },
                "detailed_results": self.results,
                "configuration": self.config.__dict__
            }, f, indent=2)

        print(f"📄 Detailed report saved to: {report_filename}")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 20)
        if successful_tests == total_tests:
            print("🎉 All tests passed! Your tool is working excellently.")
        elif successful_tests > total_tests * 0.8:
            print("👍 Most tests passed. Consider investigating failed tests.")
        else:
            print("⚠️  Many tests failed. Review configuration and error logs.")

        if challenges_solved > 0:
            print(f"🧩 Successfully solved {challenges_solved} challenges!")

        print("\n🔒 SECURITY REMINDER:")
        print("- Only test sites you own or have explicit permission to test")
        print("- Follow responsible disclosure for any security findings")
        print("- Respect rate limits and server resources")
        print("- Comply with applicable laws and regulations")

async def main():
    """Main test execution function."""
    print("🌩️ CloudflareBypass Live Testing Suite")
    print("=====================================")
    print()
    print("⚠️  IMPORTANT: Only test sites you own or have explicit permission to test!")
    print("📚 Follow ethical guidelines in ETHICAL_USAGE.md")
    print()

    # Ask for confirmation
    response = input("Do you have permission to test the configured sites? (y/N): ")
    if response.lower() != 'y':
        print("❌ Exiting. Please only test sites you own or have permission to test.")
        return

    suite = LiveCloudflareTestSuite()

    try:
        # Run test suite
        await suite.run_basic_tests()
        await suite.run_cloudflare_tests()
        await suite.run_challenge_tests()

    except KeyboardInterrupt:
        logger.info("\n⏹️  Testing interrupted by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
    finally:
        # Always generate report
        suite.generate_comprehensive_report()

if __name__ == "__main__":
    asyncio.run(main())