"""
AI共识交易系统 - 多平台对比版
支持同时在 Hyperliquid 和 Aster 平台上交易，对比收益
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from config.settings import settings, get_enabled_platforms
from ai_models.deepseek_trader import DeepSeekTrader
from ai_models.claude_trader import ClaudeTrader
from ai_models.grok_trader import GrokTrader
from ai_models.gpt_trader import GPTTrader
from ai_models.gemini_trader import GeminiTrader
from ai_models.qwen_trader import QwenTrader
from trading.hyperliquid.client import HyperliquidClient
from trading.aster.client import AsterClient
from trading.multi_platform_trader import MultiPlatformTrader
from utils.symbol_filter import symbol_filter
from trading.kline_manager import KlineManager
from ai_models.base_ai import TradingDecision
from utils.redis_manager import initialize_redis_manager, shutdown_redis_manager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()


class AIGroup:
    """AI组 - 多平台版本"""
    
    def __init__(self, name: str, ai_traders: List, private_key: str, testnet: bool = True):
        """
        初始化 AI 组
        
        Args:
            name: 组名
            ai_traders: AI 交易者列表
            private_key: 私钥
            testnet: 是否使用测试网
        """
        self.name = name
        self.ai_traders = ai_traders
        self.kline_manager = KlineManager(max_klines=16)
        self.start_time = datetime.now()
        
        # 创建多平台交易管理器
        self.multi_trader = MultiPlatformTrader()
        
        # 根据配置初始化各个平台
        enabled_platforms = get_enabled_platforms()
        logger.info(f"[{name}] 启用的交易平台: {enabled_platforms}")
        
        # 为每个平台创建一组独立的AI实例并启用Redis持久化
        self.platform_ai_traders = {}  # 存储每个平台的AI实例
        
        for platform in enabled_platforms:
            if platform == "hyperliquid":
                client = HyperliquidClient(private_key, testnet)
                self.multi_trader.add_platform(client, f"{name}-Hyperliquid")
            elif platform == "aster":
                client = AsterClient(private_key, testnet)
                self.multi_trader.add_platform(client, f"{name}-Aster")
            
            # 为每个平台创建AI交易者副本并设置平台信息
            platform_ais = []
            for ai_trader in ai_traders:
                # 创建AI实例的副本（每个平台一个实例）
                ai_class = ai_trader.__class__
                ai_copy = ai_class(
                    api_key=ai_trader.api_key,
                    platform=platform  # 传递平台参数
                )
                # 启用Redis持久化
                if settings.redis_enabled:
                    ai_copy.enable_redis_persistence()
                platform_ais.append(ai_copy)
            
            self.platform_ai_traders[platform] = platform_ais
        
        # 保存第一个客户端用于获取市场数据（所有平台看同一个市场）
        self.primary_client = list(self.multi_trader.platform_traders.values())[0].client if self.multi_trader.platform_traders else None
        
        # 统计数据
        self.stats = {
            "group_name": name,
            "platforms": {},
            "consensus_decisions": [],
            "platform_comparison": {}
        }
    
    async def initialize(self):
        """初始化组"""
        await self.multi_trader.initialize_all(settings.ai_initial_balance)
        
        # 同步各平台持仓
        for platform_name, trader in self.multi_trader.platform_traders.items():
            await self._sync_existing_positions(trader)
    
    async def _sync_existing_positions(self, trader):
        """同步平台持仓"""
        try:
            logger.info(f"[{trader.name}] 🔄 正在同步现有持仓...")
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            synced_count = 0
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    coin = pos['position']['coin']
                    size = float(pos['position']['szi'])
                    
                    if size == 0:
                        continue
                    
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    trader.auto_trader.positions[coin] = {
                        'side': 'long' if is_long else 'short',
                        'entry_price': entry_px,
                        'size': abs_size,
                        'entry_time': datetime.now(),
                        'confidence': 0,
                        'reasoning': '系统启动时同步的历史持仓',
                        'order_id': 'synced'
                    }
                    
                    synced_count += 1
                    logger.info(f"[{trader.name}]    ✅ {coin} {'LONG' if is_long else 'SHORT'} {abs_size:.5f} @ ${entry_px:,.2f}")
                
                except Exception as e:
                    logger.warning(f"[{trader.name}] 解析持仓失败: {e}")
                    continue
            
            if synced_count > 0:
                logger.info(f"[{trader.name}] ✅ 已同步 {synced_count} 个现有持仓")
            else:
                logger.info(f"[{trader.name}] 📭 没有现有持仓")
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ 同步持仓失败: {e}")
    
    async def get_consensus_decision(
        self, 
        coin: str, 
        market_data: Dict, 
        orderbook: Dict, 
        recent_trades: List,
        position_info: Optional[Dict] = None,
        platform: str = None
    ) -> Tuple[Optional[TradingDecision], float, str, List[Dict]]:
        """
        获取组内共识决策
        
        Args:
            coin: 币种
            market_data: 市场数据
            orderbook: 订单簿
            recent_trades: 最近交易
            position_info: 持仓信息
            platform: 平台名称（如果指定，使用该平台的AI实例）
        """
        kline_history_data = self.kline_manager.format_for_prompt(max_rows=16)
        
        # 选择使用哪组AI（如果指定平台，使用平台特定的AI，否则使用默认AI）
        ai_traders_to_use = self.ai_traders
        if platform and platform in self.platform_ai_traders:
            ai_traders_to_use = self.platform_ai_traders[platform]
        
        async def get_ai_decision(ai_trader):
            try:
                ai_name = ai_trader.__class__.__name__.replace('Trader', '')
                platform_name = getattr(ai_trader, 'platform', 'unknown')
                logger.info(f"[{self.name}] 🤖 正在获取 {ai_name} ({platform_name}) 的决策...")
                
                original_create_prompt = ai_trader.create_market_prompt
                def wrapped_prompt(c, m, o, p=None, kline_history=None):
                    return original_create_prompt(c, m, o, p, kline_history=kline_history_data)
                ai_trader.create_market_prompt = wrapped_prompt
                
                decision, confidence, reasoning = await ai_trader.analyze_market(
                    coin, market_data, orderbook, recent_trades, position_info
                )
                
                ai_trader.create_market_prompt = original_create_prompt
                
                logger.info(f"[{self.name}]    {ai_name} ({platform_name}): {decision} (信心: {confidence:.1f}%)")
                
                return {
                    'ai_name': ai_name,
                    'decision': decision,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'platform': platform_name
                }
            
            except Exception as e:
                logger.error(f"[{self.name}] ❌ {ai_trader.__class__.__name__} 决策失败: {e}")
                return None
        
        logger.info(f"[{self.name}] 🚀 开始并行调用 {len(ai_traders_to_use)} 个AI模型...")
        results = await asyncio.gather(*[get_ai_decision(ai) for ai in ai_traders_to_use])
        
        ai_decisions = [r for r in results if r is not None]
        
        if not ai_decisions:
            return None, 0, "所有AI决策失败", []
        
        # 统计投票
        buy_votes = []
        sell_votes = []
        hold_votes = []
        
        for d in ai_decisions:
            if d['decision'] in [TradingDecision.BUY, TradingDecision.STRONG_BUY]:
                buy_votes.append(d)
            elif d['decision'] in [TradingDecision.SELL, TradingDecision.STRONG_SELL]:
                sell_votes.append(d)
            else:
                hold_votes.append(d)
        
        buy_count = len(buy_votes)
        sell_count = len(sell_votes)
        hold_count = len(hold_votes)
        
        vote_counts = [
            (buy_count, TradingDecision.BUY, buy_votes, "看涨"),
            (sell_count, TradingDecision.SELL, sell_votes, "看跌"),
            (hold_count, TradingDecision.HOLD, hold_votes, "观望")
        ]
        vote_counts.sort(key=lambda x: x[0], reverse=True)
        
        vote_count, consensus_decision, supporting_ais, direction_name = vote_counts[0]
        
        if supporting_ais:
            avg_confidence = sum(d['confidence'] for d in supporting_ais) / len(supporting_ais)
        else:
            avg_confidence = 0
        
        vote_summary = f"看涨{buy_count}票, 看跌{sell_count}票, 观望{hold_count}票"
        consensus_summary = f"共识结果: {direction_name} ({vote_count}/{len(ai_decisions)}票, 平均信心{avg_confidence:.1f}%)\n投票详情: {vote_summary}"
        
        logger.info(f"[{self.name}] 📊 {consensus_summary}")
        
        min_votes = settings.consensus_min_votes
        if vote_count >= min_votes:
            logger.info(f"[{self.name}] ✅ 达成共识！将执行: {direction_name} ({consensus_decision})")
            return consensus_decision, avg_confidence, consensus_summary, ai_decisions
        else:
            logger.info(f"[{self.name}] ⚠️  未达成共识（需要至少{min_votes}票），保持观望")
            return TradingDecision.HOLD, avg_confidence, f"未达成共识（需要{min_votes}票，实际最多{vote_count}票），保持观望\n{vote_summary}", ai_decisions
    
    async def execute_decision_on_all_platforms(
        self, 
        coin: str, 
        decision: TradingDecision, 
        confidence: float, 
        reasoning: str, 
        current_price: float
    ):
        """在所有平台上执行决策"""
        if decision == TradingDecision.HOLD:
            logger.debug(f"[{self.name}] 💤 AI 建议观望，不执行交易")
            return
        
        logger.info(f"[{self.name}] 🚀 在所有平台上执行决策: {decision}")
        results = await self.multi_trader.execute_decision_all(
            coin, decision, confidence, reasoning, current_price
        )
        
        for platform_name, result in results.items():
            if result:
                logger.info(f"[{platform_name}] ✅ 交易已执行")
            else:
                logger.info(f"[{platform_name}] ⚠️  交易未执行")
    
    async def update_stats(self):
        """更新统计数据"""
        await self.multi_trader.update_all_stats()
        
        # 更新组统计
        comparison = self.multi_trader.get_comparison_stats()
        self.stats["platform_comparison"] = comparison
        
        # 为每个平台更新统计
        for platform_name, trader in self.multi_trader.platform_traders.items():
            self.stats["platforms"][platform_name] = trader.stats


class ConsensusArena:
    """共识竞技场 - 多平台版本"""
    
    def __init__(self):
        self.groups: List[AIGroup] = []
        self.running = False
        self.update_interval = settings.consensus_interval
    
    async def initialize(self):
        """初始化系统"""
        logger.info("=" * 80)
        logger.info("🤖 AI共识交易系统 - 多平台对比版")
        logger.info("=" * 80)
        
        # 初始化 Redis 持久化（如果启用）
        if settings.redis_enabled:
            logger.info("🔄 正在初始化 Redis 持久化...")
            redis_success = initialize_redis_manager(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None
            )
            if redis_success:
                logger.info("✅ Redis 持久化已启用")
            else:
                logger.warning("⚠️  Redis 持久化初始化失败，将仅使用内存存储")
        else:
            logger.info("ℹ️  Redis 持久化未启用")
        
        enabled_platforms = get_enabled_platforms()
        logger.info(f"启用的交易平台: {', '.join(enabled_platforms)}")
        logger.info(f"交易币种: {symbol_filter.get_default_symbol()}")
        logger.info(f"⏱️  决策周期: {self.update_interval//60}分钟")
        logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意才执行")
        logger.info(f"每组初始资金: ${settings.ai_initial_balance}")
        logger.info("=" * 80)
        
        # 初始化 Alpha 组
        logger.info("\n📊 初始化 Alpha 组 (DeepSeek + Claude + Grok)...")
        alpha_ais = [
            DeepSeekTrader(api_key=settings.deepseek_api_key),
            ClaudeTrader(api_key=settings.claude_api_key),
            GrokTrader(api_key=settings.grok_api_key)
        ]
        alpha_group = AIGroup(
            settings.group_1_name,
            alpha_ais,
            settings.group_1_private_key,
            settings.group_1_testnet
        )
        await alpha_group.initialize()
        self.groups.append(alpha_group)
        logger.info(f"✅ Alpha组初始化完成")
        
        # 初始化 Beta 组
        logger.info("\n📊 初始化 Beta 组 (GPT-4 + Gemini + Qwen)...")
        beta_ais = [
            GPTTrader(api_key=settings.openai_api_key, model=settings.gpt_model),
            GeminiTrader(api_key=settings.gemini_api_key),
            QwenTrader(api_key=settings.qwen_api_key)
        ]
        beta_group = AIGroup(
            settings.group_2_name,
            beta_ais,
            settings.group_2_private_key,
            settings.group_2_testnet
        )
        await beta_group.initialize()
        self.groups.append(beta_group)
        logger.info(f"✅ Beta组初始化完成")
        
        logger.info("\n🚀 系统初始化完成！")
        return True
    
    async def decision_loop(self):
        """共识决策循环"""
        loop_count = 0
        trading_symbol = symbol_filter.get_default_symbol()
        
        while self.running:
            try:
                loop_count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"🤖 共识决策循环 #{loop_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*80}")
                
                # 获取市场数据（使用第一个组的第一个平台客户端）
                try:
                    primary_client = self.groups[0].primary_client
                    if not primary_client:
                        logger.error("❌ 没有可用的交易客户端")
                        await asyncio.sleep(30)
                        continue
                    
                    market_data = await primary_client.get_market_data(trading_symbol)
                    current_price = market_data['price']
                    logger.info(f"💰 {trading_symbol} 价格: ${current_price:,.2f}")
                    logger.info(f"📈 24h涨跌: {market_data.get('change_24h', 0):+.2f}%")
                    
                    orderbook_data = await primary_client.get_orderbook(trading_symbol)
                    recent_trades = await primary_client.get_recent_trades(trading_symbol, limit=10)
                except Exception as e:
                    logger.error(f"❌ 获取市场数据失败: {e}")
                    await asyncio.sleep(30)
                    continue
                
                # 并行处理各组
                async def process_group(group):
                    try:
                        logger.info(f"\n{'─'*80}")
                        logger.info(f"📊 {group.name} 开始共识决策")
                        logger.info(f"{'─'*80}")
                        
                        # 更新K线
                        group.kline_manager.update_price(
                            price=current_price,
                            volume=market_data.get('volume', 0)
                        )
                        
                        # 为每个平台分别获取共识决策
                        # 注意：由于我们为每个平台创建了独立的AI实例，所以每个平台的决策是独立的
                        # 这里简化处理，获取一次共识决策（所有AI的综合决策）
                        first_trader = list(group.multi_trader.platform_traders.values())[0]
                        position_info = first_trader.auto_trader.positions.get(trading_symbol)
                        
                        # 获取第一个平台的名称，用于选择对应的AI实例
                        first_platform = list(group.platform_ai_traders.keys())[0] if group.platform_ai_traders else None
                        
                        consensus_decision, confidence, summary, ai_votes = await group.get_consensus_decision(
                            trading_symbol, market_data, orderbook_data, recent_trades, position_info, first_platform
                        )
                        
                        # 记录决策
                        decision_record = {
                            "time": datetime.now().isoformat(),
                            "decision": str(consensus_decision),
                            "confidence": confidence,
                            "summary": summary,
                            "ai_votes": ai_votes,
                            "price": current_price
                        }
                        group.stats["consensus_decisions"].insert(0, decision_record)
                        group.stats["consensus_decisions"] = group.stats["consensus_decisions"][:100]
                        
                        # 在所有平台上执行决策
                        await group.execute_decision_on_all_platforms(
                            trading_symbol,
                            consensus_decision,
                            confidence,
                            summary,
                            current_price
                        )
                        
                        # 更新统计
                        await group.update_stats()
                        
                        # 显示平台对比
                        if settings.platform_comparison_enabled:
                            logger.info(f"\n[{group.name}] 📊 平台收益对比:")
                            comparison = group.stats["platform_comparison"]
                            for platform_stats in comparison.get("platforms", []):
                                logger.info(f"  {platform_stats['name']}: "
                                          f"余额=${platform_stats['balance']:.2f}, "
                                          f"盈亏=${platform_stats['pnl']:+.2f}, "
                                          f"ROI={platform_stats['roi']:+.2f}%, "
                                          f"胜率={platform_stats['win_rate']:.1f}%")
                        
                    except Exception as e:
                        logger.error(f"[{group.name}] ❌ 决策执行错误: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # 并行处理所有组
                await asyncio.gather(*[process_group(group) for group in self.groups])
                
                logger.info(f"\n⏰ 等待 {self.update_interval} 秒后进行下一轮决策...")
                await asyncio.sleep(self.update_interval)
            
            except asyncio.CancelledError:
                logger.info("⏹️  决策循环被取消")
                break
            except Exception as e:
                logger.error(f"❌ 决策循环错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(30)
    
    async def start(self):
        """启动系统"""
        if await self.initialize():
            self.running = True
            logger.info("🚀 共识交易系统已启动")
            await self.decision_loop()
    
    async def stop(self):
        """停止系统"""
        self.running = False
        logger.info("🛑 共识交易系统正在停止...")
        for group in self.groups:
            for trader in group.multi_trader.platform_traders.values():
                await trader.client.close_session()
        
        # 关闭 Redis 连接
        if settings.redis_enabled:
            logger.info("🔄 正在关闭 Redis 连接...")
            shutdown_redis_manager()
        
        logger.info("✅ 共识交易系统已停止")


arena: Optional[ConsensusArena] = None


@app.on_event("startup")
async def startup_event():
    global arena
    arena = ConsensusArena()
    asyncio.create_task(arena.start())


@app.on_event("shutdown")
async def shutdown_event():
    if arena:
        await arena.stop()


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    if not arena:
        return {"status": "not_started"}
    
    groups_data = []
    for group in arena.groups:
        group_info = {
            "group_name": group.stats["group_name"],
            "platforms": group.stats.get("platforms", {}),
            "platform_comparison": group.stats.get("platform_comparison", {}),
            "consensus_decisions": group.stats.get("consensus_decisions", [])
        }
        groups_data.append(group_info)
    
    return {
        "status": "running" if arena.running else "stopped",
        "groups": groups_data,
        "update_interval": f"{arena.update_interval//60}分钟",
        "consensus_rule": f"至少{settings.consensus_min_votes}个AI同意",
        "enabled_platforms": get_enabled_platforms()
    }


@app.get("/api/platform_comparison")
async def get_platform_comparison():
    """获取平台对比数据"""
    if not arena:
        return {"error": "系统未启动"}
    
    comparison_data = []
    for group in arena.groups:
        comparison_data.append({
            "group_name": group.stats["group_name"],
            "comparison": group.stats.get("platform_comparison", {})
        })
    
    return {
        "groups": comparison_data,
        "enabled_platforms": get_enabled_platforms()
    }


@app.get("/")
async def root():
    """根路径"""
    return FileResponse("web/consensus_arena.html")


app.mount("/web", StaticFiles(directory="web"), name="web")


if __name__ == "__main__":
    logger.info(f"🌐 启动AI共识交易系统 - 多平台对比版")
    logger.info(f"启用平台: {', '.join(get_enabled_platforms())}")
    logger.info(f"⏱️  决策周期: {settings.consensus_interval//60}分钟")
    logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意")
    logger.info(f"🌐 前端页面: http://localhost:{settings.api_port}/")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )

