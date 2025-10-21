"""
策略基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class Signal(Enum):
    """交易信号"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class StrategyConfig:
    """策略配置"""
    
    def __init__(
        self,
        name: str,
        coins: List[str],
        timeframe: str = "1m",
        max_positions: int = 3,
        position_size: float = 100.0,
        **kwargs
    ):
        self.name = name
        self.coins = coins
        self.timeframe = timeframe
        self.max_positions = max_positions
        self.position_size = position_size
        self.params = kwargs


class StrategyState:
    """策略状态"""
    
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.is_active = False
        self.positions: Dict[str, Dict] = {}
        self.orders: List[str] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.created_at = datetime.now()
        self.last_signal_time: Dict[str, datetime] = {}
        self.equity_curve: List[Dict] = []
    
    def add_trade(self, pnl: float, winning: bool):
        """添加交易记录"""
        self.total_trades += 1
        if winning:
            self.winning_trades += 1
        self.total_pnl += pnl
        
        # 更新回撤
        if pnl < 0:
            self.current_drawdown += abs(pnl)
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        else:
            self.current_drawdown = max(0, self.current_drawdown - pnl)
    
    def get_win_rate(self) -> float:
        """获取胜率"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "is_active": self.is_active,
            "positions": self.positions,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate": self.get_win_rate(),
            "total_pnl": self.total_pnl,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "created_at": self.created_at.isoformat()
        }


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, config: StrategyConfig):
        """
        初始化策略
        
        Args:
            config: 策略配置
        """
        self.config = config
        self.strategy_id = f"{config.name}_{int(datetime.now().timestamp())}"
        self.state = StrategyState(self.strategy_id)
        self.market_data: Dict[str, Any] = {}
    
    @abstractmethod
    async def analyze(self, coin: str, market_data: Dict) -> Signal:
        """
        分析市场数据并生成交易信号
        
        Args:
            coin: 币种
            market_data: 市场数据
            
        Returns:
            交易信号
        """
        pass
    
    @abstractmethod
    def get_position_size(self, coin: str, signal: Signal, balance: float) -> float:
        """
        计算持仓大小
        
        Args:
            coin: 币种
            signal: 交易信号
            balance: 可用余额
            
        Returns:
            持仓大小
        """
        pass
    
    async def on_market_data(self, coin: str, data: Dict):
        """
        市场数据更新回调
        
        Args:
            coin: 币种
            data: 市场数据
        """
        self.market_data[coin] = data
    
    async def on_order_filled(self, order: Dict):
        """
        订单成交回调
        
        Args:
            order: 订单信息
        """
        pass
    
    async def on_position_closed(self, position: Dict, pnl: float):
        """
        持仓平仓回调
        
        Args:
            position: 持仓信息
            pnl: 盈亏
        """
        winning = pnl > 0
        self.state.add_trade(pnl, winning)
    
    def can_trade(self, coin: str) -> bool:
        """
        检查是否可以交易
        
        Args:
            coin: 币种
            
        Returns:
            是否可以交易
        """
        # 检查是否达到最大持仓数
        if len(self.state.positions) >= self.config.max_positions:
            # 如果已经持有该币种，可以平仓
            if coin in self.state.positions:
                return True
            return False
        
        # 检查信号间隔（防止频繁交易）
        if coin in self.state.last_signal_time:
            last_time = self.state.last_signal_time[coin]
            time_diff = (datetime.now() - last_time).total_seconds()
            if time_diff < 60:  # 至少间隔 60 秒
                return False
        
        return True
    
    def update_position(self, coin: str, position_data: Dict):
        """更新持仓信息"""
        self.state.positions[coin] = position_data
    
    def remove_position(self, coin: str):
        """移除持仓"""
        if coin in self.state.positions:
            del self.state.positions[coin]
    
    def get_info(self) -> Dict:
        """获取策略信息"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.config.name,
            "coins": self.config.coins,
            "timeframe": self.config.timeframe,
            "state": self.state.to_dict(),
            "description": self.__doc__ or "No description"
        }
    
    def start(self):
        """启动策略"""
        self.state.is_active = True
    
    def stop(self):
        """停止策略"""
        self.state.is_active = False

