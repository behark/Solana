"""
Example Scoring Scenarios for Multi-Chain Memecoin Alert System
Demonstrates different token profiles and their scoring outcomes
"""

from datetime import datetime, timedelta
from alert_scoring_system import (
    TokenMetrics, TokenScorer, MLScoreOptimizer,
    AlertDistributionManager, ConfidenceCalculator,
    Chain, RiskLevel
)


class ScoringExamples:
    """Example scenarios demonstrating the scoring system"""

    def __init__(self):
        self.scorer = TokenScorer()
        self.ml_optimizer = MLScoreOptimizer()
        self.alert_manager = AlertDistributionManager()
        self.confidence_calc = ConfidenceCalculator()

    def example_1_high_potential_token(self):
        """Example: High-scoring token likely to 2x+"""
        token = TokenMetrics(
            chain=Chain.SOLANA,
            address="So11111111111111111111111111111111",
            name="MoonShot",
            symbol="MOON",
            launch_time=datetime.now() - timedelta(hours=2),

            # Strong liquidity metrics
            initial_liquidity=150000,
            liquidity_locked=True,
            liquidity_lock_duration=365,
            liquidity_to_mcap_ratio=0.20,
            liquidity_providers_count=150,

            # Excellent holder distribution
            total_holders=2500,
            top_10_holders_percentage=18,
            top_holder_percentage=3.5,
            unique_buyers_first_hour=650,
            holder_growth_rate=125,
            whale_concentration=0.25,

            # Perfect security
            contract_verified=True,
            honeypot_check=False,
            mint_disabled=True,
            max_tx_percentage=3,
            tax_percentage=3,
            ownership_renounced=True,
            audit_score=95,

            # Strong social signals
            telegram_members=8000,
            twitter_followers=5000,
            twitter_engagement_rate=6.5,
            social_growth_rate=25,
            influencer_mentions=8,
            sentiment_score=0.85,

            # Good volume patterns
            volume_1h=180000,
            volume_24h=0,  # New token
            buy_sell_ratio=1.8,
            average_trade_size=500,
            trades_per_minute=15,
            price_volatility=0.12,

            # Active development
            github_commits=75,
            code_updates_24h=6,
            developer_wallet_history=5,
            team_doxxed=True,

            # Growing community
            discord_members=3000,
            reddit_subscribers=1500,
            community_engagement_score=85,

            # No risk factors
            similar_name_tokens=0,
            rug_pull_indicators=[],
            chain_specific_risks={}
        )

        score, components = self.scorer.calculate_score(token)
        ml_prob = self.ml_optimizer.predict_success_probability(score)
        confidence = self.confidence_calc.calculate_confidence(score, components, ml_prob)

        return {
            "scenario": "High Potential Token",
            "total_score": score,
            "component_scores": components,
            "ml_success_probability": ml_prob,
            "confidence": confidence,
            "expected_outcome": "85% chance of 2x+ within 4-8 hours",
            "alert_priority": "IMMEDIATE",
            "recommended_action": "Strong Buy Signal"
        }

    def example_2_medium_potential_token(self):
        """Example: Medium-scoring token with mixed signals"""
        token = TokenMetrics(
            chain=Chain.BNB,
            address="0x123456789abcdef",
            name="SafeMoon2",
            symbol="SAFE2",
            launch_time=datetime.now() - timedelta(hours=6),

            # Moderate liquidity
            initial_liquidity=40000,
            liquidity_locked=True,
            liquidity_lock_duration=90,
            liquidity_to_mcap_ratio=0.08,
            liquidity_providers_count=45,

            # Decent holder distribution
            total_holders=800,
            top_10_holders_percentage=35,
            top_holder_percentage=8,
            unique_buyers_first_hour=200,
            holder_growth_rate=40,
            whale_concentration=0.45,

            # Good security with minor concerns
            contract_verified=True,
            honeypot_check=False,
            mint_disabled=False,  # Concern
            max_tx_percentage=2,
            tax_percentage=8,  # Slightly high
            ownership_renounced=False,  # Concern
            audit_score=70,

            # Moderate social presence
            telegram_members=2500,
            twitter_followers=1500,
            twitter_engagement_rate=3.0,
            social_growth_rate=10,
            influencer_mentions=2,
            sentiment_score=0.4,

            # Average volume
            volume_1h=35000,
            volume_24h=0,
            buy_sell_ratio=1.15,
            average_trade_size=250,
            trades_per_minute=5,
            price_volatility=0.18,

            # Limited development
            github_commits=15,
            code_updates_24h=1,
            developer_wallet_history=1,
            team_doxxed=False,

            # Small community
            discord_members=500,
            reddit_subscribers=200,
            community_engagement_score=50,

            # Some concerns
            similar_name_tokens=3,  # Copycats exist
            rug_pull_indicators=["mint_not_disabled"],
            chain_specific_risks={"bsc_scan_warnings": 1}
        )

        score, components = self.scorer.calculate_score(token)
        ml_prob = self.ml_optimizer.predict_success_probability(score)
        confidence = self.confidence_calc.calculate_confidence(score, components, ml_prob)

        return {
            "scenario": "Medium Potential Token",
            "total_score": score,
            "component_scores": components,
            "ml_success_probability": ml_prob,
            "confidence": confidence,
            "expected_outcome": "45% chance of 2x within 16-24 hours",
            "alert_priority": "STANDARD",
            "recommended_action": "Cautious Entry - Small Position"
        }

    def example_3_high_risk_token(self):
        """Example: Low-scoring token with red flags"""
        token = TokenMetrics(
            chain=Chain.ETHEREUM,
            address="0xdeadbeef",
            name="QuickPump",
            symbol="PUMP",
            launch_time=datetime.now() - timedelta(hours=1),

            # Poor liquidity
            initial_liquidity=5000,
            liquidity_locked=False,  # Red flag
            liquidity_lock_duration=0,
            liquidity_to_mcap_ratio=0.02,  # Very low
            liquidity_providers_count=5,  # Centralized

            # Terrible distribution
            total_holders=150,
            top_10_holders_percentage=75,  # Heavy concentration
            top_holder_percentage=35,  # Single whale
            unique_buyers_first_hour=30,
            holder_growth_rate=8,
            whale_concentration=0.85,  # Extreme concentration

            # Security issues
            contract_verified=False,  # Red flag
            honeypot_check=True,  # HONEYPOT!
            mint_disabled=False,
            max_tx_percentage=0.5,  # Very restrictive
            tax_percentage=25,  # Excessive tax
            ownership_renounced=False,
            audit_score=None,

            # No social presence
            telegram_members=200,
            twitter_followers=100,
            twitter_engagement_rate=0.5,
            social_growth_rate=2,
            influencer_mentions=0,
            sentiment_score=-0.3,  # Negative sentiment

            # Suspicious volume
            volume_1h=8000,
            volume_24h=0,
            buy_sell_ratio=0.6,  # More sells than buys
            average_trade_size=50,
            trades_per_minute=1,
            price_volatility=0.45,  # Extreme volatility

            # No development
            github_commits=0,
            code_updates_24h=0,
            developer_wallet_history=0,
            team_doxxed=False,

            # No community
            discord_members=0,
            reddit_subscribers=0,
            community_engagement_score=5,

            # Multiple red flags
            similar_name_tokens=15,  # Many copycats
            rug_pull_indicators=[
                "honeypot_detected",
                "liquidity_not_locked",
                "contract_not_verified",
                "excessive_taxes",
                "whale_concentration"
            ],
            chain_specific_risks={
                "etherscan_warnings": 3,
                "tokensniffer_score": 15
            }
        )

        score, components = self.scorer.calculate_score(token)
        ml_prob = self.ml_optimizer.predict_success_probability(score)
        confidence = self.confidence_calc.calculate_confidence(score, components, ml_prob)

        return {
            "scenario": "High Risk Token (Likely Scam)",
            "total_score": score,
            "component_scores": components,
            "ml_success_probability": ml_prob,
            "confidence": confidence,
            "expected_outcome": "5% chance of success, 95% chance of rug pull",
            "alert_priority": "DO NOT ALERT",
            "recommended_action": "AVOID - Multiple Red Flags"
        }

    def example_4_stealth_launch(self):
        """Example: Stealth launch with limited data"""
        token = TokenMetrics(
            chain=Chain.BASE,
            address="0xstealth",
            name="StealthGem",
            symbol="STEALTH",
            launch_time=datetime.now() - timedelta(minutes=30),

            # Quick launch metrics
            initial_liquidity=25000,
            liquidity_locked=True,
            liquidity_lock_duration=30,  # Short lock
            liquidity_to_mcap_ratio=0.15,
            liquidity_providers_count=25,

            # Rapid early growth
            total_holders=450,
            top_10_holders_percentage=40,
            top_holder_percentage=10,
            unique_buyers_first_hour=450,  # All in first hour
            holder_growth_rate=450,  # Explosive growth
            whale_concentration=0.4,

            # Basic security
            contract_verified=True,
            honeypot_check=False,
            mint_disabled=True,
            max_tx_percentage=5,
            tax_percentage=5,
            ownership_renounced=True,
            audit_score=None,  # No time for audit

            # No social yet (stealth)
            telegram_members=0,
            twitter_followers=0,
            twitter_engagement_rate=0,
            social_growth_rate=0,
            influencer_mentions=0,
            sentiment_score=0,

            # High early volume
            volume_1h=75000,
            volume_24h=0,
            buy_sell_ratio=3.5,  # Heavy buying
            average_trade_size=150,
            trades_per_minute=20,  # Very active
            price_volatility=0.25,

            # Unknown developer
            github_commits=0,
            code_updates_24h=0,
            developer_wallet_history=0,
            team_doxxed=False,

            # No community yet
            discord_members=0,
            reddit_subscribers=0,
            community_engagement_score=0,

            # Stealth specific
            similar_name_tokens=0,
            rug_pull_indicators=[],
            chain_specific_risks={"stealth_launch": True}
        )

        score, components = self.scorer.calculate_score(token)
        ml_prob = self.ml_optimizer.predict_success_probability(score)
        confidence = self.confidence_calc.calculate_confidence(score, components, ml_prob)

        return {
            "scenario": "Stealth Launch",
            "total_score": score,
            "component_scores": components,
            "ml_success_probability": ml_prob,
            "confidence": confidence,
            "expected_outcome": "High risk, high reward - 50% chance of 5x, 50% chance of dump",
            "alert_priority": "SPECULATIVE",
            "recommended_action": "High Risk Entry - Very Small Position"
        }

    def example_5_influencer_backed(self):
        """Example: Influencer-promoted token"""
        token = TokenMetrics(
            chain=Chain.SOLANA,
            address="0xinfluencer",
            name="InfluencerCoin",
            symbol="INFL",
            launch_time=datetime.now() - timedelta(hours=4),

            # Good liquidity from presale
            initial_liquidity=80000,
            liquidity_locked=True,
            liquidity_lock_duration=180,
            liquidity_to_mcap_ratio=0.10,
            liquidity_providers_count=200,

            # Mixed distribution (influencer holds large bag)
            total_holders=3000,
            top_10_holders_percentage=45,  # Influencer + team
            top_holder_percentage=15,  # Influencer wallet
            unique_buyers_first_hour=800,
            holder_growth_rate=75,
            whale_concentration=0.55,

            # Standard security
            contract_verified=True,
            honeypot_check=False,
            mint_disabled=True,
            max_tx_percentage=2,
            tax_percentage=5,
            ownership_renounced=False,  # Team controls
            audit_score=80,

            # Strong social (influencer effect)
            telegram_members=15000,  # Influencer's community
            twitter_followers=25000,  # Boosted by influencer
            twitter_engagement_rate=8.0,  # High engagement
            social_growth_rate=30,  # Rapid growth
            influencer_mentions=15,  # Multiple influencers
            sentiment_score=0.7,  # Positive hype

            # High volume from followers
            volume_1h=250000,
            volume_24h=0,
            buy_sell_ratio=1.4,
            average_trade_size=800,  # Larger trades
            trades_per_minute=12,
            price_volatility=0.22,

            # Unknown development
            github_commits=5,
            code_updates_24h=0,
            developer_wallet_history=2,
            team_doxxed=False,

            # Large but shallow community
            discord_members=5000,
            reddit_subscribers=2000,
            community_engagement_score=40,  # Low engagement

            # Influencer risks
            similar_name_tokens=5,
            rug_pull_indicators=["influencer_heavy"],
            chain_specific_risks={"pump_risk": "high"}
        )

        score, components = self.scorer.calculate_score(token)
        ml_prob = self.ml_optimizer.predict_success_probability(score)
        confidence = self.confidence_calc.calculate_confidence(score, components, ml_prob)

        return {
            "scenario": "Influencer-Backed Token",
            "total_score": score,
            "component_scores": components,
            "ml_success_probability": ml_prob,
            "confidence": confidence,
            "expected_outcome": "70% chance of initial pump to 3x, high dump risk after",
            "alert_priority": "TIME-SENSITIVE",
            "recommended_action": "Quick Entry/Exit - Take Profits Early"
        }

    def run_all_examples(self):
        """Run all example scenarios"""
        examples = [
            self.example_1_high_potential_token(),
            self.example_2_medium_potential_token(),
            self.example_3_high_risk_token(),
            self.example_4_stealth_launch(),
            self.example_5_influencer_backed()
        ]

        print("\n" + "="*80)
        print("MULTI-CHAIN MEMECOIN SCORING EXAMPLES")
        print("="*80)

        for i, example in enumerate(examples, 1):
            print(f"\n{'='*80}")
            print(f"EXAMPLE {i}: {example['scenario']}")
            print(f"{'='*80}")

            print(f"\nTotal Score: {example['total_score']:.2f}/100")
            print(f"ML Success Probability: {example['ml_success_probability']:.2%}")
            print(f"Alert Priority: {example['alert_priority']}")

            print("\nComponent Scores:")
            for component, score in example['component_scores'].items():
                print(f"  - {component.capitalize()}: {score:.2f}/100")

            print("\nConfidence Analysis:")
            confidence = example['confidence']
            print(f"  - Confidence Level: {confidence['confidence_level']}")
            print(f"  - Combined Confidence: {confidence['combined_confidence']:.2%}")
            print(f"  - Risk Level: {confidence['risk_level'].value}")
            print(f"  - Predicted Timeframe: {confidence['predicted_timeframe']}")

            if confidence['weak_points']:
                print(f"  - Weak Points: {', '.join(confidence['weak_points'])}")
            if confidence['strong_points']:
                print(f"  - Strong Points: {', '.join(confidence['strong_points'])}")

            print(f"\nExpected Outcome: {example['expected_outcome']}")
            print(f"Recommended Action: {example['recommended_action']}")

            # Check if alert would be sent
            current_hour = datetime.now().hour
            should_send, threshold = self.alert_manager.should_send_alert(
                example['total_score'],
                Chain.SOLANA,
                current_hour
            )
            print(f"\nAlert Decision: {'SEND' if should_send else 'SKIP'} (threshold: {threshold:.1f})")

        # Show alert distribution status
        print(f"\n{'='*80}")
        print("ALERT DISTRIBUTION STATUS")
        print(f"{'='*80}")

        status = self.alert_manager.get_status()
        print(f"\nToday's Progress: {status['total_sent_today']}/{status['daily_limit']} alerts sent")
        print(f"Current Hour: {status['current_hour_sent']}/{status['current_hour_quota']} alerts")

        print("\nChain Distribution:")
        for chain, stats in status['chain_breakdown'].items():
            print(f"  - {chain}: {stats['sent']}/{stats['expected']} ({stats['percentage']:.1f}%)")


def demonstrate_ml_improvement():
    """Demonstrate ML-based continuous improvement"""
    print("\n" + "="*80)
    print("MACHINE LEARNING OPTIMIZATION DEMONSTRATION")
    print("="*80)

    optimizer = MLScoreOptimizer()
    scorer = TokenScorer()

    # Simulate collecting outcomes over time
    print("\nSimulating 30 days of trading data...")

    for day in range(30):
        # Simulate 20-50 tokens per day
        num_tokens = np.random.randint(20, 50)

        for _ in range(num_tokens):
            # Random initial score
            score = np.random.uniform(30, 90)

            # Simulate outcome based on score (higher score = better outcome)
            base_probability = score / 100
            noise = np.random.uniform(-0.2, 0.2)
            success_probability = np.clip(base_probability + noise, 0, 1)

            # Determine outcome (2x or not)
            outcome = 2.5 if np.random.random() < success_probability else 0.7

            # Collect outcome
            optimizer.collect_outcome(
                token_address=f"0x{day:02d}{_:04d}",
                initial_score=score,
                outcome=outcome,
                timestamp=datetime.now() - timedelta(days=30-day)
            )

    print(f"Collected {len(optimizer.training_data)} token outcomes")

    # Train initial model
    print("\nTraining initial ML model...")
    accuracy = optimizer.train_model()

    # Show weight adjustments
    print("\nAdjusting scoring weights based on ML insights...")
    original_weights = scorer.weights
    adjusted_weights = optimizer.adjust_weights(original_weights)

    print("\nWeight Adjustments:")
    for field in ['liquidity', 'holders', 'security', 'social', 'volume']:
        original = getattr(original_weights, field)
        adjusted = getattr(adjusted_weights, field)
        change = ((adjusted - original) / original) * 100
        print(f"  - {field.capitalize()}: {original:.2%} → {adjusted:.2%} ({change:+.1f}%)")

    # Demonstrate predictions
    print("\nSuccess Probability Predictions:")
    test_scores = [30, 45, 60, 75, 90]
    for score in test_scores:
        probability = optimizer.predict_success_probability(score)
        print(f"  - Score {score}: {probability:.2%} chance of 2x+")


if __name__ == "__main__":
    # Run examples
    examples = ScoringExamples()
    examples.run_all_examples()

    # Demonstrate ML improvement
    demonstrate_ml_improvement()