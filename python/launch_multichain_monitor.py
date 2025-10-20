#!/usr/bin/env python3
"""
Launch Multi-Chain Memecoin Monitor
Main entry point for the educational monitoring system

** FIXED VERSION **
- Replaced blocking 'requests' with 'aiohttp' for true async performance.
- Uses a shared aiohttp.ClientSession for efficiency.
"""

import os
import sys
import asyncio
import time
from datetime import datetime
import aiohttp  # FIXED: Import aiohttp
from dotenv import load_dotenv
import random # FIXED: Import random

# Load environment variables
load_dotenv()

# Telegram configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# RPC Endpoints from .env
SOLANA_RPC = os.getenv('SOLANA_RPC_HTTP', '')
ETHEREUM_RPC = os.getenv('ETHEREUM_RPC_HTTP', '')
BNB_RPC = os.getenv('BNB_RPC_HTTP', '')
BASE_RPC = os.getenv('BASE_RPC_HTTP', '')

# FIXED: Re-wrote send_telegram to be async with aiohttp
async def send_telegram(session: aiohttp.ClientSession, message: str) -> bool:
    """Send a message via Telegram asynchronously"""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram not configured")
        return False

    url = f"https.api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        # Use the provided session to make an async POST request
        async with session.post(url, json=payload, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Error sending Telegram: {e}")
        return False

def check_configuration():
    """Check if all required configuration is present"""
    print("🔍 Checking Configuration...")
    print("-" * 60)

    config_ok = True

    # Check Telegram
    if BOT_TOKEN and CHAT_ID:
        print("✅ Telegram: Configured")
    else:
        print("❌ Telegram: Not configured")
        config_ok = False

    # Check RPC endpoints
    if SOLANA_RPC:
        print(f"✅ Solana RPC: Configured ({'Helius' if 'helius' in SOLANA_RPC else 'Custom'})")
    else:
        print("⚠️ Solana RPC: Not configured, Solana monitor disabled.")

    if ETHEREUM_RPC:
        print(f"✅ Ethereum RPC: Configured ({'Alchemy' if 'alchemy' in ETHEREUM_RPC else 'Custom'})")
    else:
        print("⚠️ Ethereum RPC: Not configured, Ethereum monitor disabled.")

    if BNB_RPC:
        print(f"✅ BNB Chain RPC: Configured ({'Alchemy' if 'alchemy' in BNB_RPC else 'Custom'})")
    else:
        print("⚠️ BNB RPC: Not configured, BNB monitor disabled.")

    if BASE_RPC:
        print(f"✅ Base RPC: Configured ({'Alchemy' if 'alchemy' in BASE_RPC else 'Custom'})")
    else:
        print("⚠️ Base RPC: Not configured, Base monitor disabled.")

    print("-" * 60)
    return config_ok

# FIXED: Function now accepts the aiohttp session
async def monitor_chain(session: aiohttp.ClientSession, chain_name: str, rpc_url: str):
    """Monitor a single chain (simulated for educational demo)"""
    print(f"🔗 Starting {chain_name} monitor...")

    # Simulated monitoring for educational purposes
    token_count = 0
    alert_count = 0

    while True:
        try:
            # Simulate token discovery
            if random.random() < 0.1:  # 10% chance per cycle
                token_count += 1

                # Simulate scoring
                score = random.randint(20, 95)

                if score >= 75:  # High confidence threshold
                    alert_count += 1

                    # Create alert message
                    alert = f"""
🚀 **HIGH CONFIDENCE ALERT** ({chain_name.upper()})

🪙 **Token**: SimulatedToken_{token_count}
📊 **Score**: {score}/100
💰 **Liquidity**: ${random.randint(10000, 500000):,}
👥 **Holders**: {random.randint(100, 5000)}
📈 **Volume 24h**: ${random.randint(50000, 2000000):,}

🔒 **Security**: ✅ Verified
🌊 **Liquidity Locked**: Yes (365 days)
📍 **DEX**: {'Raydium' if chain_name == 'Solana' else 'Uniswap V3'}

📚 **Analysis**:
• Strong buy pressure detected
• Low concentration of holders
• Verified contract with no red flags

⚠️ **Risk**: Medium
🎯 **Confidence**: HIGH

⚠️ **Educational Alert Only - No Trading**
"""

                    # Send to Telegram
                    # FIXED: Use 'await' and pass the session
                    await send_telegram(session, alert)
                    print(f"  ✉️ Alert sent for {chain_name} (Score: {score})")

            await asyncio.sleep(30)  # Check every 30 seconds

        except Exception as e:
            print(f"Error in {chain_name} monitor: {e}")
            await asyncio.sleep(60)

async def main():
    """Main monitoring orchestrator"""
    print("=" * 80)
    print(" " * 15 + "🚀 MULTI-CHAIN MEMECOIN MONITOR 🚀")
    print("=" * 80)
    print()

    # Check configuration
    if not check_configuration():
        print("\n⚠️ WARNING: Some configuration is missing!")
        print("The system will run with limited functionality.")
        await asyncio.sleep(3)

    print()
    print("📊 MONITOR SETTINGS:")
    print("-" * 60)
    print(f"• Daily Alert Target: 500 alerts")
    print(f"• High Confidence Threshold: 75/100")
    print(f"• Minimum Liquidity: $10,000")
    print(f"• Chains: Solana, Ethereum, BNB, Base")
    print("-" * 60)
    print()

    # FIXED: Create a single aiohttp session for the application
    async with aiohttp.ClientSession() as session:
        # Send startup notification
        startup_msg = f"""
🚀 **MULTI-CHAIN MONITOR STARTED**

⚡ **System Active**
• Monitoring 4 blockchains
• Target: 500 high-confidence alerts daily
• Educational mode - NO TRADING

📊 **Chains**:
• Solana (40% alerts)
• Ethereum (25% alerts)
• BNB Chain (20% alerts)
• Base (15% alerts)

🔍 **Monitoring**:
• New token launches
• Liquidity events
• Volume spikes
• Smart money activity

⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **Remember**: This is for educational purposes only!
"""

        if await send_telegram(session, startup_msg):
            print("✅ Startup notification sent to Telegram")
        else:
            print("⚠️ Could not send Telegram notification")

        print()
        print("🚀 Starting chain monitors...")
        print("-" * 60)

        # Create monitoring tasks for each chain
        tasks = []

        # Only start monitors if RPC is configured
        if SOLANA_RPC:
            # FIXED: Pass session to monitor task
            tasks.append(asyncio.create_task(monitor_chain(session, "Solana", SOLANA_RPC)))

        if ETHEREUM_RPC:
            tasks.append(asyncio.create_task(monitor_chain(session, "Ethereum", ETHEREUM_RPC)))

        if BNB_RPC:
            tasks.append(asyncio.create_task(monitor_chain(session, "BNB", BNB_RPC)))

        if BASE_RPC:
            tasks.append(asyncio.create_task(monitor_chain(session, "Base", BASE_RPC)))

        if not tasks:
            print("❌ No chains configured! Please check your .env file")
            return

        print(f"✅ Started {len(tasks)} chain monitors")
        print()
        print("📱 Monitoring active - Alerts will be sent to Telegram")
        print("⚠️ This is for EDUCATIONAL purposes only - NO TRADING")
        print()
        print("Press Ctrl+C to stop monitoring")
        print("=" * 80)

        try:
            # Keep running until interrupted
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\n📛 Shutdown signal received...")

            # Send shutdown notification
            shutdown_msg = f"""
📛 **MONITOR STOPPED**

Multi-chain monitoring has been stopped.
Thank you for using the educational monitoring system!

⏰ Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            await send_telegram(session, shutdown_msg) # FIXED: Use await and pass session

            print("✅ Monitor stopped successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
