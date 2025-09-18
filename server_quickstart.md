# CloudflareScraper Server Testing - Quick Start Guide

## Method 1: Simple Upload and Test (Recommended)

### Step 1: Prepare Files for Upload

**Essential files to upload to your server:**
```
1. cloudflare_research/ (entire directory)
2. requirements.txt
3. setup.py
4. quick_server_test.py
5. simple_cloudscraper_example.py
```

### Step 2: Upload to Server

**Option A: SCP (Linux/Mac)**
```bash
# From your local machine
scp -r cloudflare_research/ user@your-server.com:/home/user/
scp requirements.txt setup.py quick_server_test.py user@your-server.com:/home/user/
```

**Option B: SFTP/FTP**
```bash
# Use your preferred FTP client to upload:
# - cloudflare_research/ directory
# - requirements.txt
# - setup.py
# - quick_server_test.py
```

**Option C: Git Clone**
```bash
# On your server (if you have a Git repo)
git clone https://github.com/yourusername/CF_Solver.git
cd CF_Solver
```

### Step 3: Install on Server

**SSH into your server and run:**
```bash
# Create virtual environment (recommended)
python3 -m venv cloudflare_env
source cloudflare_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install CloudflareScraper
pip install -e .

# Test installation
python quick_server_test.py
```

### Step 4: Basic Test

**Create a test script on your server:**
```python
# save as test_cloudflare.py
import cloudflare_research as cfr

def test_on_server():
    print("Testing CloudflareScraper on server...")

    with cfr.create_scraper() as scraper:
        # Test basic functionality
        response = scraper.get("https://httpbin.org/ip")
        data = response.json()
        print(f"Server IP: {data['origin']}")

        # Test Cloudflare site
        response = scraper.get("https://discord.com")
        if 'cf-ray' in response.headers:
            print(f"SUCCESS: Cloudflare bypassed! CF-RAY: {response.headers['cf-ray']}")
        else:
            print("INFO: No Cloudflare detected")

        print(f"Status: {response.status_code}")
        print(f"Content: {len(response.text)} characters")

if __name__ == "__main__":
    test_on_server()
```

**Run the test:**
```bash
python test_cloudflare.py
```

## Method 2: Simple Copy-Paste Test

If you can't upload files easily, create this minimal test:

### Step 1: Create test file on server
```bash
# SSH to server and create test file
nano test_cf_simple.py
```

### Step 2: Paste this code:
```python
#!/usr/bin/env python3
"""
Minimal CloudflareScraper test - requires module to be installed
"""

def test_cloudflare_simple():
    try:
        import cloudflare_research as cfr
        print("✓ CloudflareScraper imported successfully")

        # Create scraper
        scraper = cfr.create_scraper()
        print("✓ Scraper created")

        # Test basic request
        response = scraper.get("https://httpbin.org/get")
        print(f"✓ Basic request: {response.status_code}")

        # Test Cloudflare site
        response = scraper.get("https://discord.com")
        cf_detected = 'cf-ray' in response.headers
        print(f"✓ Cloudflare test: {response.status_code} (CF: {cf_detected})")

        if cf_detected:
            print(f"🎉 SUCCESS: Bypassed Cloudflare! Ray: {response.headers['cf-ray']}")

        scraper.close()
        print("✓ All tests passed!")

    except ImportError:
        print("✗ CloudflareScraper not installed")
        print("Run: pip install cloudflare-research")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_cloudflare_simple()
```

### Step 3: Run test
```bash
python test_cf_simple.py
```

## Expected Output

**Successful test output should look like:**
```
✓ CloudflareScraper imported successfully
✓ Scraper created
✓ Basic request: 200
✓ Cloudflare test: 200 (CF: True)
🎉 SUCCESS: Bypassed Cloudflare! Ray: 980e6a16b808a932-SYD
✓ All tests passed!
```

## Using CloudflareScraper in Your Code

Once installed, use it exactly like cloudscraper:

```python
import cloudflare_research as cfr

# Method 1: Basic usage
scraper = cfr.create_scraper()
response = scraper.get("https://your-target-site.com")
print(response.text)
scraper.close()

# Method 2: Context manager (recommended)
with cfr.create_scraper() as scraper:
    response = scraper.get("https://your-target-site.com")
    if 'cf-ray' in response.headers:
        print(f"Bypassed Cloudflare! Ray: {response.headers['cf-ray']}")
    print(response.text)

# Method 3: One-off requests
response = cfr.get("https://your-target-site.com")
print(response.text)
```

## Troubleshooting

**ImportError: No module named 'cloudflare_research'**
```bash
# Make sure you're in the right directory and run:
pip install -e .
```

**Build errors on installation:**
```bash
# Ubuntu/Debian:
sudo apt install python3-dev build-essential libcurl4-openssl-dev

# CentOS/RHEL:
sudo yum install python3-devel gcc libcurl-devel
```

**Permission errors:**
```bash
# Use virtual environment:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Performance Testing

Test with your target sites:

```python
import cloudflare_research as cfr
import time

def test_your_sites():
    target_sites = [
        "https://your-site-1.com",
        "https://your-site-2.com",
        # Add your Cloudflare-protected sites
    ]

    with cfr.create_scraper() as scraper:
        for site in target_sites:
            start = time.time()
            response = scraper.get(site)
            duration = time.time() - start

            cf_ray = response.headers.get('cf-ray', 'Not detected')
            print(f"{site}: {response.status_code} ({duration:.2f}s) CF-RAY: {cf_ray}")

test_your_sites()
```

## API Server Setup (Optional)

For remote access, create an API server:

```python
# api.py
from flask import Flask, request, jsonify
import cloudflare_research as cfr

app = Flask(__name__)
scraper = cfr.create_scraper()

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url')

    response = scraper.get(url)
    return jsonify({
        'status': response.status_code,
        'content': response.text,
        'cloudflare_detected': 'cf-ray' in response.headers,
        'cf_ray': response.headers.get('cf-ray')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Run with: `python api.py`

Your CloudflareScraper is ready for server deployment! 🚀