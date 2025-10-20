#!/usr/bin/env python3
"""
Simple startup script for the multi-chain monitoring system
Educational purposes only - monitors blockchain activity
"""

import asyncio
import sys
import logging
from multichain_monitor import main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════╗
    ║     Multi-Chain Memecoin Monitoring System        ║
    ║           Educational Purposes Only                ║
    ╠════════════════════════════════════════════════════╣
    ║  Monitoring:                                       ║
    ║  • Solana (Raydium, Pump.fun)                    ║
    ║  • Ethereum (Uniswap V2/V3)                      ║
    ║  • BNB Chain (PancakeSwap)                       ║
    ║  • Base (Aerodrome, Uniswap)                     ║
    ╠════════════════════════════════════════════════════╣
    ║  Target: ~500 high-confidence alerts daily        ║
    ║  Scoring: 0-100 comprehensive evaluation          ║
    ╚════════════════════════════════════════════════════╝

    Starting monitoring system...
    Press Ctrl+C to stop
    """)

    try:
        # Run the main monitoring loop
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMonitoring system stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)