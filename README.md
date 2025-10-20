## Solana PumpFun/PumpSwap Raydium Copy/Sniper Trading Bot

This project is a high-performance Solana trading bot written in Rust, with a Python-based monitoring system. The bot is designed to snipe new token launches and copy trades from target wallets on various DEXs, including PumpFun, PumpSwap, and Raydium.

### Architecture

The system is composed of two main components:

1.  **Python Monitoring System (`unified_monitor.py`):** This script is responsible for discovering new tokens. It uses a combination of direct blockchain monitoring and public APIs to gather information about new tokens, score them, and send alerts via Telegram.
2.  **Rust Trading Bot:** The core of the system, written in Rust for high performance and reliability. The bot reads the tokens discovered by the Python monitor from a file-based queue (`token_queue.json`) and executes trades based on a configurable strategy.

This decoupled architecture allows for a clear separation of concerns and makes the system more modular and easier to maintain.

### Features

-   **Real-time token discovery:** The Python monitor uses a combination of methods to discover new tokens as soon as they are created.
-   **Data enrichment:** The monitor enriches the token data with information from public APIs, such as liquidity, volume, and price.
-   **Token scoring:** A configurable scoring system helps to identify the most promising tokens.
-   **Telegram alerts:** The monitor sends alerts via Telegram for new tokens that meet a certain score threshold.
-   **High-performance trading:** The Rust bot is designed for low-latency trade execution.
-   **Configurable trading strategy:** The bot's trading strategy can be configured through environment variables.
-   **File-based communication:** The Python monitor and the Rust bot communicate through a simple and reliable file-based queue.

### Setup

1.  **Prerequisites:**
    *   Rust toolchain (stable)
    *   Python 3.8+
    *   A Solana RPC endpoint
    *   A Yellowstone gRPC endpoint
    *   A Telegram bot token and chat ID

2.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-org/solana-copy-sniper-trading-bot.git
    cd solana-copy-sniper-trading-bot
    ```

    > **Note:** Replace `your-org` with the actual GitHub organization/username

3.  **Install dependencies:**

    ```bash
    # Install Rust dependencies
    cargo build --release

    # Install Python dependencies
    pip install -r python/requirements.txt
    ```

4.  **Configure the environment:**

    Create a `.env` file in the root of the project and add the following environment variables:

    ```
    # Solana RPC endpoint
    RPC_HTTP=<your-rpc-endpoint>

    # Yellowstone gRPC endpoint
    YELLOWSTONE_GRPC_HTTP=<your-yellowstone-endpoint>
    YELLOWSTONE_GRPC_TOKEN=<your-yellowstone-token>

    # Telegram bot token and chat ID
    TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
    TELEGRAM_CHAT_ID=<your-telegram-chat-id>

    # Trading configuration
    PRIVATE_KEY=<your-private-key>
    COPY_TRADING_TARGET_ADDRESS=<target-wallet-address>
    TOKEN_AMOUNT=0.001
    SLIPPAGE=3000
    TAKE_PROFIT=8.0
    STOP_LOSS=-2
    MAX_HOLD_TIME=3600
    MIN_LIQUIDITY=4
    WRAP_AMOUNT=0.5

    # See src/env.example for complete list of environment variables
    ```

### Running the System

The system consists of two independent processes that need to be run separately:

1.  **Run the Python monitor:**

    ```bash
    python3 python/unified_monitor.py
    ```

    The monitor will start discovering new tokens and will write them to the `token_queue.json` file.

2.  **Run the Rust bot:**

    ```bash
    cargo run --release
    ```

    The bot will start monitoring the `token_queue.json` file and will execute trades for the tokens that appear in the queue.

### Shell Scripts

The `scripts` directory contains a set of useful shell scripts for managing the system:

-   `run_monitor.sh`: A simple script to run the Python monitor.
-   `monitor_forever.sh`: A script that runs the Python monitor in a loop and automatically restarts it if it crashes.
-   `setup_autostart.sh`: A script that sets up a cron job to automatically start the monitor on system boot.
-   `install_service.sh`: A script to install the monitor as a systemd service.

### Disclaimer

This software is for educational purposes only. Use it at your own risk. The author is not responsible for any financial losses.
