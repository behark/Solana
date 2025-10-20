"""
Token Scoring Engine
Comprehensive scoring system for evaluating newly launched tokens
"""

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
        self.min_lp_lock_days = int(os.getenv('MIN_LP_LOCK_DAYS', 30))

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

        # 1. Liquidity Score (Max 10 pts)
        liquidity_score = await self._score_liquidity(token_data)
        analysis['scores']['liquidity'] = liquidity_score
        total_score += liquidity_score

        # 2. Volume Score (Max 20 pts)
        volume_score = await self._score_volume(token_data)
        analysis['scores']['volume'] = volume_score
        total_score += volume_score

        # 3. Holder Distribution Score (Max 15 pts)
        holder_score = await self._score_holder_distribution(token_data)
        analysis['scores']['holder_distribution'] = holder_score
        total_score += holder_score

        # 4. Contract Verification Score (Max 30 pts)
        contract_score = await self._score_contract(token_data)
        analysis['scores']['contract_verification'] = contract_score
        total_score += contract_score

        # 5. Social Presence Score (Max 15 pts)
        social_score = await self._score_social_presence(token_data)
        analysis['scores']['social_presence'] = social_score
        total_score += social_score

        # 6. Website Quality / Team Score (Max 5 pts)
        website_score = await self._score_website(token_data)
        analysis['scores']['website_quality'] = website_score
        total_score += website_score

        # 7. Token Economics Score (Max 20 pts)
        economics_score = await self._score_token_economics(token_data)
        analysis['scores']['token_economics'] = economics_score
        total_score += economics_score

        # 8. Team Quality Score (Max 15 pts)
        team_score = await self._score_team_quality(token_data)
        analysis['scores']['team_quality'] = team_score
        total_score += team_score

        # Apply penalties for red flags
        penalty = await self._calculate_penalties(token_data, analysis)
        total_score = max(0, total_score - penalty)

        # Apply bonuses for positive signals
        bonus = await self._calculate_bonuses(token_data, analysis)
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
            if total_holders >= 100 and total_holders <= 500:
                return 15  # Growth Bonus
            elif total_holders >= 10 and total_holders < 100:
                return 10  # Optimal Range
            elif total_holders < 10:
                return 0  # Below minimum
            else:
                return 10  # Above 500 still good

        except Exception as e:
            logger.error(f"Error scoring holder distribution: {e}")
            return 0

    async def _score_contract(self, token_data: Dict) -> float:
        """Score based on contract verification and safety (Max 30 points)"""
        try:
            # ✅ Verified contract = 10 points
            # ✅ Ownership renounced = 5 points
            # ✅ Liquidity locked = 5 points
            # ✅ Honeypot check passed = 10 points

            chain = token_data.get('chain', '')
            address = token_data.get('address', token_data.get('mint_address', ''))

            # Check cache
            cache_key = f"{chain}_{address}"
            if cache_key in self.contract_cache:
                return self.contract_cache[cache_key]

            score = 0

            # Contract verification (10 points)
            is_verified = token_data.get('contract_verified', False)
            if is_verified:
                score += 10

            # Honeypot check (10 points if passed, 0 if honeypot)
            honeypot_check = token_data.get('honeypot_check', {})
            if honeypot_check:
                if not honeypot_check.get('is_honeypot', False):
                    score += 10
                else:
                    return 0  # Honeypot detected, zero score total

            # Renounced ownership (5 points)
            if token_data.get('ownership_renounced', False):
                score += 5

            # Liquidity locked (5 points)
            lp_locked = token_data.get('lp_locked', False)
            lp_lock_days = token_data.get('lp_lock_days', 0)
            if lp_locked or lp_lock_days >= self.min_lp_lock_days:
                score += 5

            self.contract_cache[cache_key] = min(30, score)
            return self.contract_cache[cache_key]

        except Exception as e:
            logger.error(f"Error scoring contract: {e}")
            return 0

    async def _score_social_presence(self, token_data: Dict) -> float:
        """Score based on social media presence (Max 15 points)"""
        try:
            # Twitter: >5 followers = 5 points
            # Telegram: >5 members = 5 points
            # Active engagement = 5 additional points

            address = token_data.get('address', token_data.get('mint_address', ''))

            # Check cache
            if address in self.social_cache:
                return self.social_cache[address]

            score = 0

            # Check for social links
            social_links = token_data.get('social_links', {})

            # Twitter/X presence (5 points if >5 followers)
            if social_links.get('twitter'):
                followers = social_links.get('twitter_followers', 0)
                if followers >= self.min_twitter_followers:
                    score += 5

            # Telegram presence (5 points if >5 members)
            if social_links.get('telegram'):
                members = social_links.get('telegram_members', 0)
                if members >= self.min_telegram_members:
                    score += 5

            # Active engagement bonus (5 points)
            # Consider engagement if both Twitter and Telegram have good numbers
            if (social_links.get('twitter_followers', 0) >= 50 and
                social_links.get('telegram_members', 0) >= 50):
                score += 5

            self.social_cache[address] = min(15, score)
            return self.social_cache[address]

        except Exception as e:
            logger.error(f"Error scoring social presence: {e}")
            return 0

    async def _score_website(self, token_data: Dict) -> float:
        """Score based on website quality (Max 5 points)"""
        try:
            # Has website = 5 points

            website = token_data.get('social_links', {}).get('website', '')

            if website and website.startswith('http'):
                return 5
            else:
                return 0

        except Exception as e:
            logger.error(f"Error scoring website: {e}")
            return 0

    async def _score_token_economics(self, token_data: Dict) -> float:
        """Score based on tokenomics (Max 20 points)"""
        try:
            # Tax: <5% = 10 points
            # Supply: Reasonable unlock schedule = 5 points
            # LP locked >30 days = 5 points

            score = 0

            # Tax rates (10 points if both <5%)
            buy_tax = token_data.get('buy_tax', 0)
            sell_tax = token_data.get('sell_tax', 0)

            if buy_tax <= self.max_buy_tax and sell_tax <= self.max_sell_tax:
                score += 10

            # Reasonable supply (5 points)
            total_supply = token_data.get('total_supply', 0)
            if total_supply > 0:
                if 1_000_000 <= total_supply <= 1_000_000_000_000:
                    score += 5

            # LP locked >30 days (5 points)
            lp_lock_days = token_data.get('lp_lock_days', 0)
            if lp_lock_days >= self.min_lp_lock_days:
                score += 5

            return min(20, score)

        except Exception as e:
            logger.error(f"Error scoring token economics: {e}")
            return 0

    async def _score_team_quality(self, token_data: Dict) -> float:
        """Score based on team quality (Max 15 points)"""
        try:
            # Has website = 5 points
            # GitHub activity = 5 points
            # Team doxxed = 5 points

            score = 0

            social_links = token_data.get('social_links', {})

            # Website (5 points) - Already scored in website_quality, but count here too
            if social_links.get('website'):
                score += 5

            # GitHub activity (5 points)
            if social_links.get('github'):
                score += 5

            # Team doxxed (5 points)
            if token_data.get('team_doxxed', False):
                score += 5

            return min(15, score)

        except Exception as e:
            logger.error(f"Error scoring team quality: {e}")
            return 0

    async def _calculate_penalties(self, token_data: Dict, analysis: Dict) -> float:
        """Calculate penalties for red flags"""
        penalty = 0

        # Check for suspicious patterns in name/symbol
        name = token_data.get('name', '').lower()
        symbol = token_data.get('symbol', '').lower()

        # Common scam patterns
        scam_patterns = [
            'elon', 'musk', 'doge2.0', 'moon', 'safe', '100x', '1000x',
            'guaranteed', 'pump', 'dump', 'rugpull', 'scam', 'fake'
        ]

        for pattern in scam_patterns:
            if pattern in name or pattern in symbol:
                penalty += 20
                analysis['warnings'].append(f"Suspicious pattern in name/symbol: {pattern}")

        # Very low liquidity (below $10k minimum)
        if token_data.get('liquidity_usd', 0) < self.min_liquidity_usd:
            penalty += 10  # Small penalty, not auto-reject
            analysis['warnings'].append(f"Liquidity below minimum ${self.min_liquidity_usd}")

        # Low market cap (below $8k minimum)
        if token_data.get('market_cap', 0) < self.min_market_cap_usd:
            penalty += 5  # Warning only, not auto-reject
            analysis['warnings'].append(f"Market cap below minimum ${self.min_market_cap_usd}")

        # Low volume (below $3k minimum)
        if token_data.get('volume_24h', 0) < self.min_volume_24h:
            penalty += 5  # Warning only
            analysis['warnings'].append(f"Volume below minimum ${self.min_volume_24h}")

        # Not enough holders
        if token_data.get('holders', 0) < self.min_holders:
            penalty += 5  # Warning only, not auto-reject
            analysis['warnings'].append(f"Holders below minimum {self.min_holders}")

        # No social presence
        if not token_data.get('social_links', {}):
            penalty += 20
            analysis['warnings'].append("No social media presence")

        # High tax rates (above 5%)
        if token_data.get('buy_tax', 0) > self.max_buy_tax or token_data.get('sell_tax', 0) > self.max_sell_tax:
            penalty += 20  # Significant penalty but not auto-reject
            analysis['warnings'].append(f"Tax rates above maximum {self.max_buy_tax}%")

        return penalty

    async def _calculate_bonuses(self, token_data: Dict, analysis: Dict) -> float:
        """Calculate bonuses for positive signals"""
        bonus = 0

        # Verified and audited contract
        if token_data.get('contract_verified') and token_data.get('audited'):
            bonus += 10
            analysis['positives'].append("Verified and audited contract")

        # Strong initial momentum
        if token_data.get('volume_24h', 0) > token_data.get('liquidity_usd', 0) * 2:
            bonus += 5
            analysis['positives'].append("Strong trading volume")

        # Known DEX launch
        if token_data.get('dex') in ['Uniswap V3', 'PancakeSwap V3', 'Raydium', 'Aerodrome']:
            bonus += 5
            analysis['positives'].append(f"Launched on reputable DEX: {token_data.get('dex')}")

        # Good holder distribution
        if token_data.get('holders', {}).get('total', 0) > 100:
            bonus += 5
            analysis['positives'].append("Good initial holder count")

        return bonus

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