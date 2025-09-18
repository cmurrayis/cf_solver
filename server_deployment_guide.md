# Server Deployment Guide for CloudflareScraper

## Method 1: Direct Server Installation

### Step 1: Upload Your Code

**Option A: Git Clone (Recommended)**
```bash
# On your server
git clone https://github.com/yourusername/CF_Solver.git
cd CF_Solver
```

**Option B: SCP/SFTP Upload**
```bash
# From your local machine
scp -r CF_Solver/ user@your-server.com:/home/user/
```

**Option C: Archive Upload**
```bash
# Create archive locally
tar -czf cloudflare_scraper.tar.gz cloudflare_research/ requirements.txt setup.py

# Upload to server
scp cloudflare_scraper.tar.gz user@your-server.com:/home/user/

# Extract on server
ssh user@your-server.com
tar -xzf cloudflare_scraper.tar.gz
```

### Step 2: Server Setup

**Install Python 3.11+ and Dependencies:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
sudo apt install build-essential libcurl4-openssl-dev

# CentOS/RHEL
sudo yum install python3.11 python3.11-devel
sudo yum groupinstall "Development Tools"
sudo yum install libcurl-devel

# Create virtual environment
python3.11 -m venv cloudflare_env
source cloudflare_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Test Installation

**Create Test Script on Server:**
```python
# save as server_test.py
import cloudflare_research as cfr

def test_server_deployment():
    print("Testing CloudflareScraper on server...")

    with cfr.create_scraper() as scraper:
        # Test basic functionality
        response = scraper.get("https://httpbin.org/ip")
        data = response.json()
        print(f"Server IP: {data['origin']}")

        # Test Cloudflare site
        response = scraper.get("https://discord.com")
        if 'cf-ray' in response.headers:
            print(f"✅ Cloudflare bypass working! Ray: {response.headers['cf-ray']}")
        else:
            print("ℹ️ No Cloudflare detected")

        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)}")

if __name__ == "__main__":
    test_server_deployment()
```

**Run Test:**
```bash
python server_test.py
```

## Method 2: Docker Deployment

### Step 1: Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY cloudflare_research/ ./cloudflare_research/
COPY setup.py .

# Install the package
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 scraper
USER scraper

# Default command
CMD ["python", "-c", "import cloudflare_research; print('CloudflareScraper ready!')"]
```

### Step 2: Build and Deploy

```bash
# Build Docker image
docker build -t cloudflare-scraper .

# Upload to your server (or use registry)
docker save cloudflare-scraper | gzip > cloudflare-scraper.tar.gz
scp cloudflare-scraper.tar.gz user@your-server.com:/tmp/

# On server: Load and run
ssh user@your-server.com
docker load < /tmp/cloudflare-scraper.tar.gz
docker run -it cloudflare-scraper python server_test.py
```

## Method 3: API Server Deployment

### Step 1: Create API Server

```python
# api_server.py
from flask import Flask, request, jsonify
import cloudflare_research as cfr
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Global scraper instance
scraper = None

def get_scraper():
    global scraper
    if scraper is None:
        scraper = cfr.create_scraper()
    return scraper

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "CloudflareScraper API"})

@app.route('/scrape', methods=['POST'])
def scrape_url():
    try:
        data = request.get_json()
        url = data.get('url')
        method = data.get('method', 'GET').upper()
        headers = data.get('headers', {})

        if not url:
            return jsonify({"error": "URL is required"}), 400

        scraper = get_scraper()

        if method == 'GET':
            response = scraper.get(url, headers=headers)
        elif method == 'POST':
            post_data = data.get('data')
            json_data = data.get('json')
            response = scraper.post(url, data=post_data, json=json_data, headers=headers)
        else:
            return jsonify({"error": f"Method {method} not supported"}), 400

        # Check for Cloudflare
        cloudflare_detected = 'cf-ray' in response.headers

        result = {
            "success": True,
            "status_code": response.status_code,
            "url": response.url,
            "headers": dict(response.headers),
            "content": response.text,
            "cloudflare_detected": cloudflare_detected,
            "cloudflare_ray": response.headers.get('cf-ray'),
            "content_length": len(response.text)
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    try:
        scraper = get_scraper()

        # Test with httpbin
        response = scraper.get("https://httpbin.org/ip")
        data = response.json()

        # Test with Cloudflare site
        cf_response = scraper.get("https://discord.com")
        cf_detected = 'cf-ray' in cf_response.headers

        return jsonify({
            "basic_test": {
                "status": response.status_code,
                "server_ip": data.get('origin')
            },
            "cloudflare_test": {
                "status": cf_response.status_code,
                "cloudflare_detected": cf_detected,
                "cf_ray": cf_response.headers.get('cf-ray'),
                "content_length": len(cf_response.text)
            },
            "overall_status": "working"
        })

    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### Step 2: Deploy API Server

```bash
# On server
python api_server.py

# Test API
curl http://your-server.com:5000/health
curl http://your-server.com:5000/test

# Test scraping
curl -X POST http://your-server.com:5000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://discord.com", "method": "GET"}'
```

## Method 4: Systemd Service (Production)

### Step 1: Create Service File

```ini
# /etc/systemd/system/cloudflare-scraper.service
[Unit]
Description=CloudflareScraper API Service
After=network.target

[Service]
Type=simple
User=scraper
WorkingDirectory=/home/scraper/CF_Solver
Environment=PATH=/home/scraper/cloudflare_env/bin
ExecStart=/home/scraper/cloudflare_env/bin/python api_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-scraper
sudo systemctl start cloudflare-scraper
sudo systemctl status cloudflare-scraper
```

## Method 5: Quick Remote Test Script

```bash
# quick_server_test.sh
#!/bin/bash

echo "CloudflareScraper Server Test"
echo "============================="

# Create test script
cat > remote_test.py << 'EOF'
import cloudflare_research as cfr
import json

def main():
    print("🚀 CloudflareScraper Server Test")
    print("=" * 35)

    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=10,
        requests_per_second=2.0
    )

    with cfr.create_scraper(config) as scraper:
        # Test 1: Basic functionality
        print("\n1. Basic Test")
        response = scraper.get("https://httpbin.org/ip")
        data = response.json()
        print(f"   Server IP: {data['origin']}")
        print(f"   Status: {response.status_code}")

        # Test 2: Cloudflare site
        print("\n2. Cloudflare Test")
        response = scraper.get("https://discord.com")
        cf_ray = response.headers.get('cf-ray', 'Not detected')
        print(f"   Status: {response.status_code}")
        print(f"   CF-RAY: {cf_ray}")
        print(f"   Content: {len(response.text)} chars")

        # Test 3: POST request
        print("\n3. POST Test")
        response = scraper.post("https://httpbin.org/post",
                               json={"server": "test", "working": True})
        if response.ok:
            data = response.json()
            print(f"   Posted data: {data['json']}")

        print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    main()
EOF

# Run test
python remote_test.py
```

## Testing from Your Local Machine

### Remote API Testing Script

```python
# local_remote_test.py
import requests
import json

def test_remote_scraper(server_url):
    """Test your deployed CloudflareScraper from local machine"""

    print(f"Testing CloudflareScraper at: {server_url}")
    print("=" * 50)

    # Test 1: Health check
    try:
        response = requests.get(f"{server_url}/health")
        print(f"Health Check: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # Test 2: Basic scraping
    test_data = {
        "url": "https://httpbin.org/ip",
        "method": "GET"
    }

    try:
        response = requests.post(f"{server_url}/scrape", json=test_data)
        result = response.json()
        print(f"\nBasic Test:")
        print(f"  Status: {result['status_code']}")
        print(f"  Server IP: {json.loads(result['content'])['origin']}")
    except Exception as e:
        print(f"Basic test failed: {e}")

    # Test 3: Cloudflare site
    cf_test_data = {
        "url": "https://discord.com",
        "method": "GET"
    }

    try:
        response = requests.post(f"{server_url}/scrape", json=cf_test_data)
        result = response.json()
        print(f"\nCloudflare Test:")
        print(f"  Status: {result['status_code']}")
        print(f"  CF Detected: {result['cloudflare_detected']}")
        print(f"  CF-RAY: {result.get('cloudflare_ray', 'None')}")
        print(f"  Content Length: {result['content_length']}")
    except Exception as e:
        print(f"Cloudflare test failed: {e}")

if __name__ == "__main__":
    # Replace with your server URL
    server_url = "http://your-server.com:5000"
    test_remote_scraper(server_url)
```

## Recommended Deployment Steps

1. **Start Simple**: Use Method 1 (Direct Installation) first
2. **Test Thoroughly**: Run the server test script
3. **Add API Layer**: Implement Method 3 for remote access
4. **Production**: Use Method 4 (Systemd) for reliability
5. **Monitor**: Set up logging and monitoring

Your CloudflareScraper is ready for server deployment! Which method would you like to try first?