#!/usr/bin/env python3
"""
BNB Chain (BSC) Blockchain Monitor
Monitors PancakeSwap for new token launches using WebSocket subscriptions.
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, AsyncGenerator, Set
from datetime import datetime
import aiohttp
import aiofiles
from web3 import AsyncWeb3, WebsocketProvider, AsyncHTTPProvider
from web3.middleware import async_geth_poa_middleware
from web3.logs import DISCARD
from web3.types import LogReceipt
from dotenv import load_dotenv

load_dotenv()

# --- Setup Logging ---
# (Added basic logging config to see output)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Use DEBUG level to see verbose log parsing errors
# logging.basicConfig(level=logging.DEBUG)


class BNBMonitor:
    """Monitor BNB Chain for new token launches via WebSockets"""

    # PancakeSwap Factory Addresses
    PANCAKE_V2_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
    PANCAKE_V3_FACTORY = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"

    # Token addresses on BSC
    WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    BUSD = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
    USDT = "0x55d398326f99059fF775485246999027B3197955"
    USDC = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"

    # Event signatures (topics)
    PAIR_CREATED_TOPIC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
    POOL_CREATED_TOPIC = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"

    # --- ABIs for Log Decoding ---
    # Simplified ABI for PancakeSwap V2 PairCreated event
    PAIR_CREATED_ABI = {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "pair", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "allPairsLength", "type": "uint256"},
        ],
        "name": "PairCreated",
        "type": "event",
    }

    # Simplified ABI for PancakeSwap V3 PoolCreated event
    POOL_CREATED_ABI = {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": True, "internalType": "uint24", "name": "fee", "type": "uint24"},
            {"indexed": False, "internalType": "int24", "name": "tickSpacing", "type": "int24"},
            {"indexed": False, "internalType": "address", "name": "pool", "type": "address"},
        ],
        "name": "PoolCreated",
        "type": "event",
    }

    def __init__(self):
        """Initialize BNB Chain monitor"""
        self.rpc_url = os.getenv('BNB_RPC_HTTP') # Still needed for metadata calls
        self.wss_url = os.getenv('BNB_RPC_WSS') # Used for real-time monitoring
        
        if not self.rpc_url or not self.wss_url:
            raise ValueError("BNB_RPC_HTTP and BNB_RPC_WSS must be set in .env")

        self.w3: Optional[AsyncWeb3] = None
        self.w3_http: Optional[AsyncWeb3] = None # Separate HTTP provider for metadata
        self.session: Optional[aiohttp.ClientSession] = None

        # --- Efficient Lookups & Caching ---
        
        # Create a set for fast, lowercase comparisons
        self.BASE_TOKENS_LOWER = {
            self.WBNB.lower(),
            self.BUSD.lower(),
            self.USDT.lower(),
            self.USDC.lower()
        }

        # Cache for token metadata
        self.token_metadata_cache = {}

        # --- Persistence for Processed Transactions ---
        self.processed_txs_file = "processed_txs.json"
        self.processed_txs = set()  # Will be loaded in initialize()

        # ABI for minimal BEP20 interface
        self.bep20_abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ]

        logger.info("BNB Chain monitor initialized.")

    async def _load_processed_txs(self) -> Set[str]:
        """Load the set of processed transaction hashes from a file"""
        if not os.path.exists(self.processed_txs_file):
            return set()
        try:
            async with aiofiles.open(self.processed_txs_file, 'r') as f:
                content = await f.read()
                tx_list = json.loads(content)
                return set(tx_list)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load processed txs file, starting fresh: {e}")
            return set()

    async def _save_processed_txs(self):
        """Save the set of processed transaction hashes to a file"""
        try:
            async with aiofiles.open(self.processed_txs_file, 'w') as f:
                content = json.dumps(list(self.processed_txs))
                await f.write(content)
        except IOError as e:
            logger.error(f"Failed to save processed txs: {e}")

    async def initialize(self):
        """Initialize Web3 connections to BSC (WebSocket and HTTP)"""
        try:
            # WebSocket provider for real-time filters
            self.w3 = AsyncWeb3(WebsocketProvider(self.wss_url))
            self.w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
            is_connected_wss = self.w3.is_connected()

            # HTTP provider for metadata calls (get_token_metadata)
            # It's good practice to separate high-volume metadata calls
            # from the real-time subscription connection.
            self.w3_http = AsyncWeb3(AsyncHTTPProvider(self.rpc_url))
            self.w3_http.middleware_onion.inject(async_geth_poa_middleware, layer=0)
            is_connected_http = self.w3_http.is_connected()

            if is_connected_wss and is_connected_http:
                chain_id = await self.w3.eth.chain_id
                latest_block = await self.w3.eth.block_number
                logger.info(f"Connected to BNB Chain via WSS & HTTP (Chain ID: {chain_id}, Block: {latest_block})")
            else:
                if not is_connected_wss:
                    raise Exception("Failed to connect to BNB Chain WSS")
                if not is_connected_http:
                    raise Exception("Failed to connect to BNB Chain HTTP RPC")

            # Load processed transactions from cache
            self.processed_txs = await self._load_processed_txs()
            logger.info(f"Loaded {len(self.processed_txs)} processed txs from cache.")

            self.session = aiohttp.ClientSession()

        except Exception as e:
            logger.error(f"Error initializing BNB Chain client: {e}")
            raise

    async def cleanup(self):
        """Clean up connections"""
        if self.session:
            await self.session.close()
        # Note: web3.py's AsyncWebsocketProvider doesn't have an explicit 'close'
        # The connection will be closed when the program exits.
        logger.info("Cleaned up aiohttp session.")

    async def get_token_metadata(self, token_address: str) -> Dict:
        """Get BEP20 token metadata (uses the HTTP provider)"""
        try:
            token_address_lower = token_address.lower()
            if token_address_lower in self.token_metadata_cache:
                return self.token_metadata_cache[token_address_lower]

            metadata = {
                'address': token_address,
                'symbol': 'Unknown',
                'name': 'Unknown',
                'decimals': 18,
                'total_supply': 0
            }

            checksum_address = self.w3_http.to_checksum_address(token_address)
            contract = self.w3_http.eth.contract(address=checksum_address, abi=self.bep20_abi)

            try:
                results = await asyncio.gather(
                    contract.functions.symbol().call(),
                    contract.functions.name().call(),
                    contract.functions.decimals().call(),
                    contract.functions.totalSupply().call(),
                    return_exceptions=True
                )

                if not isinstance(results[0], Exception):
                    metadata['symbol'] = results[0]
                if not isinstance(results[1], Exception):
                    metadata['name'] = results[1]
                if not isinstance(results[2], Exception):
                    metadata['decimals'] = results[2]
                if not isinstance(results[3], Exception):
                    metadata['total_supply'] = results[3]

            except Exception as e:
                logger.debug(f"Error getting token metadata for {token_address}: {e}")

            self.token_metadata_cache[token_address_lower] = metadata
            return metadata

        except Exception as e:
            logger.error(f"Unhandled error in get_token_metadata for {token_address}: {e}")
            return {
                'address': token_address,
                'symbol': 'Unknown',
                'name': 'Unknown'
            }

    async def process_log(self, log: LogReceipt) -> Optional[Dict]:
        """
        Decodes a raw log (from V2 or V3) and enriches it with metadata.
        Returns a dictionary if it's a new, valid token pair, otherwise None.
        """
        try:
            tx_hash = log['transactionHash'].hex()
            if tx_hash in self.processed_txs:
                return None # Already processed

            topic = log['topics'][0].hex()
            token0, token1, pool_address, dex_version = None, None, None, None

            if topic == self.PAIR_CREATED_TOPIC:
                # --- It's a PancakeSwap V2 Pair ---
                event_data = self.w3.codec.decode_log(self.PAIR_CREATED_ABI, log['topics'], log['data'])
                token0 = event_data['args']['token0']
                token1 = event_data['args']['token1']
                pool_address = event_data['args']['pair']
                dex_version = 2

            elif topic == self.POOL_CREATED_TOPIC:
                # --- It's a PancakeSwap V3 Pool ---
                event_data = self.w3.codec.decode_log(self.POOL_CREATED_ABI, log['topics'], log['data'])
                token0 = event_data['args']['token0']
                token1 = event_data['args']['token1']
                pool_address = event_data['args']['pool']
                dex_version = 3
            
            else:
                return None # Not a log we care about

            # --- Identify Base Token and New Token ---
            base_token, new_token = None, None
            if token0.lower() in self.BASE_TOKENS_LOWER:
                base_token = token0
                new_token = token1
            elif token1.lower() in self.BASE_TOKENS_LOWER:
                base_token = token1
                new_token = token0
            else:
                # Skip if no recognized base token (e.g., SHIB/DOGE pair)
                return None

            # --- Get Token Metadata ---
            metadata = await self.get_token_metadata(new_token)

            # Skip obvious test tokens
            if metadata.get('symbol', '').lower() in ['test', 'testing', 'fake']:
                logger.info(f"Skipping test token: {metadata.get('symbol')}")
                return None

            # --- Get Liquidity (STUBBED) ---
            liquidity = await self.get_pool_liquidity(pool_address, dex_version)

            # --- Check for Honeypot (STUBBED) ---
            honeypot_check = await self.check_honeypot(new_token)

            # --- Assemble Final Token Data ---
            token_data = {
                'dex': f'PancakeSwap V{dex_version}',
                'version': dex_version,
                'pool_address': pool_address,
                'token0': token0,
                'token1': token1,
                'new_token': new_token,
                'base_token': base_token,
                'block_number': log['blockNumber'],
                'transaction_hash': tx_hash,
                'chain': 'bnb',
                'chain_id': 56,
                'discovered_at': datetime.now().isoformat(),
                'liquidity_usd': liquidity,
                'honeypot_check': honeypot_check,
                'explorer_link': f"https://bscscan.com/token/{new_token}",
                'dexscreener_link': f"https://dexscreener.com/bsc/{new_token}",
                'poocoin_link': f"https://poocoin.app/tokens/{new_token}",
                **metadata  # Add name, symbol, decimals, etc.
            }
            
            # Add to processed set and save
            self.processed_txs.add(tx_hash)
            await self._save_processed_txs() # Save to disk

            return token_data

        except Exception as e:
            logger.error(f"Error processing log {log.get('transactionHash', 'N/A').hex()}: {e}")
            logger.debug(f"Raw log data: {log}")
            return None

    async def check_honeypot(self, token_address: str) -> Dict:
        """
        Check if token is a honeypot using GoPlus Security API.
        Includes retry logic and proper error handling.
        """
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # GoPlus Security API for BSC (chain ID: 56)
                url = f'https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses={token_address}'

                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"GoPlus API returned status {response.status} for {token_address}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        return {
                            'is_honeypot': None,
                            'buy_tax': None,
                            'sell_tax': None,
                            'warnings': [f"API error: HTTP {response.status}"]
                        }

                    data = await response.json()

                    # Parse GoPlus response
                    if 'result' not in data or token_address.lower() not in data['result']:
                        logger.warning(f"Token {token_address} not found in GoPlus response")
                        return {
                            'is_honeypot': None,
                            'buy_tax': None,
                            'sell_tax': None,
                            'warnings': ["Token not found in security database"]
                        }

                    token_data = data['result'][token_address.lower()]

                    # Extract security information
                    is_honeypot = token_data.get('is_honeypot', '0') == '1'
                    buy_tax = float(token_data.get('buy_tax', 0)) if token_data.get('buy_tax') else 0
                    sell_tax = float(token_data.get('sell_tax', 0)) if token_data.get('sell_tax') else 0

                    # Collect warnings
                    warnings = []
                    if is_honeypot:
                        warnings.append("⚠️ HONEYPOT DETECTED")
                    if token_data.get('is_open_source', '1') == '0':
                        warnings.append("Contract not verified")
                    if token_data.get('is_proxy', '0') == '1':
                        warnings.append("Proxy contract detected")
                    if token_data.get('can_take_back_ownership', '0') == '1':
                        warnings.append("Owner can take back ownership")
                    if buy_tax > 10:
                        warnings.append(f"High buy tax: {buy_tax}%")
                    if sell_tax > 10:
                        warnings.append(f"High sell tax: {sell_tax}%")

                    logger.info(f"Honeypot check for {token_address}: honeypot={is_honeypot}, buy_tax={buy_tax}%, sell_tax={sell_tax}%")

                    return {
                        'is_honeypot': is_honeypot,
                        'buy_tax': buy_tax,
                        'sell_tax': sell_tax,
                        'warnings': warnings
                    }

            except asyncio.TimeoutError:
                logger.warning(f"Timeout checking honeypot for {token_address} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
            except Exception as e:
                logger.error(f"Error checking honeypot for {token_address}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue

        # All retries failed
        return {
            'is_honeypot': None,
            'buy_tax': None,
            'sell_tax': None,
            'warnings': ["Failed to check honeypot status after multiple attempts"]
        }

    async def get_bnb_price_usd(self) -> Optional[float]:
        """Fetch BNB price in USD from CoinGecko API"""
        try:
            url = 'https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd'
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get('binancecoin', {}).get('usd')
                    if price:
                        logger.debug(f"BNB price: ${price}")
                        return float(price)
                else:
                    logger.warning(f"CoinGecko API returned status {response.status}")
        except Exception as e:
            logger.error(f"Error fetching BNB price: {e}")
        return None

    async def get_pool_liquidity(self, pool_address: str, dex_version: int) -> Optional[float]:
        """
        Calculate pool liquidity in USD.
        Supports PancakeSwap V2 pairs.
        """
        try:
            # Get BNB price
            bnb_price = await self.get_bnb_price_usd()
            if not bnb_price:
                logger.warning(f"Could not fetch BNB price, cannot calculate liquidity for {pool_address}")
                return None

            # V2 Pair ABI (minimal - just getReserves and token0/token1)
            v2_pair_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "reserve0", "type": "uint112"},
                        {"name": "reserve1", "type": "uint112"},
                        {"name": "blockTimestampLast", "type": "uint32"}
                    ],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "type": "function"
                }
            ]

            if dex_version == 2:
                # Get reserves from V2 pair
                pair_contract = self.w3_http.eth.contract(
                    address=self.w3_http.to_checksum_address(pool_address),
                    abi=v2_pair_abi
                )

                reserves = await pair_contract.functions.getReserves().call()
                token0 = await pair_contract.functions.token0().call()
                token1 = await pair_contract.functions.token1().call()

                # Determine which reserve is WBNB
                reserve0 = reserves[0]
                reserve1 = reserves[1]

                wbnb_reserve = None
                if token0.lower() == self.WBNB.lower():
                    wbnb_reserve = reserve0
                elif token1.lower() == self.WBNB.lower():
                    wbnb_reserve = reserve1
                else:
                    # Neither token is WBNB, try to get any stablecoin pairing
                    # Check if paired with BUSD, USDT, or USDC
                    if token0.lower() in self.BASE_TOKENS_LOWER or token1.lower() in self.BASE_TOKENS_LOWER:
                        # Use the larger reserve as approximation
                        stable_reserve = max(reserve0, reserve1)
                        # Assume 1:1 for stablecoins
                        liquidity_usd = (stable_reserve / (10**18)) * 2
                        logger.debug(f"Pool {pool_address} liquidity (stablecoin pair): ${liquidity_usd:,.2f}")
                        return liquidity_usd
                    else:
                        logger.debug(f"Pool {pool_address} is not paired with WBNB or stablecoin, cannot calculate liquidity")
                        return None

                # Calculate liquidity: WBNB reserve * price * 2 (both sides of pool)
                wbnb_reserve_float = wbnb_reserve / (10**18)
                total_liquidity_usd = wbnb_reserve_float * bnb_price * 2

                logger.debug(f"Pool {pool_address} liquidity: ${total_liquidity_usd:,.2f} (WBNB reserve: {wbnb_reserve_float:.4f})")
                return total_liquidity_usd

            elif dex_version == 3:
                # V3 liquidity calculation is more complex - requires tick data
                # For now, return None and log warning
                logger.warning(f"V3 liquidity calculation not yet implemented for {pool_address}")
                return None

            else:
                logger.warning(f"Unknown DEX version {dex_version} for pool {pool_address}")
                return None

        except Exception as e:
            logger.error(f"Error calculating liquidity for pool {pool_address}: {e}")
            return None

    async def monitor(self) -> AsyncGenerator[Dict, None]:
        """
        Main monitoring loop. Subscribes to new logs via WebSocket
        and yields processed token data.
        """
        await self.initialize()

        # Create a filter to listen for PairCreated/PoolCreated events
        # from both PancakeSwap factories.
        event_filter = await self.w3.eth.filter({
            'address': [
                self.w3.to_checksum_address(self.PANCAKE_V2_FACTORY),
                self.w3.to_checksum_address(self.PANCAKE_V3_FACTORY)
            ],
            'topics': [
                [self.PAIR_CREATED_TOPIC, self.POOL_CREATED_TOPIC] # Listen for EITHER topic
            ]
        })

        logger.info("Starting WebSocket monitor for new PancakeSwap pairs/pools...")

        try:
            while True:
                try:
                    new_logs = await event_filter.get_new_entries()
                    if new_logs:
                        logger.debug(f"Received {len(new_logs)} new event logs.")
                    
                    for log in new_logs:
                        processed_token = await self.process_log(log)
                        if processed_token:
                            yield processed_token
                    
                    await asyncio.sleep(1) # Short sleep to prevent busy-looping

                except asyncio.TimeoutError:
                    logger.warning("WebSocket connection timeout. Reconnecting...")
                    # Re-initialize connections and filter
                    await self.initialize()
                    event_filter = await self.w3.eth.filter({
                        'address': [
                            self.w3.to_checksum_address(self.PANCAKE_V2_FACTORY),
                            self.w3.to_checksum_address(self.PANCAKE_V3_FACTORY)
                        ],
                        'topics': [
                            [self.PAIR_CREATED_TOPIC, self.POOL_CREATED_TOPIC]
                        ]
                    })
                except Exception as e:
                    logger.error(f"Error in BNB Chain monitoring loop: {e}")
                    logger.info("Attempting to reconnect in 30 seconds...")
                    await asyncio.sleep(30)
                    # Attempt to re-initialize
                    await self.initialize()
                    event_filter = await self.w3.eth.filter({
                        'address': [
                            self.w3.to_checksum_address(self.PANCAKE_V2_FACTORY),
                            self.w3.to_checksum_address(self.PANCAKE_V3_FACTORY)
                        ],
                        'topics': [
                            [self.PAIR_CREATED_TOPIC, self.POOL_CREATED_TOPIC]
                        ]
                    })

        finally:
            await self.cleanup()
            logger.info("Monitor shutdown complete.")


# --- Example Usage ---
async def main():
    """Main function to run the monitor"""
    monitor = BNBMonitor()
    
    try:
        async for token in monitor.monitor():
            logger.info("--- NEW TOKEN FOUND ---")
            logger.info(f"Symbol:   {token.get('symbol')}")
            logger.info(f"Name:     {token.get('name')}")
            logger.info(f"Address:  {token.get('new_token')}")
            logger.info(f"DEX:      {token.get('dex')}")
            logger.info(f"Liq (USD): {token.get('liquidity_usd')} (STUBBED)")
            logger.info(f"Honeypot: {token.get('honeypot_check', {}).get('is_honeypot')} (STUBBED)")
            logger.info(f"Poocoin:  {token.get('poocoin_link')}")
            logger.info("------------------------")
            
            # Here you would send this 'token' dictionary to your
            # database, Telegram bot, Discord bot, or frontend.
            
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Cleaning up...")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    # Make sure you have a .env file with:
    # BNB_RPC_HTTP=https://bsc-dataseed.binance.org/
    # BNB_RPC_WSS=wss://bsc-ws-node.nariox.org:443/
    # (Use your own reliable RPC provider!)
    
    asyncio.run(main())
