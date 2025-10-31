"""
Automated Trading Module
Responsible for executing AI decisions and managing positions
"""
import logging
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from ai_models.base_ai import TradingDecision
from trading.hyperliquid.client import HyperliquidClient
from config.settings import settings

logger = logging.getLogger(__name__)


class AutoTrader:
    """Automated Trader"""
    
    def __init__(self, hyperliquid_client: HyperliquidClient):
        """
        Initialize Automated Trader
        
        Args:
            hyperliquid_client: Hyperliquid client
        """
        self.client = hyperliquid_client
        
        # Trading configuration (aggressive swing trading + dynamic leverage)
        self.min_confidence = settings.min_confidence  # Read from config
        self.min_margin = settings.ai_min_margin  # Minimum margin (from config)
        self.max_margin = settings.ai_max_margin  # Maximum margin (from config)
        self.min_leverage = settings.ai_min_leverage  # Minimum leverage (from config)
        self.max_leverage = settings.ai_max_leverage  # Maximum leverage (from config)
        self.stop_loss_pct = settings.ai_stop_loss_pct  # Stop loss percentage (from config)
        self.take_profit_pct = settings.ai_take_profit_pct  # Take profit percentage (from config)
        
        # Position management
        self.positions: Dict[str, Dict] = {}  # {coin: position_info}
        self.trades: List[Dict] = []  # Trading history
        self.max_trades_history = 1000  # Maximum number of trades to keep in memory
        
        # Risk control
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info("🤖 Automated trader initialized")
        logger.info(f"   Minimum confidence threshold: {self.min_confidence}%")
        logger.info(f"   Margin range: ${self.min_margin:.0f} - ${self.max_margin:.0f}")
        logger.info(f"   Leverage range: {self.min_leverage:.0f}x - {self.max_leverage:.0f}x (AI adjusts dynamically based on confidence)")
        logger.info(f"   Stop loss/Take profit: {self.stop_loss_pct*100:.1f}% / {self.take_profit_pct*100:.1f}%")
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            logger.info(f"📅 New trading day, resetting statistics")
            logger.info(f"   Yesterday's PnL: ${self.daily_pnl:,.2f}")
            logger.info(f"   Yesterday's trade count: {self.daily_trade_count}")
            self.daily_pnl = 0.0
            self.daily_trade_count = 0
            self.last_reset_date = today
    
    def check_risk_limits(self) -> bool:
        """
        Check risk limits
        
        Returns:
            Whether trading is allowed
        """
        self.reset_daily_stats()
        
        return True
    
    async def _sync_position_from_exchange(self, coin: str):
        """
        Real-time sync position for specified coin from exchange
        Ensure system records match exchange to avoid trading errors from position desync
        
        Args:
            coin: Coin symbol
        """
        try:
            # Get exchange account info
            account = await self.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            # Find actual position for this coin (need to sum all positions for same coin)
            actual_position = None
            total_size = 0.0
            total_value = 0.0  # For calculating weighted average entry price
            position_side = None
            
            for pos in positions:
                try:
                    # 🔥 Support multi-platform data formats
                    
                    # Hyperliquid format: {"position": {"coin": "BTC", "szi": "0.001", "entryPx": "60000"}}
                    if 'position' in pos:
                        pos_coin = pos['position']['coin']
                        if pos_coin == coin:
                            size = float(pos['position']['szi'])
                            if size != 0:  # Has position
                                # Hyperliquid typically has one position per coin
                                actual_position = {
                                    'coin': coin,
                                    'size': abs(size),
                                    'side': 'long' if size > 0 else 'short',
                                    'entry_px': float(pos['position']['entryPx'])
                                }
                            break  # Hyperliquid has one position per coin
                    
                    # Aster format: {"symbol": "BTCUSDT", "positionAmt": "0.001", "entryPrice": "60000"}
                    elif 'symbol' in pos:
                        symbol = pos['symbol']
                        # Convert symbol to coin (BTCUSDT -> BTC)
                        pos_coin = symbol.replace('USDT', '').replace('USDC', '')
                        
                        if pos_coin == coin:
                            position_amt = float(pos.get('positionAmt', 0))
                            if position_amt != 0:  # Has position
                                entry_price = float(pos.get('entryPrice', 0))
                                
                                # 🔥 Critical fix: Sum all positions for same coin (Aster may have multiple)
                                if position_side is None:
                                    position_side = 'long' if position_amt > 0 else 'short'
                                
                                # Check if direction is consistent (should be consistent normally)
                                current_side = 'long' if position_amt > 0 else 'short'
                                if current_side != position_side:
                                    logger.warning(f"⚠️  Detected hedged positions for same coin: {coin} {position_side} & {current_side}")
                                
                                # Sum quantity and value (for calculating weighted average price)
                                total_size += abs(position_amt)
                                total_value += abs(position_amt) * entry_price
                                
                                logger.debug(f"   Found position: {symbol} {position_amt:+.8f} @ ${entry_price:,.2f}")
                            # ⚠️ Don't break, continue looking for other positions of same coin
                    
                except Exception as e:
                    logger.warning(f"Failed to parse position: {e}, pos={pos}")
                    continue
            
            # 🔥 If summed multiple Aster positions, calculate weighted average entry price
            if total_size > 0 and position_side is not None:
                avg_entry_price = total_value / total_size
                actual_position = {
                    'coin': coin,
                    'size': total_size,
                    'side': position_side,
                    'entry_px': avg_entry_price
                }
                # Log summed position quantity (helps debugging)
                logger.info(f"📊 {coin} total position: {total_size:.8f} {position_side.upper()}, weighted avg price=${avg_entry_price:,.2f}")
            
            # Get system recorded position
            system_position = self.positions.get(coin)
            
            # 🔥 Case 1: Exchange has position but system has no record (manual open or record lost)
            if actual_position and not system_position:
                logger.warning(f"⚠️  Detected exchange position but no system record: {coin}")
                logger.warning(f"    Exchange: {actual_position['side'].upper()} {actual_position['size']:.8f} @ ${actual_position['entry_px']:,.2f}")
                logger.info(f"🔄 Syncing to system record")
                
                self.positions[coin] = {
                    'side': actual_position['side'],
                    'entry_price': actual_position['entry_px'],
                    'size': actual_position['size'],
                    'entry_time': datetime.now(),
                    'confidence': 0,
                    'reasoning': 'Position synced from exchange',
                    'order_id': 'synced'
                }
            
            # 🔥 Case 2: Exchange has no position but system has record (manual close or close failed)
            elif not actual_position and system_position:
                logger.warning(f"⚠️  System has position record but exchange has none: {coin}")
                logger.warning(f"    System record: {system_position['side'].upper()} {system_position['size']:.8f}")
                logger.info(f"🧹 Cleaning system record")
                del self.positions[coin]
            
            # 🔥 Case 3: Both have positions but quantity or direction inconsistent
            elif actual_position and system_position:
                size_diff = abs(actual_position['size'] - system_position['size'])
                side_mismatch = actual_position['side'] != system_position['side']
                
                if size_diff > 0.00001 or side_mismatch:
                    logger.warning(f"⚠️  Position inconsistent: {coin}")
                    logger.warning(f"    System: {system_position['side'].upper()} {system_position['size']:.8f}")
                    logger.warning(f"    Exchange: {actual_position['side'].upper()} {actual_position['size']:.8f}")
                    logger.info(f"🔄 Using exchange actual position as reference, updating system record")
                    
                    self.positions[coin] = {
                        'side': actual_position['side'],
                        'entry_price': actual_position['entry_px'],
                        'size': actual_position['size'],
                        'entry_time': system_position.get('entry_time', datetime.now()),
                        'confidence': system_position.get('confidence', 0),
                        'reasoning': system_position.get('reasoning', 'Synced from exchange'),
                        'order_id': system_position.get('order_id', 'synced')
                    }
            
            # Case 4: Both have no position (normal)
            # No action needed
            
        except Exception as e:
            logger.error(f"❌ Failed to sync position: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def execute_decision(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        current_price: float,
        balance: float
    ) -> Optional[Dict]:
        """
        Execute AI decision
        
        Args:
            coin: Coin symbol
            decision: AI decision
            confidence: Confidence level
            reasoning: Decision reasoning
            current_price: Current price
            balance: Account balance
            
        Returns:
            Trade result (if a trade was executed)
        """
        # Check risk limits
        if not self.check_risk_limits():
            return None
        
        # 🔥 Critical fix: Real-time sync position from exchange, ensure system records match exchange
        await self._sync_position_from_exchange(coin)
        
        # Check if has position
        has_position = coin in self.positions
        
        # Print current position status (for debugging)
        if has_position:
            pos = self.positions[coin]
            logger.info(f"📊 Current position: {coin} {pos['side'].upper()} {pos['size']:.8f} @ ${pos['entry_price']:,.2f}")
        else:
            logger.info(f"📊 Current position: {coin} - No position")
        
        # Check stop loss and take profit
        if has_position:
            position = self.positions[coin]
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            
            # Long position stop loss/take profit
            if position['side'] == 'long':
                if pnl_pct <= -self.stop_loss_pct:
                    logger.warning(f"🛑 Stop loss triggered: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "Stop loss")
                elif pnl_pct >= self.take_profit_pct:
                    logger.info(f"🎯 Take profit triggered: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "Take profit")
            
            # Short position stop loss/take profit
            elif position['side'] == 'short':
                if pnl_pct >= self.stop_loss_pct:
                    logger.warning(f"🛑 Stop loss triggered: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "Stop loss")
                elif pnl_pct <= -self.take_profit_pct:
                    logger.info(f"🎯 Take profit triggered: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "Take profit")
        
        # Insufficient confidence, don't execute new trade
        if confidence < self.min_confidence:
            logger.debug(f"📊 Confidence {confidence:.1f}% < {self.min_confidence}%, not executing trade")
            return None
        
        # Execute trading decision
        if decision == TradingDecision.STRONG_BUY or decision == TradingDecision.BUY:
            if not has_position:
                return await self._open_position(coin, 'long', confidence, reasoning, current_price, balance)
            elif self.positions[coin]['side'] == 'short':
                # Close short position first
                close_result = await self._close_position(coin, current_price, "Reverse signal")
                if close_result is None:
                    logger.error(f"❌ Failed to close short position, canceling long position open")
                    return None
                
                # Get updated balance after closing
                account_info = await self.client.get_account_info()
                new_balance = float(account_info.get('marginSummary', {}).get('accountValue', balance))
                logger.info(f"   Balance updated after close: ${balance:.2f} → ${new_balance:.2f}")
                # Then open long position
                return await self._open_position(coin, 'long', confidence, reasoning, current_price, new_balance)
        
        elif decision == TradingDecision.STRONG_SELL or decision == TradingDecision.SELL:
            if not has_position:
                return await self._open_position(coin, 'short', confidence, reasoning, current_price, balance)
            elif self.positions[coin]['side'] == 'long':
                # Close long position first
                close_result = await self._close_position(coin, current_price, "Reverse signal")
                if close_result is None:
                    logger.error(f"❌ Failed to close long position, canceling short position open")
                    return None
                
                # Get updated balance after closing
                account_info = await self.client.get_account_info()
                new_balance = float(account_info.get('marginSummary', {}).get('accountValue', balance))
                logger.info(f"   Balance updated after close: ${balance:.2f} → ${new_balance:.2f}")
                # Then open short position
                return await self._open_position(coin, 'short', confidence, reasoning, current_price, new_balance)
        
        elif decision == TradingDecision.HOLD:
            logger.debug(f"💤 AI suggests hold")
            return None
        
        return None
    
    async def _open_position(
        self,
        coin: str,
        side: str,
        confidence: float,
        reasoning: str,
        current_price: float,
        balance: float
    ) -> Optional[Dict]:
        """
        Open position
        
        Args:
            coin: Coin symbol
            side: Direction ('long' or 'short')
            confidence: Confidence level
            reasoning: Decision reasoning
            current_price: Current price
            balance: Account balance
            
        Returns:
            Trade result
        """
        try:
            # 🎯 Dynamic leverage strategy: Adjust leverage based on AI confidence (min_leverage - max_leverage)
            # Confidence 50% -> min_leverage, Confidence 100% -> max_leverage (linear mapping)
            leverage = self.min_leverage + ((confidence - 50.0) / 50.0) * (self.max_leverage - self.min_leverage)
            leverage = max(self.min_leverage, min(leverage, self.max_leverage))  # Ensure within config range
            
            # 📊 Calculate margin (linear interpolation based on confidence: 50%->min_margin, 100%->max_margin)
            # Higher confidence uses more margin
            margin_by_confidence = self.min_margin + ((confidence - 50) / 50.0) * (self.max_margin - self.min_margin)
            
            # Limit to configured maximum margin range
            margin = min(margin_by_confidence, self.max_margin)
            
            # Ensure minimum margin requirement is met
            if margin < self.min_margin:
                margin = self.min_margin
                logger.info(f"   ⚠️  Margin adjusted to minimum: ${margin:.2f}")
            
            # Check if balance is sufficient
            if margin > balance:
                logger.warning(f"⚠️  Margin ${margin:.2f} exceeds account balance ${balance:.2f}, cannot open position")
                return None
            
            # 💰 Calculate position value = margin × leverage
            position_value = margin * leverage
            
            # 📉 Calculate quantity (coin quantity)
            size = position_value / current_price
            
            # Ensure minimum trading unit is met
            if size < 0.0001:
                logger.warning(f"⚠️  Position too small, cannot open: {size:.6f} {coin}")
                return None
            
            logger.info("=" * 60)
            logger.info(f"📈 Open {'Long' if side == 'long' else 'Short'} position (AI dynamic leverage strategy)")
            logger.info(f"   Coin: {coin}")
            logger.info(f"   Price: ${current_price:,.2f}")
            logger.info(f"   Confidence: {confidence:.1f}%")
            logger.info(f"   🎯 AI decision leverage: {leverage:.2f}x (based on confidence)")
            logger.info(f"   💰 Margin: ${margin:.2f}")
            logger.info(f"   📊 Position value: ${position_value:.2f} (margin × leverage)")
            logger.info(f"   🔢 Quantity: {size:.5f} {coin}")
            logger.info(f"   💡 Reason: {reasoning[:100]}...")
            logger.info("=" * 60)
            
            # Place order (market order)
            is_buy = (side == 'long')
            
            # Note: Hyperliquid market orders require special handling
            # Using slightly off-market limit order to simulate market order
            order_price = current_price * 1.001 if is_buy else current_price * 0.999
            
            # Prepare order parameters (pass AI calculated leverage)
            order_params = {
                "coin": coin,
                "is_buy": is_buy,
                "size": size,
                "price": order_price,
                "order_type": "Limit",
                "reduce_only": False
            }
            
            # If client supports leverage setting, pass leverage parameter
            if hasattr(self.client, 'update_leverage'):
                # Aster: 1-125x, Hyperliquid: 1-50x
                # Use more relaxed upper limit to be compatible with different platforms
                max_platform_leverage = 125
                leverage_int = max(int(self.min_leverage), min(int(round(leverage)), max_platform_leverage))
                order_params["leverage"] = leverage_int
                platform_name = getattr(self.client, 'platform_name', 'Platform')
                logger.info(f"   🎯 Passing {platform_name} leverage parameter: {leverage_int}x (original: {leverage:.2f}x)")
                logger.info(f"   💰 Expected margin: ${margin:.2f}")
                logger.info(f"   📊 Expected position value: ${position_value:.2f}")
            
            order_result = await self.client.place_order(**order_params)
            
            # Check if order succeeded (adapted for official SDK return format)
            if order_result.get('status') == 'err':
                error_msg = order_result.get('response', 'Unknown error')
                logger.error(f"❌ Order rejected: {error_msg}")
                logger.error(f"   Please check Hyperliquid account status and balance")
                return None
            
            # Check order detailed status
            if order_result.get('status') == 'ok':
                response = order_result.get('response', {})
                data = response.get('data', {})
                statuses = data.get('statuses', [])
                
                if statuses and 'error' in statuses[0]:
                    error_msg = statuses[0]['error']
                    logger.error(f"❌ Order failed: {error_msg}")
                    logger.error(f"   Order details: {order_result}")
                    return None
                
                logger.info(f"✅ Order submitted: {statuses}")
                
                # Extract order ID (adapted for official SDK format)
                order_id = 'unknown'
                if statuses:
                    status = statuses[0]
                    if 'filled' in status:
                        order_id = status['filled'].get('oid', 'unknown')
                    elif 'resting' in status:
                        order_id = status['resting'].get('oid', 'unknown')
            
            # Record position
            self.positions[coin] = {
                'side': side,
                'entry_price': current_price,
                'size': size,
                'position_value': position_value,
                'margin': margin,
                'leverage': leverage,
                'entry_time': datetime.now(),
                'confidence': confidence,
                'reasoning': reasoning,
                'order_id': order_id
            }
            
            # Record trade
            trade_record = {
                'time': datetime.now().isoformat(),
                'coin': coin,
                'action': 'open',
                'side': side,
                'price': current_price,
                'size': size,
                'value': position_value,
                'confidence': confidence,
                'reasoning': reasoning,
                'order_result': order_result
            }
            self.trades.append(trade_record)
            self.daily_trade_count += 1
            
            # Limit trades history to prevent memory leak
            if len(self.trades) > self.max_trades_history:
                self.trades = self.trades[-self.max_trades_history:]
            
            logger.info(f"✅ Position opened successfully: {side.upper()} {size:.5f} {coin} @ ${current_price:,.2f}")
            
            return trade_record
            
        except Exception as e:
            logger.error(f"❌ Failed to open position: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _close_position(
        self,
        coin: str,
        current_price: float,
        reason: str
    ) -> Optional[Dict]:
        """
        Close position
        
        Args:
            coin: Coin symbol
            current_price: Current price
            reason: Close reason
            
        Returns:
            Trade result
        """
        if coin not in self.positions:
            logger.warning(f"⚠️  No position for {coin}, cannot close")
            return None
        
        try:
            position = self.positions[coin]
            
            # 🔑 Critical fix: Get actual position quantity from exchange (supports multi-platform)
            logger.info(f"🔍 Getting actual position quantity for {coin} on exchange...")
            account_info = await self.client.get_account_info()
            actual_size = None
            actual_side = None
            total_size = 0.0
            
            for asset_pos in account_info.get('assetPositions', []):
                # Hyperliquid format
                if 'position' in asset_pos:
                    if asset_pos['position']['coin'] == coin:
                        szi = float(asset_pos['position']['szi'])
                        actual_size = abs(szi)
                        actual_side = 'long' if szi > 0 else 'short'
                        
                        logger.info(f"✅ Exchange actual position: {actual_size:.8f} {coin} {actual_side.upper()}")
                        break
                
                # Aster format (may have multiple positions)
                elif 'symbol' in asset_pos:
                    symbol = asset_pos['symbol']
                    pos_coin = symbol.replace('USDT', '').replace('USDC', '')
                    
                    if pos_coin == coin:
                        position_amt = float(asset_pos.get('positionAmt', 0))
                        if position_amt != 0:
                            # Sum all positions for same coin
                            total_size += abs(position_amt)
                            if actual_side is None:
                                actual_side = 'long' if position_amt > 0 else 'short'
                            
                            logger.debug(f"   Found position: {symbol} {position_amt:+.8f}")
            
            # Aster total position after summing
            if total_size > 0:
                actual_size = total_size
                logger.info(f"✅ Exchange actual position (summed): {actual_size:.8f} {coin} {actual_side.upper()}")
            
            if actual_size is None or actual_size == 0:
                logger.error(f"❌ No position for {coin} on exchange, but system has record!")
                logger.warning(f"⚠️  Cleaning invalid position record in system")
                del self.positions[coin]
                return None
            
            # Verify direction consistency
            if actual_side and actual_side != position['side']:
                logger.warning(f"⚠️  Position direction inconsistent! System record: {position['side']}, actual: {actual_side}")
            
            # Use exchange actual quantity (avoid precision causing remainder)
            close_size = actual_size
            
            # Calculate PnL (using actual quantity)
            if position['side'] == 'long':
                pnl = (current_price - position['entry_price']) * close_size
            else:  # short
                pnl = (position['entry_price'] - current_price) * close_size
            
            pnl_pct = (pnl / (position['entry_price'] * close_size)) * 100 if close_size > 0 else 0
            
            logger.info("=" * 60)
            logger.info(f"📉 Close {'Long' if position['side'] == 'long' else 'Short'} position")
            logger.info(f"   Coin: {coin}")
            logger.info(f"   Entry price: ${position['entry_price']:,.2f}")
            logger.info(f"   Exit price: ${current_price:,.2f}")
            logger.info(f"   System recorded quantity: {position['size']:.8f} {coin}")
            logger.info(f"   Actual close quantity: {close_size:.8f} {coin} ✅")
            logger.info(f"   PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
            logger.info(f"   Reason: {reason}")
            logger.info("=" * 60)
            
            # Place order to close position (reverse operation)
            is_buy = (position['side'] == 'short')  # Close short requires buy
            order_price = current_price * 1.001 if is_buy else current_price * 0.999
            
            # 🔥 Critical: For Aster platform, use market order to ensure complete execution
            platform_name = getattr(self.client, 'platform_name', 'Unknown')
            if platform_name == 'Aster':
                logger.info(f"[Aster] Using market order to close position ensuring complete execution")
                order_result = await self.client.place_order(
                    coin=coin,
                    is_buy=is_buy,
                    size=close_size,  # Use exchange actual quantity
                    price=None,  # Market order
                    order_type="Market",
                    reduce_only=True  # Reduce only
                )
            else:
                order_result = await self.client.place_order(
                    coin=coin,
                    is_buy=is_buy,
                    size=close_size,  # Use exchange actual quantity
                    price=order_price,
                    order_type="Limit",
                    reduce_only=True  # Reduce only
                )
            
            # Check if order succeeded
            if order_result.get('status') == 'err':
                error_msg = order_result.get('response', 'Unknown error')
                logger.error(f"❌ Close order rejected: {error_msg}")
                logger.error(f"   Please check Hyperliquid account status and position")
                return None
            
            # Check order detailed status
            if order_result.get('status') == 'ok':
                response = order_result.get('response', {})
                data = response.get('data', {})
                statuses = data.get('statuses', [])
                
                if statuses and 'error' in statuses[0]:
                    error_msg = statuses[0]['error']
                    logger.error(f"❌ Close order failed: {error_msg}")
                    logger.error(f"   Order details: {order_result}")
                    logger.warning(f"⚠️  System position out of sync with exchange, keeping internal position record")
                    return None
            
            # Record trade (using actual close quantity)
            trade_record = {
                'time': datetime.now().isoformat(),
                'coin': coin,
                'action': 'close',
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'size': close_size,  # Use actual close quantity
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'reason': reason,
                'hold_time': (datetime.now() - position['entry_time']).total_seconds(),
                'order_result': order_result
            }
            self.trades.append(trade_record)
            self.daily_trade_count += 1
            self.daily_pnl += pnl
            
            # Limit trades history to prevent memory leak
            if len(self.trades) > self.max_trades_history:
                self.trades = self.trades[-self.max_trades_history:]
            
            # Remove position
            del self.positions[coin]
            
            logger.info(f"✅ Position closed successfully: {position['side'].upper()} {close_size:.8f} {coin}, PnL: ${pnl:+.2f}")
            
            # 🔥 Verify close result (especially Aster platform)
            if platform_name == 'Aster':
                logger.info(f"[Aster] Waiting 2 seconds to verify close result...")
                await asyncio.sleep(2)  # Wait for order to be fully processed
                
                # Get position again to verify
                verify_account = await self.client.get_account_info()
                remaining_size = None
                for asset_pos in verify_account.get('assetPositions', []):
                    if asset_pos['position']['coin'] == coin:
                        szi = float(asset_pos['position']['szi'])
                        remaining_size = abs(szi)
                        if remaining_size > 0:
                            logger.warning(f"⚠️  [Aster] Remaining position after close: {remaining_size:.8f} {coin}")
                            logger.warning(f"⚠️  [Aster] Possible reasons: Partial fill or precision issues")
                        else:
                            logger.info(f"✅ [Aster] Close verification successful: No remaining position")
                        break
                
                if remaining_size is None:
                    logger.info(f"✅ [Aster] Close verification successful: No position for this coin")
            
            return trade_record
            
        except Exception as e:
            logger.error(f"❌ Failed to close position: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_position_info(self, coin: str) -> Optional[Dict]:
        """Get position info"""
        return self.positions.get(coin)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all positions"""
        return self.positions
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        return self.trades[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_pnl': 0.0
            }
        
        closed_trades = [t for t in self.trades if t['action'] == 'close']
        
        if not closed_trades:
            return {
                'total_trades': len(self.trades),
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_pnl': 0.0
            }
        
        total_pnl = sum(t['pnl'] for t in closed_trades)
        winning_trades = sum(1 for t in closed_trades if t['pnl'] > 0)
        
        return {
            'total_trades': len(closed_trades),
            'total_pnl': total_pnl,
            'win_rate': (winning_trades / len(closed_trades) * 100) if closed_trades else 0.0,
            'avg_pnl': total_pnl / len(closed_trades) if closed_trades else 0.0,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trade_count
        }

