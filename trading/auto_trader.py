"""
自动交易模块
负责执行AI决策并管理持仓
"""
import logging
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
        
        # 交易配置（15分钟超短线波段）
        self.min_confidence = 50.0  # 最小信心阈值（超短线更激进）
        self.max_position_size = 20.0  # 最大单笔仓位（USDC）
        self.stop_loss_pct = 0.015  # 止损比例 1.5%（超短线止损更紧）
        self.take_profit_pct = 0.03  # 止盈比例 3%（超短线快速止盈）
        self.leverage = 1  # 杠杆倍数
        self.max_balance_usage_pct = 0.20  # 最大使用余额的20%（更激进）
        
        # 持仓管理
        self.positions: Dict[str, Dict] = {}  # {coin: position_info}
        self.trades: List[Dict] = []  # 交易历史
        
        # 风险控制
        self.daily_loss_limit = 10.0  # 每日最大亏损（USDC）
        self.daily_trade_limit = 10  # 每日最大交易次数
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info("🤖 自动交易器初始化完成")
        logger.info(f"   最小信心阈值: {self.min_confidence}%")
        logger.info(f"   最大单笔仓位: ${self.max_position_size}")
        logger.info(f"   止损/止盈: {self.stop_loss_pct*100}% / {self.take_profit_pct*100}%")
    
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
        
        # 检查每日交易次数
        if self.daily_trade_count >= self.daily_trade_limit:
            logger.warning(f"⚠️  已达每日交易次数限制: {self.daily_trade_count}")
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
                # 再开多仓
                return await self._open_position(coin, 'long', confidence, reasoning, current_price, balance)
        
        elif decision == TradingDecision.STRONG_SELL or decision == TradingDecision.SELL:
            if not has_position:
                return await self._open_position(coin, 'short', confidence, reasoning, current_price, balance)
            elif self.positions[coin]['side'] == 'long':
                # 先平多仓
                await self._close_position(coin, current_price, "反向信号")
                # 再开空仓
                return await self._open_position(coin, 'short', confidence, reasoning, current_price, balance)
        
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
            # 计算仓位大小（根据信心度和余额）
            position_value = min(
                self.max_position_size,
                balance * 0.2,  # 最多使用20%的资金
                (confidence / 100) * self.max_position_size  # 根据信心度调整
            )
            
            # 计算数量（币的数量）
            size = position_value / current_price
            
            # 确保满足最小交易单位
            if size < 0.0001:
                logger.warning(f"⚠️  仓位太小，无法开仓: {size:.6f} {coin}")
                return None
            
            logger.info("=" * 60)
            logger.info(f"📈 开{'多' if side == 'long' else '空'}仓")
            logger.info(f"   币种: {coin}")
            logger.info(f"   价格: ${current_price:,.2f}")
            logger.info(f"   数量: {size:.5f} {coin}")
            logger.info(f"   价值: ${position_value:.2f}")
            logger.info(f"   信心: {confidence:.1f}%")
            logger.info(f"   理由: {reasoning[:100]}...")
            logger.info("=" * 60)
            
            # 下单（市价单）
            is_buy = (side == 'long')
            
            # 注意：Hyperliquid 使用市价单需要特殊处理
            # 这里使用略微偏离市场价的限价单来模拟市价单
            order_price = current_price * 1.001 if is_buy else current_price * 0.999
            
            order_result = await self.client.place_order(
                coin=coin,
                is_buy=is_buy,
                size=size,
                price=order_price,
                order_type="Limit",
                reduce_only=False
            )
            
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
            
            # 计算盈亏
            if position['side'] == 'long':
                pnl = (current_price - position['entry_price']) * position['size']
            else:  # short
                pnl = (position['entry_price'] - current_price) * position['size']
            
            pnl_pct = (pnl / (position['entry_price'] * position['size'])) * 100
            
            logger.info("=" * 60)
            logger.info(f"📉 平{'多' if position['side'] == 'long' else '空'}仓")
            logger.info(f"   币种: {coin}")
            logger.info(f"   开仓价: ${position['entry_price']:,.2f}")
            logger.info(f"   平仓价: ${current_price:,.2f}")
            logger.info(f"   数量: {position['size']:.5f} {coin}")
            logger.info(f"   盈亏: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
            logger.info(f"   原因: {reason}")
            logger.info("=" * 60)
            
            # 下单平仓（反向操作）
            is_buy = (position['side'] == 'short')  # 平空仓需要买入
            order_price = current_price * 1.001 if is_buy else current_price * 0.999
            
            order_result = await self.client.place_order(
                coin=coin,
                is_buy=is_buy,
                size=position['size'],
                price=order_price,
                order_type="Limit",
                reduce_only=True  # 只减仓
            )
            
            # 记录交易
            trade_record = {
                'time': datetime.now().isoformat(),
                'coin': coin,
                'action': 'close',
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'size': position['size'],
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
            
            logger.info(f"✅ 平仓成功: {position['side'].upper()} {position['size']:.5f} {coin}, 盈亏: ${pnl:+.2f}")
            
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

