"""
AI Trading Arena - 主程序入口
"""
import asyncio
import uvicorn
from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient
from trading.risk_manager import RiskLimits
from arena.trading_engine import TradingEngine
from arena.performance import PerformanceTracker
from arena.leaderboard import Leaderboard
from api.routes import TradingAPI
from strategies.base import StrategyConfig
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.ml_strategy import MLStrategy
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AITradingArena:
    """AI 交易竞技场"""
    
    def __init__(self):
        """初始化竞技场"""
        self.client: HyperliquidClient = None
        self.trading_engine: TradingEngine = None
        self.performance_tracker: PerformanceTracker = None
        self.leaderboard: Leaderboard = None
        self.api: TradingAPI = None
        self.engine_task = None
    
    async def setup(self):
        """设置系统组件"""
        logger.info("初始化 AI Trading Arena...")
        
        # 初始化 Hyperliquid 客户端
        if not settings.hyperliquid_private_key:
            logger.error("未设置 Hyperliquid 私钥！请在 .env 文件中配置 HYPERLIQUID_PRIVATE_KEY")
            return False
        
        self.client = HyperliquidClient(
            private_key=settings.hyperliquid_private_key,
            testnet=settings.hyperliquid_testnet
        )
        
        logger.info(f"已连接到 Hyperliquid ({'测试网' if settings.hyperliquid_testnet else '主网'})")
        logger.info(f"钱包地址: {self.client.address}")
        
        # 初始化风险管理
        risk_limits = RiskLimits(
            max_position_size=settings.max_position_size,
            max_leverage=settings.max_leverage,
            daily_loss_limit=settings.daily_loss_limit,
            max_open_positions=settings.max_open_positions,
            min_account_balance=settings.min_account_balance,
            stop_loss_percentage=settings.stop_loss_percentage,
            take_profit_percentage=settings.take_profit_percentage
        )
        
        # 初始化交易引擎
        self.trading_engine = TradingEngine(self.client, risk_limits)
        self.trading_engine.update_interval = settings.arena_update_interval
        
        # 初始化性能追踪和排行榜
        self.performance_tracker = PerformanceTracker()
        self.leaderboard = Leaderboard(self.performance_tracker)
        
        # 注册示例策略
        await self.register_demo_strategies()
        
        # 初始化 API
        self.api = TradingAPI(
            self.trading_engine,
            self.performance_tracker,
            self.leaderboard
        )
        
        logger.info("系统初始化完成！")
        return True
    
    async def register_demo_strategies(self):
        """注册示例策略"""
        logger.info("注册示例策略...")
        
        # 支持的交易对
        coins = ["BTC", "ETH", "SOL"]
        
        # 1. 趋势跟踪策略
        trend_config = StrategyConfig(
            name="Trend Following",
            coins=coins,
            timeframe="5m",
            max_positions=2,
            position_size=200.0,
            fast_period=10,
            slow_period=30
        )
        trend_strategy = TrendFollowingStrategy(trend_config)
        self.trading_engine.register_strategy(trend_strategy)
        self.performance_tracker.register_strategy(
            trend_strategy.strategy_id,
            trend_strategy.config.name,
            initial_balance=1000.0
        )
        
        # 2. 均值回归策略
        mean_reversion_config = StrategyConfig(
            name="Mean Reversion",
            coins=coins,
            timeframe="5m",
            max_positions=2,
            position_size=150.0,
            period=20,
            std_multiplier=2.0
        )
        mean_reversion_strategy = MeanReversionStrategy(mean_reversion_config)
        self.trading_engine.register_strategy(mean_reversion_strategy)
        self.performance_tracker.register_strategy(
            mean_reversion_strategy.strategy_id,
            mean_reversion_strategy.config.name,
            initial_balance=1000.0
        )
        
        # 3. 机器学习策略
        ml_config = StrategyConfig(
            name="ML Strategy",
            coins=coins,
            timeframe="5m",
            max_positions=3,
            position_size=180.0,
            lookback_period=50,
            feature_window=10
        )
        ml_strategy = MLStrategy(ml_config)
        self.trading_engine.register_strategy(ml_strategy)
        self.performance_tracker.register_strategy(
            ml_strategy.strategy_id,
            ml_strategy.config.name,
            initial_balance=1000.0
        )
        
        logger.info(f"已注册 {len(self.trading_engine.strategies)} 个策略")
    
    async def start_trading_engine(self):
        """启动交易引擎"""
        logger.info("启动交易引擎...")
        await self.trading_engine.start()
    
    def start_api_server(self):
        """启动 API 服务器"""
        logger.info(f"启动 API 服务器: http://{settings.api_host}:{settings.api_port}")
        logger.info(f"API 文档: http://{settings.api_host}:{settings.api_port}/docs")
        
        uvicorn.run(
            self.api.app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info"
        )
    
    async def run(self):
        """运行竞技场"""
        # 设置系统
        success = await self.setup()
        if not success:
            return
        
        # 显示账户信息
        async with self.client:
            try:
                balance = await self.client.get_balance()
                logger.info(f"\n{'='*60}")
                logger.info(f"账户余额: ${balance['total_value']:.2f}")
                logger.info(f"可用余额: ${balance['available_balance']:.2f}")
                logger.info(f"未实现盈亏: ${balance['unrealized_pnl']:.2f}")
                logger.info(f"{'='*60}\n")
            except Exception as e:
                logger.error(f"获取账户信息失败: {e}")
        
        # 创建任务
        self.engine_task = asyncio.create_task(self.start_trading_engine())
        
        # 启动 API 服务器（阻塞）
        self.start_api_server()
    
    async def shutdown(self):
        """关闭系统"""
        logger.info("正在关闭系统...")
        
        if self.trading_engine:
            self.trading_engine.stop()
        
        if self.engine_task:
            self.engine_task.cancel()
            try:
                await self.engine_task
            except asyncio.CancelledError:
                pass
        
        if self.client and self.client.session:
            await self.client.session.close()
        
        logger.info("系统已关闭")


async def main():
    """主函数"""
    arena = AITradingArena()
    
    try:
        await arena.run()
    except KeyboardInterrupt:
        logger.info("\n收到中断信号...")
    except Exception as e:
        logger.error(f"系统错误: {e}", exc_info=True)
    finally:
        await arena.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")

