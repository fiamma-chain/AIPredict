"""
自定义策略示例

这个文件展示了如何创建和使用自定义交易策略
"""
import asyncio
from typing import Dict
from strategies.base import BaseStrategy, StrategyConfig, Signal


class RSIStrategy(BaseStrategy):
    """
    RSI 策略示例
    基于相对强弱指标进行交易决策
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 策略参数
        self.rsi_period = config.params.get("rsi_period", 14)
        self.oversold_level = config.params.get("oversold_level", 30)
        self.overbought_level = config.params.get("overbought_level", 70)
        
        # 价格历史
        self.price_history: Dict[str, list] = {}
    
    def _calculate_rsi(self, prices: list) -> float:
        """
        计算 RSI 指标
        
        Args:
            prices: 价格列表
            
        Returns:
            RSI 值 (0-100)
        """
        if len(prices) < self.rsi_period + 1:
            return 50.0  # 默认中性值
        
        # 计算价格变化
        changes = []
        for i in range(1, len(prices)):
            changes.append(prices[i] - prices[i-1])
        
        # 分离涨跌
        gains = [max(c, 0) for c in changes[-self.rsi_period:]]
        losses = [abs(min(c, 0)) for c in changes[-self.rsi_period:]]
        
        # 计算平均涨跌
        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def analyze(self, coin: str, market_data: Dict) -> Signal:
        """
        分析市场数据并生成交易信号
        
        Args:
            coin: 币种
            market_data: 市场数据
            
        Returns:
            交易信号
        """
        # 更新市场数据
        await self.on_market_data(coin, market_data)
        
        # 获取当前价格
        current_price = float(market_data.get("markPx", 0))
        
        if current_price == 0:
            return Signal.HOLD
        
        # 初始化价格历史
        if coin not in self.price_history:
            self.price_history[coin] = []
        
        # 添加价格
        self.price_history[coin].append(current_price)
        
        # 限制历史长度
        max_length = self.rsi_period + 50
        if len(self.price_history[coin]) > max_length:
            self.price_history[coin] = self.price_history[coin][-max_length:]
        
        # 计算 RSI
        rsi = self._calculate_rsi(self.price_history[coin])
        
        # 检查是否有持仓
        has_position = coin in self.state.positions
        
        # 生成信号
        if rsi <= self.oversold_level and not has_position:
            # RSI 超卖，买入信号
            print(f"[{self.config.name}] {coin} RSI={rsi:.2f} (超卖) -> 买入")
            return Signal.BUY
        
        elif rsi >= self.overbought_level and has_position:
            # RSI 超买，卖出信号
            print(f"[{self.config.name}] {coin} RSI={rsi:.2f} (超买) -> 卖出")
            return Signal.CLOSE
        
        # 持仓止损检查
        if has_position:
            position = self.state.positions[coin]
            entry_price = position.get("entry_price", 0)
            
            if entry_price > 0:
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                # 止损 -3%
                if pnl_percentage < -3.0:
                    print(f"[{self.config.name}] {coin} 触发止损: {pnl_percentage:.2f}%")
                    return Signal.CLOSE
                
                # 止盈 +5%
                if pnl_percentage > 5.0:
                    print(f"[{self.config.name}] {coin} 触发止盈: {pnl_percentage:.2f}%")
                    return Signal.CLOSE
        
        return Signal.HOLD
    
    def get_position_size(self, coin: str, signal: Signal, balance: float) -> float:
        """
        计算持仓大小
        
        Args:
            coin: 币种
            signal: 交易信号
            balance: 可用余额
            
        Returns:
            持仓大小（USD）
        """
        if signal == Signal.HOLD or signal == Signal.CLOSE:
            return 0.0
        
        # 使用 15% 的资金
        risk_percentage = 0.15
        position_value = min(balance * risk_percentage, self.config.position_size)
        
        return position_value


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    波动率突破策略
    当价格突破波动率通道时进行交易
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        self.period = config.params.get("period", 20)
        self.multiplier = config.params.get("multiplier", 2.0)
        
        self.price_history: Dict[str, list] = {}
    
    def _calculate_bollinger_bands(self, prices: list):
        """计算布林带"""
        if len(prices) < self.period:
            return None, None, None
        
        recent = prices[-self.period:]
        mean = sum(recent) / len(recent)
        variance = sum((p - mean) ** 2 for p in recent) / len(recent)
        std = variance ** 0.5
        
        upper = mean + (self.multiplier * std)
        lower = mean - (self.multiplier * std)
        
        return upper, mean, lower
    
    async def analyze(self, coin: str, market_data: Dict) -> Signal:
        """分析市场数据"""
        await self.on_market_data(coin, market_data)
        
        current_price = float(market_data.get("markPx", 0))
        
        if current_price == 0:
            return Signal.HOLD
        
        if coin not in self.price_history:
            self.price_history[coin] = []
        
        self.price_history[coin].append(current_price)
        
        if len(self.price_history[coin]) > self.period + 10:
            self.price_history[coin] = self.price_history[coin][-(self.period + 10):]
        
        upper, middle, lower = self._calculate_bollinger_bands(self.price_history[coin])
        
        if not upper or not lower:
            return Signal.HOLD
        
        has_position = coin in self.state.positions
        
        # 价格突破上轨
        if current_price > upper and not has_position:
            print(f"[{self.config.name}] {coin} 突破上轨 -> 买入")
            return Signal.BUY
        
        # 价格回归中轨
        if has_position and abs(current_price - middle) / middle < 0.01:
            print(f"[{self.config.name}] {coin} 回归中轨 -> 平仓")
            return Signal.CLOSE
        
        # 止损
        if has_position:
            position = self.state.positions[coin]
            entry_price = position.get("entry_price", 0)
            
            if entry_price > 0:
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                if pnl_percentage < -4.0:
                    return Signal.CLOSE
        
        return Signal.HOLD
    
    def get_position_size(self, coin: str, signal: Signal, balance: float) -> float:
        """计算持仓大小"""
        if signal == Signal.HOLD or signal == Signal.CLOSE:
            return 0.0
        
        return min(balance * 0.12, self.config.position_size)


# ========== 使用示例 ==========

async def main():
    """主函数 - 展示如何使用自定义策略"""
    from config.settings import settings
    from trading.hyperliquid.client import HyperliquidClient
    from trading.risk_manager import RiskLimits
    from arena.trading_engine import TradingEngine
    from arena.performance import PerformanceTracker
    
    # 创建客户端
    client = HyperliquidClient(
        private_key=settings.hyperliquid_private_key,
        testnet=True
    )
    
    # 创建交易引擎
    risk_limits = RiskLimits()
    engine = TradingEngine(client, risk_limits)
    
    # 创建性能追踪器
    tracker = PerformanceTracker()
    
    # 1. 注册 RSI 策略
    rsi_config = StrategyConfig(
        name="RSI Strategy",
        coins=["BTC", "ETH"],
        max_positions=2,
        position_size=200.0,
        rsi_period=14,
        oversold_level=30,
        overbought_level=70
    )
    rsi_strategy = RSIStrategy(rsi_config)
    engine.register_strategy(rsi_strategy)
    tracker.register_strategy(
        rsi_strategy.strategy_id,
        rsi_strategy.config.name,
        initial_balance=1000.0
    )
    
    # 2. 注册波动率突破策略
    volatility_config = StrategyConfig(
        name="Volatility Breakout",
        coins=["BTC", "SOL"],
        max_positions=2,
        position_size=150.0,
        period=20,
        multiplier=2.0
    )
    volatility_strategy = VolatilityBreakoutStrategy(volatility_config)
    engine.register_strategy(volatility_strategy)
    tracker.register_strategy(
        volatility_strategy.strategy_id,
        volatility_strategy.config.name,
        initial_balance=1000.0
    )
    
    print("已注册自定义策略:")
    for strategy in engine.strategies.values():
        print(f"  - {strategy.config.name}")
    
    # 启动引擎
    print("\n启动交易引擎...")
    await engine.start()


if __name__ == "__main__":
    print("=" * 60)
    print("自定义策略示例")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已停止")

