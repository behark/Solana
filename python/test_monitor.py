#!/usr/bin/env python3
"""
Test script for the multi-chain monitoring system
Tests basic functionality without making actual blockchain calls
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scoring.token_scorer import TokenScorer
from alerts.telegram_dispatcher import TelegramDispatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_scoring_system():
    """Test the token scoring system"""
    print("\n=== Testing Token Scoring System ===")

    scorer = TokenScorer()

    # Test token data samples
    test_tokens = [
        {
            'name': 'Test Token 1',
            'symbol': 'TEST1',
            'address': '0x1234567890abcdef',
            'chain': 'ethereum',
            'dex': 'Uniswap V3',
            'liquidity_usd': 250000,
            'volume_24h': 500000,
            'holders': {'total': 500, 'top_10_percentage': 35},
            'contract_verified': True,
            'ownership_renounced': True,
            'social_links': {
                'twitter': 'https://twitter.com/test',
                'twitter_followers': 5000,
                'telegram': 'https://t.me/test',
                'telegram_members': 2000,
                'website': 'https://test.com'
            }
        },
        {
            'name': 'Suspicious Token',
            'symbol': 'SCAM',
            'address': '0xbad1234567890abc',
            'chain': 'bnb',
            'dex': 'PancakeSwap V2',
            'liquidity_usd': 5000,
            'volume_24h': 1000,
            'buy_tax': 25,
            'sell_tax': 30,
            'honeypot_check': {'is_honeypot': True}
        },
        {
            'name': 'Medium Quality Token',
            'symbol': 'MED',
            'address': '0xmed1234567890abc',
            'chain': 'base',
            'dex': 'Aerodrome',
            'liquidity_usd': 50000,
            'volume_24h': 25000,
            'holders': {'total': 200, 'top_10_percentage': 45},
            'contract_verified': False,
            'social_links': {
                'twitter': 'https://twitter.com/med',
                'twitter_followers': 500
            }
        }
    ]

    for token in test_tokens:
        score, analysis = await scorer.score_token(token)
        print(f"\nToken: {token['name']} ({token['symbol']})")
        print(f"Chain: {token['chain']}")
        print(f"Score: {score:.2f}/100")
        print(f"Confidence: {analysis['confidence_level']}")

        if analysis.get('warnings'):
            print("Warnings:")
            for warning in analysis['warnings']:
                print(f"  - {warning}")

        if analysis.get('positives'):
            print("Positives:")
            for positive in analysis['positives']:
                print(f"  + {positive}")

    await scorer.cleanup()


async def test_telegram_alerts():
    """Test Telegram alert formatting (without sending)"""
    print("\n=== Testing Telegram Alert Formatting ===")

    dispatcher = TelegramDispatcher()

    # Test token for alert
    test_token = {
        'name': 'Example Token',
        'symbol': 'EXAMPLE',
        'address': '0x1234567890abcdef1234567890abcdef12345678',
        'chain': 'ethereum',
        'dex': 'Uniswap V3',
        'score': 85,
        'liquidity_usd': 500000,
        'volume_24h': 1000000,
        'holders': {'total': 1000, 'top_10_percentage': 30},
        'contract_verified': True,
        'ownership_renounced': True,
        'analysis': {
            'confidence_level': 'High',
            'scores': {
                'liquidity': 90,
                'volume': 85,
                'holder_distribution': 80,
                'contract_verification': 100,
                'social_presence': 75
            },
            'warnings': ['High initial volume spike'],
            'positives': ['Verified contract', 'Good holder distribution', 'Strong liquidity']
        },
        'explorer_link': 'https://etherscan.io/token/0x1234',
        'dexscreener_link': 'https://dexscreener.com/ethereum/0x1234',
        'social_links': {
            'website': 'https://example.com',
            'twitter': 'https://twitter.com/example',
            'telegram': 'https://t.me/example'
        }
    }

    # Format message (without sending)
    message = dispatcher._format_alert_message(test_token, "🔥", "HIGH CONFIDENCE ALERT")
    print("\nFormatted Telegram Message:")
    print("-" * 50)
    print(message.replace('<b>', '**').replace('</b>', '**')
          .replace('<i>', '_').replace('</i>', '_')
          .replace('<code>', '`').replace('</code>', '`')
          .replace('<a href=', '[').replace('</a>', ']')
          .replace('">', '](').replace('"', ')'))
    print("-" * 50)


async def test_chain_connectivity():
    """Test basic chain connectivity (simplified)"""
    print("\n=== Testing Chain Connectivity ===")

    chains = {
        'Solana': os.getenv('SOLANA_RPC_HTTP'),
        'Ethereum': os.getenv('ETHEREUM_RPC_HTTP'),
        'BNB Chain': os.getenv('BNB_RPC_HTTP'),
        'Base': os.getenv('BASE_RPC_HTTP')
    }

    for chain, rpc_url in chains.items():
        if rpc_url:
            print(f"✓ {chain}: RPC configured")
        else:
            print(f"✗ {chain}: No RPC configured")


def test_configuration():
    """Test configuration loading"""
    print("\n=== Testing Configuration ===")

    from dotenv import load_dotenv
    load_dotenv()

    config_items = [
        ('TELEGRAM_BOT_TOKEN', 'Telegram Bot Token'),
        ('TELEGRAM_CHAT_ID', 'Telegram Chat ID'),
        ('DAILY_ALERT_TARGET', 'Daily Alert Target'),
        ('HIGH_CONFIDENCE_THRESHOLD', 'High Confidence Threshold'),
        ('MIN_LIQUIDITY_USD', 'Minimum Liquidity USD')
    ]

    all_configured = True
    for env_var, description in config_items:
        value = os.getenv(env_var)
        if value:
            if 'TOKEN' in env_var or 'KEY' in env_var:
                display_value = value[:10] + '...' if len(value) > 10 else value
            else:
                display_value = value
            print(f"✓ {description}: {display_value}")
        else:
            print(f"✗ {description}: Not configured")
            all_configured = False

    return all_configured


async def main():
    """Run all tests"""
    print("""
    ╔════════════════════════════════════════════════════╗
    ║     Multi-Chain Monitoring System Test Suite      ║
    ║           Educational Purposes Only                ║
    ╚════════════════════════════════════════════════════╝
    """)

    # Test configuration
    config_ok = test_configuration()

    # Test chain connectivity
    await test_chain_connectivity()

    # Test scoring system
    await test_scoring_system()

    # Test alert formatting
    await test_telegram_alerts()

    print("\n=== Test Summary ===")
    if config_ok:
        print("✓ Configuration: OK")
    else:
        print("⚠ Configuration: Some items missing (check .env file)")

    print("✓ Scoring System: OK")
    print("✓ Alert Formatting: OK")
    print("\nTests completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest error: {e}")
        import traceback
        traceback.print_exc()