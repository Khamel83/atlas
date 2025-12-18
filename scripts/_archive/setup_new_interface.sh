#!/bin/bash
# Setup script to ensure the new OOS interface is ready to use

echo "🚀 Setting up new OOS interactive interface..."

# Make sure run.py is executable
chmod +x run.py
echo "✅ Made run.py executable"

# Test that Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi
echo "✅ Python 3 found"

# Test that the script runs
if python3 run.py --help > /dev/null 2>&1; then
    echo "✅ New interface is working"
else
    echo "❌ New interface test failed"
    exit 1
fi

# Check for 1Password CLI (optional)
if command -v op &> /dev/null; then
    echo "✅ 1Password CLI found"
else
    echo "⚠️  1Password CLI not found (optional for full functionality)"
fi

echo ""
echo "🎉 New OOS interface is ready!"
echo ""
echo "Usage:"
echo "  ./run.py              # Interactive mode (recommended)"
echo "  ./run.py --help       # Show help"
echo ""
echo "Try it now:"
echo "  mkdir /tmp/test-project && cd /tmp/test-project"
echo "  $PWD/run.py"
echo ""