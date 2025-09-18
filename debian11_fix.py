#!/usr/bin/env python3
"""
Debian 11 Fix for CloudflareScraper

This script fixes issues with Python 3.9 on Debian 11 and sets up CloudflareScraper correctly.
"""

import sys
import os
import subprocess

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def run_command(cmd, description):
    """Run a command and show output"""
    print(f"\nRunning: {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAILED: {description}")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def check_and_install_venv():
    """Check and install python3-venv if needed"""
    print_header("FIXING VIRTUAL ENVIRONMENT ISSUE")

    print("Debian 11 often missing python3-venv package...")

    # Try to install python3-venv
    commands = [
        "apt update",
        "apt install -y python3-venv python3-pip python3-dev",
        "apt install -y build-essential libcurl4-openssl-dev libssl-dev",
        "apt install -y pkg-config libffi-dev"
    ]

    for cmd in commands:
        if not run_command(f"sudo {cmd}", f"Installing packages: {cmd}"):
            print(f"⚠️ Warning: Failed to run {cmd}")
            print("You may need to run this manually with sudo")

    return True

def create_venv_manually():
    """Create virtual environment manually"""
    print_header("CREATING VIRTUAL ENVIRONMENT")

    # Remove existing venv if it exists
    if os.path.exists("cloudflare_env"):
        print("Removing existing cloudflare_env directory...")
        run_command("rm -rf cloudflare_env", "Removing old virtual environment")

    # Try different methods to create venv
    venv_commands = [
        "python3 -m venv cloudflare_env",
        "python3 -m virtualenv cloudflare_env",
        "virtualenv -p python3 cloudflare_env"
    ]

    for cmd in venv_commands:
        print(f"\nTrying: {cmd}")
        if run_command(cmd, f"Creating venv with: {cmd}"):
            return True

    # If all fail, try installing virtualenv first
    print("\nTrying to install virtualenv...")
    if run_command("pip3 install virtualenv", "Installing virtualenv"):
        if run_command("virtualenv -p python3 cloudflare_env", "Creating venv with virtualenv"):
            return True

    return False

def test_venv():
    """Test if virtual environment works"""
    print_header("TESTING VIRTUAL ENVIRONMENT")

    if not os.path.exists("cloudflare_env/bin/activate"):
        print("❌ Virtual environment not found")
        return False

    # Test activation
    test_cmd = "source cloudflare_env/bin/activate && python --version"
    if run_command(test_cmd, "Testing virtual environment activation"):
        print("✅ Virtual environment working!")
        return True
    else:
        print("❌ Virtual environment not working")
        return False

def install_dependencies():
    """Install dependencies in virtual environment"""
    print_header("INSTALLING DEPENDENCIES")

    commands = [
        "source cloudflare_env/bin/activate && pip install --upgrade pip",
        "source cloudflare_env/bin/activate && pip install wheel setuptools",
        "source cloudflare_env/bin/activate && pip install -r requirements.txt",
        "source cloudflare_env/bin/activate && pip install -e ."
    ]

    for cmd in commands:
        description = cmd.split("&&")[-1].strip()
        if not run_command(cmd, description):
            print(f"❌ Failed: {description}")
            return False

    return True

def test_import():
    """Test CloudflareScraper import"""
    print_header("TESTING IMPORT")

    test_cmd = '''source cloudflare_env/bin/activate && python -c "
import cloudflare_research as cfr
print('✅ CloudflareScraper imported successfully!')
print(f'Version: {getattr(cfr, \\"__version__\\", \\"Unknown\\")}')
"'''

    return run_command(test_cmd, "Testing CloudflareScraper import")

def quick_functionality_test():
    """Quick test of basic functionality"""
    print_header("QUICK FUNCTIONALITY TEST")

    test_script = '''
import cloudflare_research as cfr
import sys

try:
    print("Creating scraper...")
    scraper = cfr.create_scraper()
    print("✅ Scraper created")

    print("Testing basic HTTP request...")
    response = scraper.get("https://httpbin.org/ip", timeout=10)
    data = response.json()
    print(f"✅ HTTP request successful: {response.status_code}")
    print(f"✅ Server IP: {data.get('origin', 'Unknown')}")

    print("Testing Cloudflare site...")
    response = scraper.get("https://discord.com", timeout=15)
    cf_ray = response.headers.get('cf-ray', 'Not detected')
    print(f"✅ Discord.com: {response.status_code}")
    print(f"✅ CF-RAY: {cf_ray}")

    if cf_ray != 'Not detected':
        print("🎉 SUCCESS: Cloudflare bypass working!")
    else:
        print("ℹ️ No Cloudflare detected")

    scraper.close()
    print("✅ All tests passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
'''

    # Write test to file
    with open("temp_quick_test.py", "w") as f:
        f.write(test_script)

    # Run test
    result = run_command("source cloudflare_env/bin/activate && python temp_quick_test.py",
                        "Running quick functionality test")

    # Clean up
    if os.path.exists("temp_quick_test.py"):
        os.remove("temp_quick_test.py")

    return result

def create_debian11_usage_script():
    """Create a usage script specifically for Debian 11"""
    print_header("CREATING DEBIAN 11 USAGE SCRIPT")

    script_content = '''#!/usr/bin/env python3
"""
CloudflareScraper Usage Script for Debian 11

This script shows how to use CloudflareScraper on Debian 11 with Python 3.9
"""

import cloudflare_research as cfr
import time

def test_basic_usage():
    """Test basic CloudflareScraper usage"""
    print("CloudflareScraper Basic Usage Test")
    print("=" * 40)

    # Create scraper with conservative settings for Debian 11
    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=5,
        requests_per_second=2.0,
        timeout=30.0
    )

    with cfr.create_scraper(config) as scraper:
        # Test 1: Basic HTTP
        print("\\n1. Testing basic HTTP...")
        response = scraper.get("https://httpbin.org/get")
        print(f"   Status: {response.status_code}")

        # Test 2: JSON parsing
        print("\\n2. Testing JSON parsing...")
        data = response.json()
        print(f"   User-Agent: {data.get('headers', {}).get('User-Agent', 'N/A')[:50]}...")

        # Test 3: Cloudflare site
        print("\\n3. Testing Cloudflare site...")
        response = scraper.get("https://discord.com")
        cf_ray = response.headers.get('cf-ray', 'Not detected')
        print(f"   Discord Status: {response.status_code}")
        print(f"   CF-RAY: {cf_ray}")
        print(f"   Content Length: {len(response.text)}")

        if cf_ray != 'Not detected':
            print("   🎉 SUCCESS: Cloudflare bypassed!")
        else:
            print("   ℹ️ No Cloudflare detected")

        # Test 4: POST request
        print("\\n4. Testing POST request...")
        post_data = {"debian": "11", "python": "3.9", "test": True}
        response = scraper.post("https://httpbin.org/post", json=post_data)
        print(f"   POST Status: {response.status_code}")

        if response.ok:
            data = response.json()
            received = data.get('json', {})
            print(f"   Data sent and received: {received.get('debian') == '11'}")

def test_your_sites():
    """Template for testing your own sites"""
    print("\\n" + "=" * 50)
    print("TEST YOUR OWN SITES")
    print("=" * 50)

    # Replace these with your actual target sites
    your_sites = [
        # "https://your-site-1.com",
        # "https://your-site-2.com",
        "https://example.com",  # Example site for testing
    ]

    with cfr.create_scraper() as scraper:
        for site in your_sites:
            print(f"\\nTesting: {site}")
            try:
                start_time = time.time()
                response = scraper.get(site, timeout=20)
                duration = time.time() - start_time

                print(f"  Status: {response.status_code}")
                print(f"  Time: {duration:.2f}s")
                print(f"  Size: {len(response.text)} chars")

                # Check Cloudflare indicators
                cf_ray = response.headers.get('cf-ray')
                cf_cache = response.headers.get('cf-cache-status')
                server = response.headers.get('server', '').lower()

                if cf_ray:
                    print(f"  🛡️ CF-RAY: {cf_ray}")
                    print(f"  ✅ Cloudflare bypassed!")
                elif 'cloudflare' in server:
                    print(f"  🛡️ Cloudflare server detected")
                else:
                    print(f"  ℹ️ No Cloudflare protection")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            # Respectful delay
            time.sleep(1)

if __name__ == "__main__":
    print("CloudflareScraper on Debian 11 with Python 3.9")
    print("=" * 50)

    test_basic_usage()
    test_your_sites()

    print("\\n✅ Usage example completed!")
    print("\\nTo run this script:")
    print("1. source cloudflare_env/bin/activate")
    print("2. python debian11_usage.py")
'''

    # Write the script
    with open("debian11_usage.py", "w") as f:
        f.write(script_content)

    print("✅ Created debian11_usage.py")
    print("Run with: source cloudflare_env/bin/activate && python debian11_usage.py")

def main():
    """Main execution"""
    print_header("CLOUDFLARE SCRAPER - DEBIAN 11 FIX")
    print("This script will fix CloudflareScraper setup issues on Debian 11")
    print("Detected: Debian 11.11 with Python 3.9.2")
    print()

    # Check if we're in the right directory
    if not (os.path.exists("cloudflare_research") and os.path.exists("requirements.txt")):
        print("❌ Error: Not in CF_Solver directory")
        print("Please run this script from the CF_Solver directory")
        return

    success_count = 0
    total_steps = 6

    # Step 1: Install missing packages
    if check_and_install_venv():
        success_count += 1

    # Step 2: Create virtual environment
    if create_venv_manually():
        success_count += 1
    else:
        print("❌ Cannot create virtual environment. Stopping.")
        return

    # Step 3: Test virtual environment
    if test_venv():
        success_count += 1
    else:
        print("❌ Virtual environment not working. Stopping.")
        return

    # Step 4: Install dependencies
    if install_dependencies():
        success_count += 1

    # Step 5: Test import
    if test_import():
        success_count += 1

    # Step 6: Quick functionality test
    if quick_functionality_test():
        success_count += 1

    # Create usage script
    create_debian11_usage_script()

    # Final report
    print_header("FINAL REPORT")
    print(f"Completed: {success_count}/{total_steps} steps successful")

    if success_count == total_steps:
        print("🎉 SUCCESS: CloudflareScraper is now working on Debian 11!")
        print()
        print("✅ Next steps:")
        print("1. source cloudflare_env/bin/activate")
        print("2. python debian11_usage.py")
        print("3. Test against your target sites")
    elif success_count >= 4:
        print("⚠️ PARTIAL SUCCESS: Basic functionality should work")
        print("Some advanced features may have issues")
    else:
        print("❌ SETUP FAILED: Multiple issues detected")
        print("You may need to manually install missing packages")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")