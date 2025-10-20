"""
Enhanced Telegram Alert Dispatcher
Sends formatted alerts with rich information to Telegram
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TelegramDispatcher:
    """Enhanced Telegram bot for sending alerts"""

    def __init__(self):
        """Initialize Telegram dispatcher"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = os.getenv('TELEGRAM_ALERTS_ENABLED', 'false').lower() == 'true'

        if not self.enabled:
            logger.warning("Telegram alerts are disabled")
        elif not self.bot_token or not self.chat_id:
            logger.error("Telegram bot token or chat ID not configured")
            self.enabled = False

        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        # Rate limiting
        self.last_message_time = datetime.now()
        self.min_interval = timedelta(seconds=1)  # Minimum 1 second between messages

        # Message queue
        self.message_queue = asyncio.Queue()
        self.queue_processor_task = None

        logger.info(f"Telegram dispatcher initialized (Enabled: {self.enabled})")

    async def initialize(self):
        """Initialize async resources"""
        if not self.enabled:
            return

        try:
            self.session = aiohttp.ClientSession()

            # Test bot connection
            await self._test_connection()

            # Start queue processor
            self.queue_processor_task = asyncio.create_task(self._process_queue())

            logger.info("Telegram dispatcher ready")

        except Exception as e:
            logger.error(f"Error initializing Telegram dispatcher: {e}")
            self.enabled = False

    async def cleanup(self):
        """Clean up resources"""
        if self.queue_processor_task:
            self.queue_processor_task.cancel()

        if self.session:
            await self.session.close()

    async def _test_connection(self):
        """Test bot connection"""
        try:
            async with self.session.get(f"{self.base_url}/getMe") as response:
                if response.status == 200:
                    data = await response.json()
                    bot_info = data.get('result', {})
                    logger.info(f"Connected to Telegram bot: @{bot_info.get('username')}")
                else:
                    raise Exception(f"Failed to connect to Telegram bot: {response.status}")

        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            raise

    async def send_startup_notification(self, config: dict):
        """Send startup notification with system status"""
        if not self.enabled:
            return

        try:
            from datetime import datetime

            # Build enabled chains list
            enabled_chains = []
            for chain, percentage in config.get('chain_distribution', {}).items():
                if config.get('chain_enabled', {}).get(chain, False):
                    enabled_chains.append(f"✅ {chain.capitalize()} Monitor: Active ({percentage}%)")

            chains_text = "\n".join(enabled_chains)

            # Build startup message
            message = (
                f"🚀 <b>Monitor Started</b>\n\n"
                f"{chains_text}\n\n"
                f"📊 Daily Target: {config.get('daily_target', 'N/A')} alerts\n"
                f"🎯 Min Score: {config.get('min_score', 'N/A')}/100\n"
                f"⚡ Status: <b>Scanning...</b>\n\n"
                f"Started at: {datetime.now().strftime('%H:%M:%S %Z')}"
            )

            # Send directly (bypass queue for startup message)
            await self._send_raw_message(message)
            logger.info("Startup notification sent")

        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")

    async def _process_queue(self):
        """Process message queue with rate limiting"""
        while True:
            try:
                # Get message from queue
                message = await self.message_queue.get()

                # Rate limiting
                time_since_last = datetime.now() - self.last_message_time
                if time_since_last < self.min_interval:
                    await asyncio.sleep((self.min_interval - time_since_last).total_seconds())

                # Send message
                await self._send_raw_message(message)
                self.last_message_time = datetime.now()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(5)

    async def _send_raw_message(self, message: str):
        """Send raw message to Telegram"""
        if not self.enabled or not self.session:
            return

        try:
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }

            async with self.session.post(f"{self.base_url}/sendMessage", json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to send Telegram message: {error_text}")

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    async def send_alert(self, token_data: Dict, priority: str = 'medium'):
        """Send formatted alert to Telegram"""
        if not self.enabled:
            return

        try:
            # Format message based on priority
            if priority == 'high':
                emoji = "🔥"
                prefix = "HIGH CONFIDENCE ALERT"
            elif priority == 'medium':
                emoji = "⚡"
                prefix = "MEDIUM CONFIDENCE ALERT"
            else:
                emoji = "💡"
                prefix = "NEW TOKEN ALERT"

            # Build message
            message = self._format_alert_message(token_data, emoji, prefix)

            # Add to queue
            await self.message_queue.put(message)

        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    def _format_alert_message(self, token_data: Dict, emoji: str, prefix: str) -> str:
        """Format token data into compact alert message"""
        chain = token_data.get('chain', 'Unknown').upper()
        symbol = token_data.get('symbol', 'Unknown')
        name = token_data.get('name', 'Unknown')
        address = token_data.get('address', token_data.get('mint_address', token_data.get('new_token', '')))
        dex = token_data.get('dex', 'Unknown')
        score = token_data.get('score', 0)
        analysis = token_data.get('analysis', {})

        # Get message format (compact or standard)
        message_format = os.getenv('TELEGRAM_MESSAGE_FORMAT', 'compact').lower()

        if message_format == 'ultra_compact':
            return self._format_ultra_compact_message(token_data, emoji, prefix)
        elif message_format == 'compact':
            return self._format_compact_message(token_data, emoji, prefix)
        else:
            return self._format_standard_message(token_data, emoji, prefix)

    def _format_ultra_compact_message(self, token_data: Dict, emoji: str, prefix: str) -> str:
        """Ultra compact format - Enhanced 4-line version"""
        chain = token_data.get('chain', 'Unknown').upper()
        symbol = token_data.get('symbol', 'Unknown')
        score = token_data.get('score', 0)
        address = token_data.get('address', token_data.get('mint_address', ''))

        # Chain short codes
        chain_short = {
            'SOLANA': 'SOL',
            'BNB': 'BNB',
            'BASE': 'BASE',
            'ETHEREUM': 'ETH'
        }.get(chain, chain[:3])

        # Priority level
        if score >= 75:
            priority = "HIGH"
        elif score >= 60:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Format numbers with emoji coding
        liquidity = token_data.get('liquidity_usd', 0)
        liq_str = self._format_usd_compact(liquidity)

        volume = token_data.get('volume_24h', 0)
        vol_str = self._format_usd_compact(volume) if volume > 0 else "New"

        holders = token_data.get('holders', 0)

        # Calculate token age (compact format without emoji)
        age_str = self._get_token_age_compact(token_data)

        # Line 1: 🔥 HIGH | SOL | $MINU | 82/100 | 🆕2h
        line1 = f"{emoji} <b>{priority}</b> | {chain_short} | ${symbol} | {score}/100"
        if age_str:
            line1 += f" | {age_str}"

        # Line 2: 💰 $45K liq | 📊 $12K vol | 👥 145 hold
        line2 = f"💰 {liq_str} liq | 📊 {vol_str} vol | 👥 {holders} hold"

        # Line 3: ✅ Verified ✅ Renounced | 🔒 LP locked
        badges = []
        if token_data.get('contract_verified'):
            badges.append("✅ Verified")
        if token_data.get('ownership_renounced'):
            badges.append("✅ Renounced")

        # Check LP locked status
        lp_locked = token_data.get('lp_locked', False)
        lp_lock_days = token_data.get('lp_lock_days', 0)

        if badges:
            line3 = " ".join(badges)
            if lp_locked or lp_lock_days >= 30:
                line3 += " | 🔒 LP locked"
            else:
                line3 += " | ⚠️ LP not locked"
        elif lp_locked or lp_lock_days >= 30:
            line3 = "🔒 LP locked"
        else:
            line3 = "⚠️ LP not locked"

        # Line 4: 📈 Chart | 🔗 Contract | 🐦 Twitter | 💬 TG
        links = []

        # Chart link
        if token_data.get('dexscreener_link'):
            links.append(f"📈 <a href='{token_data['dexscreener_link']}'>Chart</a>")

        # Contract link
        short_addr = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
        if token_data.get('explorer_link'):
            links.append(f"🔗 <a href='{token_data['explorer_link']}'>Contract</a>")
        else:
            links.append(f"🔗 <code>{short_addr}</code>")

        # Social links
        if token_data.get('social_links', {}).get('twitter'):
            links.append(f"🐦 <a href='{token_data['social_links']['twitter']}'>Twitter</a>")
        if token_data.get('social_links', {}).get('telegram'):
            links.append(f"💬 <a href='{token_data['social_links']['telegram']}'>TG</a>")

        line4 = " | ".join(links) if links else "🔗 Links not available"

        return f"{line1}\n{line2}\n{line3}\n{line4}"

    def _format_compact_message(self, token_data: Dict, emoji: str, prefix: str) -> str:
        """Compact format - optimized for readability"""
        chain = token_data.get('chain', 'Unknown').upper()
        symbol = token_data.get('symbol', 'Unknown')
        name = token_data.get('name', 'Unknown')
        address = token_data.get('address', token_data.get('mint_address', ''))
        dex = token_data.get('dex', 'Unknown')
        score = token_data.get('score', 0)
        analysis = token_data.get('analysis', {})

        # Format numbers
        liquidity = token_data.get('liquidity_usd', 0)
        liq_str = self._format_usd_compact(liquidity)

        volume = token_data.get('volume_24h', 0)
        vol_str = self._format_usd_compact(volume) if volume > 0 else "New"

        holders = token_data.get('holders', 0)

        # Calculate token age
        age_str = self._get_token_age(token_data)

        # Price
        price = token_data.get('price_usd', 0)

        # Score indicator
        if score >= 75:
            score_indicator = "🔴 IMMEDIATE"
        elif score >= 60:
            score_indicator = "🟡 Review 30min"
        else:
            score_indicator = "🟢 Hourly"

        # Build compact message
        lines = [
            f"<b>{emoji} {prefix.replace('CONFIDENCE ALERT', 'ALERT')} {emoji}</b>",
            "",
            f"<b>Token:</b> {name} (${symbol})",
            f"<b>Chain:</b> {chain} | <b>DEX:</b> {dex}",
            f"<b>Score:</b> {score}/100 {score_indicator}",
            "",
            f"<b>📊 Key Metrics</b>",
            f"Liq: {liq_str} | Vol: {vol_str} | Hold: {holders}",
        ]

        if age_str:
            lines[-1] += f" | {age_str}"

        # Verification badges
        badges = []
        if token_data.get('contract_verified'):
            badges.append("✅ Verified")
        if token_data.get('ownership_renounced'):
            badges.append("✅ Renounced")
        if token_data.get('lp_locked'):
            badges.append("✅ LP Locked")

        if badges:
            lines.append(" | ".join(badges))

        # Add warnings or strengths (max 3)
        warnings = analysis.get('warnings', [])
        positives = analysis.get('positives', [])

        if score >= 60 and positives:
            lines.extend([
                "",
                "<b>⚡ Strengths</b>"
            ])
            for positive in positives[:3]:
                lines.append(f"• {positive}")
        elif warnings:
            lines.extend([
                "",
                "<b>⚠️ Cautions</b>"
            ])
            for warning in warnings[:3]:
                lines.append(f"• {warning}")

        # Links (consolidated in one line)
        lines.append("")
        links = []

        # Contract
        short_addr = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
        if token_data.get('explorer_link'):
            links.append(f"<a href='{token_data['explorer_link']}'>Contract</a>")

        # Chart
        if token_data.get('dexscreener_link'):
            links.append(f"<a href='{token_data['dexscreener_link']}'>Chart</a>")

        # Social
        social_links = token_data.get('social_links', {})
        if social_links.get('twitter'):
            links.append(f"<a href='{social_links['twitter']}'>Twitter</a>")
        if social_links.get('telegram'):
            links.append(f"<a href='{social_links['telegram']}'>Telegram</a>")

        if links:
            lines.append(f"🔗 {' | '.join(links)}")

        # Footer
        lines.extend([
            "",
            f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC</i>",
            "<i>⚠️ DYOR - Not financial advice</i>"
        ])

        return "\n".join(lines)

    def _format_standard_message(self, token_data: Dict, emoji: str, prefix: str) -> str:
        """Standard format - original detailed version"""
        chain = token_data.get('chain', 'Unknown').upper()
        symbol = token_data.get('symbol', 'Unknown')
        name = token_data.get('name', 'Unknown')
        address = token_data.get('address', token_data.get('mint_address', token_data.get('new_token', '')))
        dex = token_data.get('dex', 'Unknown')
        score = token_data.get('score', 0)
        analysis = token_data.get('analysis', {})

        # Format numbers
        liquidity = token_data.get('liquidity_usd', 0)
        liquidity_str = self._format_usd(liquidity)

        volume = token_data.get('volume_24h', 0)
        volume_str = self._format_usd(volume) if volume > 0 else "New"

        # Build message
        lines = [
            f"<b>{emoji} {prefix} {emoji}</b>",
            "",
            f"<b>Token:</b> {name} ({symbol})",
            f"<b>Chain:</b> {chain}",
            f"<b>DEX:</b> {dex}",
            f"<b>Score:</b> {score}/100 ({analysis.get('confidence_level', 'Unknown')})",
            "",
            f"<b>📊 Metrics</b>",
            f"• Liquidity: {liquidity_str}",
            f"• Volume 24h: {volume_str}"
        ]

        # Add holder info if available
        holders = token_data.get('holders', {})
        if holders:
            lines.append(f"• Holders: {holders.get('total', 'Unknown')}")

        # Add contract info
        if token_data.get('contract_verified'):
            lines.append("• ✅ Contract Verified")

        if token_data.get('ownership_renounced'):
            lines.append("• ✅ Ownership Renounced")

        # Add scores breakdown
        if analysis.get('scores'):
            lines.extend([
                "",
                "<b>📈 Score Breakdown</b>"
            ])
            for metric, value in analysis['scores'].items():
                metric_name = metric.replace('_', ' ').title()
                lines.append(f"• {metric_name}: {value:.1f}")

        # Add warnings if any
        warnings = analysis.get('warnings', [])
        if warnings:
            lines.extend([
                "",
                "<b>⚠️ Warnings</b>"
            ])
            for warning in warnings[:3]:  # Limit to 3 warnings
                lines.append(f"• {warning}")

        # Add positives if any
        positives = analysis.get('positives', [])
        if positives:
            lines.extend([
                "",
                "<b>✅ Positives</b>"
            ])
            for positive in positives[:3]:  # Limit to 3 positives
                lines.append(f"• {positive}")

        # Add links
        lines.extend([
            "",
            "<b>🔗 Links</b>"
        ])

        # Contract address (shortened)
        short_address = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
        lines.append(f"• Contract: <code>{short_address}</code>")

        # Explorer link
        if token_data.get('explorer_link'):
            lines.append(f"• <a href='{token_data['explorer_link']}'>View on Explorer</a>")

        # DexScreener link
        if token_data.get('dexscreener_link'):
            lines.append(f"• <a href='{token_data['dexscreener_link']}'>View on DexScreener</a>")

        # Social links
        social_links = token_data.get('social_links', {})
        if social_links.get('website'):
            lines.append(f"• <a href='{social_links['website']}'>Website</a>")
        if social_links.get('twitter'):
            lines.append(f"• <a href='{social_links['twitter']}'>Twitter</a>")
        if social_links.get('telegram'):
            lines.append(f"• <a href='{social_links['telegram']}'>Telegram</a>")

        # Add timestamp
        lines.extend([
            "",
            f"<i>🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        ])

        # Add disclaimer
        lines.extend([
            "",
            "<i>⚠️ Educational purposes only. Not financial advice. Always DYOR!</i>"
        ])

        return "\n".join(lines)

    def _format_usd(self, amount: float) -> str:
        """Format USD amount with proper notation"""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.2f}K"
        else:
            return f"${amount:.2f}"

    def _format_usd_compact(self, amount: float) -> str:
        """Format USD amount in compact notation"""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.1f}K"
        else:
            return f"${amount:.0f}"

    def _get_token_age(self, token_data: Dict) -> str:
        """Calculate and format token age"""
        try:
            discovered_at = token_data.get('discovered_at')
            created_at = token_data.get('created_at')

            # Try to parse the timestamp
            if discovered_at:
                if isinstance(discovered_at, str):
                    token_time = datetime.fromisoformat(discovered_at.replace('Z', '+00:00'))
                else:
                    token_time = discovered_at
            elif created_at:
                if isinstance(created_at, str):
                    token_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    token_time = created_at
            else:
                return ""

            # Calculate age
            age = datetime.now() - token_time.replace(tzinfo=None)
            hours = int(age.total_seconds() / 3600)
            minutes = int((age.total_seconds() % 3600) / 60)

            if hours == 0:
                return f"🆕 {minutes}m old"
            elif hours < 24:
                return f"⏱️ {hours}h old"
            else:
                days = int(hours / 24)
                return f"⏱️ {days}d old"

        except Exception as e:
            logger.debug(f"Error calculating token age: {e}")
            return ""

    def _get_token_age_compact(self, token_data: Dict) -> str:
        """Calculate and format token age (compact version for header)"""
        try:
            discovered_at = token_data.get('discovered_at')
            created_at = token_data.get('created_at')

            # Try to parse the timestamp
            if discovered_at:
                if isinstance(discovered_at, str):
                    token_time = datetime.fromisoformat(discovered_at.replace('Z', '+00:00'))
                else:
                    token_time = discovered_at
            elif created_at:
                if isinstance(created_at, str):
                    token_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    token_time = created_at
            else:
                return ""

            # Calculate age
            age = datetime.now() - token_time.replace(tzinfo=None)
            hours = int(age.total_seconds() / 3600)
            minutes = int((age.total_seconds() % 3600) / 60)

            if hours == 0:
                return f"🆕{minutes}m"
            elif hours < 24:
                return f"🆕{hours}h"
            else:
                days = int(hours / 24)
                return f"⏱️{days}d"

        except Exception as e:
            logger.debug(f"Error calculating token age: {e}")
            return ""

    async def send_summary(self, stats: Dict):
        """Send daily summary to Telegram"""
        if not self.enabled:
            return

        try:
            lines = [
                "<b>📊 Daily Monitoring Summary 📊</b>",
                "",
                f"<b>Tokens Discovered:</b> {stats.get('tokens_discovered', 0)}",
                f"<b>Alerts Sent:</b> {stats.get('alerts_sent_today', 0)}",
                "",
                "<b>Alert Breakdown:</b>",
                f"• High Confidence: {stats.get('high_confidence_alerts', 0)}",
                f"• Medium Confidence: {stats.get('medium_confidence_alerts', 0)}",
                f"• Low Confidence: {stats.get('low_confidence_alerts', 0)}",
                "",
                "<b>Chain Distribution:</b>"
            ]

            for chain, count in stats.get('chain_stats', {}).items():
                lines.append(f"• {chain.upper()}: {count} tokens")

            if stats.get('errors', 0) > 0:
                lines.extend([
                    "",
                    f"<b>⚠️ Errors:</b> {stats.get('errors', 0)}"
                ])

            lines.extend([
                "",
                f"<i>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            ])

            message = "\n".join(lines)
            await self.message_queue.put(message)

        except Exception as e:
            logger.error(f"Error sending summary: {e}")

    async def send_error_alert(self, error_message: str, chain: str = None):
        """Send error alert to Telegram"""
        if not self.enabled:
            return

        try:
            lines = [
                "<b>❌ MONITORING ERROR ❌</b>",
                ""
            ]

            if chain:
                lines.append(f"<b>Chain:</b> {chain.upper()}")

            lines.extend([
                f"<b>Error:</b> {error_message}",
                "",
                f"<i>🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            ])

            message = "\n".join(lines)
            await self.message_queue.put(message)

        except Exception as e:
            logger.error(f"Error sending error alert: {e}")