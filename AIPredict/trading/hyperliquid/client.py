"""
Hyperliquid Trading Client (using official SDK)
"""
import logging
from typing import Dict, List, Optional
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

from trading.base_client import BaseExchangeClient
from trading.precision_config import precision_config

logger = logging.getLogger(__name__)


class HyperliquidClient(BaseExchangeClient):
    """Hyperliquid Trading Client (official SDK version)"""
    
    def __init__(self, private_key: str, testnet: bool = True, max_retries: int = 3):
        """
        Initialize Hyperliquid Client
        
        Args:
            private_key: Ethereum private key (with or without 0x prefix)
            testnet: Whether to use testnet
            max_retries: Maximum retry attempts
        """
        super().__init__(private_key, testnet)
        self.testnet = testnet
        
        # Ensure private key format is correct
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # Use official SDK
        if testnet:
            base_url = constants.TESTNET_API_URL
        else:
            base_url = constants.MAINNET_API_URL
        
        # Add retry mechanism to initialize client
        import time
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Attempting to connect to Hyperliquid API (attempt {attempt + 1}/{max_retries})...")
                
                # Initialize Info (queries) and Exchange (trading)
                # Use longer timeout
                self.info = Info(base_url, skip_ws=True, timeout=30)
                self.exchange = Exchange(
                    wallet=None,  # Use private key
                    base_url=base_url,
                    account_address=None  # SDK will derive from private key
                )
                
                # Set account from private key
                from eth_account import Account
                account = Account.from_key(private_key)
                self.address = account.address
                self.exchange.wallet = account
                self.exchange.account_address = self.address
                
                logger.info(f"✅ Hyperliquid client initialized successfully")
                logger.info(f"   Address: {self.address}")
                logger.info(f"   Network: {'Testnet' if testnet else 'Mainnet'}")
                return  # Success, exit retry loop
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  Connection failed (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 2^attempt seconds
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    # All retries failed
                    error_msg = (
                        f"❌ Hyperliquid API connection failed (retried {max_retries} times)\n"
                        f"   Error: {str(last_error)}\n"
                        f"   This may be due to:\n"
                        f"   1. Network connection issues\n"
                        f"   2. SSL/TLS handshake failure\n"
                        f"   3. Hyperliquid API temporarily unavailable\n"
                        f"   Suggestion: Use backup data source or retry later"
                    )
                    logger.error(error_msg)
                    raise last_error
    
    @property
    def platform_name(self) -> str:
        """Platform name"""
        return "Hyperliquid"
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass
    
    async def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Account information dictionary
        """
        try:
            user_state = self.info.user_state(self.address)
            return user_state
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}
    
    async def get_market_data(self, coin: str) -> Dict:
        """
        Get market data
        
        Args:
            coin: Coin symbol (e.g. 'BTC', 'ETH')
            
        Returns:
            Market data
        """
        try:
            # Get all market data
            all_mids = self.info.all_mids()
            meta = self.info.meta()
            
            # Find specified coin
            if coin not in all_mids:
                raise ValueError(f"Coin {coin} not found")
            
            current_price = float(all_mids[coin])
            
            # Get detailed market context
            meta_and_asset_ctxs = self.info.meta_and_asset_ctxs()
            
            # Find coin index
            asset_index = None
            for i, asset in enumerate(meta_and_asset_ctxs[0]['universe']):
                if asset['name'] == coin:
                    asset_index = i
                    break
            
            if asset_index is None:
                raise ValueError(f"Coin {coin} not found in universe")
            
            ctx = meta_and_asset_ctxs[1][asset_index]
            
            # Extract data
            mark_price = float(ctx.get('markPx', current_price))
            funding = float(ctx.get('funding', 0))
            open_interest = float(ctx.get('openInterest', 0))
            prev_mark_px = float(ctx.get('prevDayPx', mark_price))
            volume_usd = float(ctx.get('dayNtlVlm', 0))
            
            # Calculate 24h change
            change_24h = ((mark_price - prev_mark_px) / prev_mark_px * 100) if prev_mark_px > 0 else 0
            
            return {
                "coin": coin,
                "price": mark_price,
                "mark_price": mark_price,
                "funding_rate": funding,
                "open_interest": open_interest,
                "change_24h": change_24h,
                "volume": volume_usd,
                "raw_ctx": ctx
            }
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            raise
    
    async def get_orderbook(self, coin: str) -> Dict:
        """
        Get order book
        
        Args:
            coin: Coin symbol
            
        Returns:
            Order book data {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """
        try:
            l2_snapshot = self.info.l2_snapshot(coin)
            # l2_snapshot format: {"levels": [[{"px": price, "sz": size, "n": count},...], [...]]}
            levels = l2_snapshot.get('levels', [[], []])
            
            # Convert to standard format [[price, size], ...]
            bids = [[float(level['px']), float(level['sz'])] for level in levels[0]] if len(levels) > 0 else []
            asks = [[float(level['px']), float(level['sz'])] for level in levels[1]] if len(levels) > 1 else []
            
            return {
                "bids": bids,
                "asks": asks
            }
        except Exception as e:
            logger.error(f"Failed to get order book: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"bids": [], "asks": []}
    
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """
        Get recent trades
        
        Args:
            coin: Coin symbol
            limit: Return quantity
            
        Returns:
            Trade list [{"time": ts, "px": price, "sz": size, "side": "A/B"}, ...]
        """
        try:
            # ⚠️ Hyperliquid SDK's Info object doesn't have recent_trades method
            # Currently returns empty list, this is not a core feature and doesn't affect trading
            logger.debug(f"[Hyperliquid] recent_trades feature not yet implemented, returning empty list")
            return []
        except Exception as e:
            logger.warning(f"Failed to get recent trades: {e}, returning empty list")
            return []
    
    def update_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> Dict:
        """
        Update leverage
        
        Args:
            coin: Coin symbol
            leverage: Leverage multiplier (1-50)
            is_cross: Whether to use cross margin mode (True=Cross, False=Isolated)
            
        Returns:
            Update result
        """
        try:
            # Use official SDK's update_leverage method
            result = self.exchange.update_leverage(leverage, coin, is_cross)
            logger.info(f"✅ Leverage updated: {coin} -> {leverage}x ({'Cross' if is_cross else 'Isolated'})")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to update leverage: {e}")
            raise
    
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "Limit",
        reduce_only: bool = False,
        max_retries: int = 3,
        leverage: int = None
    ) -> Dict:
        """
        Place order (supports retry on failure and leverage setting)
        
        Args:
            coin: Coin symbol
            is_buy: Whether to buy
            size: Quantity
            price: Price
            order_type: Order type ("Limit" or "Market")
            reduce_only: Whether to reduce only
            max_retries: Maximum retry attempts (default 3)
            leverage: Leverage multiplier (1-50, None means use current setting)
            
        Returns:
            Order result
        """
        # If leverage is specified, set leverage first
        if leverage is not None and not reduce_only:
            try:
                self.update_leverage(coin, leverage, is_cross=True)
            except Exception as e:
                logger.warning(f"⚠️ Failed to set leverage, using current leverage: {e}")
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Attempt {attempt + 1} to place order...")
                    await asyncio.sleep(0.5)  # Wait 0.5s before retry
                
                # Use official SDK to place order
                # Official SDK parameters: name, is_buy, sz, limit_px, order_type, reduce_only
                
                # Use unified precision config to process quantity
                size_rounded, _ = precision_config.format_hyperliquid_quantity(
                    coin, size, round_down=(not reduce_only)
                )
                
                # Process price: if None (market order), get current market price
                if price is None:
                    logger.info("📊 Market order, fetching current market price...")
                    orderbook = await self.get_orderbook(coin)
                    bids = orderbook.get("bids", [])
                    asks = orderbook.get("asks", [])
                    
                    # Buy order uses ask price, sell order uses bid price (ensure immediate execution)
                    if is_buy:
                        base_price = float(asks[0][0]) if asks else None
                    else:
                        base_price = float(bids[0][0]) if bids else None
                    
                    if base_price is None:
                        raise ValueError(f"Unable to get market price for {coin}")
                    
                    # Add slippage protection, increase slippage on retry
                    # 1st: 0.1%, 2nd: 0.15%, 3rd: 0.2%
                    slippage = 0.001 * (1 + attempt * 0.5)  # 0.1%, 0.15%, 0.2%
                    if is_buy:
                        # Buy with upward slippage to ensure execution
                        price = base_price * (1 + slippage)
                    else:
                        # Sell with downward slippage to ensure execution
                        price = base_price * (1 - slippage)
                    
                    logger.info(f"📊 Market order base price: ${base_price:,.2f}")
                    logger.info(f"📊 After adding {slippage*100:.2f}% slippage: ${price:,.2f} ({'Buy upward' if is_buy else 'Sell downward'})")
                
                # Use unified precision config to process price
                price_rounded, _ = precision_config.format_hyperliquid_price(coin, price)
                
                # Validate order parameters
                is_valid, error_msg = precision_config.validate_hyperliquid_order(coin, size_rounded, price_rounded)
                if not is_valid:
                    raise ValueError(f"Order parameter validation failed: {error_msg}")
                
                logger.info(f"📊 Original quantity: {size}, Processed: {size_rounded}")
                logger.info(f"📊 Original price: {price}, Processed: {price_rounded}")
                
                # Close orders use Ioc (Immediate or Cancel), open orders use Gtc (Good Till Cancel)
                if reduce_only:
                    # Close order: use Ioc to ensure immediate execution
                    order_type_param = {"limit": {"tif": "Ioc"}}
                else:
                    # Open order: decide based on order_type parameter
                    if order_type == "Limit":
                        order_type_param = {"limit": {"tif": "Gtc"}}
                    else:
                        order_type_param = {"limit": {"tif": "Ioc"}}  # Market orders also use Ioc
                
                order_result = self.exchange.order(
                    name=coin,
                    is_buy=is_buy,
                    sz=size_rounded,
                    limit_px=price_rounded,
                    order_type=order_type_param,
                    reduce_only=reduce_only
                )
                
                logger.info(f"📝 Official SDK order result: {order_result}")
                
                # Check if order is successful
                if order_result.get('status') == 'ok':
                    response = order_result.get('response', {})
                    data = response.get('data', {})
                    statuses = data.get('statuses', [])
                    
                    # Check if there's an error
                    if statuses and 'error' in statuses[0]:
                        error_msg = statuses[0]['error']
                        last_error = error_msg
                        logger.warning(f"⚠️  Order failed (attempt {attempt + 1}/{max_retries}): {error_msg}")
                        
                        # If not last attempt, continue retrying
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error(f"❌ All retries failed, last error: {error_msg}")
                            return order_result
                    else:
                        # Success, return directly
                        logger.info(f"✅ Order successful (attempt {attempt + 1}/{max_retries})")
                        return order_result
                else:
                    # Order rejected
                    last_error = order_result.get('response', 'Unknown error')
                    logger.warning(f"⚠️  Order rejected (attempt {attempt + 1}/{max_retries}): {last_error}")
                    
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return order_result
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️  Order exception (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    continue
                else:
                    logger.error(f"❌ All retries failed")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {"status": "err", "response": str(e)}
        
        # If all retries failed
        logger.error(f"❌ Order finally failed after {max_retries} attempts")
        return {"status": "err", "response": f"All {max_retries} attempts failed. Last error: {last_error}"}
    
    async def cancel_order(self, coin: str, order_id) -> Dict:
        """
        Cancel order
        
        Args:
            coin: Coin symbol
            order_id: Order ID
            
        Returns:
            Cancel result
        """
        try:
            oid = int(order_id) if isinstance(order_id, str) else order_id
            result = self.exchange.cancel(coin, oid)
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {"status": "err", "response": str(e)}
    
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """
        Get open orders
        
        Args:
            coin: Coin symbol (optional, Hyperliquid doesn't support filtering by coin)
        
        Returns:
            Order list
        """
        try:
            user_state = await self.get_account_info()
            orders = user_state.get('assetPositions', [])
            # If coin is specified, filter results
            if coin:
                orders = [o for o in orders if o.get('position', {}).get('coin') == coin]
            return orders
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """
        Get user historical trades
        
        Args:
            limit: Return quantity limit
            start_time_ms: Start time (millisecond timestamp), if None gets all
            
        Returns:
            Trade list
        """
        try:
            if start_time_ms:
                # Use time range query
                fills = self.info.user_fills_by_time(self.address, start_time_ms)
            else:
                # Get all trade records
                fills = self.info.user_fills(self.address)
            
            if not fills:
                return []
            
            # Limit return quantity
            if len(fills) > limit:
                fills = fills[:limit]
            
            logger.info(f"📊 Retrieved {len(fills)} historical trade records from Hyperliquid")
            return fills
        except Exception as e:
            logger.error(f"Failed to get historical trades: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def get_candles(self, coin: str, interval: str = "15m", lookback: int = 100, timeout: int = 30) -> List[Dict]:
        """
        Get candlestick data (with timeout protection)
        
        Args:
            coin: Coin symbol
            interval: Candlestick period ("1m", "5m", "15m", "1h", "4h", "1d")
            lookback: Lookback candlestick count
            timeout: Timeout (seconds), default 30 seconds
            
        Returns:
            Candlestick data list [{"time": timestamp, "open": o, "high": h, "low": l, "close": c, "volume": v}, ...]
        """
        import asyncio
        import time
        
        async def _fetch_candles():
            """Internal async fetch function"""
            # Use official SDK to get candlestick data, endTime is current timestamp (milliseconds)
            end_time_ms = int(time.time() * 1000)
            
            # SDK call is synchronous, need to run in executor
            loop = asyncio.get_event_loop()
            candles = await loop.run_in_executor(
                None,
                self.info.candles_snapshot,
                coin, interval, lookback, end_time_ms
            )
            return candles
        
        try:
            # Use asyncio.wait_for to add timeout protection
            candles = await asyncio.wait_for(_fetch_candles(), timeout=timeout)
            
            if not candles:
                logger.warning(f"⚠️  No candlestick data retrieved, returning empty list")
                return []
            
            # Convert to standard format
            result = []
            for candle in candles:
                result.append({
                    "time": candle.get('t', 0),  # Timestamp (milliseconds)
                    "open": float(candle.get('o', 0)),
                    "high": float(candle.get('h', 0)),
                    "low": float(candle.get('l', 0)),
                    "close": float(candle.get('c', 0)),
                    "volume": float(candle.get('v', 0))
                })
            
            logger.info(f"📊 Retrieved {len(result)} {interval} candlesticks")
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️  Candlestick data request timeout ({timeout}s), returning empty list")
            return []
        except Exception as e:
            logger.warning(f"⚠️  Failed to get candlestick data: {e}, returning empty list")
            return []

