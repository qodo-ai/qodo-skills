#!/bin/bash
# Wrapper script that detects available Python interpreter and runs the fetch script
# This ensures compatibility across systems that have either python3 or python

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/fetch-qodo-rules.py"

# Detect available Python interpreter
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    # Check if it's Python 3
    PYTHON_VERSION=$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null || echo "2")
    if [ "$PYTHON_VERSION" = "3" ]; then
        PYTHON_CMD="python"
    else
        echo "⚠️  Python 3 is required but not found. Please install Python 3:"
        echo "   - macOS: brew install python3"
        echo "   - Ubuntu/Debian: apt-get install python3"
        echo "   - Windows: Download from https://www.python.org/downloads/"
        exit 0
    fi
else
    echo "⚠️  Python is not installed. Please install Python 3:"
    echo "   - macOS: brew install python3"
    echo "   - Ubuntu/Debian: apt-get install python3"
    echo "   - Windows: Download from https://www.python.org/downloads/"
    exit 0
fi

# Execute the Python script
exec "$PYTHON_CMD" "$PYTHON_SCRIPT" "$@"
