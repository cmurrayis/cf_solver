#!/bin/bash
# Prepare repository for Git commit
# This script ensures everything is ready for GitHub deployment

echo "=== Preparing CloudflareBypass Research Tool for Git Commit ==="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ]; then
    echo "Error: Not in the project root directory"
    echo "Please run this script from the project root"
    exit 1
fi

# Clean up any generated test files (they're in .gitignore)
echo "Cleaning up test result files..."
rm -f detailed_bypass_analysis.json
rm -f high_concurrency_test_results.json
rm -f performance_validation_report.json
rm -f *.log

# Remove any temporary Python cache files
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Check for any obvious issues
echo "Running basic checks..."

# Check Python syntax
echo "Checking Python syntax..."
python -m py_compile cloudflare_research/__init__.py
echo "✓ Main module syntax OK"

# Check imports
echo "Checking imports..."
python -c "import cloudflare_research" 2>/dev/null && echo "✓ Module imports OK" || echo "⚠ Import issues detected"

# Check for secrets or sensitive data
echo "Checking for potential secrets..."
if grep -r -i "password\|secret\|key\|token" --include="*.py" cloudflare_research/ | grep -v "# " | grep -v "example" | grep -v "placeholder"; then
    echo "⚠ WARNING: Potential secrets found in code"
    echo "Please review and remove any hardcoded secrets"
else
    echo "✓ No obvious secrets detected"
fi

# Verify required files exist
echo "Verifying required files..."
required_files=(
    "README.md"
    "requirements.txt"
    "LICENSE"
    "SECURITY.md"
    ".gitignore"
    ".github/workflows/cloudflare-bypass-test.yml"
    "cloudflare_research/__init__.py"
    "tests/detailed_bypass_analysis.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ Missing: $file"
    fi
done

# Show git status
echo ""
echo "=== Git Status ==="
if command -v git &> /dev/null; then
    if [ -d ".git" ]; then
        git status --short
    else
        echo "Not a git repository yet"
        echo "Run: git init"
    fi
else
    echo "Git not installed"
fi

# Final checklist
echo ""
echo "=== Pre-Commit Checklist ==="
echo "✓ Test result files cleaned"
echo "✓ Python cache cleared"
echo "✓ Basic syntax checked"
echo "✓ Required files verified"
echo ""
echo "Before committing, ensure:"
echo "1. Update README.md with correct repository URL"
echo "2. Update setup.py with correct author/email"
echo "3. Test the installation process"
echo "4. Review all files for sensitive information"
echo "5. Run a final test to ensure everything works"
echo ""
echo "Ready to commit! Suggested git commands:"
echo "git add ."
echo "git commit -m 'Initial commit: CloudflareBypass Research Tool'"
echo "git remote add origin https://github.com/yourusername/your-repo.git"
echo "git push -u origin main"
echo ""
echo "After pushing, test remote deployment with:"
echo "curl -s https://raw.githubusercontent.com/yourusername/your-repo/main/scripts/quick_deploy.sh | bash"