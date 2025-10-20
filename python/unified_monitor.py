#!/usr/bin/env python3
"""
Unified Multi-Chain Memecoin Monitoring System

This script combines real-time token discovery with API-based data enrichment
to provide a comprehensive monitoring solution.

** Refactored Version **
- Uses asyncio.PriorityQueue for efficient alert handling.
- Uses asyncio.to_thread for non-blocking file I/O.
- Persists 'sent_alerts' to disk to prevent duplicates on restart.
- Implements smarter Dexscreener pair logic.
- Fixes signal handling for graceful shutdown.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import json
import time
import signal
from collections import defaultdict
from dotenv import load_dotenv
import aiohttp

# Add src to path
# (Assuming your monitors are in a 'chains' directory)
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

        # --- FIXED: Use efficient PriorityQueue and persist sent_alerts ---
        self.sent_alerts_file = "sent_alerts.json"
        self.sent_alerts: Set[str] = self._load_sent_alerts()
        self.alert_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Holds alerts if quotas are full, to be re-queued later
        self.holding_queue: List[Tuple] = [] 
        # ---

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
        logger.info(f"Loaded {len(self.sent_alerts)} sent alerts from {self.sent_alerts_file}")

    # --- ADDED: Persistence for sent_alerts ---
    def _load_sent_alerts(self) -> Set[str]:
        """Load the set of sent alert keys from a file"""
        if not os.path.exists(self.sent_alerts_file):
            return set()
        try:
            with open(self.sent_alerts_file, 'r') as f:
                data = json.load(f)
                return set(data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load sent_alerts.json, starting fresh: {e}")
            return set()

    def _save_sent_alerts(self):
        """Save the set of sent alert keys to a file"""
        # This is blocking, but should be fast. 
        # For ultra-high performance, this could also be run in a thread.
        try:
            with open(self.sent_alerts_file, 'w') as f:
                json.dump(list(self.sent_alerts), f)
        except IOError as e:
            logger.error(f"Failed to save sent_alerts.json: {e}")
    # ---

    def _calculate_chain_quotas(self) -> Dict[str, int]:
        """Calculate daily alert quotas per chain"""
        quotas = {}
        for chain, percentage in self.chain_alert_distribution.items():
            quotas[chain] = int(self.daily_alert_target * percentage / 100)
        return quotas

    def _get_alert_key(self, token_data: Dict) -> str:
        """Generate unique key for alert deduplication"""
        # Use token address as primary key, fallback to pair address
        address = token_data.get('address', token_data.get('new_token'))
        if address:
            return f"{token_data.get('chain')}_{address}"
        
        # Fallback for systems that only provide pair
        pair_address = token_data.get('pair_address', token_data.get('pool_address'))
        return f"{token_data.get('chain')}_{pair_address}"

    async def process_token_discovery(self, token_data: Dict, chain: str):
        """Process a newly discovered token"""
        try:
            # Add chain info
            token_data['chain'] = chain
            if 'discovered_at' not in token_data:
                token_data['discovered_at'] = datetime.now().isoformat()

            # Generate unique key
            alert_key = self._get_alert_key(token_data)

            # Check if already sent
            if alert_key in self.sent_alerts:
                return

            # Enrich token data with market info
            enriched_data = await self.enrich_token_data(token_data)

            # Debug: Log enrichment results
            logger.debug(f"Enriched data - Liquidity: ${enriched_data.get('liquidity_usd', 0):,.0f}, "
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

            # --- FIXED: Use PriorityQueue ---
            # Add to queue if meets threshold
            if score >= self.minimum_alert_score:
                priority_num = 0 if priority == 'high' else 1 if priority == 'medium' else 2
                
                # We use -score so a higher score has a higher priority (lower number)
                # We add datetime for tie-breaking
                alert_tuple = (
                    priority_num,
                    -score,
                    datetime.now(),
                    {'token_data': enriched_data, 'priority': priority}
                )
                await self.alert_queue.put(alert_tuple)

            # --- FIXED: Non-blocking file I/O ---
            # Write to file for Rust bot
            # This uses asyncio.to_thread to run the blocking file I/O
            # in a separate thread, not blocking the main async loop.
            # Requires Python 3.9+
            def write_data_to_file():
                try:
                    with open('token_queue.json', 'a') as f:
                        json.dump(enriched_data, f)
                        f.write('\n')
                except Exception as e:
                    logger.error(f"Failed to write to token_queue.json: {e}")

            await asyncio.to_thread(write_data_to_file)

            logger.info(f"Token discovered on {chain}: {enriched_data.get('symbol', 'Unknown')} "
                        f"(Score: {score}, Priority: {priority})")

        except Exception as e:
            logger.error(f"Error processing token discovery: {e}", exc_info=True)
            self.stats.errors += 1

    async def enrich_token_data(self, token_data: Dict) -> Dict:
        """Enrich token data with information from Dexscreener"""
        try:
            # --- FIXED: Removed redundant session check ---
            # self.session is now reliably created in run()
            
            # Get pair/pool address
            pair_address = token_data.get('pair_address') or token_data.get('pool_address')
            
            # Solana often uses the token mint address as the "pair"
            if not pair_address and token_data['chain'] == 'solana':
                 pair_address = token_data.get('address') # 'address' is the mint

            if not pair_address:
                logger.debug(f"No pair/pool address found for token: {token_data.get('symbol', 'Unknown')}")
                return token_data

            chain_map = {"bnb": "bsc", "solana": "solana", "ethereum": "ethereum", "base": "base"}
            ds_chain = chain_map.get(token_data['chain'].lower(), token_data['chain'])
            url = f"{DEXSCREENER_API}/pairs/{ds_chain}/{pair_address}"
            async with self.session.get(url) as response:
                
                # --- ADDED: Rate limit check ---
                if response.status == 429:
                    logger.warning(f"Dexscreener rate limit hit. Skipping enrichment for {pair_address}")
                    return token_data
                
                if response.status == 200:
                    data = await response.json()
                    
                    # --- FIXED: Smarter pair selection ---
                    if data.get('pairs'):
                        best_pair = None
                        target_base_token = token_data.get('base_token', '').lower()

                        if target_base_token:
                            for pair in data['pairs']:
                                base_addr = pair.get('baseToken', {}).get('address', '').lower()
                                if base_addr == target_base_token:
                                    best_pair = pair
                                    break # Found the exact pair
                        
                        # Fallback: if no exact match, use the one with most liquidity
                        if not best_pair:
                            best_pair = max(data['pairs'], key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))

                        pair_data = best_pair
                        # ---
                        
                        token_data['liquidity_usd'] = float(pair_data.get('liquidity', {}).get('usd', 0))
                        token_data['volume_24h'] = float(pair_data.get('volume', {}).get('h24', 0))
                        token_data['price_usd'] = float(pair_data.get('priceUsd', 0))
                        token_data['price_change_24h'] = float(pair_data.get('priceChange', {}).get('h24', 0))
                        token_data['market_cap'] = float(pair_data.get('marketCap', 0))
                        # Dexscreener holders data can be unreliable, use with caution
                        # token_data['holders'] = int(pair_data.get('holders', 0))
                        token_data['dex'] = pair_data.get('dexId', 'unknown')
                else:
                    logger.debug(f"Dexscreener API error {response.status} for {pair_address}")

        except Exception as e:
            logger.error(f"Error enriching token data: {e}", exc_info=True)
        
        return token_data

    # --- FIXED: Complete rewrite of dispatch_alerts ---
    async def dispatch_alerts(self):
        """Dispatch alerts based on quotas and priorities from the PriorityQueue"""
        while self.running:
            try:
                # Reset daily stats if needed
                if datetime.now().date() > self.stats.last_alert_reset.date():
                    self.stats.reset_daily_stats()
                    self.chain_alerts_sent.clear()
                    self.sent_alerts.clear() # Clear in-memory, file will be overwritten
                    self._save_sent_alerts()
                    
                    # --- ADDED: Re-queue held alerts ---
                    logger.info(f"Daily reset: Re-queuing {len(self.holding_queue)} held alerts.")
                    for alert_tuple in self.holding_queue:
                        await self.alert_queue.put(alert_tuple)
                    self.holding_queue.clear()
                    # ---

                try:
                    # Get highest priority item, wait max 5s if queue is empty
                    alert_tuple = await asyncio.wait_for(self.alert_queue.get(), timeout=5.0)
                    # alert_tuple is (priority_num, -score, timestamp, alert_dict)
                    alert = alert_tuple[3] 
                    chain = alert['token_data']['chain']
                    alert_key = self._get_alert_key(alert['token_data'])

                    # Double-check if sent (in case it was held over a reset)
                    if alert_key in self.sent_alerts:
                        self.alert_queue.task_done()
                        continue

                    # Check daily total quota
                    if self.stats.alerts_sent_today >= self.daily_alert_target:
                        logger.warning(f"Daily alert quota ({self.daily_alert_target}) hit. Holding alert.")
                        self.holding_queue.append(alert_tuple)
                        self.alert_queue.task_done()
                        continue 

                    # Check chain-specific quota
                    if self.chain_alerts_sent[chain] >= self.chain_quotas[chain]:
                        logger.warning(f"Chain quota ({self.chain_quotas[chain]}) hit for {chain}. Holding alert.")
                        self.holding_queue.append(alert_tuple)
                        self.alert_queue.task_done()
                        continue
                    
                    # --- Quotas passed, send the alert ---
                    try:
                        await self.telegram.send_alert(
                            alert['token_data'],
                            alert['priority']
                        )

                        # Update counters
                        self.stats.alerts_sent_today += 1
                        self.chain_alerts_sent[chain] += 1
                        self.sent_alerts.add(alert_key)
                        self._save_sent_alerts() # Save sent status to disk

                        # Rate limiting
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error sending alert: {e}. Holding alert to retry later.")
                        self.holding_queue.append(alert_tuple) # Put it back if send fails
                    
                    finally:
                        self.alert_queue.task_done() # Mark as processed

                except asyncio.TimeoutError:
                    # Queue was empty, just loop again
                    continue
                
                # --- REMOVED: Old queue cleanup logic ---

            except Exception as e:
                logger.error(f"Error in alert dispatcher: {e}", exc_info=True)
                await asyncio.sleep(5)
    # ---

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
                logger.error(f"Error in {chain_name} monitor: {e}", exc_info=True)
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
                quota = self.chain_quotas.get(chain, 0)
                sent = self.chain_alerts_sent.get(chain, 0)
                logger.info(f"  {chain}: {count} discovered, {sent}/{quota} alerts sent")
            
            # --- UPDATED: Statistics for new queues ---
            logger.info(f"Alert Queue Size: {self.alert_queue.qsize()}")
            logger.info(f"Holding Queue Size: {len(self.holding_queue)}")
            # ---
            
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
            logger.info("Received shutdown signal (Ctrl+C)")
        except Exception as e:
            logger.error(f"Fatal error in monitoring system: {e}", exc_info=True)
        finally:
            self.running = False # Tell all tasks to stop
            logger.info("Shutting down... waiting for tasks to finish.")
            
            # Give tasks a moment to stop gracefully
            await asyncio.sleep(2) 
            
            if self.session:
                await self.session.close()
                logger.info("Aiohttp session closed.")
            
            await self.telegram.shutdown() # Properly close telegram bot
            logger.info("Monitoring system stopped.")

    def stop(self):
        """Stop the monitoring system"""
        logger.info("Stopping monitoring system...")
        self.running = False

# Global monitor instance
monitor: Optional[UnifiedMonitor] = None


# --- FIXED: Graceful signal handling ---
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name}. Initiating graceful shutdown...")
    if monitor:
        monitor.stop()
    # DO NOT CALL sys.exit() here, let the main loop handle it
# ---

async def main():
    """Main entry point"""
    global monitor

    # Setup signal handlers
    # SIGINT (Ctrl+C) is handled by the KeyboardInterrupt exception in run()
    signal.signal(signal.SIGTERM, signal_handler) # Handle "kill" or "docker stop"

    # Create and run monitor
    monitor = UnifiedMonitor()
    await monitor.run()


if __name__ == "__main__":
    # Run the monitoring system
    asyncio.run(main())
