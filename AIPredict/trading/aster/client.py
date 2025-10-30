"""
Aster Trading Client Implementation
Based on AsterDex Futures API V3
Documentation: https://github.com/asterdex/api-docs
"""
import logging
import time
import asyncio
import json
import math
from typing import Dict, List, Optional
import aiohttp
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode
from web3 import Web3
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from trading.base_client import BaseExchangeClient
from trading.precision_config import precision_config
from config.settings import settings

logger = logging.getLogger(__name__)


class AsterClient(BaseExchangeClient):
    """Aster Trading Client - Based on AsterDex Futures API V3"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        Initialize Aster Client
        
        Args:
            private_key: Ethereum private key (with or without 0x prefix)
            testnet: Whether to use testnet
        
        Note: Need to create API Wallet (AGENT) from https://www.asterdex.com/en/api-wallet
        """
        super().__init__(private_key, testnet)
        
        # Ensure private key format is correct
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # API base URL (AsterDex official)
        self.base_url = "https://fapi.asterdex.com"
        
        # Generate account from private key
        account = Account.from_key(private_key)
        self.address = account.address  # This is the user address
        self.account = account
        self.private_key = private_key
        
        # Note: AsterDex requires signer and user separation
        # signer is API Wallet address, need to get from https://www.asterdex.com/en/api-wallet
        # Default to use same address here, need to configure correct signer in actual use
        self.signer = account.address
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"✅ Aster client initialized successfully")
        logger.info(f"   User address: {self.address}")
        logger.info(f"   Signer address: {self.signer}")
        logger.info(f"   ⚠️  Please ensure API Wallet is created at https://www.asterdex.com/en/api-wallet")
    
    @property
    def platform_name(self) -> str:
        """Platform name"""
        return "Aster"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _trim_dict(self, my_dict: Dict) -> Dict:
        """Convert dictionary values to strings (AsterDex requirement)"""
        for key in my_dict:
            value = my_dict[key]
            if isinstance(value, list):
                new_value = []
                for item in value:
                    if isinstance(item, dict):
                        new_value.append(json.dumps(self._trim_dict(item)))
                    else:
                        new_value.append(str(item))
                my_dict[key] = json.dumps(new_value)
                continue
            if isinstance(value, dict):
                my_dict[key] = json.dumps(self._trim_dict(value))
                continue
            my_dict[key] = str(value)
        return my_dict
    
    def _trim_param(self, params: Dict, nonce: int) -> str:
        """Generate signature message hash"""
        self._trim_dict(params)
        json_str = json.dumps(params, sort_keys=True).replace(' ', '').replace('\'', '\"')
        
        # Use eth_abi encoding
        encoded = encode(
            ['string', 'address', 'address', 'uint256'],
            [json_str, self.address, self.signer, nonce]
        )
        
        # Calculate keccak256 hash
        keccak_hex = Web3.keccak(encoded).hex()
        return keccak_hex
    
    def _sign_request(self, params: Dict) -> Dict:
        """
        Sign request (AsterDex signature algorithm)
        
        Args:
            params: Request parameters
            
        Returns:
            Signed parameters (includes signature, nonce, user, signer)
        """
        # Generate nonce (microsecond-level timestamp)
        nonce = math.trunc(time.time() * 1000000)
        
        # Remove None values
        params = {key: value for key, value in params.items() if value is not None}
        
        # Add required parameters
        params['recvWindow'] = 50000
        params['timestamp'] = int(round(time.time() * 1000))
        
        # Generate signature message
        msg = self._trim_param(params.copy(), nonce)
        signable_msg = encode_defunct(hexstr=msg)
        signed_message = Account.sign_message(signable_message=signable_msg, private_key=self.private_key)
        
        # Add signature-related parameters
        params['nonce'] = nonce
        params['user'] = self.address
        params['signer'] = self.signer
        params['signature'] = '0x' + signed_message.signature.hex()
        
        return params
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        signed: bool = False
    ) -> Dict:
        """
        Send API request
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Request parameters
            signed: Whether signature is required
            
        Returns:
            Response data
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        # If signature is required, add signature parameters
        if signed:
            params = self._sign_request(params)
        
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'AIPredict/1.0'
            }
            
            if method == "GET":
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Aster] API error {response.status}: {error_text}")
                    response.raise_for_status()
                    return await response.json()
            elif method == "POST":
                async with session.post(url, data=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Aster] API error {response.status}: {error_text}")
                    response.raise_for_status()
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, data=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Aster] API error {response.status}: {error_text}")
                    response.raise_for_status()
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        except aiohttp.ClientError as e:
            logger.error(f"[Aster] API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"[Aster] Request exception: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            # Get account information (V3)
            result = await self._request("GET", "/fapi/v3/account", signed=True)
            
            # Get balance (sum USDC + USDT, use marginBalance including unrealized PnL)
            # Aster uses USDT as contract margin, need to count both USDC and USDT
            total_wallet_balance = 0.0
            total_unrealized_profit = 0.0
            total_margin_balance = 0.0
            total_available_balance = 0.0
            
            if 'assets' in result:
                for asset in result['assets']:
                    asset_type = asset.get('asset', '')
                    if asset_type in ['USDC', 'USDT']:  # Count USDC and USDT balance
                        wallet_balance = float(asset.get('walletBalance', 0))
                        margin_balance = float(asset.get('marginBalance', 0))  # marginBalance = walletBalance + unrealizedProfit
                        unrealized_profit = float(asset.get('unrealizedProfit', 0))
                        available_balance = float(asset.get('availableBalance', 0))
                        
                        # Use marginBalance as actual balance (includes unrealized PnL)
                        total_wallet_balance += wallet_balance
                        total_margin_balance += margin_balance
                        total_unrealized_profit += unrealized_profit
                        total_available_balance += available_balance
                        
                        logger.info(f"[Aster] {asset_type} - Wallet:{wallet_balance:.6f} Margin:{margin_balance:.6f} UnrealizedPnL:{unrealized_profit:.6f}")
            
            # Output total balance (USDC + USDT)
            logger.info(f"[Aster] 📊 Total contract account balance: ${total_margin_balance:.6f} (USDC+USDT)")
            
            # Filter positions with positionAmt > 0
            all_positions = result.get('positions', [])
            active_positions = []
            for pos in all_positions:
                if float(pos.get('positionAmt', 0)) != 0:
                    # Convert to Hyperliquid-compatible nested format
                    # Hyperliquid uses nested 'position' object
                    symbol = pos.get('symbol', '')
                    # Convert BTCUSDT -> BTC for Hyperliquid compatibility
                    coin = symbol.replace('USDT', '').replace('USDC', '') if symbol else ''
                    position_side = pos.get('positionSide', 'BOTH')
                    leverage = {
                        'type': 'isolated' if pos.get('isolated', False) else 'cross',
                        'value': int(pos.get('leverage', '1'))
                    }
                    
                    formatted_pos = {
                        'type': 'oneWay' if position_side == 'BOTH' else 'hedge',
                        'position': {
                            'coin': coin,
                            'szi': pos.get('positionAmt', '0'),
                            'entryPx': pos.get('entryPrice', '0'),
                            'leverage': leverage,
                            'positionValue': pos.get('notional', '0'),
                            'unrealizedPnl': pos.get('unrealizedProfit', '0'),
                        },
                        # Keep original Aster fields for reference
                        'aster_raw': pos
                    }
                    active_positions.append(formatted_pos)
            
            # Standardized return format, compatible with Hyperliquid format, includes Aster specific info
            # Use marginBalance (includes unrealized PnL) as account value
            return {
                "marginSummary": {
                    "accountValue": total_margin_balance  # Use marginBalance instead of walletBalance
                },
                "assetPositions": active_positions,
                "withdrawable": total_available_balance,  # Compatible with Hyperliquid format
                # Aster-specific fields
                "equity": total_margin_balance,
                "availableBalance": total_available_balance,
                "totalPositionInitialMargin": float(result.get('totalPositionInitialMargin', 0)),
                "totalUnrealizedProfit": total_unrealized_profit,
                "positions": active_positions,
                "raw": result
            }
        except Exception as e:
            logger.error(f"[Aster] Failed to get account info: {e}")
            return {"marginSummary": {"accountValue": 0}, "assetPositions": []}
    
    async def get_market_data(self, coin: str) -> Dict:
        """Get market data"""
        try:
            # Convert coin format (BTC -> BTCUSDT)
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            # Get 24-hour ticker
            result = await self._request("GET", "/fapi/v1/ticker/24hr", params={"symbol": symbol})
            
            return {
                "coin": coin,
                "price": float(result.get('lastPrice', 0)),
                "mark_price": float(result.get('lastPrice', 0)),  # Aster doesn't have separate mark price endpoint
                "funding_rate": 0.0,  # Need to fetch separately
                "open_interest": float(result.get('openInterest', 0)),
                "change_24h": float(result.get('priceChangePercent', 0)),
                "volume": float(result.get('volume', 0)),
                "raw_ctx": result
            }
        except Exception as e:
            logger.error(f"[Aster] Failed to get market data: {e}")
            raise
    
    async def get_orderbook(self, coin: str) -> Dict:
        """Get order book"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request("GET", "/fapi/v1/depth", params={"symbol": symbol, "limit": 20})
            
            bids = [[float(b[0]), float(b[1])] for b in result.get('bids', [])]
            asks = [[float(a[0]), float(a[1])] for a in result.get('asks', [])]
            
            return {"bids": bids, "asks": asks}
        except Exception as e:
            logger.error(f"[Aster] Failed to get order book: {e}")
            return {"bids": [], "asks": []}
    
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request("GET", "/fapi/v1/trades", params={"symbol": symbol, "limit": limit})
            
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"[Aster] Failed to get recent trades: {e}")
            return []
    
    def update_leverage(self, coin: str, leverage: int) -> Dict:
        """
        Update leverage (synchronous method)
        Args:
            coin: Coin symbol
            leverage: Leverage multiplier (1-125)
        Returns:
            Update result
        """
        import asyncio
        try:
            # Create new event loop to run async method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.update_leverage_async(coin, leverage))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"❌ [Aster] Failed to update leverage: {e}")
            raise

    async def update_leverage_async(self, coin: str, leverage: int) -> Dict:
        """
        Update leverage (asynchronous method)
        Args:
            coin: Coin symbol
            leverage: Leverage multiplier (1-125)
        Returns:
            Update result
        """
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            params = {
                "symbol": symbol,
                "leverage": leverage
            }
            
            # Use v3 endpoint (v1 endpoint returns 401 on Aster)
            result = await self._request("POST", "/fapi/v3/leverage", params=params, signed=True)
            logger.info(f"✅ [Aster] Leverage updated: {coin} -> {leverage}x (returned: {result})")
            return result
        except Exception as e:
            logger.error(f"❌ [Aster] Failed to update leverage: {e}")
            raise

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: Optional[float],
        order_type: str = "Limit",
        reduce_only: bool = False,
        leverage: int = None
    ) -> Dict:
        """
        Place order (supports leverage setting)
        Args:
            coin: Coin symbol
            is_buy: Whether to buy
            size: Quantity
            price: Price (None for market order, will fetch current market price)
            order_type: Order type
            reduce_only: Whether to reduce only
            leverage: Leverage multiplier (optional, will set leverage before placing order if provided)
        """
        try:
            # Initialize effective_leverage for later use
            effective_leverage = leverage if leverage is not None else 1
            
            # Aster platform risk control: leverage limits and margin requirements
            if not reduce_only:
                # 1. Leverage limit: use configured maximum leverage
                max_leverage = int(settings.ai_max_leverage)
                if leverage is not None and leverage > max_leverage:
                    error_msg = f"❌ [Aster] Leverage cannot exceed {max_leverage}x (current: {leverage}x, config: AI_MAX_LEVERAGE={settings.ai_max_leverage})"
                    logger.error(error_msg)
                    return {"status": "err", "response": error_msg}
                
                # 2. Get actual price (for margin calculation)
                actual_price = price
                if actual_price is None:
                    # If price not specified, get current market price
                    orderbook = await self.get_orderbook(coin)
                    bids = orderbook.get("bids", [])
                    asks = orderbook.get("asks", [])
                    
                    if is_buy:
                        actual_price = float(asks[0][0]) if asks else None
                    else:
                        actual_price = float(bids[0][0]) if bids else None
                    
                    if actual_price is None:
                        error_msg = f"❌ [Aster] Unable to get market price for {coin}"
                        logger.error(error_msg)
                        return {"status": "err", "response": error_msg}
                
                # 3. Calculate margin: margin = (size * price) / leverage
                position_value = size * actual_price
                required_margin = position_value / effective_leverage
                
                # 4. Margin requirement: use configured minimum margin
                min_margin = settings.ai_min_margin
                if required_margin < min_margin:
                    error_msg = (
                        f"❌ [Aster] Margin below minimum requirement\n"
                        f"   Position value: ${position_value:.2f}\n"
                        f"   Leverage: {effective_leverage}x\n"
                        f"   Required margin: ${required_margin:.2f}\n"
                        f"   Minimum margin: ${min_margin:.2f} (config: AI_MIN_MARGIN={settings.ai_min_margin})"
                    )
                    logger.error(error_msg)
                    return {"status": "err", "response": error_msg}
                
                logger.info(
                    f"[Aster] ✅ Risk control check passed - "
                    f"Leverage: {effective_leverage}x, "
                    f"Margin: ${required_margin:.2f} (min: ${min_margin})"
                )
            
            # If leverage is specified, set leverage first (must succeed, otherwise cancel order)
            if leverage is not None and not reduce_only:
                try:
                    # 🔍 Check account available balance first
                    account_info = await self.get_account_info()
                    available_balance = float(account_info.get('availableBalance', 0))
                    total_balance = float(account_info.get('marginSummary', {}).get('accountValue', 0))
                    
                    logger.info(f"[Aster] 💰 Account balance check:")
                    logger.info(f"   Total balance (accountValue): ${total_balance:.2f}")
                    logger.info(f"   Available balance (availableBalance): ${available_balance:.2f}")
                    logger.info(f"   Used margin: ${total_balance - available_balance:.2f}")
                    logger.info(f"   Required margin: ${required_margin:.2f}")
                    logger.info(f"   Position value: ${position_value:.2f}")
                    logger.info(f"   Leverage: {leverage}x")
                    
                    # Output position info (if any)
                    if account_info.get('positions'):
                        logger.info(f"   Current positions: {len(account_info['positions'])} positions")
                        for pos in account_info['positions'][:3]:  # Show only first 3
                            logger.info(f"      - {pos.get('symbol', 'Unknown')}: quantity={pos.get('positionAmt', 0)}")
                    else:
                        logger.info(f"   Current positions: 0 positions")
                    
                    # Check if available balance is sufficient (5% buffer reserved)
                    required_with_buffer = required_margin * 1.05
                    if available_balance < required_with_buffer:
                        # Insufficient available balance, try to reduce leverage or position size
                        logger.warning(f"⚠️ [Aster] Insufficient available balance (${available_balance:.2f} < ${required_with_buffer:.2f})")
                        
                        # Option 1: Calculate maximum usable leverage based on available balance
                        if available_balance > min_margin:
                            max_usable_leverage = int(position_value / available_balance)
                            if max_usable_leverage >= 1:
                                logger.info(f"🔧 [Aster] Auto-adjust leverage: {leverage}x -> {max_usable_leverage}x")
                                leverage = max_usable_leverage
                                required_margin = position_value / leverage
                                logger.info(f"   Adjusted margin: ${required_margin:.2f}")
                            else:
                                error_msg = (
                                    f"❌ [Aster] Insufficient balance to open position\n"
                                    f"   Available balance: ${available_balance:.2f}\n"
                                    f"   Required margin: ${required_with_buffer:.2f}\n"
                                    f"   Suggestion: Reduce position size or increase account balance"
                                )
                                logger.error(error_msg)
                                return {"status": "err", "response": error_msg}
                        else:
                            error_msg = (
                                f"❌ [Aster] Insufficient account balance, cannot open position\n"
                                f"   Total balance: ${total_balance:.2f}\n"
                                f"   Available balance: ${available_balance:.2f}\n"
                                f"   Used: ${total_balance - available_balance:.2f}\n"
                                f"   Required margin: ${required_with_buffer:.2f}\n"
                                f"   Minimum margin requirement: ${min_margin:.2f}\n"
                                f"   💡 Suggestion: Close some positions to free up margin"
                            )
                            logger.error(error_msg)
                            return {"status": "err", "response": error_msg}
                    
                    logger.info(f"[Aster] 🎯 Preparing to set leverage: {coin} -> {leverage}x")
                    leverage_result = await self.update_leverage_async(coin, leverage)
                    logger.info(f"[Aster] ✅ Leverage set successfully: {leverage}x, returned: {leverage_result}")
                    
                    # Verify leverage was actually set successfully
                    if isinstance(leverage_result, dict):
                        actual_leverage = leverage_result.get('leverage')
                        if actual_leverage and int(actual_leverage) != leverage:
                            logger.warning(f"⚠️ [Aster] Leverage value mismatch: expected {leverage}x, actual {actual_leverage}x")
                except Exception as e:
                    error_msg = f"❌ [Aster] Failed to set leverage, canceling order: {e}"
                    logger.error(error_msg)
                    return {"status": "err", "response": error_msg}
            
            # Convert coin format
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            # Use unified precision config to process quantity
            size_rounded, _ = precision_config.format_aster_quantity(
                coin, size, round_down=(not reduce_only)
            )
            
            # Process price
            if price is None:
                # Market order
                orderbook = await self.get_orderbook(coin)
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                
                if is_buy:
                    price = float(asks[0][0]) if asks else None
                else:
                    price = float(bids[0][0]) if bids else None
                
                if price is None:
                    raise ValueError(f"Unable to get market price for {coin}")
                
                logger.info(f"[Aster] Market order price: ${price:,.2f}")
            
            # Use unified precision config to process price
            price_rounded, _ = precision_config.format_aster_price(coin, price)
            
            # Validate order parameters
            is_valid, error_msg = precision_config.validate_aster_order(coin, size_rounded, price_rounded)
            if not is_valid:
                raise ValueError(f"Order parameter validation failed: {error_msg}")
            
            # Final order information
            final_position_value = size_rounded * (price_rounded or actual_price)
            final_margin = final_position_value / effective_leverage if effective_leverage > 0 else final_position_value
            
            logger.info("=" * 70)
            logger.info(f"[Aster] 📊 Final order parameters:")
            logger.info(f"   Trading pair: {symbol}")
            logger.info(f"   Direction: {'Buy (Long)' if is_buy else 'Sell (Short)'}")
            logger.info(f"   Quantity: {size_rounded} {coin}")
            logger.info(f"   Price: ${price_rounded if price_rounded else actual_price:,.2f}")
            logger.info(f"   🎯 Leverage: {effective_leverage}x")
            logger.info(f"   💰 Expected margin: ${final_margin:.2f}")
            logger.info(f"   📊 Expected position value: ${final_position_value:.2f}")
            logger.info("=" * 70)
            
            # Build order request (AsterDex V3 format)
            order_params = {
                "symbol": symbol,
                "positionSide": "BOTH",  # One-way position mode
                "side": "BUY" if is_buy else "SELL",
                "type": "LIMIT" if order_type == "Limit" else "MARKET",
                "quantity": str(size_rounded),
                "reduceOnly": reduce_only
            }
            
            # Market orders don't need price and timeInForce
            if order_type == "Limit":
                order_params["price"] = price_rounded  # Already processed precision according to API specs
                order_params["timeInForce"] = "GTC" if not reduce_only else "IOC"
            
            # Debug: print order parameters
            logger.info(f"[Aster] 🔍 Order parameters: {order_params}")
            
            # Send order request (use V3 endpoint)
            result = await self._request("POST", "/fapi/v3/order", params=order_params, signed=True)
            
            logger.info(f"[Aster] 📝 Order result: {result}")
            
            # Standardized return format
            if result.get('orderId'):
                return {
                    "status": "ok",
                    "response": {
                        "data": {
                            "statuses": [{
                                "filled": {
                                    "oid": result.get('orderId')
                                }
                            }]
                        }
                    },
                    "raw": result
                }
            else:
                return {"status": "err", "response": result}
            
        except Exception as e:
            logger.error(f"[Aster] ❌ Order placement failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "err", "response": str(e)}
    
    async def cancel_order(self, coin: str, order_id: str) -> Dict:
        """Cancel order"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request(
                "DELETE",
                "/fapi/v3/order",  # Use v3 endpoint (v1 returns 401 on Aster when signature required)
                params={"symbol": symbol, "orderId": order_id},
                signed=True
            )
            return result
        except Exception as e:
            logger.error(f"[Aster] Failed to cancel order: {e}")
            return {"status": "err", "response": str(e)}
    
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """Get open orders"""
        try:
            params = {}
            if coin:
                symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
                params["symbol"] = symbol
            
            # Use v3 endpoint (v1 returns 401 on Aster when signature required)
            result = await self._request("GET", "/fapi/v3/openOrders", params=params, signed=True)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"[Aster] Failed to get open orders: {e}")
            return []
    
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """Get user historical trades"""
        try:
            params = {"limit": limit}
            if start_time_ms:
                params["startTime"] = start_time_ms
            
            # Use v3 endpoint (v1 returns 401 on Aster when signature required)
            result = await self._request("GET", "/fapi/v3/userTrades", params=params, signed=True)
            
            fills = result if isinstance(result, list) else []
            logger.info(f"[Aster] 📊 Retrieved {len(fills)} historical trade records")
            return fills
        except Exception as e:
            logger.error(f"[Aster] Failed to get historical trades: {e}")
            return []
    
    async def get_candles(
        self,
        coin: str,
        interval: str = "15m",
        lookback: int = 100,
        timeout: int = 30
    ) -> List[Dict]:
        """Get candlestick data"""
        async def _fetch_candles():
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": lookback
            }
            result = await self._request("GET", "/fapi/v1/klines", params=params)
            
            # Convert AsterDex candlestick format
            # [openTime, open, high, low, close, volume, closeTime, ...]
            candles = []
            if isinstance(result, list):
                for candle in result:
                    candles.append({
                        "time": int(candle[0]),  # openTime (milliseconds)
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5])
                    })
            
            logger.info(f"[Aster] 📊 Retrieved {len(candles)} {interval} candlesticks")
            return candles
        
        try:
            candles = await asyncio.wait_for(_fetch_candles(), timeout=timeout)
            return candles
        except asyncio.TimeoutError:
            logger.warning(f"[Aster] ⚠️  Candlestick data request timeout ({timeout}s)")
            return []
        except Exception as e:
            logger.warning(f"[Aster] ⚠️  Failed to get candlestick data: {e}")
            return []
    
    async def close_session(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[Aster] ✅ Session closed")
