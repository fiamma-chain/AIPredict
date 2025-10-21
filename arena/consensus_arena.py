"""
AI 共识竞技场
多个 AI 投票决策，需要达成共识才执行交易
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter

from trading.hyperliquid.client import HyperliquidClient
from trading.order_manager import OrderManager, OrderSide
from trading.risk_manager import RiskManager
from ai_models.base_ai import AITradingModel, TradingDecision

logger = logging.getLogger(__name__)


class AIGroup:
    """AI 组"""
    
    def __init__(
        self,
        group_name: str,
        ai_models: List[AITradingModel],
        client: HyperliquidClient,
        risk_manager: RiskManager,
        consensus_threshold: int = 2
    ):
        """
        初始化 AI 组
        
        Args:
            group_name: 组名
            ai_models: AI 模型列表
            client: Hyperliquid 客户端
            risk_manager: 风险管理器
            consensus_threshold: 共识阈值（默认2，即至少2个AI同意）
        """
        self.group_name = group_name
        self.ai_models = ai_models
        self.client = client
        self.risk_manager = risk_manager
        self.order_manager = OrderManager(client)
        self.consensus_threshold = consensus_threshold
        
        # 组的统计
        self.initial_balance = 0
        self.current_balance = 0
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.consensus_history: List[Dict] = []
        
        # 交易对
        self.trading_pairs = ["BTC", "ETH", "SOL"]
    
    async def get_balance(self) -> float:
        """获取组的当前余额"""
        try:
            async with self.client:
                balance_info = await self.client.get_balance()
                return balance_info.get('total_value', 0)
        except Exception as e:
            logger.error(f"获取余额失败 [{self.group_name}]: {e}")
            return self.current_balance
    
    async def analyze_and_vote(self, coin: str) -> Dict:
        """
        让组内所有 AI 分析并投票
        
        Args:
            coin: 币种
            
        Returns:
            投票结果字典
        """
        try:
            # 获取市场数据
            market_data = await self.client.get_market_data(coin)
            orderbook = await self.client.get_orderbook(coin)
            ctx = market_data.get("ctx", {})
            current_price = float(ctx.get("markPx", 0))
            
            if current_price == 0:
                return None
            
            # 收集所有 AI 的投票
            votes = []
            for ai_model in self.ai_models:
                try:
                    decision, confidence, reasoning = await ai_model.analyze_market(
                        coin=coin,
                        market_data=ctx,
                        orderbook=orderbook,
                        recent_trades=[]
                    )
                    
                    votes.append({
                        'ai_name': ai_model.model_name,
                        'decision': decision,
                        'confidence': confidence,
                        'reasoning': reasoning
                    })
                    
                    logger.info(
                        f"  🗳️  {ai_model.model_name}: {decision.value} "
                        f"(置信度: {confidence:.1f}%) - {reasoning[:50]}..."
                    )
                    
                except Exception as e:
                    logger.error(f"AI 投票失败 [{ai_model.model_name}]: {e}")
                    continue
            
            if not votes:
                return None
            
            # 分析投票结果
            consensus = self._analyze_consensus(votes, coin, current_price)
            
            # 记录共识
            self.consensus_history.append({
                'timestamp': datetime.now().isoformat(),
                'coin': coin,
                'votes': votes,
                'consensus': consensus,
                'price': current_price
            })
            
            # 只保留最近100条
            if len(self.consensus_history) > 100:
                self.consensus_history = self.consensus_history[-100:]
            
            return consensus
            
        except Exception as e:
            logger.error(f"分析投票失败 [{self.group_name}] {coin}: {e}")
            return None
    
    def _analyze_consensus(self, votes: List[Dict], coin: str, current_price: float) -> Dict:
        """
        分析投票达成共识
        
        Args:
            votes: 投票列表
            coin: 币种
            current_price: 当前价格
            
        Returns:
            共识结果
        """
        # 统计决策
        decisions = [v['decision'] for v in votes]
        decision_counts = Counter(decisions)
        
        # 计算平均置信度
        avg_confidence = sum(v['confidence'] for v in votes) / len(votes)
        
        # 找出最多的决策
        most_common_decision, count = decision_counts.most_common(1)[0]
        
        # 判断是否达成共识（至少threshold个AI同意）
        has_consensus = count >= self.consensus_threshold
        
        # 生成共识总结
        if has_consensus:
            agreeing_ais = [v['ai_name'] for v in votes if v['decision'] == most_common_decision]
            disagreeing_ais = [v['ai_name'] for v in votes if v['decision'] != most_common_decision]
            
            # 收集同意方的理由
            agreeing_reasons = [
                v['reasoning'] for v in votes 
                if v['decision'] == most_common_decision
            ]
            
            summary = (
                f"✅ 达成共识: {most_common_decision.value.upper()}\n"
                f"👍 同意 ({count}/{len(votes)}): {', '.join(agreeing_ais)}\n"
            )
            
            if disagreeing_ais:
                summary += f"👎 反对: {', '.join(disagreeing_ais)}\n"
            
            summary += f"💡 核心理由: {agreeing_reasons[0]}"
            
        else:
            summary = (
                f"⚠️ 未达成共识\n"
                f"决策分布: {dict(decision_counts)}\n"
                f"需要至少 {self.consensus_threshold} 个 AI 同意"
            )
        
        has_position = coin in self.positions
        
        return {
            'has_consensus': has_consensus,
            'decision': most_common_decision,
            'vote_count': count,
            'total_votes': len(votes),
            'avg_confidence': avg_confidence,
            'summary': summary,
            'votes': votes,
            'can_execute': has_consensus and self._can_execute_decision(
                most_common_decision, has_position
            )
        }
    
    def _can_execute_decision(self, decision: TradingDecision, has_position: bool) -> bool:
        """判断是否可以执行决策"""
        # 买入：需要没有持仓
        if decision in [TradingDecision.BUY, TradingDecision.STRONG_BUY]:
            return not has_position
        # 卖出：需要有持仓
        elif decision in [TradingDecision.SELL, TradingDecision.STRONG_SELL]:
            return has_position
        # 持有：不操作
        else:
            return False
    
    async def execute_consensus(self, coin: str, consensus: Dict):
        """
        执行共识决策
        
        Args:
            coin: 币种
            consensus: 共识结果
        """
        if not consensus or not consensus.get('can_execute'):
            logger.info(f"  ⏸️  不执行: {consensus.get('summary', '无法执行').split(chr(10))[0]}")
            return
        
        decision = consensus['decision']
        avg_confidence = consensus['avg_confidence']
        
        try:
            # 获取当前价格
            market_data = await self.client.get_market_data(coin)
            ctx = market_data.get("ctx", {})
            current_price = float(ctx.get("markPx", 0))
            
            if current_price == 0:
                return
            
            # 买入
            if decision in [TradingDecision.BUY, TradingDecision.STRONG_BUY]:
                await self._execute_buy(coin, decision, avg_confidence, current_price, consensus)
            
            # 卖出
            elif decision in [TradingDecision.SELL, TradingDecision.STRONG_SELL]:
                await self._execute_sell(coin, current_price, consensus)
                
        except Exception as e:
            logger.error(f"执行共识失败 [{self.group_name}] {coin}: {e}")
    
    async def _execute_buy(
        self,
        coin: str,
        decision: TradingDecision,
        avg_confidence: float,
        current_price: float,
        consensus: Dict
    ):
        """执行买入"""
        # 计算仓位
        base_ratio = 0.15 if decision == TradingDecision.STRONG_BUY else 0.10
        confidence_multiplier = avg_confidence / 100.0
        
        position_value = self.current_balance * base_ratio * confidence_multiplier
        position_value = min(position_value, 30.0)  # 最大30U
        
        if position_value <= 0:
            return
        
        quantity = position_value / current_price
        
        # 风险检查
        can_trade, reason = await self.risk_manager.check_order_risk(
            coin, quantity, current_price, "long"
        )
        
        if not can_trade:
            logger.warning(f"  ⚠️  风险检查失败 [{self.group_name}]: {reason}")
            return
        
        # 创建订单
        order = await self.order_manager.create_order(
            strategy_id=self.group_name,
            coin=coin,
            side=OrderSide.BUY,
            size=quantity,
            price=current_price,
            order_type="market"
        )
        
        success = await self.order_manager.submit_order(order)
        
        if success:
            # 记录持仓
            self.positions[coin] = {
                'entry_price': current_price,
                'size': quantity,
                'entry_time': datetime.now(),
                'consensus': consensus,
                'order_id': order.order_id
            }
            
            self.current_balance -= position_value
            
            logger.info(
                f"  📈 [{self.group_name}] 开仓成功: {coin} "
                f"{quantity:.4f} @ ${current_price:,.2f} (${position_value:.2f})"
            )
            logger.info(f"  💬 {consensus['summary'].split(chr(10))[0]}")
    
    async def _execute_sell(self, coin: str, current_price: float, consensus: Dict):
        """执行卖出"""
        if coin not in self.positions:
            return
        
        position = self.positions[coin]
        size = position['size']
        entry_price = position['entry_price']
        
        # 创建平仓订单
        order = await self.order_manager.create_order(
            strategy_id=self.group_name,
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
            
            # 更新余额
            self.current_balance += (entry_price * size + pnl)
            
            # 记录交易
            self.trade_history.append({
                'coin': coin,
                'entry_price': entry_price,
                'exit_price': current_price,
                'size': size,
                'pnl': pnl,
                'pnl_percentage': pnl_pct,
                'entry_time': position['entry_time'].isoformat(),
                'exit_time': datetime.now().isoformat(),
                'entry_consensus': position.get('consensus'),
                'exit_consensus': consensus
            })
            
            # 移除持仓
            del self.positions[coin]
            
            logger.info(
                f"  📉 [{self.group_name}] 平仓: {coin} "
                f"${pnl:+.2f} ({pnl_pct:+.2f}%)"
            )
            logger.info(f"  💬 {consensus['summary'].split(chr(10))[0]}")
    
    def get_stats(self) -> Dict:
        """获取组统计"""
        winning_trades = sum(1 for t in self.trade_history if t['pnl'] > 0)
        total_trades = len(self.trade_history)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = self.current_balance - self.initial_balance
        roi = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        return {
            'group_name': self.group_name,
            'ai_members': [ai.model_name for ai in self.ai_models],
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_pnl': total_pnl,
            'roi_percentage': roi,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'active_positions': len(self.positions),
            'recent_consensus': self.consensus_history[-10:] if self.consensus_history else []
        }


class ConsensusArena:
    """共识竞技场"""
    
    def __init__(self):
        """初始化共识竞技场"""
        self.groups: Dict[str, AIGroup] = {}
        self.is_running = False
        self.update_interval = 600  # 10分钟
    
    def register_group(self, group: AIGroup):
        """注册 AI 组"""
        self.groups[group.group_name] = group
        logger.info(
            f"✅ AI 组已注册: {group.group_name} "
            f"({', '.join([ai.model_name for ai in group.ai_models])})"
        )
    
    async def run_group_cycle(self, group: AIGroup):
        """运行一个组的周期"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🏟️  {group.group_name} 开始分析")
        logger.info(f"{'='*60}")
        
        # 更新余额
        group.current_balance = await group.get_balance()
        
        # 为每个交易对进行投票
        for coin in group.trading_pairs:
            logger.info(f"\n💰 {coin} - 开始投票")
            
            # 收集投票并达成共识
            consensus = await group.analyze_and_vote(coin)
            
            if consensus:
                logger.info(f"\n📊 共识结果:")
                logger.info(consensus['summary'])
                
                # 执行共识决策
                await group.execute_consensus(coin, consensus)
            
            # 短暂延迟
            await asyncio.sleep(2)
    
    async def run_arena_cycle(self):
        """运行竞技场周期"""
        logger.info("\n" + "="*80)
        logger.info("🏟️  开始新的共识竞技场周期")
        logger.info("="*80)
        
        # 并行运行所有组
        tasks = [self.run_group_cycle(group) for group in self.groups.values()]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 显示排行榜
        self.display_leaderboard()
    
    def display_leaderboard(self):
        """显示排行榜"""
        logger.info("\n" + "="*80)
        logger.info("🏆 AI 组排行榜")
        logger.info("="*80)
        
        # 按 ROI 排序
        groups = sorted(
            self.groups.values(),
            key=lambda g: g.current_balance - g.initial_balance,
            reverse=True
        )
        
        logger.info(
            f"{'排名':<6} {'组名':<15} {'成员':<40} {'余额':<12} {'盈亏':<12} "
            f"{'ROI':<10} {'交易数':<8} {'胜率':<8}"
        )
        logger.info("-"*110)
        
        for i, group in enumerate(groups, 1):
            stats = group.get_stats()
            members = ', '.join(stats['ai_members'])
            logger.info(
                f"{i:<6} {stats['group_name']:<15} {members:<40} "
                f"${stats['current_balance']:<11.2f} "
                f"${stats['total_pnl']:<11,.2f} "
                f"{stats['roi_percentage']:<9.2f}% "
                f"{stats['total_trades']:<8} "
                f"{stats['win_rate']:<7.1f}%"
            )
        
        logger.info("="*110 + "\n")
    
    async def start(self):
        """启动竞技场"""
        if not self.groups:
            logger.error("❌ 没有注册的 AI 组！")
            return
        
        logger.info(f"🚀 共识竞技场启动！共有 {len(self.groups)} 个 AI 组参赛")
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
        logger.info("🛑 正在停止共识竞技场...")
        self.is_running = False
    
    def get_status(self) -> Dict:
        """获取竞技场状态"""
        return {
            'is_running': self.is_running,
            'total_groups': len(self.groups),
            'groups': [group.get_stats() for group in self.groups.values()]
        }

