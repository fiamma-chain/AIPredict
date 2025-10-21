"""
交易执行引擎
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

from trading.hyperliquid.client import HyperliquidClient
from trading.order_manager import OrderManager, OrderSide
from trading.risk_manager import RiskManager, RiskLimits
from strategies.base import BaseStrategy, Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingEngine:
    """交易执行引擎"""
    
    def __init__(
        self,
        client: HyperliquidClient,
        risk_limits: Optional[RiskLimits] = None
    ):
        """
        初始化交易引擎
        
        Args:
            client: Hyperliquid 客户端
            risk_limits: 风险限制
        """
        self.client = client
        self.order_manager = OrderManager(client)
        self.risk_manager = RiskManager(client, risk_limits)
        
        self.strategies: Dict[str, BaseStrategy] = {}
        self.is_running = False
        self.update_interval = 10  # 秒
    
    def register_strategy(self, strategy: BaseStrategy):
        """
        注册策略
        
        Args:
            strategy: 策略实例
        """
        self.strategies[strategy.strategy_id] = strategy
        logger.info(f"策略已注册: {strategy.config.name} (ID: {strategy.strategy_id})")
    
    def unregister_strategy(self, strategy_id: str):
        """
        注销策略
        
        Args:
            strategy_id: 策略 ID
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            logger.info(f"策略已注销: {strategy_id}")
    
    async def execute_signal(
        self,
        strategy: BaseStrategy,
        coin: str,
        signal: Signal,
        current_price: float
    ):
        """
        执行交易信号
        
        Args:
            strategy: 策略实例
            coin: 币种
            signal: 交易信号
            current_price: 当前价格
        """
        try:
            # 检查是否可以交易
            if not strategy.can_trade(coin):
                return
            
            # 获取账户余额
            balance_info = await self.client.get_balance()
            available_balance = balance_info["available_balance"]
            
            if signal == Signal.BUY:
                # 买入信号
                position_size = strategy.get_position_size(coin, signal, available_balance)
                
                if position_size <= 0:
                    return
                
                # 计算交易数量
                quantity = position_size / current_price
                
                # 风险检查
                can_trade, reason = await self.risk_manager.check_order_risk(
                    coin, quantity, current_price, "long"
                )
                
                if not can_trade:
                    logger.warning(f"风险检查失败 [{strategy.config.name}]: {reason}")
                    return
                
                # 创建订单
                order = await self.order_manager.create_order(
                    strategy_id=strategy.strategy_id,
                    coin=coin,
                    side=OrderSide.BUY,
                    size=quantity,
                    price=current_price,
                    order_type="market"
                )
                
                # 提交订单
                success = await self.order_manager.submit_order(order)
                
                if success:
                    logger.info(
                        f"买入订单已提交 [{strategy.config.name}]: "
                        f"{coin} {quantity:.4f} @ ${current_price:.2f}"
                    )
                    
                    # 更新策略持仓
                    strategy.update_position(coin, {
                        "entry_price": current_price,
                        "size": quantity,
                        "side": "long",
                        "entry_time": datetime.now()
                    })
                    strategy.state.last_signal_time[coin] = datetime.now()
            
            elif signal == Signal.CLOSE:
                # 平仓信号
                if coin not in strategy.state.positions:
                    return
                
                position = strategy.state.positions[coin]
                size = position.get("size", 0)
                entry_price = position.get("entry_price", 0)
                
                if size <= 0:
                    return
                
                # 创建平仓订单
                order = await self.order_manager.create_order(
                    strategy_id=strategy.strategy_id,
                    coin=coin,
                    side=OrderSide.SELL,
                    size=size,
                    price=current_price,
                    order_type="market"
                )
                
                # 提交订单
                success = await self.order_manager.submit_order(order)
                
                if success:
                    # 计算盈亏
                    pnl = (current_price - entry_price) * size
                    pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                    
                    logger.info(
                        f"平仓订单已提交 [{strategy.config.name}]: "
                        f"{coin} {size:.4f} @ ${current_price:.2f}, "
                        f"PnL: ${pnl:.2f} ({pnl_percentage:.2f}%)"
                    )
                    
                    # 通知策略
                    await strategy.on_position_closed(position, pnl)
                    
                    # 移除持仓
                    strategy.remove_position(coin)
                    strategy.state.last_signal_time[coin] = datetime.now()
        
        except Exception as e:
            logger.error(f"执行交易信号失败 [{strategy.config.name}] {coin}: {e}")
    
    async def update_strategy(self, strategy: BaseStrategy):
        """
        更新单个策略
        
        Args:
            strategy: 策略实例
        """
        if not strategy.state.is_active:
            return
        
        try:
            # 遍历策略关注的币种
            for coin in strategy.config.coins:
                try:
                    # 获取市场数据
                    market_data = await self.client.get_market_data(coin)
                    ctx = market_data.get("ctx", {})
                    
                    # 分析市场并生成信号
                    signal = await strategy.analyze(coin, ctx)
                    
                    # 执行信号
                    if signal != Signal.HOLD:
                        current_price = float(ctx.get("markPx", 0))
                        await self.execute_signal(strategy, coin, signal, current_price)
                
                except Exception as e:
                    logger.error(f"更新策略失败 [{strategy.config.name}] {coin}: {e}")
        
        except Exception as e:
            logger.error(f"策略更新异常 [{strategy.config.name}]: {e}")
    
    async def run_loop(self):
        """主循环"""
        logger.info("交易引擎已启动")
        
        while self.is_running:
            try:
                # 更新持仓信息
                await self.risk_manager.update_positions()
                
                # 更新订单状态
                await self.order_manager.update_order_status()
                
                # 检查止损止盈
                risk_actions = await self.risk_manager.check_stop_loss_take_profit()
                if risk_actions:
                    await self.risk_manager.execute_risk_actions(risk_actions)
                
                # 更新所有活跃策略
                tasks = [
                    self.update_strategy(strategy)
                    for strategy in self.strategies.values()
                ]
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # 等待下一次更新
                await asyncio.sleep(self.update_interval)
            
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                await asyncio.sleep(5)
        
        logger.info("交易引擎已停止")
    
    async def start(self):
        """启动引擎"""
        if self.is_running:
            logger.warning("交易引擎已在运行中")
            return
        
        self.is_running = True
        
        # 启动所有策略
        for strategy in self.strategies.values():
            strategy.start()
        
        # 运行主循环
        await self.run_loop()
    
    def stop(self):
        """停止引擎"""
        logger.info("正在停止交易引擎...")
        self.is_running = False
        
        # 停止所有策略
        for strategy in self.strategies.values():
            strategy.stop()
    
    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "is_running": self.is_running,
            "strategies": [
                strategy.get_info()
                for strategy in self.strategies.values()
            ],
            "risk_metrics": self.risk_manager.get_risk_metrics()
        }

