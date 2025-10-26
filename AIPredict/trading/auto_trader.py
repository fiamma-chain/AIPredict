"""
自动交易模块
负责执行AI决策并管理持仓
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
    """自动交易器"""
    
    def __init__(self, hyperliquid_client: HyperliquidClient):
        """
        初始化自动交易器
        
        Args:
            hyperliquid_client: Hyperliquid 客户端
        """
        self.client = hyperliquid_client
        
        # 交易配置（激进波段交易 + 动态杠杆）
        self.min_confidence = settings.min_confidence  # 从配置读取
        self.min_margin = settings.ai_min_margin  # 最小保证金（从配置读取）
        self.max_margin = settings.ai_max_margin  # 最大保证金（从配置读取）
        self.min_leverage = settings.ai_min_leverage  # 最小杠杆（从配置读取）
        self.max_leverage = settings.ai_max_leverage  # 最大杠杆（从配置读取）
        self.stop_loss_pct = settings.ai_stop_loss_pct  # 止损比例（从配置读取）
        self.take_profit_pct = settings.ai_take_profit_pct  # 止盈比例（从配置读取）
        
        # 持仓管理
        self.positions: Dict[str, Dict] = {}  # {coin: position_info}
        self.trades: List[Dict] = []  # 交易历史
        
        # 风险控制
        self.daily_loss_limit = 10.0  # 每日最大亏损（USDC）
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info("🤖 自动交易器初始化完成")
        logger.info(f"   最小信心阈值: {self.min_confidence}%")
        logger.info(f"   保证金范围: ${self.min_margin:.0f} - ${self.max_margin:.0f}")
        logger.info(f"   杠杆范围: {self.min_leverage:.0f}x - {self.max_leverage:.0f}x (AI根据信心度动态调整)")
        logger.info(f"   止损/止盈: {self.stop_loss_pct*100:.1f}% / {self.take_profit_pct*100:.1f}%")
    
    def reset_daily_stats(self):
        """重置每日统计"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            logger.info(f"📅 新的交易日，重置统计")
            logger.info(f"   昨日盈亏: ${self.daily_pnl:,.2f}")
            logger.info(f"   昨日交易次数: {self.daily_trade_count}")
            self.daily_pnl = 0.0
            self.daily_trade_count = 0
            self.last_reset_date = today
    
    def check_risk_limits(self) -> bool:
        """
        检查风险限制
        
        Returns:
            是否允许交易
        """
        self.reset_daily_stats()
        
        # 检查每日亏损限制
        if self.daily_pnl < -self.daily_loss_limit:
            logger.warning(f"⚠️  已达每日亏损限制: ${self.daily_pnl:,.2f}")
            return False
        
        return True
    
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
        执行AI决策
        
        Args:
            coin: 币种
            decision: AI决策
            confidence: 信心度
            reasoning: 决策理由
            current_price: 当前价格
            balance: 账户余额
            
        Returns:
            交易结果（如果执行了交易）
        """
        # 检查风险限制
        if not self.check_risk_limits():
            return None
        
        # 检查是否有持仓
        has_position = coin in self.positions
        
        # 检查止损止盈
        if has_position:
            position = self.positions[coin]
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            
            # 多头止损止盈
            if position['side'] == 'long':
                if pnl_pct <= -self.stop_loss_pct:
                    logger.warning(f"🛑 触发止损: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "止损")
                elif pnl_pct >= self.take_profit_pct:
                    logger.info(f"🎯 触发止盈: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "止盈")
            
            # 空头止损止盈
            elif position['side'] == 'short':
                if pnl_pct >= self.stop_loss_pct:
                    logger.warning(f"🛑 触发止损: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "止损")
                elif pnl_pct <= -self.take_profit_pct:
                    logger.info(f"🎯 触发止盈: {pnl_pct*100:.2f}%")
                    return await self._close_position(coin, current_price, "止盈")
        
        # 信心度不足，不执行新交易
        if confidence < self.min_confidence:
            logger.debug(f"📊 信心度 {confidence:.1f}% < {self.min_confidence}%，不执行交易")
            return None
        
        # 执行交易决策
        if decision == TradingDecision.STRONG_BUY or decision == TradingDecision.BUY:
            if not has_position:
                return await self._open_position(coin, 'long', confidence, reasoning, current_price, balance)
            elif self.positions[coin]['side'] == 'short':
                # 先平空仓
                await self._close_position(coin, current_price, "反向信号")
                # 平仓后重新获取余额
                account_info = await self.client.get_account_info()
                new_balance = float(account_info.get('marginSummary', {}).get('accountValue', balance))
                logger.info(f"   平仓后余额更新: ${balance:.2f} → ${new_balance:.2f}")
                # 再开多仓
                return await self._open_position(coin, 'long', confidence, reasoning, current_price, new_balance)
        
        elif decision == TradingDecision.STRONG_SELL or decision == TradingDecision.SELL:
            if not has_position:
                return await self._open_position(coin, 'short', confidence, reasoning, current_price, balance)
            elif self.positions[coin]['side'] == 'long':
                # 先平多仓
                await self._close_position(coin, current_price, "反向信号")
                # 平仓后重新获取余额
                account_info = await self.client.get_account_info()
                new_balance = float(account_info.get('marginSummary', {}).get('accountValue', balance))
                logger.info(f"   平仓后余额更新: ${balance:.2f} → ${new_balance:.2f}")
                # 再开空仓
                return await self._open_position(coin, 'short', confidence, reasoning, current_price, new_balance)
        
        elif decision == TradingDecision.HOLD:
            logger.debug(f"💤 AI 建议观望")
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
        开仓
        
        Args:
            coin: 币种
            side: 方向 ('long' 或 'short')
            confidence: 信心度
            reasoning: 决策理由
            current_price: 当前价格
            balance: 账户余额
            
        Returns:
            交易结果
        """
        try:
            # 🎯 动态杠杆策略：根据AI信心度调整杠杆（min_leverage - max_leverage）
            # 信心度50% -> min_leverage, 信心度100% -> max_leverage (线性映射)
            leverage = self.min_leverage + ((confidence - 50.0) / 50.0) * (self.max_leverage - self.min_leverage)
            leverage = max(self.min_leverage, min(leverage, self.max_leverage))  # 确保在配置范围内
            
            # 📊 计算保证金（根据信心度线性插值：50%->min_margin, 100%->max_margin）
            # 信心度越高，使用的保证金越多
            margin_by_confidence = self.min_margin + ((confidence - 50) / 50.0) * (self.max_margin - self.min_margin)
            
            # 限制在配置的最大保证金范围内
            margin = min(margin_by_confidence, self.max_margin)
            
            # 确保满足最小保证金要求
            if margin < self.min_margin:
                margin = self.min_margin
                logger.info(f"   ⚠️  保证金已调整至最小值: ${margin:.2f}")
            
            # 检查余额是否充足
            if margin > balance:
                logger.warning(f"⚠️  保证金${margin:.2f}超过账户余额${balance:.2f}，无法开仓")
                return None
            
            # 💰 计算仓位价值 = 保证金 × 杠杆倍数
            position_value = margin * leverage
            
            # 📉 计算数量（币的数量）
            size = position_value / current_price
            
            # 确保满足最小交易单位
            if size < 0.0001:
                logger.warning(f"⚠️  仓位太小，无法开仓: {size:.6f} {coin}")
                return None
            
            logger.info("=" * 60)
            logger.info(f"📈 开{'多' if side == 'long' else '空'}仓 (AI动态杠杆策略)")
            logger.info(f"   币种: {coin}")
            logger.info(f"   价格: ${current_price:,.2f}")
            logger.info(f"   信心度: {confidence:.1f}%")
            logger.info(f"   🎯 AI决策杠杆: {leverage:.2f}x (基于信心度)")
            logger.info(f"   💰 保证金: ${margin:.2f}")
            logger.info(f"   📊 仓位价值: ${position_value:.2f} (保证金 × 杠杆)")
            logger.info(f"   🔢 数量: {size:.5f} {coin}")
            logger.info(f"   💡 理由: {reasoning[:100]}...")
            logger.info("=" * 60)
            
            # 下单（市价单）
            is_buy = (side == 'long')
            
            # 注意：Hyperliquid 使用市价单需要特殊处理
            # 这里使用略微偏离市场价的限价单来模拟市价单
            order_price = current_price * 1.001 if is_buy else current_price * 0.999
            
            # 准备下单参数（传入AI计算的杠杆）
            order_params = {
                "coin": coin,
                "is_buy": is_buy,
                "size": size,
                "price": order_price,
                "order_type": "Limit",
                "reduce_only": False
            }
            
            # 如果客户端支持杠杆设置，传入杠杆参数
            if hasattr(self.client, 'update_leverage'):
                # Aster: 1-125x, Hyperliquid: 1-50x
                # 使用更宽松的上限以兼容不同平台
                max_platform_leverage = 125
                leverage_int = max(int(self.min_leverage), min(int(round(leverage)), max_platform_leverage))
                order_params["leverage"] = leverage_int
                platform_name = getattr(self.client, 'platform_name', 'Platform')
                logger.info(f"   🎯 传递{platform_name}杠杆参数: {leverage_int}x (原始: {leverage:.2f}x)")
                logger.info(f"   💰 预期保证金: ${margin:.2f}")
                logger.info(f"   📊 预期仓位价值: ${position_value:.2f}")
            
            order_result = await self.client.place_order(**order_params)
            
            # 检查订单是否成功（适配官方SDK返回格式）
            if order_result.get('status') == 'err':
                error_msg = order_result.get('response', 'Unknown error')
                logger.error(f"❌ 订单被拒绝: {error_msg}")
                logger.error(f"   请检查 Hyperliquid 账户状态和余额")
                return None
            
            # 检查订单详细状态
            if order_result.get('status') == 'ok':
                response = order_result.get('response', {})
                data = response.get('data', {})
                statuses = data.get('statuses', [])
                
                if statuses and 'error' in statuses[0]:
                    error_msg = statuses[0]['error']
                    logger.error(f"❌ 订单失败: {error_msg}")
                    logger.error(f"   订单详情: {order_result}")
                    return None
                
                logger.info(f"✅ 订单已提交: {statuses}")
                
                # 提取订单ID（适配官方SDK格式）
                order_id = 'unknown'
                if statuses:
                    status = statuses[0]
                    if 'filled' in status:
                        order_id = status['filled'].get('oid', 'unknown')
                    elif 'resting' in status:
                        order_id = status['resting'].get('oid', 'unknown')
            
            # 记录持仓
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
            
            # 记录交易
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
            
            logger.info(f"✅ 开仓成功: {side.upper()} {size:.5f} {coin} @ ${current_price:,.2f}")
            
            return trade_record
            
        except Exception as e:
            logger.error(f"❌ 开仓失败: {e}")
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
        平仓
        
        Args:
            coin: 币种
            current_price: 当前价格
            reason: 平仓原因
            
        Returns:
            交易结果
        """
        if coin not in self.positions:
            logger.warning(f"⚠️  没有 {coin} 的持仓，无法平仓")
            return None
        
        try:
            position = self.positions[coin]
            
            # 🔑 关键修复：从交易所获取实际持仓数量
            logger.info(f"🔍 获取 {coin} 在交易所的实际持仓数量...")
            account_info = await self.client.get_account_info()
            actual_size = None
            
            for asset_pos in account_info.get('assetPositions', []):
                if asset_pos['position']['coin'] == coin:
                    szi = float(asset_pos['position']['szi'])
                    actual_size = abs(szi)
                    actual_side = 'long' if szi > 0 else 'short'
                    
                    # 验证方向是否一致
                    if actual_side != position['side']:
                        logger.warning(f"⚠️  持仓方向不一致！系统记录: {position['side']}, 实际: {actual_side}")
                    
                    logger.info(f"✅ 交易所实际持仓: {actual_size:.8f} {coin}")
                    break
            
            if actual_size is None:
                logger.error(f"❌ 交易所无 {coin} 持仓，但系统有记录！")
                logger.warning(f"⚠️  清理系统内的无效持仓记录")
                del self.positions[coin]
                return None
            
            # 使用交易所的实际数量（避免精度导致残余）
            close_size = actual_size
            
            # 计算盈亏（使用实际数量）
            if position['side'] == 'long':
                pnl = (current_price - position['entry_price']) * close_size
            else:  # short
                pnl = (position['entry_price'] - current_price) * close_size
            
            pnl_pct = (pnl / (position['entry_price'] * close_size)) * 100 if close_size > 0 else 0
            
            logger.info("=" * 60)
            logger.info(f"📉 平{'多' if position['side'] == 'long' else '空'}仓")
            logger.info(f"   币种: {coin}")
            logger.info(f"   开仓价: ${position['entry_price']:,.2f}")
            logger.info(f"   平仓价: ${current_price:,.2f}")
            logger.info(f"   系统记录数量: {position['size']:.8f} {coin}")
            logger.info(f"   实际平仓数量: {close_size:.8f} {coin} ✅")
            logger.info(f"   盈亏: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
            logger.info(f"   原因: {reason}")
            logger.info("=" * 60)
            
            # 下单平仓（反向操作）
            is_buy = (position['side'] == 'short')  # 平空仓需要买入
            order_price = current_price * 1.001 if is_buy else current_price * 0.999
            
            # 🔥 关键：对于Aster平台，使用市价单确保完全成交
            platform_name = getattr(self.client, 'platform_name', 'Unknown')
            if platform_name == 'Aster':
                logger.info(f"[Aster] 使用市价单平仓以确保完全成交")
                order_result = await self.client.place_order(
                    coin=coin,
                    is_buy=is_buy,
                    size=close_size,  # 使用交易所实际数量
                    price=None,  # 市价单
                    order_type="Market",
                    reduce_only=True  # 只减仓
                )
            else:
                order_result = await self.client.place_order(
                    coin=coin,
                    is_buy=is_buy,
                    size=close_size,  # 使用交易所实际数量
                    price=order_price,
                    order_type="Limit",
                    reduce_only=True  # 只减仓
                )
            
            # 检查订单是否成功
            if order_result.get('status') == 'err':
                error_msg = order_result.get('response', 'Unknown error')
                logger.error(f"❌ 平仓订单被拒绝: {error_msg}")
                logger.error(f"   请检查 Hyperliquid 账户状态和持仓")
                return None
            
            # 检查订单详细状态
            if order_result.get('status') == 'ok':
                response = order_result.get('response', {})
                data = response.get('data', {})
                statuses = data.get('statuses', [])
                
                if statuses and 'error' in statuses[0]:
                    error_msg = statuses[0]['error']
                    logger.error(f"❌ 平仓订单失败: {error_msg}")
                    logger.error(f"   订单详情: {order_result}")
                    logger.warning(f"⚠️  系统持仓与交易所不同步，保留内部持仓记录")
                    return None
            
            # 记录交易（使用实际平仓数量）
            trade_record = {
                'time': datetime.now().isoformat(),
                'coin': coin,
                'action': 'close',
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'size': close_size,  # 使用实际平仓数量
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'reason': reason,
                'hold_time': (datetime.now() - position['entry_time']).total_seconds(),
                'order_result': order_result
            }
            self.trades.append(trade_record)
            self.daily_trade_count += 1
            self.daily_pnl += pnl
            
            # 移除持仓
            del self.positions[coin]
            
            logger.info(f"✅ 平仓成功: {position['side'].upper()} {close_size:.8f} {coin}, 盈亏: ${pnl:+.2f}")
            
            # 🔥 验证平仓结果（特别是Aster平台）
            if platform_name == 'Aster':
                logger.info(f"[Aster] 等待2秒后验证平仓结果...")
                await asyncio.sleep(2)  # 等待订单完全处理
                
                # 重新获取持仓验证
                verify_account = await self.client.get_account_info()
                remaining_size = None
                for asset_pos in verify_account.get('assetPositions', []):
                    if asset_pos['position']['coin'] == coin:
                        szi = float(asset_pos['position']['szi'])
                        remaining_size = abs(szi)
                        if remaining_size > 0:
                            logger.warning(f"⚠️  [Aster] 平仓后仍有残余仓位: {remaining_size:.8f} {coin}")
                            logger.warning(f"⚠️  [Aster] 可能原因: 订单部分成交或精度问题")
                        else:
                            logger.info(f"✅ [Aster] 平仓验证成功: 无残余仓位")
                        break
                
                if remaining_size is None:
                    logger.info(f"✅ [Aster] 平仓验证成功: 无该币种持仓")
            
            return trade_record
            
        except Exception as e:
            logger.error(f"❌ 平仓失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_position_info(self, coin: str) -> Optional[Dict]:
        """获取持仓信息"""
        return self.positions.get(coin)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """获取所有持仓"""
        return self.positions
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """获取交易历史"""
        return self.trades[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取交易统计"""
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

