#!/usr/bin/env python3
"""
Simple Telegram Alert Test
"""

import requests
import time
from datetime import datetime

# Telegram credentials
BOT_TOKEN = "7558858258:AAFSRDFIG4Fh15iAehE8bGIg-iWuBblR6SU"
CHAT_ID = "1507876704"

def send_telegram(message):
    """Send a message via Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("="*60)
    print("EDUCATIONAL SOLANA MONITOR - SIMPLIFIED VERSION")
    print("="*60)
    print("Sending startup message to Telegram...")

    # Send startup message
    startup_msg = (
        "🚀 **Educational Monitor Started!**\n\n"
        "✅ System is now active\n"
        "📚 This is for educational purposes only\n"
        "❌ No trading will be performed\n\n"
        f"🕐 Started at: {datetime.now().strftime('%H:%M:%S')}\n\n"
        "You will receive simulated alerts every 30 seconds.\n"
        "Press Ctrl+C to stop monitoring.\n\n"
        "⚠️ Remember: This is educational content only!"
    )

    if send_telegram(startup_msg):
        print("✅ Startup message sent successfully!")
    else:
        print("❌ Failed to send startup message")
        return

    print("\nMonitoring started. Sending alerts every 30 seconds...")
    print("Press Ctrl+C to stop\n")

    patterns = [
        ("🚀 New Token", "EduToken launched with 50 SOL liquidity"),
        ("📈 Price Movement", "Token ABC up 25% in last hour"),
        ("💚 Buy Activity", "Wallet xyz123... bought 10 SOL of Token XYZ"),
        ("📊 Volume Spike", "3x normal volume detected on Token DEF"),
        ("🎯 Pattern Alert", "Accumulation pattern detected on Token GHI")
    ]

    try:
        iteration = 0
        while True:
            iteration += 1

            # Select a pattern to simulate
            pattern_type, description = patterns[iteration % len(patterns)]

            alert_msg = (
                f"{pattern_type} **Alert #{iteration}** (Simulated)\n\n"
                f"📍 Details: {description}\n"
                f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "📚 **Educational Note:**\n"
                "• This is simulated data for learning\n"
                "• Real markets are unpredictable\n"
                "• Always verify information\n"
                "• Never invest more than you can afford to lose\n\n"
                "⚠️ Educational purposes only!"
            )

            if send_telegram(alert_msg):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent alert #{iteration}: {pattern_type}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to send alert #{iteration}")

            # Wait 30 seconds
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nShutting down...")

        shutdown_msg = (
            "📛 **Monitor Stopped**\n\n"
            f"Educational monitoring stopped at {datetime.now().strftime('%H:%M:%S')}\n"
            "Thank you for using the educational system!"
        )

        send_telegram(shutdown_msg)
        print("✅ Shutdown message sent")
        print("Goodbye!")

if __name__ == "__main__":
    main()