#!/bin/bash
# Multi-Chain Memecoin Monitor Service Script
# This script runs the educational monitoring system

# Set working directory
cd /home/behar/Desktop/New\ Folder\ \(12\)/solana-copy-sniper-trading-bot

# Log startup
echo "$(date): Starting Multi-Chain Memecoin Monitor..." >> monitor.log

# Run the Python script
/usr/bin/python3 python/unified_monitor.py 2>&1 | tee -a monitor.log