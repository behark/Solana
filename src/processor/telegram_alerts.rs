use anyhow::Result;
use chrono::{DateTime, Utc};
use solana_sdk::pubkey::Pubkey;
use std::sync::Arc;
use teloxide::{prelude::*, Bot};
use tokio::sync::RwLock;

/// Educational Alert System for monitoring Solana tokens
/// This module sends Telegram notifications for educational purposes only
/// No actual trading is performed
pub struct TelegramAlertSystem {
    bot: Bot,
    chat_id: ChatId,
    enabled: bool,
    alert_settings: AlertSettings,
    rate_limiter: Arc<RwLock<RateLimiter>>,
}

#[derive(Clone, Debug)]
pub struct AlertSettings {
    /// Alert when new tokens are detected
    pub alert_new_tokens: bool,
    /// Alert on target wallet activity
    pub alert_wallet_activity: bool,
    /// Alert on price movements
    pub alert_price_movements: bool,
    /// Minimum price change percentage to trigger alert
    pub price_change_threshold: f64,
    /// Alert on volume spikes
    pub alert_volume_spikes: bool,
    /// Minimum volume multiplier to trigger alert
    pub volume_spike_threshold: f64,
    /// Alert on potential sniper opportunities (educational)
    pub alert_sniper_opportunities: bool,
    /// Include risk warnings in alerts
    pub include_risk_warnings: bool,
}

impl Default for AlertSettings {
    fn default() -> Self {
        Self {
            alert_new_tokens: true,
            alert_wallet_activity: true,
            alert_price_movements: true,
            price_change_threshold: 10.0, // 10% price change
            alert_volume_spikes: true,
            volume_spike_threshold: 3.0, // 3x normal volume
            alert_sniper_opportunities: true,
            include_risk_warnings: true,
        }
    }
}

/// Rate limiter to prevent spam
struct RateLimiter {
    last_alert_times: std::collections::HashMap<String, DateTime<Utc>>,
    min_interval_seconds: i64,
}

impl RateLimiter {
    fn new(min_interval_seconds: i64) -> Self {
        Self {
            last_alert_times: std::collections::HashMap::new(),
            min_interval_seconds,
        }
    }

    fn can_send(&mut self, key: &str) -> bool {
        let now = Utc::now();
        if let Some(last_time) = self.last_alert_times.get(key) {
            if now.timestamp() - last_time.timestamp() < self.min_interval_seconds {
                return false;
            }
        }
        self.last_alert_times.insert(key.to_string(), now);
        true
    }
}

impl TelegramAlertSystem {
    /// Create a new Telegram alert system for educational monitoring
    pub fn new(bot_token: String, chat_id: i64, enabled: bool) -> Result<Self> {
        let bot = Bot::new(bot_token);
        let chat_id = ChatId(chat_id);

        Ok(Self {
            bot,
            chat_id,
            enabled,
            alert_settings: AlertSettings::default(),
            rate_limiter: Arc::new(RwLock::new(RateLimiter::new(30))), // 30 seconds between similar alerts
        })
    }

    /// Configure alert settings
    pub fn configure(&mut self, settings: AlertSettings) {
        self.alert_settings = settings;
    }

    /// Alert on new token detection (educational purposes only)
    pub async fn alert_new_token(&self,
        token_address: &Pubkey,
        token_name: Option<String>,
        initial_liquidity: f64,
        dex: &str,
    ) -> Result<()> {
        if !self.enabled || !self.alert_settings.alert_new_tokens {
            return Ok(());
        }

        let mut rate_limiter = self.rate_limiter.write().await;
        if !rate_limiter.can_send(&format!("new_token_{}", token_address)) {
            return Ok(());
        }

        let message = format!(
            "🚀 **NEW TOKEN DETECTED** (Educational Alert)\n\n\
            📍 **Token**: {}\n\
            📝 **Name**: {}\n\
            💰 **Initial Liquidity**: {} SOL\n\
            🏪 **DEX**: {}\n\
            🔗 **Address**: `{}`\n\n\
            {}",
            token_name.as_ref().unwrap_or(&"Unknown".to_string()),
            token_name.unwrap_or("Unknown".to_string()),
            initial_liquidity,
            dex,
            token_address,
            self.get_risk_warning()
        );

        self.send_message(&message).await
    }

    /// Alert on target wallet activity (educational purposes only)
    pub async fn alert_wallet_activity(&self,
        wallet_address: &Pubkey,
        action: &str, // "BUY" or "SELL"
        token_address: &Pubkey,
        token_name: Option<String>,
        amount_sol: f64,
        price: Option<f64>,
    ) -> Result<()> {
        if !self.enabled || !self.alert_settings.alert_wallet_activity {
            return Ok(());
        }

        let mut rate_limiter = self.rate_limiter.write().await;
        let key = format!("wallet_{}_{}", wallet_address, token_address);
        if !rate_limiter.can_send(&key) {
            return Ok(());
        }

        let action_emoji = if action == "BUY" { "💚" } else { "💔" };
        let message = format!(
            "{} **WALLET ACTIVITY** (Educational Alert)\n\n\
            👤 **Wallet**: `{}`\n\
            📊 **Action**: {}\n\
            🪙 **Token**: {}\n\
            💵 **Amount**: {} SOL\n\
            {}\
            🔗 **Token Address**: `{}`\n\n\
            {}",
            action_emoji,
            &wallet_address.to_string()[..8],
            action,
            token_name.unwrap_or("Unknown".to_string()),
            amount_sol,
            price.map(|p| format!("💱 **Price**: ${:.6}\n", p)).unwrap_or_default(),
            token_address,
            self.get_educational_note(action)
        );

        self.send_message(&message).await
    }

    /// Alert on significant price movements (educational purposes only)
    pub async fn alert_price_movement(&self,
        token_address: &Pubkey,
        token_name: Option<String>,
        old_price: f64,
        new_price: f64,
        volume_24h: Option<f64>,
    ) -> Result<()> {
        if !self.enabled || !self.alert_settings.alert_price_movements {
            return Ok(());
        }

        let change_percentage = ((new_price - old_price) / old_price) * 100.0;

        if change_percentage.abs() < self.alert_settings.price_change_threshold {
            return Ok(());
        }

        let mut rate_limiter = self.rate_limiter.write().await;
        if !rate_limiter.can_send(&format!("price_{}", token_address)) {
            return Ok(());
        }

        let trend_emoji = if change_percentage > 0.0 { "📈" } else { "📉" };
        let message = format!(
            "{} **PRICE MOVEMENT** (Educational Alert)\n\n\
            🪙 **Token**: {}\n\
            💱 **Old Price**: ${:.8}\n\
            💱 **New Price**: ${:.8}\n\
            📊 **Change**: {:.2}%\n\
            {}\
            🔗 **Address**: `{}`\n\n\
            {}",
            trend_emoji,
            token_name.unwrap_or("Unknown".to_string()),
            old_price,
            new_price,
            change_percentage,
            volume_24h.map(|v| format!("📊 **24h Volume**: ${:.2}\n", v)).unwrap_or_default(),
            token_address,
            self.get_market_analysis_note(change_percentage)
        );

        self.send_message(&message).await
    }

    /// Alert on volume spikes (educational purposes only)
    pub async fn alert_volume_spike(&self,
        token_address: &Pubkey,
        token_name: Option<String>,
        current_volume: f64,
        average_volume: f64,
    ) -> Result<()> {
        if !self.enabled || !self.alert_settings.alert_volume_spikes {
            return Ok(());
        }

        let spike_multiplier = current_volume / average_volume;

        if spike_multiplier < self.alert_settings.volume_spike_threshold {
            return Ok(());
        }

        let mut rate_limiter = self.rate_limiter.write().await;
        if !rate_limiter.can_send(&format!("volume_{}", token_address)) {
            return Ok(());
        }

        let message = format!(
            "📊 **VOLUME SPIKE** (Educational Alert)\n\n\
            🪙 **Token**: {}\n\
            📈 **Current Volume**: ${:.2}\n\
            📊 **Average Volume**: ${:.2}\n\
            🔥 **Spike**: {:.1}x average\n\
            🔗 **Address**: `{}`\n\n\
            📚 **Educational Note**: Volume spikes can indicate:\n\
            • Increased market interest\n\
            • Potential price movements\n\
            • News or events affecting the token\n\n\
            {}",
            token_name.unwrap_or("Unknown".to_string()),
            current_volume,
            average_volume,
            spike_multiplier,
            token_address,
            self.get_risk_warning()
        );

        self.send_message(&message).await
    }

    /// Alert on potential sniper opportunities (educational analysis only)
    pub async fn alert_sniper_opportunity(&self,
        token_address: &Pubkey,
        token_name: Option<String>,
        opportunity_type: &str,
        details: &str,
    ) -> Result<()> {
        if !self.enabled || !self.alert_settings.alert_sniper_opportunities {
            return Ok(());
        }

        let mut rate_limiter = self.rate_limiter.write().await;
        if !rate_limiter.can_send(&format!("sniper_{}", token_address)) {
            return Ok(());
        }

        let message = format!(
            "🎯 **PATTERN DETECTED** (Educational Analysis)\n\n\
            🪙 **Token**: {}\n\
            📍 **Pattern Type**: {}\n\
            📊 **Details**: {}\n\
            🔗 **Address**: `{}`\n\n\
            📚 **Educational Context**:\n\
            This pattern suggests a potential market opportunity based on:\n\
            • Historical price action\n\
            • Volume analysis\n\
            • Market sentiment indicators\n\n\
            ⚠️ **IMPORTANT**: This is for educational purposes only!\n\
            • Real trading involves significant risk\n\
            • Past patterns don't guarantee future results\n\
            • Always do your own research\n\
            • Never invest more than you can afford to lose",
            token_name.unwrap_or("Unknown".to_string()),
            opportunity_type,
            details,
            token_address
        );

        self.send_message(&message).await
    }

    /// Send daily summary (educational purposes)
    pub async fn send_daily_summary(&self,
        tokens_monitored: usize,
        wallet_activities: usize,
        significant_movements: usize,
    ) -> Result<()> {
        if !self.enabled {
            return Ok(());
        }

        let message = format!(
            "📊 **DAILY SUMMARY** (Educational Report)\n\n\
            📅 **Date**: {}\n\
            🔍 **Tokens Monitored**: {}\n\
            👥 **Wallet Activities**: {}\n\
            📈 **Significant Movements**: {}\n\n\
            📚 **Market Insights**:\n\
            • Monitor multiple data points for better analysis\n\
            • Look for patterns across different tokens\n\
            • Consider market sentiment and external factors\n\n\
            {}",
            Utc::now().format("%Y-%m-%d"),
            tokens_monitored,
            wallet_activities,
            significant_movements,
            self.get_risk_warning()
        );

        self.send_message(&message).await
    }

    /// Send a custom educational alert
    pub async fn send_custom_alert(&self, title: &str, content: &str) -> Result<()> {
        if !self.enabled {
            return Ok(());
        }

        let message = format!(
            "📢 **{}** (Educational Alert)\n\n\
            {}\n\n\
            {}",
            title,
            content,
            self.get_risk_warning()
        );

        self.send_message(&message).await
    }

    /// Internal method to send messages via Telegram
    async fn send_message(&self, text: &str) -> Result<()> {
        self.bot
            .send_message(self.chat_id, text)
            .parse_mode(teloxide::types::ParseMode::Markdown)
            .send()
            .await?;
        Ok(())
    }

    /// Get risk warning text
    fn get_risk_warning(&self) -> &str {
        if self.alert_settings.include_risk_warnings {
            "⚠️ **Risk Warning**: Cryptocurrency trading involves substantial risk of loss. \
            This is educational content only - not financial advice."
        } else {
            ""
        }
    }

    /// Get educational note based on action
    fn get_educational_note(&self, action: &str) -> &str {
        match action {
            "BUY" => {
                "📚 **Note**: This wallet is purchasing tokens. \
                Consider factors like liquidity, market cap, and project fundamentals."
            },
            "SELL" => {
                "📚 **Note**: This wallet is selling tokens. \
                This could indicate profit-taking or risk management."
            },
            _ => ""
        }
    }

    /// Get market analysis note based on price change
    fn get_market_analysis_note(&self, change_percentage: f64) -> String {
        if change_percentage > 50.0 {
            "📚 **Analysis**: Extreme price increase detected. \
            Could indicate pump activity or major news. Exercise extreme caution.".to_string()
        } else if change_percentage > 20.0 {
            "📚 **Analysis**: Significant price increase. \
            Monitor for sustainability and volume confirmation.".to_string()
        } else if change_percentage < -50.0 {
            "📚 **Analysis**: Major price drop detected. \
            Could indicate dump, bad news, or market correction.".to_string()
        } else if change_percentage < -20.0 {
            "📚 **Analysis**: Significant price decrease. \
            May present opportunities but assess the cause first.".to_string()
        } else {
            "📚 **Analysis**: Normal market movement. \
            Continue monitoring for patterns.".to_string()
        }
    }
}

/// Initialize Telegram alert system from environment variables
pub fn init_from_env() -> Result<Option<TelegramAlertSystem>> {
    let bot_token = std::env::var("TELEGRAM_BOT_TOKEN").ok();
    let chat_id = std::env::var("TELEGRAM_CHAT_ID")
        .ok()
        .and_then(|s| s.parse::<i64>().ok());
    let enabled = std::env::var("TELEGRAM_ALERTS_ENABLED")
        .unwrap_or_else(|_| "false".to_string())
        .parse::<bool>()
        .unwrap_or(false);

    match (bot_token, chat_id, enabled) {
        (Some(token), Some(id), true) => {
            println!("✅ Telegram alerts enabled for educational monitoring");
            Ok(Some(TelegramAlertSystem::new(token, id, true)?))
        },
        _ => {
            println!("ℹ️ Telegram alerts disabled or not configured");
            Ok(None)
        }
    }
}