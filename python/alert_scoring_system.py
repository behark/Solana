"""
Multi-Chain Memecoin Alert Scoring and Filtering System
Processes thousands of token launches and filters to 500 high-confidence alerts daily
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from enum import Enum
import logging
from collections import deque
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Chain(Enum):
    SOLANA = "solana"
    ETHEREUM = "ethereum"
    BNB = "bnb"
    BASE = "base"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TokenMetrics:
    """Comprehensive token metrics for scoring"""
    # Basic Info
    chain: Chain
    address: str
    name: str
    symbol: str
    launch_time: datetime

    # Liquidity Metrics (30% weight)
    initial_liquidity: float  # USD value
    liquidity_locked: bool
    liquidity_lock_duration: int  # days
    liquidity_to_mcap_ratio: float
    liquidity_providers_count: int

    # Holder Distribution (20% weight)
    total_holders: int
    top_10_holders_percentage: float
    top_holder_percentage: float
    unique_buyers_first_hour: int
    holder_growth_rate: float  # holders/hour
    whale_concentration: float  # Gini coefficient

    # Smart Contract Security (25% weight)
    contract_verified: bool
    honeypot_check: bool  # False = safe
    mint_disabled: bool
    max_tx_percentage: float
    tax_percentage: float
    ownership_renounced: bool
    audit_score: Optional[float]  # 0-100

    # Social Signals (10% weight)
    telegram_members: int
    twitter_followers: int
    twitter_engagement_rate: float
    social_growth_rate: float  # % per hour
    influencer_mentions: int
    sentiment_score: float  # -1 to 1

    # Trading Volume Patterns (10% weight)
    volume_1h: float  # USD
    volume_24h: float  # USD
    buy_sell_ratio: float
    average_trade_size: float
    trades_per_minute: float
    price_volatility: float  # standard deviation

    # Developer Activity (3% weight)
    github_commits: int
    code_updates_24h: int
    developer_wallet_history: int  # previous projects
    team_doxxed: bool

    # Community Growth (2% weight)
    discord_members: int
    reddit_subscribers: int
    community_engagement_score: float  # 0-100

    # Additional Risk Factors
    similar_name_tokens: int  # potential copycats
    rug_pull_indicators: List[str] = field(default_factory=list)
    chain_specific_risks: Dict = field(default_factory=dict)


@dataclass
class ScoringWeights:
    """Configurable weights for scoring algorithm"""
    liquidity: float = 0.30
    holders: float = 0.20
    security: float = 0.25
    social: float = 0.10
    volume: float = 0.10
    developer: float = 0.03
    community: float = 0.02

    # Sub-weights for liquidity
    liquidity_amount: float = 0.40
    liquidity_locked: float = 0.30
    liquidity_ratio: float = 0.20
    liquidity_providers: float = 0.10

    # Sub-weights for holders
    distribution: float = 0.50
    growth_rate: float = 0.30
    unique_buyers: float = 0.20

    # Sub-weights for security
    contract_safety: float = 0.40
    ownership: float = 0.20
    audit: float = 0.20
    taxes: float = 0.20


class TokenScorer:
    """Advanced scoring system with ML-based continuous improvement"""

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.score_history = deque(maxlen=10000)
        self.performance_tracker = {}
        self.ml_model = None
        self.feature_importance = {}

    def calculate_score(self, token: TokenMetrics) -> Tuple[float, Dict[str, float]]:
        """
        Calculate comprehensive token score
        Returns: (total_score, component_scores)
        """
        component_scores = {}

        # 1. Liquidity Score (30%)
        liquidity_score = self._score_liquidity(token)
        component_scores['liquidity'] = liquidity_score

        # 2. Holder Distribution Score (20%)
        holder_score = self._score_holders(token)
        component_scores['holders'] = holder_score

        # 3. Security Score (25%)
        security_score = self._score_security(token)
        component_scores['security'] = security_score

        # 4. Social Signals Score (10%)
        social_score = self._score_social(token)
        component_scores['social'] = social_score

        # 5. Volume Patterns Score (10%)
        volume_score = self._score_volume(token)
        component_scores['volume'] = volume_score

        # 6. Developer Activity Score (3%)
        dev_score = self._score_developer(token)
        component_scores['developer'] = dev_score

        # 7. Community Growth Score (2%)
        community_score = self._score_community(token)
        component_scores['community'] = community_score

        # Calculate weighted total
        total_score = (
            liquidity_score * self.weights.liquidity +
            holder_score * self.weights.holders +
            security_score * self.weights.security +
            social_score * self.weights.social +
            volume_score * self.weights.volume +
            dev_score * self.weights.developer +
            community_score * self.weights.community
        )

        # Apply chain-specific adjustments
        chain_multiplier = self._get_chain_multiplier(token.chain)
        total_score *= chain_multiplier

        # Apply time decay (newer tokens get slight boost)
        time_multiplier = self._get_time_multiplier(token.launch_time)
        total_score *= time_multiplier

        # Cap score at 100
        total_score = min(100, total_score)

        return total_score, component_scores

    def _score_liquidity(self, token: TokenMetrics) -> float:
        """Score liquidity metrics (0-100)"""
        score = 0

        # Initial liquidity amount (40% of liquidity score)
        if token.initial_liquidity >= 100000:
            score += 40
        elif token.initial_liquidity >= 50000:
            score += 30
        elif token.initial_liquidity >= 20000:
            score += 20
        elif token.initial_liquidity >= 10000:
            score += 10
        else:
            score += max(0, (token.initial_liquidity / 10000) * 10)

        # Liquidity locked (30% of liquidity score)
        if token.liquidity_locked:
            if token.liquidity_lock_duration >= 365:
                score += 30
            elif token.liquidity_lock_duration >= 180:
                score += 25
            elif token.liquidity_lock_duration >= 90:
                score += 20
            elif token.liquidity_lock_duration >= 30:
                score += 15
            else:
                score += 10

        # Liquidity to market cap ratio (20% of liquidity score)
        if token.liquidity_to_mcap_ratio >= 0.15:
            score += 20
        elif token.liquidity_to_mcap_ratio >= 0.10:
            score += 15
        elif token.liquidity_to_mcap_ratio >= 0.05:
            score += 10
        else:
            score += max(0, (token.liquidity_to_mcap_ratio / 0.05) * 10)

        # Liquidity providers count (10% of liquidity score)
        if token.liquidity_providers_count >= 100:
            score += 10
        elif token.liquidity_providers_count >= 50:
            score += 7
        elif token.liquidity_providers_count >= 20:
            score += 5
        else:
            score += max(0, (token.liquidity_providers_count / 20) * 5)

        return min(100, score)

    def _score_holders(self, token: TokenMetrics) -> float:
        """Score holder distribution metrics (0-100)"""
        score = 0

        # Distribution score (50% of holder score)
        # Lower concentration is better
        if token.top_10_holders_percentage <= 20:
            score += 50
        elif token.top_10_holders_percentage <= 30:
            score += 40
        elif token.top_10_holders_percentage <= 40:
            score += 30
        elif token.top_10_holders_percentage <= 50:
            score += 20
        else:
            score += max(0, (1 - (token.top_10_holders_percentage - 50) / 50) * 20)

        # Holder growth rate (30% of holder score)
        if token.holder_growth_rate >= 100:  # 100+ holders per hour
            score += 30
        elif token.holder_growth_rate >= 50:
            score += 25
        elif token.holder_growth_rate >= 20:
            score += 20
        elif token.holder_growth_rate >= 10:
            score += 15
        else:
            score += max(0, (token.holder_growth_rate / 10) * 15)

        # Unique buyers in first hour (20% of holder score)
        if token.unique_buyers_first_hour >= 500:
            score += 20
        elif token.unique_buyers_first_hour >= 200:
            score += 15
        elif token.unique_buyers_first_hour >= 100:
            score += 10
        elif token.unique_buyers_first_hour >= 50:
            score += 5
        else:
            score += max(0, (token.unique_buyers_first_hour / 50) * 5)

        # Penalize high whale concentration
        if token.whale_concentration > 0.7:
            score *= 0.5
        elif token.whale_concentration > 0.5:
            score *= 0.75

        return min(100, score)

    def _score_security(self, token: TokenMetrics) -> float:
        """Score security metrics (0-100)"""
        score = 0

        # Contract safety (40% of security score)
        if token.contract_verified:
            score += 10
        if not token.honeypot_check:  # False means safe
            score += 20
        if token.mint_disabled:
            score += 10

        # Ownership (20% of security score)
        if token.ownership_renounced:
            score += 20

        # Audit score (20% of security score)
        if token.audit_score:
            score += (token.audit_score / 100) * 20

        # Taxes and limits (20% of security score)
        if token.tax_percentage <= 5:
            score += 10
        elif token.tax_percentage <= 10:
            score += 5

        if token.max_tx_percentage >= 2:
            score += 10
        elif token.max_tx_percentage >= 1:
            score += 5

        # Heavy penalties for security issues
        if token.honeypot_check:  # True means it's a honeypot
            score = 0
        elif len(token.rug_pull_indicators) > 0:
            score *= max(0.2, 1 - (len(token.rug_pull_indicators) * 0.2))

        return min(100, score)

    def _score_social(self, token: TokenMetrics) -> float:
        """Score social signals (0-100)"""
        score = 0

        # Community size (40% of social score)
        total_community = token.telegram_members + token.twitter_followers
        if total_community >= 10000:
            score += 40
        elif total_community >= 5000:
            score += 30
        elif total_community >= 2000:
            score += 20
        elif total_community >= 1000:
            score += 10
        else:
            score += max(0, (total_community / 1000) * 10)

        # Engagement rate (30% of social score)
        if token.twitter_engagement_rate >= 5:
            score += 30
        elif token.twitter_engagement_rate >= 3:
            score += 20
        elif token.twitter_engagement_rate >= 1:
            score += 10
        else:
            score += max(0, token.twitter_engagement_rate * 10)

        # Growth rate (20% of social score)
        if token.social_growth_rate >= 20:  # 20% per hour
            score += 20
        elif token.social_growth_rate >= 10:
            score += 15
        elif token.social_growth_rate >= 5:
            score += 10
        else:
            score += max(0, (token.social_growth_rate / 5) * 10)

        # Sentiment and influencers (10% of social score)
        sentiment_contribution = (token.sentiment_score + 1) / 2 * 5  # Convert -1,1 to 0,5
        score += sentiment_contribution

        if token.influencer_mentions >= 5:
            score += 5
        elif token.influencer_mentions >= 2:
            score += 3
        elif token.influencer_mentions >= 1:
            score += 1

        return min(100, score)

    def _score_volume(self, token: TokenMetrics) -> float:
        """Score volume patterns (0-100)"""
        score = 0

        # Volume magnitude (40% of volume score)
        if token.volume_1h >= 100000:
            score += 40
        elif token.volume_1h >= 50000:
            score += 30
        elif token.volume_1h >= 20000:
            score += 20
        elif token.volume_1h >= 10000:
            score += 10
        else:
            score += max(0, (token.volume_1h / 10000) * 10)

        # Buy/sell ratio (30% of volume score)
        if token.buy_sell_ratio >= 1.5:
            score += 30
        elif token.buy_sell_ratio >= 1.2:
            score += 20
        elif token.buy_sell_ratio >= 1.0:
            score += 10
        else:
            score += max(0, token.buy_sell_ratio * 10)

        # Trading activity (20% of volume score)
        if token.trades_per_minute >= 10:
            score += 20
        elif token.trades_per_minute >= 5:
            score += 15
        elif token.trades_per_minute >= 2:
            score += 10
        else:
            score += max(0, (token.trades_per_minute / 2) * 10)

        # Volatility check (10% of volume score)
        # Moderate volatility is good, too high or too low is bad
        if 0.05 <= token.price_volatility <= 0.15:
            score += 10
        elif 0.03 <= token.price_volatility <= 0.20:
            score += 5

        return min(100, score)

    def _score_developer(self, token: TokenMetrics) -> float:
        """Score developer activity (0-100)"""
        score = 0

        # Team transparency (40% of dev score)
        if token.team_doxxed:
            score += 40

        # Development activity (30% of dev score)
        if token.github_commits >= 50:
            score += 30
        elif token.github_commits >= 20:
            score += 20
        elif token.github_commits >= 10:
            score += 10
        else:
            score += max(0, (token.github_commits / 10) * 10)

        # Recent updates (15% of dev score)
        if token.code_updates_24h >= 5:
            score += 15
        elif token.code_updates_24h >= 2:
            score += 10
        elif token.code_updates_24h >= 1:
            score += 5

        # Developer history (15% of dev score)
        if token.developer_wallet_history >= 3:
            score += 15
        elif token.developer_wallet_history >= 1:
            score += 10
        elif token.developer_wallet_history == 0:
            score += 5  # New developer, neutral

        return min(100, score)

    def _score_community(self, token: TokenMetrics) -> float:
        """Score community growth (0-100)"""
        score = 0

        # Community size (50% of community score)
        total_community = token.discord_members + token.reddit_subscribers
        if total_community >= 5000:
            score += 50
        elif total_community >= 2000:
            score += 35
        elif total_community >= 1000:
            score += 25
        elif total_community >= 500:
            score += 15
        else:
            score += max(0, (total_community / 500) * 15)

        # Engagement score (50% of community score)
        score += (token.community_engagement_score / 100) * 50

        return min(100, score)

    def _get_chain_multiplier(self, chain: Chain) -> float:
        """Get chain-specific score multiplier"""
        multipliers = {
            Chain.SOLANA: 1.1,      # Slightly favor Solana for memecoins
            Chain.ETHEREUM: 0.95,   # Higher gas fees
            Chain.BNB: 1.05,        # Good balance
            Chain.BASE: 1.0         # Neutral
        }
        return multipliers.get(chain, 1.0)

    def _get_time_multiplier(self, launch_time: datetime) -> float:
        """Get time-based score multiplier (prefer newer tokens)"""
        hours_since_launch = (datetime.now() - launch_time).total_seconds() / 3600

        if hours_since_launch <= 1:
            return 1.2  # Very new, higher potential
        elif hours_since_launch <= 4:
            return 1.1
        elif hours_since_launch <= 12:
            return 1.0
        elif hours_since_launch <= 24:
            return 0.95
        else:
            return 0.9  # Older than 24 hours


class MLScoreOptimizer:
    """Machine learning component for continuous score improvement"""

    def __init__(self):
        self.training_data = []
        self.model = None
        self.feature_columns = []
        self.performance_history = deque(maxlen=1000)

    def collect_outcome(self, token_address: str, initial_score: float,
                        outcome: float, timestamp: datetime):
        """Collect actual outcomes for training"""
        self.training_data.append({
            'address': token_address,
            'score': initial_score,
            'outcome': outcome,  # Actual price change after 24h
            'timestamp': timestamp,
            'success': outcome >= 2.0  # 2x or more
        })

    def train_model(self):
        """Train ML model on collected data"""
        if len(self.training_data) < 100:
            return  # Need minimum data

        df = pd.DataFrame(self.training_data)

        # Extract features and labels
        X = df[['score']].values
        y = df['success'].values

        # Simple logistic regression for now
        # In production, use XGBoost or similar
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        self.model = LogisticRegression()
        self.model.fit(X_train, y_train)

        # Calculate performance metrics
        accuracy = self.model.score(X_test, y_test)
        logger.info(f"Model retrained. Accuracy: {accuracy:.2%}")

        return accuracy

    def adjust_weights(self, current_weights: ScoringWeights) -> ScoringWeights:
        """Adjust scoring weights based on ML insights"""
        if not self.model or len(self.training_data) < 500:
            return current_weights

        # Analyze feature importance (simplified)
        # In production, use SHAP values or similar
        df = pd.DataFrame(self.training_data)
        successful = df[df['success'] == True]
        failed = df[df['success'] == False]

        # Calculate average scores for successful vs failed
        success_avg = successful['score'].mean()
        fail_avg = failed['score'].mean()

        # Adjust weights slightly based on performance
        adjustment_factor = min(1.1, max(0.9, success_avg / (fail_avg + 0.01)))

        # Apply small adjustments to avoid drastic changes
        adjusted = ScoringWeights()
        for field in ['liquidity', 'holders', 'security', 'social', 'volume']:
            current_value = getattr(current_weights, field)
            adjusted_value = current_value * (1 + (adjustment_factor - 1) * 0.1)
            setattr(adjusted, field, adjusted_value)

        # Normalize weights to sum to 1
        total = sum([adjusted.liquidity, adjusted.holders, adjusted.security,
                    adjusted.social, adjusted.volume, adjusted.developer, adjusted.community])

        for field in ['liquidity', 'holders', 'security', 'social', 'volume', 'developer', 'community']:
            current_value = getattr(adjusted, field)
            setattr(adjusted, field, current_value / total)

        return adjusted

    def predict_success_probability(self, score: float) -> float:
        """Predict probability of 2x success"""
        if not self.model:
            # Fallback to simple threshold
            if score >= 75:
                return 0.7
            elif score >= 60:
                return 0.5
            elif score >= 45:
                return 0.3
            else:
                return 0.1

        return self.model.predict_proba([[score]])[0][1]


class AlertDistributionManager:
    """Manages distribution of 500 alerts throughout the day"""

    def __init__(self, daily_limit: int = 500):
        self.daily_limit = daily_limit
        self.alerts_sent_today = 0
        self.hourly_distribution = self._calculate_hourly_distribution()
        self.alert_history = deque(maxlen=10000)
        self.chain_quotas = {
            Chain.SOLANA: 0.40,     # 40% of alerts
            Chain.ETHEREUM: 0.25,   # 25% of alerts
            Chain.BNB: 0.20,        # 20% of alerts
            Chain.BASE: 0.15        # 15% of alerts
        }

    def _calculate_hourly_distribution(self) -> Dict[int, int]:
        """Calculate how many alerts to send each hour"""
        # Peak hours (more alerts)
        # 9-11 AM UTC: 30 alerts/hour
        # 2-4 PM UTC: 30 alerts/hour
        # 8-10 PM UTC: 25 alerts/hour
        # Other hours: 15-20 alerts/hour

        distribution = {}
        total_allocated = 0

        for hour in range(24):
            if 9 <= hour <= 11:  # Morning peak
                alerts = 30
            elif 14 <= hour <= 16:  # Afternoon peak
                alerts = 30
            elif 20 <= hour <= 22:  # Evening peak
                alerts = 25
            elif 0 <= hour <= 6:  # Night time (fewer)
                alerts = 10
            else:  # Regular hours
                alerts = 20

            distribution[hour] = alerts
            total_allocated += alerts

        # Adjust to exactly 500
        adjustment = self.daily_limit - total_allocated
        distribution[12] += adjustment  # Add adjustment to noon

        return distribution

    def should_send_alert(self, score: float, chain: Chain,
                          current_hour: int) -> Tuple[bool, float]:
        """
        Determine if alert should be sent based on score and quotas
        Returns: (should_send, confidence_threshold)
        """
        # Get hourly quota
        hourly_quota = self.hourly_distribution.get(current_hour, 20)

        # Get alerts sent this hour
        recent_alerts = [a for a in self.alert_history
                        if a['hour'] == current_hour and
                        a['date'] == datetime.now().date()]
        alerts_this_hour = len(recent_alerts)

        # Calculate remaining quota
        remaining_quota = hourly_quota - alerts_this_hour

        if remaining_quota <= 0:
            return False, 100  # No quota left

        # Calculate dynamic threshold based on remaining time and quota
        minutes_remaining = 60 - datetime.now().minute
        alerts_per_minute_needed = remaining_quota / max(1, minutes_remaining)

        # Adjust threshold based on urgency
        if alerts_per_minute_needed > 1:
            # Need to send more alerts, lower threshold
            base_threshold = 50
        elif alerts_per_minute_needed > 0.5:
            base_threshold = 60
        else:
            # Can be selective
            base_threshold = 70

        # Adjust for chain quota
        chain_alerts = [a for a in recent_alerts if a['chain'] == chain]
        chain_quota = int(hourly_quota * self.chain_quotas[chain])
        chain_remaining = chain_quota - len(chain_alerts)

        if chain_remaining <= 0:
            # Chain quota exhausted, need higher score
            threshold = base_threshold + 20
        else:
            threshold = base_threshold

        # Check if score meets threshold
        should_send = score >= threshold

        if should_send:
            # Record alert
            self.alert_history.append({
                'timestamp': datetime.now(),
                'date': datetime.now().date(),
                'hour': current_hour,
                'chain': chain,
                'score': score
            })
            self.alerts_sent_today += 1

        return should_send, threshold

    def get_status(self) -> Dict:
        """Get current distribution status"""
        current_hour = datetime.now().hour
        today_alerts = [a for a in self.alert_history
                       if a['date'] == datetime.now().date()]

        hourly_breakdown = {}
        for hour in range(24):
            hour_alerts = [a for a in today_alerts if a['hour'] == hour]
            hourly_breakdown[hour] = {
                'sent': len(hour_alerts),
                'quota': self.hourly_distribution[hour]
            }

        chain_breakdown = {}
        for chain in Chain:
            chain_alerts = [a for a in today_alerts if a['chain'] == chain]
            expected = int(self.daily_limit * self.chain_quotas[chain])
            chain_breakdown[chain.value] = {
                'sent': len(chain_alerts),
                'expected': expected,
                'percentage': (len(chain_alerts) / expected * 100) if expected > 0 else 0
            }

        return {
            'total_sent_today': len(today_alerts),
            'daily_limit': self.daily_limit,
            'current_hour_quota': self.hourly_distribution[current_hour],
            'current_hour_sent': hourly_breakdown[current_hour]['sent'],
            'hourly_breakdown': hourly_breakdown,
            'chain_breakdown': chain_breakdown
        }


class ConfidenceCalculator:
    """Calculate confidence scores for alerts"""

    @staticmethod
    def calculate_confidence(score: float, component_scores: Dict[str, float],
                           ml_probability: float) -> Dict:
        """
        Calculate multi-dimensional confidence metrics
        """
        # Base confidence from score
        if score >= 80:
            base_confidence = "HIGH"
            confidence_value = 0.85
        elif score >= 65:
            base_confidence = "MEDIUM"
            confidence_value = 0.65
        elif score >= 50:
            base_confidence = "LOW"
            confidence_value = 0.45
        else:
            base_confidence = "VERY_LOW"
            confidence_value = 0.25

        # Adjust based on ML prediction
        ml_adjusted = confidence_value * 0.7 + ml_probability * 0.3

        # Calculate confidence factors
        factors = {
            'score_confidence': confidence_value,
            'ml_confidence': ml_probability,
            'combined_confidence': ml_adjusted,
            'confidence_level': base_confidence
        }

        # Identify weak points
        weak_points = []
        for component, comp_score in component_scores.items():
            if comp_score < 40:
                weak_points.append(component)

        factors['weak_points'] = weak_points
        factors['strong_points'] = [k for k, v in component_scores.items() if v >= 70]

        # Risk assessment
        if 'security' in weak_points:
            factors['risk_level'] = RiskLevel.HIGH
        elif len(weak_points) >= 3:
            factors['risk_level'] = RiskLevel.MEDIUM
        else:
            factors['risk_level'] = RiskLevel.LOW

        # Success prediction
        factors['predicted_2x_probability'] = ml_adjusted
        factors['predicted_timeframe'] = ConfidenceCalculator._estimate_timeframe(ml_adjusted)

        return factors

    @staticmethod
    def _estimate_timeframe(confidence: float) -> str:
        """Estimate timeframe for 2x based on confidence"""
        if confidence >= 0.7:
            return "4-8 hours"
        elif confidence >= 0.5:
            return "8-16 hours"
        elif confidence >= 0.3:
            return "16-24 hours"
        else:
            return "24+ hours"


def save_model(scorer: TokenScorer, optimizer: MLScoreOptimizer, filepath: str):
    """Save model and weights to file"""
    model_data = {
        'weights': scorer.weights,
        'feature_importance': scorer.feature_importance,
        'ml_model': optimizer.model,
        'training_data': optimizer.training_data
    }

    with open(filepath, 'wb') as f:
        pickle.dump(model_data, f)

    logger.info(f"Model saved to {filepath}")


def load_model(filepath: str) -> Tuple[TokenScorer, MLScoreOptimizer]:
    """Load model and weights from file"""
    with open(filepath, 'rb') as f:
        model_data = pickle.load(f)

    scorer = TokenScorer(weights=model_data['weights'])
    scorer.feature_importance = model_data['feature_importance']

    optimizer = MLScoreOptimizer()
    optimizer.model = model_data['ml_model']
    optimizer.training_data = model_data['training_data']

    logger.info(f"Model loaded from {filepath}")
    return scorer, optimizer