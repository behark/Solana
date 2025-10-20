/// Educational monitoring entry point
/// This version ONLY monitors and sends alerts - NO TRADING
use anyhow::Result;
use dotenv::dotenv;
use std::sync::Arc;
use tokio::time::{sleep, Duration};

mod common;
mod processor;
mod library;
mod dex;
mod error;
mod block_engine;

use crate::processor::telegram_alerts::{TelegramAlertSystem, AlertSettings};
use crate::processor::educational_monitor::EducationalMonitor;
use crate::common::config::Config;

#[tokio::main]
async fn main() -> Result<()> {
    // Load environment variables
    dotenv().ok();

    println!("\n{'='*60}");
    println!("📚 SOLANA EDUCATIONAL MONITORING SYSTEM");
    println!("⚠️  NO TRADING - ALERTS ONLY");
    println!("{'='*60}\n");

    // Initialize configuration
    let config = Config::from_env().await?;
    println!("✅ Configuration loaded");

    // Initialize Telegram alerts if configured
    let telegram = match processor::telegram_alerts::init_from_env()? {
        Some(mut system) => {
            // Configure alert settings
            let mut settings = AlertSettings::default();
            settings.alert_new_tokens = true;
            settings.alert_wallet_activity = true;
            settings.alert_price_movements = true;
            settings.price_change_threshold = 10.0; // 10% threshold
            settings.alert_volume_spikes = true;
            settings.volume_spike_threshold = 3.0; // 3x volume
            settings.alert_sniper_opportunities = true;
            settings.include_risk_warnings = true;

            system.configure(settings);
            println!("✅ Telegram alerts configured and ready");

            // Send startup notification
            system.send_custom_alert(
                "System Started",
                "Educational monitoring system is now active. \
                This system will monitor tokens and send alerts for educational purposes only. \
                No trading will be performed."
            ).await?;

            Some(Arc::new(system))
        },
        None => {
            println!("ℹ️  Telegram alerts not configured - monitoring will continue without alerts");
            None
        }
    };

    // Initialize educational monitor
    let monitor = EducationalMonitor::new(config.clone(), telegram.clone());
    println!("✅ Educational monitor initialized");

    // Display monitoring configuration
    println!("\n📊 Monitoring Configuration:");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    if let Ok(targets) = std::env::var("COPY_TRADING_TARGET_ADDRESS") {
        let wallets: Vec<&str> = targets.split(',').collect();
        println!("👥 Target Wallets: {} wallets", wallets.len());
        for (i, wallet) in wallets.iter().enumerate().take(3) {
            println!("   {}. {}...{}", i+1, &wallet[..4], &wallet[wallet.len()-4..]);
        }
        if wallets.len() > 3 {
            println!("   ... and {} more", wallets.len() - 3);
        }
    } else {
        println!("👥 Target Wallets: Not configured");
    }

    if let Ok(limit) = std::env::var("COUNTER_LIMIT") {
        println!("🎯 Max Tokens to Track: {}", limit);
    }

    if let Ok(drop_threshold) = std::env::var("FOCUS_DROP_THRESHOLD_PCT") {
        if let Ok(threshold) = drop_threshold.parse::<f64>() {
            println!("📉 Price Drop Alert Threshold: {:.1}%", threshold * 100.0);
        }
    }

    if let Ok(trigger_sol) = std::env::var("FOCUS_TRIGGER_SOL") {
        println!("💰 Large Transaction Threshold: {} SOL", trigger_sol);
    }

    println!("\n🚦 System Status:");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("✅ Monitoring: ACTIVE");
    println!("❌ Trading: DISABLED");
    println!("📱 Telegram Alerts: {}",
        if telegram.is_some() { "ENABLED" } else { "DISABLED" }
    );

    println!("\n📚 Educational Features:");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("• Real-time token monitoring");
    println!("• Wallet activity tracking");
    println!("• Price movement analysis");
    println!("• Volume spike detection");
    println!("• Pattern recognition");
    println!("• Hypothetical PnL tracking");
    println!("• Daily educational reports");

    println!("\n⚠️  IMPORTANT REMINDERS:");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("• This system is for EDUCATIONAL purposes only");
    println!("• NO actual trades will be executed");
    println!("• Cryptocurrency trading involves significant risk");
    println!("• Past performance does not indicate future results");
    println!("• Always do your own research");
    println!("• Never invest more than you can afford to lose");

    println!("\n🔄 Starting monitoring loop...\n");

    // Main monitoring loop
    let mut report_timer = tokio::time::interval(Duration::from_secs(3600)); // Hourly reports

    loop {
        tokio::select! {
            _ = report_timer.tick() => {
                // Generate and send educational report
                match monitor.generate_educational_report().await {
                    Ok(report) => {
                        println!("{}", report);
                        if let Some(tg) = &telegram {
                            let _ = tg.send_custom_alert(
                                "Hourly Educational Report",
                                &report
                            ).await;
                        }
                    },
                    Err(e) => {
                        eprintln!("Error generating report: {}", e);
                    }
                }
            }

            _ = tokio::signal::ctrl_c() => {
                println!("\n📛 Shutdown signal received");

                // Send shutdown notification
                if let Some(tg) = &telegram {
                    let _ = tg.send_custom_alert(
                        "System Shutdown",
                        "Educational monitoring system is shutting down gracefully."
                    ).await;
                }

                println!("✅ Educational monitoring stopped");
                println!("Thank you for using the educational monitoring system!");
                break;
            }
        }
    }

    Ok(())
}

/// Display usage instructions
fn display_usage() {
    println!("\n📖 USAGE INSTRUCTIONS");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!();
    println!("1. Configure your .env file with:");
    println!("   - RPC endpoints (RPC_HTTP, YELLOWSTONE_GRPC_HTTP)");
    println!("   - Telegram bot credentials (optional)");
    println!("   - Wallet addresses to monitor");
    println!("   - Alert thresholds");
    println!();
    println!("2. Run the educational monitor:");
    println!("   cargo run --bin educational_main");
    println!();
    println!("3. Monitor the console and Telegram for alerts");
    println!();
    println!("4. Review hourly educational reports");
    println!();
    println!("Press Ctrl+C to stop monitoring");
    println!();
}