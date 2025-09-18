# CloudflareScraper Installation Guide for Debian 12

## Complete Step-by-Step Instructions

### Prerequisites Check

First, check your system:
```bash
# Check Debian version
cat /etc/debian_version
# Should show: 12.x

# Check current user
whoami

# Check if you have sudo access
sudo -l
```

## Step 1: System Preparation

### Update System Packages
```bash
# Update package list
sudo apt update

# Upgrade existing packages (optional but recommended)
sudo apt upgrade -y
```

### Install Essential Build Tools
```bash
# Install Python 3.11+ and development tools
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install build essentials and dependencies
sudo apt install -y build-essential curl wget git

# Install libcurl development headers (required for curl-cffi)
sudo apt install -y libcurl4-openssl-dev libssl-dev

# Install additional dependencies that might be needed
sudo apt install -y pkg-config libffi-dev
```

### Verify Python Installation
```bash
# Check Python version (should be 3.11+)
python3 --version

# Check pip
python3 -m pip --version
```

## Step 2: Upload CloudflareScraper Code

### Option A: Git Clone (if you have a repository)
```bash
# Clone your repository
git clone https://github.com/yourusername/CF_Solver.git
cd CF_Solver
```

### Option B: SCP Upload from Local Machine
```bash
# From your local Windows machine, upload to server
# Replace 'user' and 'your-server.com' with your details

# Upload main directory
scp -r cloudflare_research/ user@your-server.com:/home/user/

# Upload essential files
scp requirements.txt setup.py quick_server_test.py user@your-server.com:/home/user/

# Upload examples
scp simple_cloudscraper_example.py user@your-server.com:/home/user/
```

### Option C: Create Archive and Upload
```bash
# On your local machine, create archive
tar -czf cloudflare_scraper.tar.gz cloudflare_research/ requirements.txt setup.py *.py

# Upload archive
scp cloudflare_scraper.tar.gz user@your-server.com:/home/user/

# On server: extract
tar -xzf cloudflare_scraper.tar.gz
```

## Step 3: Create Virtual Environment

```bash
# Navigate to your project directory
cd /home/user  # or wherever you uploaded files

# Create virtual environment
python3 -m venv cloudflare_env

# Activate virtual environment
source cloudflare_env/bin/activate

# Verify virtual environment is active (should show the venv path)
which python
which pip
```

## Step 4: Install Dependencies

```bash
# Make sure you're in the virtual environment
source cloudflare_env/bin/activate

# Upgrade pip in virtual environment
pip install --upgrade pip

# Install wheel and setuptools
pip install wheel setuptools

# Install dependencies from requirements.txt
pip install -r requirements.txt

# If you get build errors, install additional packages:
# sudo apt install -y python3-wheel python3-setuptools-scm
```

## Step 5: Install CloudflareScraper

```bash
# Install CloudflareScraper in development mode
pip install -e .

# Verify installation
python -c "import cloudflare_research; print('✓ Import successful')"
```

## Step 6: Run Tests

### Quick Test
```bash
# Run the comprehensive test suite
python quick_server_test.py
```

### Manual Test
```bash
# Create a simple test file
cat > test_basic.py << 'EOF'
#!/usr/bin/env python3
import cloudflare_research as cfr

def test_basic():
    print("Testing CloudflareScraper on Debian 12...")

    with cfr.create_scraper() as scraper:
        # Test basic functionality
        response = scraper.get("https://httpbin.org/ip")
        data = response.json()
        print(f"Server IP: {data['origin']}")

        # Test Cloudflare site
        response = scraper.get("https://discord.com")
        cf_ray = response.headers.get('cf-ray', 'Not detected')

        print(f"Discord Status: {response.status_code}")
        print(f"CF-RAY: {cf_ray}")
        print(f"Content Length: {len(response.text)}")

        if cf_ray != 'Not detected':
            print("🎉 SUCCESS: Cloudflare bypass working!")
        else:
            print("ℹ️ No Cloudflare detected")

if __name__ == "__main__":
    test_basic()
EOF

# Run the test
python test_basic.py
```

## Step 7: Test Your Target Sites

```bash
# Create test for your specific sites
cat > test_my_sites.py << 'EOF'
#!/usr/bin/env python3
import cloudflare_research as cfr
import time

def test_target_sites():
    # Replace with your actual target sites
    target_sites = [
        "https://your-target-site-1.com",
        "https://your-target-site-2.com",
        # Add more sites as needed
    ]

    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=5,
        requests_per_second=2.0,  # Be respectful
        timeout=30.0
    )

    with cfr.create_scraper(config) as scraper:
        for site in target_sites:
            print(f"\nTesting: {site}")
            try:
                start_time = time.time()
                response = scraper.get(site)
                duration = time.time() - start_time

                # Check for Cloudflare
                cf_ray = response.headers.get('cf-ray', 'Not detected')
                cf_cache = response.headers.get('cf-cache-status', 'Not detected')
                server = response.headers.get('server', 'Unknown')

                print(f"  Status: {response.status_code}")
                print(f"  Duration: {duration:.2f}s")
                print(f"  CF-RAY: {cf_ray}")
                print(f"  CF-Cache: {cf_cache}")
                print(f"  Server: {server}")
                print(f"  Content: {len(response.text)} chars")

                if cf_ray != 'Not detected':
                    print("  ✅ CLOUDFLARE BYPASSED!")
                elif 'cloudflare' in server.lower():
                    print("  ✅ Cloudflare detected in server header")
                else:
                    print("  ℹ️ No Cloudflare protection detected")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            # Be respectful - add delay between requests
            time.sleep(2)

if __name__ == "__main__":
    test_target_sites()
EOF

# Edit the file to add your target sites
nano test_my_sites.py

# Run the test
python test_my_sites.py
```

## Step 8: Production Usage

### Basic Usage Example
```bash
# Create production usage example
cat > production_example.py << 'EOF'
#!/usr/bin/env python3
import cloudflare_research as cfr

def scrape_protected_site():
    """Example of using CloudflareScraper in production"""

    # Configure for production use
    config = cfr.CloudflareBypassConfig(
        max_concurrent_requests=10,
        requests_per_second=5.0,
        timeout=30.0,
        solve_javascript_challenges=True,
        enable_tls_fingerprinting=True
    )

    # Use context manager for automatic cleanup
    with cfr.create_scraper(config) as scraper:
        try:
            # Replace with your target URL
            url = "https://your-protected-site.com"

            # Make request
            response = scraper.get(url)

            # Check if successful
            if response.ok:
                print(f"✅ Success: {response.status_code}")

                # Check if Cloudflare was bypassed
                if 'cf-ray' in response.headers:
                    print(f"🛡️ Cloudflare bypassed: {response.headers['cf-ray']}")

                # Process the content
                print(f"📄 Content length: {len(response.text)}")

                # Example: Save to file
                with open('scraped_content.html', 'w') as f:
                    f.write(response.text)

                return response.text

            else:
                print(f"❌ Failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"💥 Error: {e}")
            return None

if __name__ == "__main__":
    content = scrape_protected_site()
    if content:
        print("✅ Scraping completed successfully!")
EOF
```

### API Server Setup (Optional)
```bash
# Install Flask for API server
pip install flask

# Create API server
cat > api_server.py << 'EOF'
#!/usr/bin/env python3
from flask import Flask, request, jsonify
import cloudflare_research as cfr
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize scraper
scraper = cfr.create_scraper()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "CloudflareScraper"})

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "URL required"}), 400

        response = scraper.get(url)

        result = {
            "success": True,
            "status_code": response.status_code,
            "url": response.url,
            "content": response.text,
            "cloudflare_detected": 'cf-ray' in response.headers,
            "cf_ray": response.headers.get('cf-ray'),
            "headers": dict(response.headers)
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF

# Run API server
python api_server.py
```

## Step 9: System Service Setup (Optional)

### Create Systemd Service
```bash
# Create service file
sudo tee /etc/systemd/system/cloudflare-scraper.service > /dev/null << 'EOF'
[Unit]
Description=CloudflareScraper API Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username
Environment=PATH=/home/your-username/cloudflare_env/bin
ExecStart=/home/your-username/cloudflare_env/bin/python api_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Replace 'your-username' with your actual username
sudo sed -i "s/your-username/$(whoami)/g" /etc/systemd/system/cloudflare-scraper.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-scraper
sudo systemctl start cloudflare-scraper

# Check status
sudo systemctl status cloudflare-scraper
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Build Errors
```bash
# If you get compilation errors, install additional packages
sudo apt install -y python3-distutils python3-lib2to3

# For older systems, you might need:
sudo apt install -y python3.11-dev python3.11-venv
```

#### 2. Permission Errors
```bash
# Make sure you own the files
sudo chown -R $(whoami):$(whoami) /home/$(whoami)/cloudflare_research

# Make scripts executable
chmod +x *.py
```

#### 3. Import Errors
```bash
# Reinstall in virtual environment
source cloudflare_env/bin/activate
pip uninstall cloudflare-research
pip install -e .
```

#### 4. Network Issues
```bash
# Test network connectivity
curl -I https://httpbin.org/get
curl -I https://discord.com

# Check if firewall is blocking
sudo ufw status
```

#### 5. Memory Issues
```bash
# Check available memory
free -h

# If low memory, create swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Performance Optimization

### System Tuning
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize network settings
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Monitoring Setup
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Monitor CloudflareScraper performance
htop  # Check CPU/memory usage
nethogs  # Check network usage
```

## Testing Checklist

- [ ] ✅ System packages installed
- [ ] ✅ Virtual environment created and activated
- [ ] ✅ Dependencies installed successfully
- [ ] ✅ CloudflareScraper installed
- [ ] ✅ Basic import test passes
- [ ] ✅ HTTP requests working
- [ ] ✅ Cloudflare detection working
- [ ] ✅ Target sites accessible
- [ ] ✅ Performance acceptable

## Expected Results

**Successful installation should show:**
```
Testing CloudflareScraper on Debian 12...
Server IP: xxx.xxx.xxx.xxx
Discord Status: 200
CF-RAY: 980e6a16b808a932-SYD
Content Length: 157936
🎉 SUCCESS: Cloudflare bypass working!
```

## Usage in Your Applications

Once installed, use exactly like cloudscraper:

```python
# Replace this:
# import cloudscraper
# scraper = cloudscraper.create_scraper()

# With this:
import cloudflare_research as cfr
scraper = cfr.create_scraper()

# Everything else stays the same!
response = scraper.get("https://protected-site.com")
print(response.text)
```

Your CloudflareScraper is now ready for production use on Debian 12! 🚀

For support or issues, check the troubleshooting section above or refer to the main documentation.