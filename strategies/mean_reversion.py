"""
均值回归策略
"""
from typing import Dict, List
import numpy as np
from .base import BaseStrategy, StrategyConfig, Signal


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略
    当价格偏离均值过多时进行反向操作
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 策略参数
        self.period = config.params.get("period", 20)
        self.std_multiplier = config.params.get("std_multiplier", 2.0)
        self.mean_revert_threshold = config.params.get("mean_revert_threshold", 0.02)
        
        # 价格历史
        self.price_history: Dict[str, List[float]] = {}
    
    def _calculate_mean(self, prices: List[float]) -> float:
        """计算均值"""
        if not prices:
            return 0.0
        return sum(prices) / len(prices)
    
    def _calculate_std(self, prices: List[float], mean: float) -> float:
        """计算标准差"""
        if len(prices) < 2:
            return 0.0
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return variance ** 0.5
    
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
        
        # 添加价格到历史
        self.price_history[coin].append(current_price)
        
        # 限制历史长度
        if len(self.price_history[coin]) > self.period + 10:
            self.price_history[coin] = self.price_history[coin][-(self.period + 10):]
        
        # 检查是否有足够的数据
        if len(self.price_history[coin]) < self.period:
            return Signal.HOLD
        
        # 计算统计指标
        prices = self.price_history[coin][-self.period:]
        mean_price = self._calculate_mean(prices)
        std_price = self._calculate_std(prices, mean_price)
        
        if mean_price == 0 or std_price == 0:
            return Signal.HOLD
        
        # 计算 Z-score
        z_score = (current_price - mean_price) / std_price
        
        # 检查是否有持仓
        has_position = coin in self.state.positions
        
        # 价格超卖，买入
        if z_score < -self.std_multiplier:
            if not has_position:
                return Signal.BUY
        
        # 价格超买，卖出
        elif z_score > self.std_multiplier:
            if has_position:
                return Signal.CLOSE
        
        # 如果有持仓，检查是否回归到均值附近
        if has_position:
            position = self.state.positions[coin]
            entry_price = position.get("entry_price", 0)
            
            if entry_price > 0:
                # 价格回归到均值，平仓获利
                if abs(z_score) < 0.5:
                    return Signal.CLOSE
                
                # 止损
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                if pnl_percentage < -5.0:
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
        risk_percentage = 0.15  # 15% 的资金
        position_value = min(balance * risk_percentage, self.config.position_size)
        
        return position_value

