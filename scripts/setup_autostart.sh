#!/bin/bash
# Setup auto-start on boot using crontab (no sudo required)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==================================================================="
echo "        Auto-Start Setup for Memecoin Monitor"
echo "==================================================================="
echo ""

# Create the startup script
cat > "$SCRIPT_DIR/start_on_boot.sh" << 'EOF'
#!/bin/bash
# Auto-start script for Multi-Chain Memecoin Monitor

# Wait for network to be ready
sleep 30

# Change to script directory
cd "/home/behar/Desktop/New Folder (12)/solana-copy-sniper-trading-bot"

# Check if already running
if pgrep -f "unified_monitor.py" > /dev/null; then
    echo "Monitor already running"
    exit 0
fi

# Start the monitor with auto-restart
nohup ./scripts/monitor_forever.sh > /dev/null 2>&1 &
echo "Monitor started on boot at $(date)" >> boot.log
EOF

chmod +x "$SCRIPT_DIR/start_on_boot.sh"
echo "✅ Created startup script"

# Add to crontab
CRON_CMD="@reboot $SCRIPT_DIR/start_on_boot.sh"

# Check if already in crontab
if crontab -l 2>/dev/null | grep -q "start_on_boot.sh"; then
    echo "⚠️  Auto-start already configured in crontab"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Added to crontab for auto-start on boot"
fi

echo ""
echo "==================================================================="
echo "✅ Auto-Start Setup Complete!"
echo ""
echo "The monitor will now:"
echo "  • Start automatically on system boot"
echo "  • Auto-restart if it crashes"
echo "  • Run 24/7 in the background"
echo ""
echo "To start the monitor now:"
echo "  ./monitor_forever.sh &"
echo ""
echo "To view your crontab:"
echo "  crontab -l"
echo ""
echo "To remove auto-start:"
echo "  crontab -e  (then remove the @reboot line)"
echo "==================================================================="