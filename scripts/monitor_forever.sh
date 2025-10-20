#!/bin/bash
# Auto-restart monitoring script
# This script ensures the monitor runs 24/7 and restarts on crashes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="monitor_forever.log"
PID_FILE="monitor.pid"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to cleanup on exit
cleanup() {
    log_message "Shutting down monitor..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill $PID 2>/dev/null
        rm "$PID_FILE"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

log_message "==================================="
log_message "Multi-Chain Monitor Forever Started"
log_message "==================================="

# Main loop - keeps the monitor running
while true; do
    log_message "Starting Multi-Chain Memecoin Monitor..."

    # Run the Python script in background
    python3 python/unified_monitor.py >> monitor.log 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"

    log_message "Monitor started with PID: $PID"

    # Wait for the process to finish
    wait $PID
    EXIT_CODE=$?

    log_message "Monitor stopped with exit code: $EXIT_CODE"

    # Clean up PID file
    rm -f "$PID_FILE"

    # Wait before restarting
    log_message "Restarting in 10 seconds..."
    sleep 10
done