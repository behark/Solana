#!/bin/bash
# Installation script for Multi-Chain Memecoin Monitor Service
# Run this script with sudo to install the systemd service

echo "==================================================================="
echo "        Multi-Chain Memecoin Monitor Service Installer"
echo "==================================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo:"
    echo "sudo ./install_service.sh"
    exit 1
fi

echo "📦 Installing systemd service..."

# Copy the service file
cp ../memecoin-monitor.service /etc/systemd/system/
echo "✅ Service file copied"

# Reload systemd
systemctl daemon-reload
echo "✅ Systemd reloaded"

# Enable the service for auto-start on boot
systemctl enable memecoin-monitor.service
echo "✅ Service enabled for auto-start on boot"

# Start the service
systemctl start memecoin-monitor.service
echo "✅ Service started"

# Check status
echo ""
echo "📊 Service Status:"
systemctl status memecoin-monitor.service --no-pager

echo ""
echo "==================================================================="
echo "✅ Installation Complete!"
echo ""
echo "Useful commands:"
echo "  • Check status:  sudo systemctl status memecoin-monitor"
echo "  • View logs:     sudo journalctl -u memecoin-monitor -f"
echo "  • Stop service:  sudo systemctl stop memecoin-monitor"
echo "  • Start service: sudo systemctl start memecoin-monitor"
echo "  • Restart:       sudo systemctl restart memecoin-monitor"
echo "  • Disable:       sudo systemctl disable memecoin-monitor"
echo ""
echo "The service will now:"
echo "  ✅ Run 24/7 in the background"
echo "  ✅ Auto-restart if it crashes"
echo "  ✅ Auto-start on system boot"
echo "  ✅ Send alerts to your Telegram"
echo "==================================================================="