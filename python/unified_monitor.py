#!/usr/bin/env python3
"""
Unified Multi-Chain Memecoin Monitoring System

This script combines real-time token discovery with API-based data enrichment to provide a comprehensive monitoring solution.

"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json
import time
import signal
from collections import defaultdict
from dotenv import load_dotenv
import aiohttp

# Add src to path


# Import chain monitors
from chains.solana_monitor import SolanaMonitor
from chains.ethereum_monitor import EthereumMonitor
from chains.bnb_monitor import BNBMonitor
from chains.base_monitor import BaseMonitor
from scoring.token_scorer import TokenScorer
from alerts.telegram_dispatcher import TelegramDispatcher

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Endpoints
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"

@dataclass
class MonitoringStats:
    """Statistics for monitoring performance"""
    tokens_discovered: int = 0
    high_confidence_alerts: int = 0
    medium_confidence_alerts: int = 0
    low_confidence_alerts: int = 0
    alerts_sent_today: int = 0
    last_alert_reset: datetime = field(default_factory=datetime.now)
    chain_stats: Dict[str, int] = field(default_factory=dict)
    errors: int = 0

    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.alerts_sent_today = 0
        self.last_alert_reset = datetime.now()
        logger.info("Daily statistics reset")


class UnifiedMonitor:
    """Main orchestrator for multi-chain token monitoring"""

    def __init__(self):
        """Initialize the multi-chain monitoring system"""
        self.running = False
        self.stats = MonitoringStats()

        # Configuration
        self.daily_alert_target = int(os.getenv('DAILY_ALERT_TARGET', 500))
        self.high_confidence_threshold = int(os.getenv('HIGH_CONFIDENCE_THRESHOLD', 75))
        self.medium_confidence_threshold = int(os.getenv('MEDIUM_CONFIDENCE_THRESHOLD', 60))
        self.minimum_alert_score = int(os.getenv('MINIMUM_ALERT_SCORE', 60))

        # Chain enabled flags
        self.chain_enabled = {
            'solana': os.getenv('SOLANA_ENABLED', 'true').lower() == 'true',
            'ethereum': os.getenv('ETHEREUM_ENABLED', 'false').lower() == 'true',
            'bnb': os.getenv('BNB_ENABLED', 'true').lower() == 'true',
            'base': os.getenv('BASE_ENABLED', 'true').lower() == 'true',
        }

        # Alert distribution percentages
        self.chain_alert_distribution = {
            'solana': int(os.getenv('SOLANA_ALERT_PERCENTAGE', 50)),
            'ethereum': int(os.getenv('ETHEREUM_ALERT_PERCENTAGE', 0)),
            'bnb': int(os.getenv('BNB_ALERT_PERCENTAGE', 45)),
            'base': int(os.getenv('BASE_ALERT_PERCENTAGE', 5))
        }

        # Track sent alerts to avoid duplicates
        self.sent_alerts: Set[str] = set()
        self.alert_queue: List[Dict] = []

        # Initialize components
        self.scorer = TokenScorer()
        self.telegram = TelegramDispatcher()
        self.session: Optional[aiohttp.ClientSession] = None

        # Initialize only enabled chain monitors
        self.monitors = {}
        if self.chain_enabled['solana']:
            self.monitors['solana'] = SolanaMonitor()
        if self.chain_enabled['ethereum']:
            self.monitors['ethereum'] = EthereumMonitor()
        if self.chain_enabled['bnb']:
            self.monitors['bnb'] = BNBMonitor()
        if self.chain_enabled['base']:
            self.monitors['base'] = BaseMonitor()

        # Chain-specific alert quotas
        self.chain_quotas = self._calculate_chain_quotas()
        self.chain_alerts_sent = defaultdict(int)

        logger.info(f"Unified Monitor initialized with daily target: {self.daily_alert_target} alerts")
        logger.info(f"Enabled chains: {[chain for chain, enabled in self.chain_enabled.items() if enabled]}")
        logger.info(f"Chain distribution: {self.chain_alert_distribution}")
        logger.info(f"Minimum alert score threshold: {self.minimum_alert_score}")

    def _calculate_chain_quotas(self) -> Dict[str, int]:
        """Calculate daily alert quotas per chain"""
        quotas = {}
        for chain, percentage in self.chain_alert_distribution.items():
            quotas[chain] = int(self.daily_alert_target * percentage / 100)
        return quotas

    def _get_alert_key(self, token_data: Dict) -> str:
        """Generate unique key for alert deduplication"""
        return f"{token_data.get('chain')}_{token_data.get('address', '')}_{token_data.get('pair_address', '')}"

    async def process_token_discovery(self, token_data: Dict, chain: str):
        """Process a newly discovered token"""
        try:
            # Add chain info
            token_data['chain'] = chain
            token_data['discovered_at'] = datetime.now().isoformat()

            # Generate unique key
            alert_key = self._get_alert_key(token_data)

            # Check if already sent
            if alert_key in self.sent_alerts:
                return

            # Enrich token data with market info
            enriched_data = await self.enrich_token_data(token_data)

            # Debug: Log enrichment results
            logger.info(f"Enriched data - Liquidity: ${enriched_data.get('liquidity_usd', 0):,.0f}, "
                        f"Volume: ${enriched_data.get('volume_24h', 0):,.0f}, "
                        f"Holders: {enriched_data.get('holders', 0)}, "
                        f"MarketCap: ${enriched_data.get('market_cap', 0):,.0f}")

            # Score the token
            score, analysis = await self.scorer.score_token(enriched_data)
            enriched_data['score'] = score
            enriched_data['analysis'] = analysis

            # Update statistics
            self.stats.tokens_discovered += 1
            self.stats.chain_stats[chain] = self.stats.chain_stats.get(chain, 0) + 1

            # Determine alert priority
            if score >= self.high_confidence_threshold:
                priority = 'high'
                self.stats.high_confidence_alerts += 1
            elif score >= self.medium_confidence_threshold:
                priority = 'medium'
                self.stats.medium_confidence_alerts += 1
            else:
                priority = 'low'
                self.stats.low_confidence_alerts += 1

            # Add to queue if meets threshold
            if score >= self.minimum_alert_score:
                self.alert_queue.append({
                    'token_data': enriched_data,
                    'priority': priority,
                    'timestamp': datetime.now()
                })

            # Write to file for Rust bot
            with open('token_queue.json', 'a') as f:
                json.dump(enriched_data, f)
                f.write('\n')

            logger.info(f"Token discovered on {chain}: {enriched_data.get('symbol', 'Unknown')} "
                       f"(Score: {score}, Priority: {priority})")

        except Exception as e:
            logger.error(f"Error processing token discovery: {e}")
            self.stats.errors += 1

    async def enrich_token_data(self, token_data: Dict) -> Dict:
        """Enrich token data with information from Dexscreener"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Get pair/pool address (different field names for V2 vs V3)
            pair_address = token_data.get('pair_address') or token_data.get('pool_address') or token_data.get('mint_address')
            if not pair_address:
                logger.debug(f"No pair/pool address found for token: {token_data.get('symbol', 'Unknown')}")
                return token_data

            url = f"{DEXSCREENER_API}/pairs/{token_data['chain']}/{pair_address}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('pairs'):
                        pair_data = data['pairs'][0]
                        token_data['liquidity_usd'] = float(pair_data.get('liquidity', {}).get('usd', 0))
                        token_data['volume_24h'] = float(pair_data.get('volume', {}).get('h24', 0))
                        token_data['price_usd'] = float(pair_data.get('priceUsd', 0))
                        token_data['price_change_24h'] = float(pair_data.get('priceChange', {}).get('h24', 0))
                        token_data['market_cap'] = float(pair_data.get('marketCap', 0))
                        token_data['holders'] = int(pair_data.get('holders', 0))
                        token_data['dex'] = pair_data.get('dexId', 'unknown')
        except Exception as e:
            logger.error(f"Error enriching token data: {e}")
        
        return token_data

    async def dispatch_alerts(self):
        """Dispatch alerts based on quotas and priorities"""
        while self.running:
            try:
                # Reset daily stats if needed
                if datetime.now().date() > self.stats.last_alert_reset.date():
                    self.stats.reset_daily_stats()
                    self.chain_alerts_sent.clear()
                    self.sent_alerts.clear()

                # Check if we have alerts to send
                if not self.alert_queue:
                    await asyncio.sleep(5)
                    continue

                # Sort queue by priority and score
                self.alert_queue.sort(
                    key=lambda x: (
                        0 if x['priority'] == 'high' else 1 if x['priority'] == 'medium' else 2,
                        -x['token_data']['score']
                    )
                )

                # Process alerts respecting quotas
                alerts_to_send = []
                for alert in self.alert_queue[:]:
                    chain = alert['token_data']['chain']

                    # Check chain quota
                    if self.chain_alerts_sent[chain] >= self.chain_quotas[chain]:
                        continue

                    # Check daily limit
                    if self.stats.alerts_sent_today >= self.daily_alert_target:
                        break

                    alerts_to_send.append(alert)
                    self.alert_queue.remove(alert)

                # Send alerts
                for alert in alerts_to_send:
                    try:
                        await self.telegram.send_alert(
                            alert['token_data'],
                            alert['priority']
                        )

                        # Update counters
                        self.stats.alerts_sent_today += 1
                        self.chain_alerts_sent[alert['token_data']['chain']] += 1
                        self.sent_alerts.add(self._get_alert_key(alert['token_data']))

                        # Rate limiting
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error sending alert: {e}")

                # Clean old alerts from queue (older than 1 hour)
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.alert_queue = [
                    alert for alert in self.alert_queue
                    if alert['timestamp'] > cutoff_time
                ]

                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in alert dispatcher: {e}")
                await asyncio.sleep(5)

    async def monitor_chain(self, chain_name: str, monitor):
        """Monitor a specific blockchain"""
        logger.info(f"Starting {chain_name} monitor")

        while self.running:
            try:
                # Get new tokens from monitor
                async for token_data in monitor.monitor():
                    if not self.running:
                        break

                    await self.process_token_discovery(token_data, chain_name)

            except Exception as e:
                logger.error(f"Error in {chain_name} monitor: {e}")
                self.stats.errors += 1
                await asyncio.sleep(30)  # Wait before retrying

    async def print_statistics(self):
        """Periodically print monitoring statistics"""
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes

            logger.info("=== Monitoring Statistics ===")
            logger.info(f"Tokens Discovered: {self.stats.tokens_discovered}")
            logger.info(f"Alerts Sent Today: {self.stats.alerts_sent_today}/{self.daily_alert_target}")
            logger.info(f"High Confidence: {self.stats.high_confidence_alerts}")
            logger.info(f"Medium Confidence: {self.stats.medium_confidence_alerts}")
            logger.info(f"Low Confidence: {self.stats.low_confidence_alerts}")
            logger.info(f"Errors: {self.stats.errors}")
            logger.info("Chain Distribution:")
            for chain, count in self.stats.chain_stats.items():
                quota = self.chain_quotas[chain]
                sent = self.chain_alerts_sent[chain]
                logger.info(f"  {chain}: {count} discovered, {sent}/{quota} alerts sent")
            logger.info(f"Queue Size: {len(self.alert_queue)}")
            logger.info("===========================")

    async def run(self):
        """Run the multi-chain monitoring system"""
        self.running = True
        logger.info("Starting Unified Monitoring System")

        try:
            # Initialize Telegram bot and aiohttp session
            await self.telegram.initialize()
            self.session = aiohttp.ClientSession()

            # Send startup notification
            startup_config = {
                'chain_enabled': self.chain_enabled,
                'chain_distribution': self.chain_alert_distribution,
                'daily_target': self.daily_alert_target,
                'min_score': self.minimum_alert_score
            }
            await self.telegram.send_startup_notification(startup_config)

            # Create monitoring tasks
            tasks = []

            # Add chain monitoring tasks
            for chain_name, monitor in self.monitors.items():
                tasks.append(asyncio.create_task(
                    self.monitor_chain(chain_name, monitor)
                ))

            # Add alert dispatcher
            tasks.append(asyncio.create_task(self.dispatch_alerts()))

            # Add statistics printer
            tasks.append(asyncio.create_task(self.print_statistics()))

            # Run all tasks
            await asyncio.gather(*tasks)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in monitoring system: {e}")
        finally:
            self.running = False
            if self.session:
                await self.session.close()
            logger.info("Monitoring system stopped")

    def stop(self):
        """Stop the monitoring system"""
        logger.info("Stopping monitoring system...")
        self.running = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if monitor:
        monitor.stop()
    sys.exit(0)


# Global monitor instance
monitor: Optional[UnifiedMonitor] = None


async def main():
    """Main entry point"""
    global monitor

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run monitor
    monitor = UnifiedMonitor()
    await monitor.run()


if __name__ == "__main__":
    # Run the monitoring system
    asyncio.run(main())
