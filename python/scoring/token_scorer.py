""" Token Scoring Engine Comprehensive scoring system for evaluating
newly launched tokens """

import logging
import os
import re
import asyncio
import aiohttp
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solana.rpc.api import Client

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ScoringCriteria:
    """Criteria and weights for token scoring (max 100 points)"""
    liquidity_weight: float = float(os.getenv('LIQUIDITY_WEIGHT', 10.0))  # Max 10 points
    volume_weight: float = float(os.getenv('VOLUME_WEIGHT', 20.0))  # Max 20 points
    holder_distribution_weight: float = float(os.getenv('HOLDER_DISTRIBUTION_WEIGHT', 15.0))  # Max 15 points
    contract_verification_weight: float = float(os.getenv('CONTRACT_VERIFICATION_WEIGHT', 30.0))  # Max 30 points
    social_presence_weight: float = float(os.getenv('SOCIAL_PRESENCE_WEIGHT', 15.0))  # Max 15 points
    website_quality_weight: float = float(os.getenv('WEBSITE_QUALITY_WEIGHT', 5.0))  # Max 5 points
    token_economics_weight: float = float(os.getenv('TOKEN_ECONOMICS_WEIGHT', 20.0))  # Max 20 points
    team_quality_weight: float = float(os.getenv('TEAM_QUALITY_WEIGHT', 15.0))  # Max 15 points


class TokenScorer:
    """Advanced token scoring system"""

    # Scale factor to normalize base scores (max 45: liquidity 10 + volume 20 + holder 15) to 0-100 range
    SCORE_MULTIPLIER = 100.0 / 45.0  # ~2.22

    def __init__(self):
        """Initialize the token scorer"""
        self.criteria = ScoringCriteria()
        self.session: Optional[aiohttp.ClientSession] = None

        # Minimum thresholds (Automatic Filters)
        self.min_liquidity_usd = float(os.getenv('MIN_LIQUIDITY_USD', 10000))
        self.min_market_cap_usd = float(os.getenv('MIN_MARKET_CAP_USD', 8000))
        self.min_volume_24h = float(os.getenv('MIN_VOLUME_24H', 3000))
        self.min_holders = int(os.getenv('MIN_HOLDERS', 10))
        self.max_token_age_hours = int(os.getenv('MAX_TOKEN_AGE_HOURS', 24))
        self.max_buy_tax = float(os.getenv('MAX_BUY_TAX_PERCENT', 5.0))
        self.max_sell_tax = float(os.getenv('MAX_SELL_TAX_PERCENT', 5.0))
        self.min_twitter_followers = int(os.getenv('MIN_TWITTER_FOLLOWERS', 5))
        self.min_telegram_members = int(os.getenv('MIN_TELEGRAM_MEMBERS', 5))
        self.min_lp_lock_days = int(os.getenv('MIN_LP_LOCK_DAYS', 0))

        # Cache for external data
        self.social_cache = {}
        self.contract_cache = {}

        logger.info("Token Scorer initialized with new criteria")

    async def initialize(self):
        """Initialize async resources"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

    async def score_token(self, token_data: Dict) -> Tuple[float, Dict]:
        """
        Score a token from 0-100 based on multiple factors
        Returns: (score, analysis_details)
        """
        if not self.session:
            await self.initialize()

        analysis = {
            'timestamp': datetime.now().isoformat(),
            'token_address': token_data.get('address', token_data.get('mint_address', '')),
            'chain': token_data.get('chain', 'unknown'),
            'scores': {},
            'warnings': [],
            'positives': []
        }

        total_score = 0.0

        # Score based on available data (scaled to 0-100 range)
        liquidity_score = await self._score_liquidity(token_data) * self.SCORE_MULTIPLIER
        volume_score = await self._score_volume(token_data) * self.SCORE_MULTIPLIER
        holder_score = await self._score_holder_distribution(token_data) * self.SCORE_MULTIPLIER

        analysis['scores']['liquidity'] = liquidity_score
        analysis['scores']['volume'] = volume_score
        analysis['scores']['holder_distribution'] = holder_score

        total_score = liquidity_score + volume_score + holder_score

        # Simplified penalties
        penalty = 0
        if token_data.get('liquidity_usd', 0) < self.min_liquidity_usd:
            penalty += 10
            analysis['warnings'].append(f"Liquidity below minimum ${self.min_liquidity_usd}")
        if token_data.get('volume_24h', 0) < self.min_volume_24h:
            penalty += 5
            analysis['warnings'].append(f"Volume below minimum ${self.min_volume_24h}")
        if token_data.get('holders', 0) < self.min_holders:
            penalty += 5
            analysis['warnings'].append(f"Holders below minimum {self.min_holders}")

        total_score = max(0, total_score - penalty)

        # Simplified bonuses
        bonus = 0
        if token_data.get('volume_24h', 0) > token_data.get('liquidity_usd', 0) * 2:
            bonus += 5
            analysis['positives'].append("Strong trading volume")
        if token_data.get('dex') in ['Uniswap V3', 'PancakeSwap V3', 'Raydium', 'Aerodrome']:
            bonus += 5
            analysis['positives'].append(f"Launched on reputable DEX: {token_data.get('dex')}")

        total_score = min(100, total_score + bonus)

        analysis['final_score'] = round(total_score, 2)
        analysis['confidence_level'] = self._get_confidence_level(total_score)

        if os.getenv('DRY_RUN', 'false').lower() == 'true':
            print(json.dumps(analysis, indent=4))

        return total_score, analysis

    async def _score_liquidity(self, token_data: Dict) -> float:
        """Score based on liquidity (Max 10 points)"""
        try:
            liquidity = token_data.get('liquidity_usd', 0)

            # Liquidity Tier: >$10k = 10 points
            if liquidity < self.min_liquidity_usd:
                return 0

            # Simple scoring: >$10k gets 10 points
            if liquidity >= 10000:
                return 10
            else:
                return 0

        except Exception as e:
            logger.error(f"Error scoring liquidity: {e}")
            return 0

    async def _score_volume(self, token_data: Dict) -> float:
        """Score based on trading volume (Max 20 points)"""
        try:
            # Minimum Volume: >$3k daily = 10 points
            # High Volume Bonus: >$10k = 20 points
            volume_24h = token_data.get('volume_24h', 0)

            if volume_24h >= 10000:  # $10k+ volume
                return 20
            elif volume_24h >= 3000:  # $3k+ volume
                return 10
            else:
                return 0

        except Exception as e:
            logger.error(f"Error scoring volume: {e}")
            return 0



    async def _get_holder_distribution(self, token_address: str, chain: str) -> Optional[Dict]:
        """Get holder distribution from the blockchain"""
        if chain != 'solana':
            return None

        try:
            client = Client(os.getenv("RPC_HTTP"))
            mint_pubkey = Pubkey.from_string(token_address)

            # Get total supply
            total_supply_response = client.get_token_supply(mint_pubkey)
            total_supply = total_supply_response.value.ui_amount

            # Get largest accounts
            largest_accounts_response = client.get_token_largest_accounts(mint_pubkey)
            largest_accounts = largest_accounts_response.value

            top_10_balance = sum(acc.ui_amount for acc in largest_accounts[:10])
            top_10_percentage = (top_10_balance / total_supply) * 100 if total_supply > 0 else 0

            return {
                'total': len(largest_accounts),
                'top_10_percentage': top_10_percentage,
            }
        except Exception as e:
            logger.error(f"Error getting holder distribution: {e}")
            return None

    async def _score_holder_distribution(self, token_data: Dict) -> float:
        """Score based on holder distribution (Max 15 points)"""
        try:
            # Minimum Holders: 10
            # Optimal Range: 10-100 holders = 10 points
            # Growth Bonus: 100-500 holders = 15 points

            holders = await self._get_holder_distribution(token_data.get('address', ''), token_data.get('chain', ''))

            if not holders:
                # Use holder count from token data if available
                total_holders = token_data.get('holders', 0)
            else:
                total_holders = holders.get('total', 0)

            # Scoring based on holder count
            if total_holders >= 10 and total_holders <= 50:
                return 15  # Growth Bonus
            elif total_holders >= 10 and total_holders < 20:
                return 10  # Optimal Range
            elif total_holders < 10:
                return 0  # Below minimum
            else:
                return 10  # Above 500 still good

        except Exception as e:
            logger.error(f"Error scoring holder distribution: {e}")
            return 0

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level based on score (Alert Distribution Strategy)"""
        if score >= 75:
            return "🔴 High (75-100): Immediate action"
        elif score >= 60:
            return "🟡 Medium (60-74): Review within 30min"
        elif score >= 50:
            return "🟢 Low (50-59): Hourly check"
        else:
            return "⚪ Logged (<50): Filtered out"
