"""
AI 竞技场引擎
管理多个 AI 模型并行交易
"""
import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from trading.hyperliquid.client import HyperliquidClient
from trading.order_manager import OrderManager, OrderSide
from trading.risk_manager import RiskManager
from ai_models.base_ai import AITradingModel, TradingDecision

logger = logging.getLogger(__name__)


class AIArena:
    """AI 竞技场"""
    
    def __init__(self, client: HyperliquidClient, risk_manager: RiskManager):
        """
        初始化 AI 竞技场
        
        Args:
            client: Hyperliquid 客户端
            risk_manager: 风险管理器
        """
        self.client = client
        self.risk_manager = risk_manager
        self.order_manager = OrderManager(client)
        
        self.ai_models: Dict[str, AITradingModel] = {}
        self.is_running = False
        self.update_interval = 300  # 5分钟更新一次
        
        # 交易对
        self.trading_pairs = ["BTC", "ETH", "SOL"]
    
    def register_ai_model(self, ai_model: AITradingModel):
        """
        注册 AI 模型
        
        Args:
            ai_model: AI 模型实例
        """
        self.ai_models[ai_model.model_name] = ai_model
        logger.info(f"✅ AI 模型已注册: {ai_model.model_name}")
    
    async def run_ai_analysis(self, ai_model: AITradingModel, coin: str):
        """
        运行单个 AI 的分析
        
        Args:
            ai_model: AI 模型
            coin: 币种
        """
        try:
            # 获取市场数据
            market_data = await self.client.get_market_data(coin)
            orderbook = await self.client.get_orderbook(coin)
            
            ctx = market_data.get("ctx", {})
            
            # AI 分析
            decision, confidence, reasoning = await ai_model.analyze_market(
                coin=coin,
                market_data=ctx,
                orderbook=orderbook,
                recent_trades=[]
            )
            
            logger.info(
                f"🤖 {ai_model.model_name} | {coin} | "
                f"决策: {decision.value} | 置信度: {confidence:.1f}% | "
                f"理由: {reasoning[:50]}..."
            )
            
            # 执行交易决策
            await self.execute_ai_decision(ai_model, coin, decision, confidence, ctx)
        
        except Exception as e:
            logger.error(f"AI 分析失败 [{ai_model.model_name}] {coin}: {e}")
    
    async def execute_ai_decision(
        self,
        ai_model: AITradingModel,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        market_data: Dict
    ):
        """
        执行 AI 的交易决策
        
        Args:
            ai_model: AI 模型
            coin: 币种
            decision: 交易决策
            confidence: 置信度
            market_data: 市场数据
        """
        current_price = float(market_data.get("markPx", 0))
        
        if current_price == 0:
            return
        
        has_position = coin in ai_model.positions
        
        # 买入决策
        if decision in [TradingDecision.BUY, TradingDecision.STRONG_BUY] and not has_position:
            # 计算仓位大小
            position_value = ai_model.calculate_position_size(decision, confidence, current_price)
            
            if position_value > 0:
                quantity = position_value / current_price
                
                # 风险检查
                can_trade, reason = await self.risk_manager.check_order_risk(
                    coin, quantity, current_price, "long"
                )
                
                if not can_trade:
                    logger.warning(f"⚠️  风险检查失败 [{ai_model.model_name}]: {reason}")
                    return
                
                # 创建并提交订单
                order = await self.order_manager.create_order(
                    strategy_id=ai_model.model_name,
                    coin=coin,
                    side=OrderSide.BUY,
                    size=quantity,
                    price=current_price,
                    order_type="market"
                )
                
                success = await self.order_manager.submit_order(order)
                
                if success:
                    # 更新 AI 模型持仓
                    ai_model.positions[coin] = {
                        "entry_price": current_price,
                        "size": quantity,
                        "entry_time": datetime.now(),
                        "order_id": order.order_id
                    }
                    
                    ai_model.current_balance -= position_value
                    
                    logger.info(
                        f"📈 开仓成功 [{ai_model.model_name}] {coin}: "
                        f"{quantity:.4f} @ ${current_price:,.2f}"
                    )
        
        # 卖出决策
        elif decision in [TradingDecision.SELL, TradingDecision.STRONG_SELL] and has_position:
            position = ai_model.positions[coin]
            size = position["size"]
            entry_price = position["entry_price"]
            
            # 创建平仓订单
            order = await self.order_manager.create_order(
                strategy_id=ai_model.model_name,
                coin=coin,
                side=OrderSide.SELL,
                size=size,
                price=current_price,
                order_type="market"
            )
            
            success = await self.order_manager.submit_order(order)
            
            if success:
                # 计算盈亏
                pnl = (current_price - entry_price) * size
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                # 更新 AI 模型
                ai_model.current_balance += (entry_price * size + pnl)
                ai_model.total_trades += 1
                if pnl > 0:
                    ai_model.winning_trades += 1
                
                # 记录交易
                ai_model.trade_history.append({
                    "coin": coin,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "size": size,
                    "pnl": pnl,
                    "pnl_percentage": pnl_pct,
                    "entry_time": position["entry_time"].isoformat(),
                    "exit_time": datetime.now().isoformat()
                })
                
                # 移除持仓
                del ai_model.positions[coin]
                
                logger.info(
                    f"📉 平仓 [{ai_model.model_name}] {coin}: "
                    f"${pnl:+.2f} ({pnl_pct:+.2f}%)"
                )
    
    async def run_arena_cycle(self):
        """运行一个竞技场周期"""
        logger.info("=" * 60)
        logger.info("🏟️  开始新的竞技场周期")
        logger.info("=" * 60)
        
        # 更新风险管理器
        await self.risk_manager.update_positions()
        
        # 检查止损止盈
        risk_actions = await self.risk_manager.check_stop_loss_take_profit()
        if risk_actions:
            await self.risk_manager.execute_risk_actions(risk_actions)
        
        # 为每个 AI 模型运行分析
        tasks = []
        for ai_model in self.ai_models.values():
            for coin in self.trading_pairs:
                tasks.append(self.run_ai_analysis(ai_model, coin))
        
        # 并行执行所有 AI 分析
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 显示当前排名
        self.display_leaderboard()
    
    def display_leaderboard(self):
        """显示排行榜"""
        logger.info("\n" + "=" * 80)
        logger.info("🏆 AI 模型排行榜")
        logger.info("=" * 80)
        
        # 按总盈亏排序
        models = sorted(
            self.ai_models.values(),
            key=lambda m: m.current_balance - m.initial_balance,
            reverse=True
        )
        
        logger.info(
            f"{'排名':<6} {'模型':<20} {'余额':<15} {'盈亏':<15} {'ROI':<10} "
            f"{'交易数':<8} {'胜率':<8}"
        )
        logger.info("-" * 80)
        
        for i, model in enumerate(models, 1):
            stats = model.get_stats()
            logger.info(
                f"{i:<6} {model.model_name:<20} "
                f"${stats['current_balance']:<14,.2f} "
                f"${stats['total_pnl']:<14,.2f} "
                f"{stats['roi_percentage']:<9.2f}% "
                f"{stats['total_trades']:<8} "
                f"{stats['win_rate']:<7.1f}%"
            )
        
        logger.info("=" * 80 + "\n")
    
    async def start(self):
        """启动竞技场"""
        if not self.ai_models:
            logger.error("❌ 没有注册的 AI 模型！")
            return
        
        logger.info(f"🚀 AI 竞技场启动！共有 {len(self.ai_models)} 个 AI 参赛")
        logger.info(f"📊 交易对: {', '.join(self.trading_pairs)}")
        logger.info(f"⏱️  更新间隔: {self.update_interval} 秒")
        
        self.is_running = True
        
        while self.is_running:
            try:
                await self.run_arena_cycle()
                await asyncio.sleep(self.update_interval)
            except KeyboardInterrupt:
                logger.info("\n收到停止信号...")
                break
            except Exception as e:
                logger.error(f"竞技场周期异常: {e}", exc_info=True)
                await asyncio.sleep(10)
    
    def stop(self):
        """停止竞技场"""
        logger.info("🛑 正在停止 AI 竞技场...")
        self.is_running = False
    
    def get_status(self) -> Dict:
        """获取竞技场状态"""
        return {
            "is_running": self.is_running,
            "total_ai_models": len(self.ai_models),
            "trading_pairs": self.trading_pairs,
            "ai_models": [model.get_stats() for model in self.ai_models.values()]
        }

