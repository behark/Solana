#!/bin/bash

# Exit on error
set -e

# Change to script directory
cd "$(dirname "$0")" || {
    echo "Error: Failed to change directory" >&2
    exit 1
}

# Check if virtual environment exists and is executable
if [ ! -f "venv/bin/python" ]; then
    echo "Error: Virtual environment not found at venv/bin/python" >&2
    echo "Please create a virtual environment first: python3 -m venv venv" >&2
    exit 1
fi

if [ ! -x "venv/bin/python" ]; then
    echo "Error: venv/bin/python is not executable" >&2
    exit 1
fi

# Check if monitor script exists
if [ ! -f "python/unified_monitor.py" ]; then
    echo "Error: Monitor script not found at python/unified_monitor.py" >&2
    exit 1
fi

# Execute the monitor script (using exec to replace the shell process)
exec "venv/bin/python" "python/unified_monitor.py"