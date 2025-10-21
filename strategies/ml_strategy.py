"""
机器学习策略
"""
from typing import Dict, List
import numpy as np
from .base import BaseStrategy, StrategyConfig, Signal


class MLStrategy(BaseStrategy):
    """
    机器学习策略
    使用简单的特征和规则模拟 ML 决策
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 策略参数
        self.lookback_period = config.params.get("lookback_period", 50)
        self.feature_window = config.params.get("feature_window", 10)
        
        # 数据存储
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
    
    def _extract_features(self, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        """
        提取特征
        
        Args:
            prices: 价格历史
            volumes: 交易量历史
            
        Returns:
            特征字典
        """
        if len(prices) < self.feature_window:
            return {}
        
        recent_prices = prices[-self.feature_window:]
        recent_volumes = volumes[-self.feature_window:] if len(volumes) >= self.feature_window else [1.0] * self.feature_window
        
        # 价格特征
        price_mean = np.mean(recent_prices)
        price_std = np.std(recent_prices)
        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        
        # 动量特征
        momentum_5 = (recent_prices[-1] - recent_prices[-5]) / recent_prices[-5] if len(recent_prices) >= 5 and recent_prices[-5] != 0 else 0
        momentum_10 = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        
        # 波动率特征
        volatility = price_std / price_mean if price_mean != 0 else 0
        
        # 成交量特征
        volume_mean = np.mean(recent_volumes)
        volume_trend = (recent_volumes[-1] - volume_mean) / volume_mean if volume_mean != 0 else 0
        
        # RSI-like 指标
        gains = []
        losses = []
        for i in range(1, len(recent_prices)):
            change = recent_prices[i] - recent_prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs != 0 else 50
        
        return {
            "price_trend": price_trend,
            "momentum_5": momentum_5,
            "momentum_10": momentum_10,
            "volatility": volatility,
            "volume_trend": volume_trend,
            "rsi": rsi
        }
    
    def _predict_signal(self, features: Dict[str, float]) -> Signal:
        """
        使用特征预测信号（简化的决策树逻辑）
        
        Args:
            features: 特征字典
            
        Returns:
            交易信号
        """
        if not features:
            return Signal.HOLD
        
        score = 0
        
        # 趋势得分
        if features["price_trend"] > 0.02:
            score += 1
        elif features["price_trend"] < -0.02:
            score -= 1
        
        # 动量得分
        if features["momentum_5"] > 0.01:
            score += 1
        elif features["momentum_5"] < -0.01:
            score -= 1
        
        # RSI 得分
        if features["rsi"] < 30:  # 超卖
            score += 2
        elif features["rsi"] > 70:  # 超买
            score -= 2
        
        # 成交量确认
        if features["volume_trend"] > 0.5:
            score = int(score * 1.5)  # 放大信号
        
        # 波动率过滤
        if features["volatility"] > 0.05:  # 高波动率，降低信号强度
            score = int(score * 0.5)
        
        # 生成信号
        if score >= 2:
            return Signal.BUY
        elif score <= -2:
            return Signal.SELL
        else:
            return Signal.HOLD
    
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
        current_volume = float(market_data.get("dayNtlVlm", 1000000))  # 日成交量
        
        if current_price == 0:
            return Signal.HOLD
        
        # 初始化历史数据
        if coin not in self.price_history:
            self.price_history[coin] = []
            self.volume_history[coin] = []
        
        # 添加数据到历史
        self.price_history[coin].append(current_price)
        self.volume_history[coin].append(current_volume)
        
        # 限制历史长度
        if len(self.price_history[coin]) > self.lookback_period:
            self.price_history[coin] = self.price_history[coin][-self.lookback_period:]
            self.volume_history[coin] = self.volume_history[coin][-self.lookback_period:]
        
        # 检查是否有足够的数据
        if len(self.price_history[coin]) < self.feature_window:
            return Signal.HOLD
        
        # 提取特征
        features = self._extract_features(
            self.price_history[coin],
            self.volume_history[coin]
        )
        
        # 预测信号
        signal = self._predict_signal(features)
        
        # 检查持仓状态
        has_position = coin in self.state.positions
        
        if signal == Signal.BUY and not has_position:
            return Signal.BUY
        
        elif signal == Signal.SELL and has_position:
            return Signal.CLOSE
        
        # 检查止损止盈
        if has_position:
            position = self.state.positions[coin]
            entry_price = position.get("entry_price", 0)
            
            if entry_price > 0:
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                # 动态止损（根据波动率调整）
                volatility = features.get("volatility", 0.02)
                stop_loss = -max(3.0, volatility * 100 * 2)
                
                if pnl_percentage < stop_loss:
                    return Signal.CLOSE
                
                # 动态止盈
                take_profit = max(5.0, volatility * 100 * 3)
                if pnl_percentage > take_profit:
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
        
        # 根据信号强度调整仓位
        if coin in self.price_history and len(self.price_history[coin]) >= self.feature_window:
            features = self._extract_features(
                self.price_history[coin],
                self.volume_history[coin]
            )
            
            # 根据 RSI 和波动率调整仓位大小
            rsi = features.get("rsi", 50)
            volatility = features.get("volatility", 0.02)
            
            # 基础仓位
            base_risk = 0.12  # 12%
            
            # RSI 调整
            if rsi < 25 or rsi > 75:  # 极端超卖或超买
                base_risk *= 1.3
            
            # 波动率调整
            if volatility < 0.02:  # 低波动
                base_risk *= 1.2
            elif volatility > 0.05:  # 高波动
                base_risk *= 0.8
            
            position_value = min(balance * base_risk, self.config.position_size)
        else:
            position_value = min(balance * 0.1, self.config.position_size)
        
        return position_value

