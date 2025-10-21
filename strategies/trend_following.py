"""
趋势跟踪策略
"""
from typing import Dict, List
import numpy as np
from .base import BaseStrategy, StrategyConfig, Signal


class TrendFollowingStrategy(BaseStrategy):
    """
    趋势跟踪策略
    使用移动平均线交叉来判断趋势
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 策略参数
        self.fast_period = config.params.get("fast_period", 10)
        self.slow_period = config.params.get("slow_period", 30)
        self.atr_period = config.params.get("atr_period", 14)
        
        # 价格历史
        self.price_history: Dict[str, List[float]] = {}
        self.high_history: Dict[str, List[float]] = {}
        self.low_history: Dict[str, List[float]] = {}
    
    def _calculate_sma(self, prices: List[float], period: int) -> float:
        """计算简单移动平均"""
        if len(prices) < period:
            return 0.0
        return sum(prices[-period:]) / period
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """计算平均真实波幅"""
        if len(closes) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, min(period + 1, len(closes))):
            high = highs[-i]
            low = lows[-i]
            prev_close = closes[-i-1]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    async def analyze(self, coin: str, market_data: Dict) -> Signal:
        """
        分析市场数据
        
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
            self.high_history[coin] = []
            self.low_history[coin] = []
        
        # 添加价格到历史
        self.price_history[coin].append(current_price)
        self.high_history[coin].append(current_price * 1.001)  # 简化处理
        self.low_history[coin].append(current_price * 0.999)   # 简化处理
        
        # 限制历史长度
        max_length = max(self.slow_period, self.atr_period) + 10
        if len(self.price_history[coin]) > max_length:
            self.price_history[coin] = self.price_history[coin][-max_length:]
            self.high_history[coin] = self.high_history[coin][-max_length:]
            self.low_history[coin] = self.low_history[coin][-max_length:]
        
        # 检查是否有足够的数据
        if len(self.price_history[coin]) < self.slow_period:
            return Signal.HOLD
        
        # 计算移动平均线
        fast_ma = self._calculate_sma(self.price_history[coin], self.fast_period)
        slow_ma = self._calculate_sma(self.price_history[coin], self.slow_period)
        
        # 计算前一周期的移动平均线
        prev_fast_ma = self._calculate_sma(self.price_history[coin][:-1], self.fast_period)
        prev_slow_ma = self._calculate_sma(self.price_history[coin][:-1], self.slow_period)
        
        # 生成信号
        has_position = coin in self.state.positions
        
        # 金叉：快线上穿慢线
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            if not has_position:
                return Signal.BUY
        
        # 死叉：快线下穿慢线
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            if has_position:
                return Signal.CLOSE
        
        # 如果已有持仓，检查是否需要止损
        if has_position:
            position = self.state.positions[coin]
            entry_price = position.get("entry_price", 0)
            
            if entry_price > 0:
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                # 止损
                if pnl_percentage < -3.0:
                    return Signal.CLOSE
                
                # 止盈
                if pnl_percentage > 5.0:
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
        
        # 使用固定比例的账户余额
        risk_percentage = 0.1  # 10% 的资金
        position_value = min(balance * risk_percentage, self.config.position_size)
        
        return position_value

