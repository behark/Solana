use crate::processor::telegram_alerts::TelegramAlertSystem;
use crate::processor::transaction_parser::{ParsedData, SwapType};
use crate::common::config::Config;
use anyhow::Result;
use solana_sdk::pubkey::Pubkey;
use std::sync::Arc;
use tokio::sync::RwLock;
use std::collections::HashMap;
use chrono::Utc;

/// Educational monitoring system that tracks tokens without trading
/// This replaces the trading functionality with alert-only monitoring
pub struct EducationalMonitor {
    config: Config,
    telegram: Option<Arc<TelegramAlertSystem>>,
    tracked_tokens: Arc<RwLock<HashMap<Pubkey, TokenMetrics>>>,
    tracked_wallets: Arc<RwLock<HashMap<Pubkey, WalletMetrics>>>,
}

#[derive(Clone, Debug)]
pub struct TokenMetrics {
    pub address: Pubkey,
    pub name: Option<String>,
    pub symbol: Option<String>,
    pub initial_price: Option<f64>,
    pub current_price: Option<f64>,
    pub volume_24h: f64,
    pub liquidity: f64,
    pub holder_count: usize,
    pub first_seen: chrono::DateTime<Utc>,
    pub last_updated: chrono::DateTime<Utc>,
    pub buy_count: u32,
    pub sell_count: u32,
    pub largest_buy_sol: f64,
    pub largest_sell_sol: f64,
}

#[derive(Clone, Debug)]
pub struct WalletMetrics {
    pub address: Pubkey,
    pub total_buys: u32,
    pub total_sells: u32,
    pub tokens_traded: Vec<Pubkey>,
    pub total_volume_sol: f64,
    pub hypothetical_pnl: f64, // What PnL would have been if trades were made
    pub win_rate: f64,
    pub average_hold_time: u64,
}

impl EducationalMonitor {
    pub fn new(config: Config, telegram: Option<Arc<TelegramAlertSystem>>) -> Self {
        Self {
            config,
            telegram,
            tracked_tokens: Arc::new(RwLock::new(HashMap::new())),
            tracked_wallets: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Process parsed data for educational monitoring (no trading)
    pub async fn process_for_education(&self, parsed_data: &ParsedData) -> Result<()> {
        match parsed_data.swap_type {
            SwapType::Buy => {
                self.handle_buy_signal(parsed_data).await?;
            },
            SwapType::Sell => {
                self.handle_sell_signal(parsed_data).await?;
            },
            _ => {}
        }

        // Update metrics
        self.update_token_metrics(parsed_data).await?;
        self.update_wallet_metrics(parsed_data).await?;

        // Check for patterns
        self.detect_patterns(parsed_data).await?;

        Ok(())
    }

    /// Handle buy signals for educational purposes
    async fn handle_buy_signal(&self, parsed_data: &ParsedData) -> Result<()> {
        let token_address = parsed_data.token_mint;
        let wallet_address = parsed_data.signer;
        let amount_sol = parsed_data.sol_amount.unwrap_or(0.0);

        // Send Telegram alert if configured
        if let Some(telegram) = &self.telegram {
            telegram.alert_wallet_activity(
                &wallet_address,
                "BUY",
                &token_address,
                parsed_data.token_name.clone(),
                amount_sol,
                None,
            ).await?;

            // Check if this is a new token
            let tokens = self.tracked_tokens.read().await;
            if !tokens.contains_key(&token_address) {
                drop(tokens); // Release read lock

                telegram.alert_new_token(
                    &token_address,
                    parsed_data.token_name.clone(),
                    parsed_data.liquidity.unwrap_or(0.0),
                    &parsed_data.dex_name,
                ).await?;
            }
        }

        // Log the educational analysis
        self.log_educational_analysis(
            "BUY_SIGNAL",
            &format!(
                "Educational Analysis - Buy Signal Detected:\n\
                Token: {} ({})\n\
                Wallet: {}\n\
                Amount: {} SOL\n\
                DEX: {}\n\
                Analysis: This buy signal indicates potential interest in the token.\n\
                Educational Note: In real trading, factors to consider would include:\n\
                - Token liquidity and market cap\n\
                - Wallet's trading history\n\
                - Current market conditions\n\
                - Risk/reward ratio",
                parsed_data.token_name.as_ref().unwrap_or(&"Unknown".to_string()),
                token_address,
                wallet_address,
                amount_sol,
                parsed_data.dex_name
            )
        );

        Ok(())
    }

    /// Handle sell signals for educational purposes
    async fn handle_sell_signal(&self, parsed_data: &ParsedData) -> Result<()> {
        let token_address = parsed_data.token_mint;
        let wallet_address = parsed_data.signer;
        let amount_sol = parsed_data.sol_amount.unwrap_or(0.0);

        // Send Telegram alert if configured
        if let Some(telegram) = &self.telegram {
            telegram.alert_wallet_activity(
                &wallet_address,
                "SELL",
                &token_address,
                parsed_data.token_name.clone(),
                amount_sol,
                None,
            ).await?;
        }

        // Calculate hypothetical PnL for educational purposes
        let hypothetical_pnl = self.calculate_hypothetical_pnl(&token_address).await;

        self.log_educational_analysis(
            "SELL_SIGNAL",
            &format!(
                "Educational Analysis - Sell Signal Detected:\n\
                Token: {} ({})\n\
                Wallet: {}\n\
                Amount: {} SOL\n\
                Hypothetical PnL: {:.2}%\n\
                Analysis: This sell signal could indicate:\n\
                - Profit taking\n\
                - Stop loss execution\n\
                - Risk management\n\
                - Change in market sentiment",
                parsed_data.token_name.as_ref().unwrap_or(&"Unknown".to_string()),
                token_address,
                wallet_address,
                amount_sol,
                hypothetical_pnl
            )
        );

        Ok(())
    }

    /// Update token metrics for educational tracking
    async fn update_token_metrics(&self, parsed_data: &ParsedData) -> Result<()> {
        let mut tokens = self.tracked_tokens.write().await;
        let token_address = parsed_data.token_mint;

        let metrics = tokens.entry(token_address).or_insert_with(|| {
            TokenMetrics {
                address: token_address,
                name: parsed_data.token_name.clone(),
                symbol: parsed_data.token_symbol.clone(),
                initial_price: parsed_data.token_price,
                current_price: parsed_data.token_price,
                volume_24h: 0.0,
                liquidity: parsed_data.liquidity.unwrap_or(0.0),
                holder_count: 0,
                first_seen: Utc::now(),
                last_updated: Utc::now(),
                buy_count: 0,
                sell_count: 0,
                largest_buy_sol: 0.0,
                largest_sell_sol: 0.0,
            }
        });

        // Update metrics based on swap type
        match parsed_data.swap_type {
            SwapType::Buy => {
                metrics.buy_count += 1;
                let amount_sol = parsed_data.sol_amount.unwrap_or(0.0);
                if amount_sol > metrics.largest_buy_sol {
                    metrics.largest_buy_sol = amount_sol;
                }
                metrics.volume_24h += amount_sol;
            },
            SwapType::Sell => {
                metrics.sell_count += 1;
                let amount_sol = parsed_data.sol_amount.unwrap_or(0.0);
                if amount_sol > metrics.largest_sell_sol {
                    metrics.largest_sell_sol = amount_sol;
                }
                metrics.volume_24h += amount_sol;
            },
            _ => {}
        }

        metrics.current_price = parsed_data.token_price;
        metrics.liquidity = parsed_data.liquidity.unwrap_or(metrics.liquidity);
        metrics.last_updated = Utc::now();

        // Check for significant price movement
        if let (Some(initial), Some(current)) = (metrics.initial_price, metrics.current_price) {
            let change_pct = ((current - initial) / initial) * 100.0;

            if change_pct.abs() > 20.0 {
                if let Some(telegram) = &self.telegram {
                    telegram.alert_price_movement(
                        &token_address,
                        metrics.name.clone(),
                        initial,
                        current,
                        Some(metrics.volume_24h),
                    ).await?;
                }
            }
        }

        Ok(())
    }

    /// Update wallet metrics for educational tracking
    async fn update_wallet_metrics(&self, parsed_data: &ParsedData) -> Result<()> {
        let mut wallets = self.tracked_wallets.write().await;
        let wallet_address = parsed_data.signer;

        let metrics = wallets.entry(wallet_address).or_insert_with(|| {
            WalletMetrics {
                address: wallet_address,
                total_buys: 0,
                total_sells: 0,
                tokens_traded: Vec::new(),
                total_volume_sol: 0.0,
                hypothetical_pnl: 0.0,
                win_rate: 0.0,
                average_hold_time: 0,
            }
        });

        // Update metrics
        match parsed_data.swap_type {
            SwapType::Buy => metrics.total_buys += 1,
            SwapType::Sell => metrics.total_sells += 1,
            _ => {}
        }

        if !metrics.tokens_traded.contains(&parsed_data.token_mint) {
            metrics.tokens_traded.push(parsed_data.token_mint);
        }

        metrics.total_volume_sol += parsed_data.sol_amount.unwrap_or(0.0);

        Ok(())
    }

    /// Detect patterns for educational purposes
    async fn detect_patterns(&self, parsed_data: &ParsedData) -> Result<()> {
        let tokens = self.tracked_tokens.read().await;

        if let Some(metrics) = tokens.get(&parsed_data.token_mint) {
            // Pattern 1: High buy/sell ratio
            if metrics.buy_count > 0 && metrics.sell_count > 0 {
                let ratio = metrics.buy_count as f64 / metrics.sell_count as f64;
                if ratio > 3.0 {
                    if let Some(telegram) = &self.telegram {
                        telegram.alert_sniper_opportunity(
                            &parsed_data.token_mint,
                            metrics.name.clone(),
                            "High Buy Pressure",
                            &format!("Buy/Sell Ratio: {:.2}:1 - Strong buying interest detected", ratio),
                        ).await?;
                    }
                }
            }

            // Pattern 2: Volume spike
            if parsed_data.sol_amount.unwrap_or(0.0) > 10.0 {
                if let Some(telegram) = &self.telegram {
                    telegram.alert_sniper_opportunity(
                        &parsed_data.token_mint,
                        metrics.name.clone(),
                        "Large Transaction",
                        &format!("Transaction size: {} SOL - Whale activity detected",
                            parsed_data.sol_amount.unwrap_or(0.0)),
                    ).await?;
                }
            }

            // Pattern 3: Recovery after dip
            if let (Some(initial), Some(current)) = (metrics.initial_price, metrics.current_price) {
                let drop_pct = ((initial - current) / initial) * 100.0;
                if drop_pct > 30.0 && metrics.buy_count > metrics.sell_count {
                    if let Some(telegram) = &self.telegram {
                        telegram.alert_sniper_opportunity(
                            &parsed_data.token_mint,
                            metrics.name.clone(),
                            "Potential Recovery",
                            &format!("Token down {:.1}% but buying pressure increasing", drop_pct),
                        ).await?;
                    }
                }
            }
        }

        Ok(())
    }

    /// Calculate hypothetical PnL for educational purposes
    async fn calculate_hypothetical_pnl(&self, token_address: &Pubkey) -> f64 {
        let tokens = self.tracked_tokens.read().await;

        if let Some(metrics) = tokens.get(token_address) {
            if let (Some(initial), Some(current)) = (metrics.initial_price, metrics.current_price) {
                return ((current - initial) / initial) * 100.0;
            }
        }

        0.0
    }

    /// Log educational analysis
    fn log_educational_analysis(&self, analysis_type: &str, message: &str) {
        println!("\n{'='*60}");
        println!("📚 EDUCATIONAL ANALYSIS - {}", analysis_type);
        println!("{'='*60}");
        println!("{}", message);
        println!("{'='*60}\n");
    }

    /// Generate educational report
    pub async fn generate_educational_report(&self) -> Result<String> {
        let tokens = self.tracked_tokens.read().await;
        let wallets = self.tracked_wallets.read().await;

        let mut report = String::new();
        report.push_str("\n📊 EDUCATIONAL MONITORING REPORT\n");
        report.push_str("=====================================\n\n");

        // Token statistics
        report.push_str(&format!("📈 Tokens Monitored: {}\n", tokens.len()));

        let total_volume: f64 = tokens.values().map(|t| t.volume_24h).sum();
        report.push_str(&format!("💰 Total Volume: {:.2} SOL\n", total_volume));

        // Top movers
        let mut top_gainers: Vec<_> = tokens.values()
            .filter_map(|t| {
                if let (Some(initial), Some(current)) = (t.initial_price, t.current_price) {
                    let gain = ((current - initial) / initial) * 100.0;
                    Some((t.name.clone().unwrap_or_default(), gain))
                } else {
                    None
                }
            })
            .collect();

        top_gainers.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        report.push_str("\n🚀 Top Gainers:\n");
        for (name, gain) in top_gainers.iter().take(5) {
            report.push_str(&format!("  • {}: +{:.2}%\n", name, gain));
        }

        // Wallet statistics
        report.push_str(&format!("\n👥 Wallets Tracked: {}\n", wallets.len()));

        // Most active wallets
        let mut active_wallets: Vec<_> = wallets.values()
            .map(|w| (w.address.to_string(), w.total_buys + w.total_sells))
            .collect();

        active_wallets.sort_by(|a, b| b.1.cmp(&a.1));

        report.push_str("\n🏃 Most Active Wallets:\n");
        for (addr, trades) in active_wallets.iter().take(3) {
            report.push_str(&format!("  • {}...: {} trades\n", &addr[..8], trades));
        }

        report.push_str("\n📚 Educational Insights:\n");
        report.push_str("• High-activity wallets may be bots or experienced traders\n");
        report.push_str("• Volume spikes often precede price movements\n");
        report.push_str("• Buy/sell ratios indicate market sentiment\n");
        report.push_str("• Always verify patterns with multiple indicators\n");

        report.push_str("\n⚠️ Remember: This is for educational purposes only!\n");
        report.push_str("Real trading involves significant financial risk.\n");

        // Send report via Telegram if configured
        if let Some(telegram) = &self.telegram {
            telegram.send_custom_alert("Daily Educational Report", &report).await?;
        }

        Ok(report)
    }
}