"""
AI共识交易系统 - 分组竞技场
Alpha组: DeepSeek + Claude + Grok4
Beta组: GPT-4 + Gemini + Qwen
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from config.settings import settings
from ai_models.deepseek_trader import DeepSeekTrader
from ai_models.claude_trader import ClaudeTrader
from ai_models.grok_trader import GrokTrader
from ai_models.gpt_trader import GPTTrader
from ai_models.gemini_trader import GeminiTrader
from ai_models.qwen_trader import QwenTrader
from trading.hyperliquid.client import HyperliquidClient
from trading.auto_trader import AutoTrader
from utils.symbol_filter import symbol_filter
from trading.kline_manager import KlineManager
from ai_models.base_ai import TradingDecision

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
    """AI组"""
    def __init__(self, name: str, ai_traders: List, hyperliquid_client: HyperliquidClient):
        self.name = name
        self.ai_traders = ai_traders
        self.hyperliquid = hyperliquid_client
        self.auto_trader = AutoTrader(hyperliquid_client)
        self.kline_manager = KlineManager(max_klines=16)
        self.start_time = datetime.now()  # 记录系统启动时间
        
        self.stats = {
            "group_name": name,
            "balance": 0.0,
            "pnl": 0.0,
            "roi": 0.0,
            "total_trades": 0,
            "consensus_decisions": [],
            "equity_curve": [],
            "trades": [],
            "positions": {}
        }
    
    async def sync_existing_positions(self):
        """同步现有持仓"""
        try:
            logger.info(f"[{self.name}] 🔄 正在同步现有持仓...")
            account = await self.hyperliquid.get_account_info()
            positions = account.get('assetPositions', [])
            
            synced_count = 0
            for pos in positions:
                try:
                    coin = pos['position']['coin']
                    size = float(pos['position']['szi'])
                    
                    if size == 0:
                        continue
                    
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    self.auto_trader.positions[coin] = {
                        'side': 'long' if is_long else 'short',
                        'entry_price': entry_px,
                        'size': abs_size,
                        'entry_time': datetime.now(),
                        'confidence': 0,
                        'reasoning': '系统启动时同步的历史持仓',
                        'order_id': 'synced'
                    }
                    
                    synced_count += 1
                    logger.info(f"[{self.name}]    ✅ {coin} {'LONG' if is_long else 'SHORT'} {abs_size:.5f} @ ${entry_px:,.2f}")
                
                except Exception as e:
                    logger.warning(f"[{self.name}] 解析持仓失败: {e}")
                    continue
            
            if synced_count > 0:
                logger.info(f"[{self.name}] ✅ 已同步 {synced_count} 个现有持仓")
            else:
                logger.info(f"[{self.name}] 📭 没有现有持仓")
        
        except Exception as e:
            logger.error(f"[{self.name}] ❌ 同步持仓失败: {e}")
    
    async def get_consensus_decision(self, coin: str, market_data: Dict, orderbook: Dict, recent_trades: List, position_info: Optional[Dict] = None) -> Tuple[Optional[TradingDecision], float, str, List[Dict]]:
        """获取组内共识决策（并行调用所有AI）"""
        
        # 为AI创建K线历史prompt
        kline_history_data = self.kline_manager.format_for_prompt(max_rows=16)
        
        # 定义单个AI的决策任务
        async def get_ai_decision(ai_trader):
            try:
                ai_name = ai_trader.__class__.__name__.replace('Trader', '')
                logger.info(f"[{self.name}] 🤖 正在获取 {ai_name} 的决策...")
                
                # 临时包装prompt方法
                original_create_prompt = ai_trader.create_market_prompt
                def wrapped_prompt(c, m, o, p=None, kline_history=None):
                    return original_create_prompt(c, m, o, p, kline_history=kline_history_data)
                ai_trader.create_market_prompt = wrapped_prompt
                
                decision, confidence, reasoning = await ai_trader.analyze_market(
                    coin, market_data, orderbook, recent_trades, position_info
                )
                
                # 恢复原始方法
                ai_trader.create_market_prompt = original_create_prompt
                
                logger.info(f"[{self.name}]    {ai_name}: {decision} (信心: {confidence:.1f}%)")
                
                return {
                    'ai_name': ai_name,
                    'decision': decision,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
            
            except Exception as e:
                logger.error(f"[{self.name}] ❌ {ai_trader.__class__.__name__} 决策失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return None
        
        # 并行调用所有AI
        logger.info(f"[{self.name}] 🚀 开始并行调用 {len(self.ai_traders)} 个AI模型...")
        results = await asyncio.gather(*[get_ai_decision(ai) for ai in self.ai_traders])
        
        # 过滤掉失败的结果
        ai_decisions = [r for r in results if r is not None]
        
        if not ai_decisions:
            return None, 0, "所有AI决策失败", []
        
        # 统计投票 - 将BUY和STRONG_BUY归为一类，SELL和STRONG_SELL归为一类
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
        
        # 统计各方向的票数
        buy_count = len(buy_votes)
        sell_count = len(sell_votes)
        hold_count = len(hold_votes)
        
        # 找到得票最多的方向
        vote_counts = [
            (buy_count, TradingDecision.BUY, buy_votes, "看涨"),
            (sell_count, TradingDecision.SELL, sell_votes, "看跌"),
            (hold_count, TradingDecision.HOLD, hold_votes, "观望")
        ]
        vote_counts.sort(key=lambda x: x[0], reverse=True)
        
        vote_count, consensus_decision, supporting_ais, direction_name = vote_counts[0]
        
        # 计算平均信心度（只计算支持该方向的AI）
        if supporting_ais:
            avg_confidence = sum(d['confidence'] for d in supporting_ais) / len(supporting_ais)
        else:
            avg_confidence = 0
        
        # 生成共识总结
        vote_summary = f"看涨{buy_count}票, 看跌{sell_count}票, 观望{hold_count}票"
        consensus_summary = f"共识结果: {direction_name} ({vote_count}/{len(ai_decisions)}票, 平均信心{avg_confidence:.1f}%)\n投票详情: {vote_summary}"
        
        logger.info(f"[{self.name}] 📊 {consensus_summary}")
        
        # 判断是否达成共识（至少MIN_VOTES个AI同意）
        min_votes = settings.consensus_min_votes
        if vote_count >= min_votes:
            logger.info(f"[{self.name}] ✅ 达成共识！将执行: {direction_name} ({consensus_decision})")
            return consensus_decision, avg_confidence, consensus_summary, ai_decisions
        else:
            logger.info(f"[{self.name}] ⚠️  未达成共识（需要至少{min_votes}票），保持观望")
            return TradingDecision.HOLD, avg_confidence, f"未达成共识（需要{min_votes}票，实际最多{vote_count}票），保持观望\n{vote_summary}", ai_decisions
    
    async def sync_trades_from_hyperliquid(self):
        """从Hyperliquid同步交易记录（只统计系统启动后的交易）"""
        try:
            # 计算启动时间的毫秒时间戳
            start_time_ms = int(self.start_time.timestamp() * 1000)
            
            # 从Hyperliquid获取交易记录（只获取启动后的）
            fills = await self.hyperliquid.get_user_fills(limit=200, start_time_ms=start_time_ms)
            
            if not fills:
                logger.debug(f"[{self.name}] 📊 没有新的交易记录")
                return
            
            # 提取已有交易的唯一标识
            existing_keys = {fill.get('hash', '') for fill in self.stats["trades"] if fill.get('hash')}
            
            new_trade_count = 0
            for fill in fills:
                fill_hash = fill.get('hash', '')
                if not fill_hash or fill_hash in existing_keys:
                    continue
                
                # 解析交易时间（Hyperliquid返回的是毫秒时间戳）
                fill_time_ms = fill.get('time', 0)
                fill_datetime = datetime.fromtimestamp(fill_time_ms / 1000) if fill_time_ms else None
                
                # 再次确认时间过滤
                if fill_datetime and fill_datetime < self.start_time:
                    continue
                
                # 判断开仓还是平仓
                direction = fill.get('dir', '')
                is_open = 'Open' in direction
                is_long = 'Long' in direction
                
                # 构建交易记录
                trade_record = {
                    "time": fill_datetime.isoformat() if fill_datetime else "",
                    "coin": fill.get('coin', ''),
                    "side": "LONG" if is_long else "SHORT",
                    "action": "OPEN" if is_open else "CLOSE",
                    "size": abs(float(fill.get('sz', 0))),
                    "px": float(fill.get('px', 0)),
                    "closedPnl": float(fill.get('closedPnl', 0)),
                    "fee": float(fill.get('fee', 0)),
                    "hash": fill_hash
                }
                
                self.stats["trades"].insert(0, trade_record)
                existing_keys.add(fill_hash)
                new_trade_count += 1
            
            # 按时间排序
            self.stats["trades"].sort(key=lambda x: x.get('time', ''), reverse=True)
            
            if new_trade_count > 0:
                logger.info(f"[{self.name}] 📊 新增 {new_trade_count} 笔交易，总计 {len(self.stats['trades'])} 笔")
            
        except Exception as e:
            logger.error(f"[{self.name}] ❌ 同步交易记录失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_stats(self, balance: float, price: float):
        """更新统计数据（保留所有历史）"""
        self.stats["balance"] = balance
        self.stats["pnl"] = balance - settings.ai_initial_balance
        self.stats["roi"] = (self.stats["pnl"] / settings.ai_initial_balance * 100) if settings.ai_initial_balance > 0 else 0

        # 交易记录已由 sync_trades_from_hyperliquid() 同步，无需重复添加
        self.stats["total_trades"] = len(self.stats["trades"])
        self.stats["positions"] = self.auto_trader.get_all_positions()

        # 添加权益曲线数据点（保留所有历史，不限制）
        self.stats["equity_curve"].append({
            "time": datetime.now().isoformat(),
            "balance": balance
        })


class ConsensusArena:
    """共识竞技场"""
    def __init__(self):
        self.groups: List[AIGroup] = []
        self.running = False
        self.update_interval = settings.consensus_interval
    
    async def initialize(self):
        """初始化系统"""
        logger.info("=" * 80)
        logger.info("🤖 AI共识交易系统 - 分组竞技场")
        logger.info("=" * 80)
        logger.info(f"网络: {'测试网' if settings.hyperliquid_testnet else '⚠️  主网'}")
        logger.info(f"交易币种: {symbol_filter.get_default_symbol()}")
        logger.info(f"⏱️  决策周期: {self.update_interval//60}分钟")
        logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意才执行")
        logger.info(f"🛡️  风险管理: 每日亏损限制 + 动态止损止盈")
        logger.info(f"每组初始资金: ${settings.ai_initial_balance}")
        logger.info("=" * 80)
        
        # 初始化 Alpha 组
        logger.info("\n📊 初始化 Alpha 组 (DeepSeek + Claude + Grok4)...")
        alpha_client = HyperliquidClient(
            private_key=settings.group_1_private_key,
            testnet=settings.hyperliquid_testnet
        )
        alpha_ais = [
            DeepSeekTrader(api_key=settings.deepseek_api_key),
            ClaudeTrader(api_key=settings.claude_api_key),
            GrokTrader(api_key=settings.grok_api_key)
        ]
        alpha_group = AIGroup("Alpha组", alpha_ais, alpha_client)
        await alpha_group.sync_existing_positions()
        self.groups.append(alpha_group)
        logger.info(f"✅ Alpha组初始化完成 (地址: {alpha_client.address})")
        
        # 初始化 Beta 组
        logger.info("\n📊 初始化 Beta 组 (GPT-4 + Gemini + Qwen)...")
        beta_client = HyperliquidClient(
            private_key=settings.group_2_private_key,
            testnet=settings.hyperliquid_testnet
        )
        beta_ais = [
            GPTTrader(api_key=settings.openai_api_key, model=settings.gpt_model),
            GeminiTrader(api_key=settings.gemini_api_key),
            QwenTrader(api_key=settings.qwen_api_key)
        ]
        beta_group = AIGroup("Beta组", beta_ais, beta_client)
        await beta_group.sync_existing_positions()
        self.groups.append(beta_group)
        logger.info(f"✅ Beta组初始化完成 (地址: {beta_client.address})")
        
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
                
                # 获取市场数据（所有组共享）
                try:
                    market_data = await self.groups[0].hyperliquid.get_market_data(trading_symbol)
                    current_price = market_data['price']
                    logger.info(f"💰 {trading_symbol} 价格: ${current_price:,.2f}")
                    logger.info(f"📈 24h涨跌: {market_data.get('change_24h', 0):+.2f}%")
                    
                    orderbook_data = await self.groups[0].hyperliquid.get_orderbook(trading_symbol)
                    recent_trades = await self.groups[0].hyperliquid.get_recent_trades(trading_symbol, limit=10)
                except Exception as e:
                    logger.error(f"❌ 获取市场数据失败: {e}")
                    await asyncio.sleep(30)
                    continue
                
                # 为每个组并行执行决策
                async def process_group(group):
                    """处理单个组的决策"""
                    try:
                        logger.info(f"\n{'─'*80}")
                        logger.info(f"📊 {group.name} 开始共识决策")
                        logger.info(f"{'─'*80}")
                        
                        # 更新K线
                        group.kline_manager.update_price(
                            price=current_price,
                            volume=market_data.get('volume', 0)
                        )
                        
                        # 获取账户余额
                        account = await group.hyperliquid.get_account_info()
                        balance = float(account.get('marginSummary', {}).get('accountValue', 0))
                        logger.info(f"[{group.name}] 💰 账户余额: ${balance:,.2f}")
                        
                        # 检查是否有持仓
                        has_position = trading_symbol in group.auto_trader.positions
                        position_info = group.auto_trader.positions.get(trading_symbol)
                        
                        if has_position:
                            logger.info(f"[{group.name}] 📍 当前持有 {position_info['side'].upper()} 仓位")
                        
                        # 获取共识决策
                        consensus_decision, confidence, summary, ai_votes = await group.get_consensus_decision(
                            trading_symbol, market_data, orderbook_data, recent_trades, position_info
                        )
                        
                        # 记录决策（保留所有历史）
                        decision_record = {
                            "time": datetime.now().isoformat(),
                            "decision": str(consensus_decision),
                            "confidence": confidence,
                            "summary": summary,
                            "ai_votes": ai_votes,
                            "price": current_price,
                            "has_position": has_position
                        }
                        group.stats["consensus_decisions"].insert(0, decision_record)
                        # 保留最近100条决策记录（增加历史容量）
                        group.stats["consensus_decisions"] = group.stats["consensus_decisions"][:100]
                        
                        # 执行决策
                        if consensus_decision and consensus_decision != TradingDecision.HOLD:
                            await group.auto_trader.execute_decision(
                                trading_symbol,
                                consensus_decision,
                                confidence,
                                summary,
                                current_price,
                                balance
                            )
                        
                        # 从Hyperliquid同步交易记录
                        await group.sync_trades_from_hyperliquid()
                        
                        # 更新统计
                        group.update_stats(balance, current_price)
                        
                    except Exception as e:
                        logger.error(f"[{group.name}] ❌ 决策执行错误: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # 🚀 并行处理所有组（Alpha和Beta同时执行）
                logger.info(f"🚀 开始并行处理 {len(self.groups)} 个组...")
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
            if group.hyperliquid:
                await group.hyperliquid.close_session()
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
        groups_data.append({
            "group_name": group.stats["group_name"],
            "address": group.hyperliquid.address,
            "balance": group.stats["balance"],
            "pnl": group.stats["pnl"],
            "roi": group.stats["roi"],
            "total_trades": group.stats["total_trades"],
            "consensus_decisions": group.stats["consensus_decisions"],
            "equity_curve": group.stats["equity_curve"],
            "trades": group.stats.get("trades", []),
            "positions": group.stats.get("positions", {})
        })
    
    return {
        "status": "running" if arena.running else "stopped",
        "groups": groups_data,
        "update_interval": f"{arena.update_interval//60}分钟",
        "consensus_rule": f"至少{settings.consensus_min_votes}个AI同意"
    }

@app.get("/api/kline")
async def get_kline_data(interval: str = "15m", lookback: int = 200):
    """
    获取K线数据和交易标记
    
    Args:
        interval: K线周期 (1m, 5m, 15m, 1h, 4h, 1d)
        lookback: 回溯K线数量
    """
    if not arena or not arena.groups:
        return {"error": "系统未启动"}
    
    try:
        trading_symbol = symbol_filter.get_default_symbol()
        
        # 从第一个组的客户端获取K线数据（所有组看同一个市场）
        candles = await arena.groups[0].hyperliquid.get_candles(
            trading_symbol, 
            interval=interval, 
            lookback=lookback
        )
        
        # 收集所有组的交易标记（只显示系统启动后的交易）
        trade_markers = []
        for group in arena.groups:
            # 使用组的start_time过滤
            group_start_time = group.start_time
            
            for trade in group.stats.get("trades", []):
                # 将ISO时间转换为毫秒时间戳
                try:
                    from datetime import datetime
                    trade_time = datetime.fromisoformat(trade.get("time", ""))
                    
                    # 只显示系统启动后的交易
                    if trade_time < group_start_time:
                        continue
                    
                    timestamp_ms = int(trade_time.timestamp() * 1000)
                    
                    trade_markers.append({
                        "time": timestamp_ms,
                        "price": trade.get("px", 0),
                        "group": group.stats["group_name"],
                        "action": trade.get("action", ""),
                        "side": trade.get("side", ""),
                        "size": trade.get("size", 0),
                        "pnl": trade.get("closedPnl", 0)  # 平仓盈亏
                    })
                except:
                    continue
        
        return {
            "candles": candles,
            "trade_markers": trade_markers,
            "symbol": trading_symbol,
            "interval": interval
        }
        
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.get("/")
async def root():
    """根路径"""
    return FileResponse("web/consensus_arena.html")

app.mount("/web", StaticFiles(directory="web"), name="web")

if __name__ == "__main__":
    logger.info(f"🌐 启动AI共识交易系统")
    logger.info(f"⏱️  决策周期: {settings.consensus_interval//60}分钟")
    logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意")
    logger.info(f"🌐 前端页面: http://localhost:{settings.api_port}/")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )

