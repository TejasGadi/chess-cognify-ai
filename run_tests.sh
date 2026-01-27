#!/bin/bash
# Test script runner - ensures virtual environment is activated

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies if needed
echo "📦 Checking dependencies..."
pip install -q -r requirements.txt

# Run the test script
echo ""
echo "🧪 Running implementation tests..."
echo ""
python3 test_implementation.py

# Deactivate virtual environment
deactivate
