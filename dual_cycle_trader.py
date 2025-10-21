#!/usr/bin/env python3
"""
双周期交易系统
- 开仓决策：15分钟周期
- 持仓管理：2分钟检查
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from config.settings import settings
from ai_models.deepseek_trader import DeepSeekTrader
from trading.hyperliquid.client import HyperliquidClient
from trading.auto_trader import AutoTrader
from utils.symbol_filter import symbol_filter
from trading.kline_manager import KlineManager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arena.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DualCycleArena:
    """双周期交易系统"""
    
    def __init__(self):
        self.ai_trader = None
        self.hyperliquid = None
        self.auto_trader = None
        self.kline_manager = None
        self.running = False
        
        # 双周期配置
        self.decision_interval = 900  # 15分钟：用于开仓决策
        self.check_interval = 120     # 2分钟：用于持仓检查
        
        self.stats = {
            "ai_name": "DeepSeek",
            "balance": 0.0,
            "pnl": 0.0,
            "roi": 0.0,
            "total_trades": 0,
            "decisions": [],
            "position_checks": [],  # 新增：持仓检查记录
            "equity_curve": [],
            "trades": [],
            "positions": {}
        }
    
    async def initialize(self):
        """初始化"""
        logger.info("=" * 80)
        logger.info("🤖 DeepSeek AI - 15分钟超短线波段交易系统")
        logger.info("=" * 80)
        logger.info(f"网络: {'测试网' if settings.hyperliquid_testnet else '⚠️  主网'}")
        logger.info(f"交易币种: {symbol_filter.get_default_symbol()}")
        logger.info(f"📊 开仓决策周期: {self.decision_interval//60}分钟（超短线波段）")
        logger.info(f"⚡ 持仓检查周期: {self.check_interval//60}分钟")
        logger.info(f"🎯 策略: 快进快出，目标1-3%波动")
        logger.info(f"🛡️  止损: 1.5% | 止盈: 3%")
        logger.info("=" * 80)
        
        self.ai_trader = DeepSeekTrader(api_key=settings.deepseek_api_key)
        logger.info("✅ DeepSeek AI 初始化成功")
        
        self.hyperliquid = HyperliquidClient(
            private_key=settings.hyperliquid_private_key,
            testnet=settings.hyperliquid_testnet
        )
        logger.info(f"✅ Hyperliquid 连接成功 ({self.hyperliquid.address})")
        
        self.auto_trader = AutoTrader(self.hyperliquid)
        logger.info(f"✅ 自动交易器已启用")
        
        # 初始化K线管理器（保留16根K线 = 4小时历史）
        self.kline_manager = KlineManager(max_klines=16)
        logger.info(f"✅ K线管理器已启用（Intraday Series模式）")
        
        return True
    
    async def decision_loop(self):
        """开仓决策循环（15分钟）"""
        loop_count = 0
        trading_symbol = symbol_filter.get_default_symbol()
        
        while self.running:
            try:
                loop_count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"📊 开仓决策循环 #{loop_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*80}")
                
                # 获取市场数据
                market_data = await self.hyperliquid.get_market_data(trading_symbol)
                current_price = market_data['price']
                logger.info(f"💰 {trading_symbol} 价格: ${current_price:,.2f}")
                logger.info(f"📈 24h涨跌: {market_data.get('change_24h', 0):+.2f}%")
                
                # 更新K线数据（积累历史）
                self.kline_manager.update_price(
                    price=current_price,
                    volume=market_data.get('volume', 0)
                )
                
                # 获取订单簿
                try:
                    orderbook_data = await self.hyperliquid.get_orderbook(trading_symbol)
                    logger.info(f"📖 订单簿: {len(orderbook_data.get('levels', [[],[]])[0])} 档买单, {len(orderbook_data.get('levels', [[],[]])[1])} 档卖单")
                except Exception as e:
                    logger.warning(f"⚠️  获取订单簿失败: {e}")
                    orderbook_data = {"levels": [[], []]}
                
                # 获取最近成交
                try:
                    recent_trades = await self.hyperliquid.get_recent_trades(trading_symbol, limit=10)
                except Exception as e:
                    logger.warning(f"⚠️  获取最近成交失败: {e}")
                    recent_trades = []
                
                # 获取账户信息
                account = await self.hyperliquid.get_account_info()
                balance = float(account.get('marginSummary', {}).get('accountValue', 0))
                current_balance = balance
                self.ai_trader.current_balance = current_balance
                
                logger.info(f"💰 账户余额: ${current_balance:,.2f}")
                
                # 检查是否有持仓
                has_position = trading_symbol in self.auto_trader.positions
                
                if has_position:
                    logger.info(f"⚠️  已有持仓，跳过开仓决策")
                else:
                    # 只在无持仓时进行开仓决策
                    logger.info(f"🤖 进行开仓决策分析（强制方向模式）...")
                    
                    # 临时修改提示词生成器，强制 AI 选择方向
                    original_create_prompt = self.ai_trader.create_market_prompt
                    
                    def aggressive_prompt_creator(coin, market_data, orderbook, recent_trades, position_info=None):
                        # 获取K线历史数据
                        kline_history = self.kline_manager.format_for_prompt(max_rows=16)
                        
                        # 调用原始提示词生成器（传入K线历史）
                        prompt = original_create_prompt(coin, market_data, orderbook, position_info, kline_history=kline_history)
                        # 替换决策选项，移除 HOLD
                        prompt = prompt.replace(
                            "DECISION: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL]",
                            "DECISION: [BUY/SELL] (15分钟超短线波段，必须选择方向)"
                        )
                        # 添加超短线波段交易指引
                        prompt += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
交易策略：15分钟超短线波段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你是一个超短线波段交易员，基于15分钟K线周期交易。

核心原则：
1. 必须选择 BUY（做多）或 SELL（做空），不允许观望
2. 捕捉15分钟内的短期价格波动
3. 快进快出，目标 1-2% 的波动利润
4. 重点关注：
   - 近期价格趋势（24h涨跌）
   - 订单簿买卖压力
   - 资金费率方向
   - 成交量变化

决策逻辑：
• 看多信号：24h涨幅 > 0 OR 买盘深度 > 卖盘 OR 资金费率负值（空头付费）
• 看空信号：24h跌幅 < 0 OR 卖盘深度 > 买盘 OR 资金费率正值（多头付费）

风险管理：
• 系统自动设置 2% 止损
• 系统自动设置 5% 止盈
• 你只需选择方向和信心度（建议 60-80%）

当前市场快照：
• 价格: ${market_data.get('price', 0):,.2f}
• 24h变化: {market_data.get('change_24h', 0):+.2f}%
• 趋势判断: {'看多' if market_data.get('change_24h', 0) > 0 else '看空'}

立即做出方向判断！
"""
                        return prompt
                    
                    # 替换提示词生成器
                    self.ai_trader.create_market_prompt = aggressive_prompt_creator
                    
                    result = await self.ai_trader.analyze_market(
                        trading_symbol,
                        market_data,
                        orderbook=orderbook_data,
                        recent_trades=recent_trades
                    )
                    
                    # 恢复原始提示词生成器
                    self.ai_trader.create_market_prompt = original_create_prompt
                    
                    decision_action, confidence, reasoning = result
                    logger.info(f"🤖 DeepSeek 决策: {decision_action} (信心: {confidence:.1f}%)")
                    logger.info(f"   理由: {reasoning[:150]}...")
                    
                    # 记录决策到前端
                    decision_record = {
                        "time": datetime.now().isoformat(),
                        "action": str(decision_action),
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "price": market_data['price']
                    }
                    self.stats["decisions"].insert(0, decision_record)
                    self.stats["decisions"] = self.stats["decisions"][:20]  # 保留最近20条
                    
                    # 尝试执行开仓
                    trade_result = await self.auto_trader.execute_decision(
                        coin=trading_symbol,
                        decision=decision_action,
                        confidence=confidence,
                        reasoning=reasoning,
                        current_price=market_data['price'],
                        balance=current_balance
                    )
                    
                    if trade_result:
                        logger.info(f"✅ 已开仓！")
                
                # 更新统计
                self.update_stats(current_balance, market_data['price'])
                
                # 等待下一个决策周期
                logger.info(f"⏰ 等待 {self.decision_interval} 秒后进行下一次开仓决策...")
                await asyncio.sleep(self.decision_interval)
                
            except asyncio.CancelledError:
                logger.info("⏹️  决策循环被取消")
                break
            except Exception as e:
                logger.error(f"❌ 决策循环错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)
    
    async def check_loop(self):
        """持仓检查循环（2分钟）"""
        loop_count = 0
        trading_symbol = symbol_filter.get_default_symbol()
        
        # 延迟5秒启动，避免与决策循环冲突
        await asyncio.sleep(5)
        
        while self.running:
            try:
                loop_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"⚡ 持仓检查循环 #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"{'='*60}")
                
                # 检查是否有持仓
                positions = self.auto_trader.get_all_positions()
                
                if not positions:
                    logger.info(f"💤 无持仓，跳过检查")
                else:
                    # 有持仓，进行止损止盈检查
                    logger.info(f"📊 检查持仓: {len(positions)} 个")
                    
                    # 获取当前价格
                    market_data = await self.hyperliquid.get_market_data(trading_symbol)
                    current_price = market_data['price']
                    
                    logger.info(f"💰 当前价格: ${current_price:,.2f}")
                    
                    # 检查每个持仓
                    for coin, position in list(positions.items()):
                        entry_price = position['entry_price']
                        side = position['side']
                        
                        # 计算盈亏
                        if side == 'long':
                            pnl_pct = (current_price - entry_price) / entry_price
                        else:  # short
                            pnl_pct = (entry_price - current_price) / entry_price
                        
                        logger.info(f"   {coin} {side.upper()}: 入场 ${entry_price:,.2f}, 盈亏 {pnl_pct*100:+.2f}%")
                        
                        # 检查止损
                        if side == 'long' and pnl_pct <= -self.auto_trader.stop_loss_pct:
                            logger.warning(f"🛑 {coin} 触发止损！")
                            await self.auto_trader._close_position(coin, current_price, "止损")
                        elif side == 'short' and pnl_pct <= -self.auto_trader.stop_loss_pct:
                            logger.warning(f"🛑 {coin} 触发止损！")
                            await self.auto_trader._close_position(coin, current_price, "止损")
                        
                        # 检查止盈
                        elif pnl_pct >= self.auto_trader.take_profit_pct:
                            logger.info(f"🎯 {coin} 触发止盈！")
                            await self.auto_trader._close_position(coin, current_price, "止盈")
                    
                    # 更新账户余额
                    account = await self.hyperliquid.get_account_info()
                    balance = float(account.get('marginSummary', {}).get('accountValue', 0))
                    logger.info(f"💰 当前余额: ${balance:,.2f}")
                    
                    # 更新统计数据（包括权益曲线）
                    self.update_stats(balance, current_price)
                
                # 等待下一个检查周期
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("⏹️  检查循环被取消")
                break
            except Exception as e:
                logger.error(f"❌ 检查循环错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(30)
    
    def update_stats(self, balance: float, price: float):
        """更新统计数据"""
        self.stats["balance"] = balance
        self.stats["pnl"] = balance - settings.ai_initial_balance
        self.stats["roi"] = (self.stats["pnl"] / settings.ai_initial_balance * 100) if settings.ai_initial_balance > 0 else 0
        
        trading_stats = self.auto_trader.get_statistics()
        self.stats["total_trades"] = trading_stats.get("total_trades", 0)
        self.stats["trades"] = self.auto_trader.get_trade_history(limit=20)
        self.stats["positions"] = self.auto_trader.get_all_positions()
        
        # 记录权益曲线
        self.stats["equity_curve"].append({
            "time": datetime.now().isoformat(),
            "balance": balance
        })
        if len(self.stats["equity_curve"]) > 100:
            self.stats["equity_curve"] = self.stats["equity_curve"][-100:]
    
    def stop(self):
        """停止"""
        logger.info("\n⏹️  正在停止...")
        self.running = False


# 全局实例
arena: Optional[DualCycleArena] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global arena
    
    # 启动
    arena = DualCycleArena()
    if await arena.initialize():
        logger.info("")
        logger.info("🚀 双周期系统启动成功！")
        logger.info("")
        arena.running = True
        
        # 启动两个循环
        asyncio.create_task(arena.decision_loop())  # 15分钟决策
        asyncio.create_task(arena.check_loop())     # 2分钟检查
    
    yield
    
    # 关闭
    if arena:
        arena.stop()


# FastAPI 应用
app = FastAPI(title="DeepSeek Dual Cycle Arena", lifespan=lifespan)


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    if not arena:
        return {"status": "not_started"}
    
    trading_stats = arena.auto_trader.get_statistics() if arena.auto_trader else {}
    
    return {
        "status": "running" if arena.running else "stopped",
        "ai_name": arena.stats["ai_name"],
        "balance": arena.stats["balance"],
        "pnl": arena.stats["pnl"],
        "roi": arena.stats["roi"],
        "total_trades": arena.stats["total_trades"],
        "decisions": arena.stats["decisions"],
        "equity_curve": arena.stats["equity_curve"],
        "trades": arena.stats.get("trades", []),
        "positions": arena.stats.get("positions", {}),
        "trading_stats": trading_stats,
        "auto_trading_enabled": True,
        "strategy": "dual_cycle",
        "decision_interval": "15分钟",
        "check_interval": "2分钟"
    }


@app.get("/")
async def root():
    """根路径"""
    return FileResponse("web/deepseek_arena.html")


# 挂载静态文件
app.mount("/web", StaticFiles(directory="web"), name="web")


if __name__ == "__main__":
    logger.info(f"🌐 启动双周期交易系统")
    logger.info(f"📊 开仓决策: 15分钟周期")
    logger.info(f"⚡ 持仓检查: 2分钟周期")
    logger.info(f"🌐 前端页面: http://localhost:{settings.api_port}/")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )

