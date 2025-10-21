"""
性能追踪模块
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json


@dataclass
class PerformanceMetrics:
    """性能指标"""
    strategy_id: str
    strategy_name: str
    
    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # 盈亏统计
    total_pnl: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    
    # 风险指标
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # ROI
    initial_balance: float = 1000.0
    current_balance: float = 1000.0
    roi: float = 0.0
    roi_percentage: float = 0.0
    
    # 时间统计
    first_trade_time: Optional[str] = None
    last_trade_time: Optional[str] = None
    total_runtime_hours: float = 0.0
    
    # 持仓统计
    current_positions: int = 0
    max_positions: int = 0
    average_holding_time_hours: float = 0.0
    
    # 更新时间
    updated_at: str = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class PerformanceTracker:
    """性能追踪器"""
    
    def __init__(self):
        """初始化性能追踪器"""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.trade_history: Dict[str, List[Dict]] = {}
        self.equity_curves: Dict[str, List[Dict]] = {}
    
    def register_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        initial_balance: float = 1000.0
    ):
        """
        注册策略
        
        Args:
            strategy_id: 策略 ID
            strategy_name: 策略名称
            initial_balance: 初始资金
        """
        self.metrics[strategy_id] = PerformanceMetrics(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            initial_balance=initial_balance,
            current_balance=initial_balance
        )
        self.trade_history[strategy_id] = []
        self.equity_curves[strategy_id] = [
            {
                "timestamp": datetime.now().isoformat(),
                "balance": initial_balance
            }
        ]
    
    def record_trade(
        self,
        strategy_id: str,
        coin: str,
        side: str,
        entry_price: float,
        exit_price: float,
        size: float,
        pnl: float,
        entry_time: datetime,
        exit_time: datetime
    ):
        """
        记录交易
        
        Args:
            strategy_id: 策略 ID
            coin: 币种
            side: 方向
            entry_price: 入场价格
            exit_price: 出场价格
            size: 数量
            pnl: 盈亏
            entry_time: 入场时间
            exit_time: 出场时间
        """
        if strategy_id not in self.metrics:
            return
        
        metrics = self.metrics[strategy_id]
        
        # 记录交易历史
        trade = {
            "coin": coin,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "size": size,
            "pnl": pnl,
            "pnl_percentage": ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0,
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "holding_time_hours": (exit_time - entry_time).total_seconds() / 3600
        }
        
        self.trade_history[strategy_id].append(trade)
        
        # 更新指标
        metrics.total_trades += 1
        metrics.total_pnl += pnl
        metrics.current_balance += pnl
        
        if pnl > 0:
            metrics.winning_trades += 1
            metrics.total_profit += pnl
        else:
            metrics.losing_trades += 1
            metrics.total_loss += abs(pnl)
        
        # 更新时间
        if not metrics.first_trade_time:
            metrics.first_trade_time = entry_time.isoformat()
        metrics.last_trade_time = exit_time.isoformat()
        
        # 计算衍生指标
        self._calculate_metrics(strategy_id)
        
        # 更新权益曲线
        self.equity_curves[strategy_id].append({
            "timestamp": exit_time.isoformat(),
            "balance": metrics.current_balance,
            "pnl": pnl
        })
        
        metrics.updated_at = datetime.now().isoformat()
    
    def update_positions(self, strategy_id: str, positions: List[Dict]):
        """
        更新持仓信息
        
        Args:
            strategy_id: 策略 ID
            positions: 持仓列表
        """
        if strategy_id not in self.metrics:
            return
        
        metrics = self.metrics[strategy_id]
        metrics.current_positions = len(positions)
        metrics.max_positions = max(metrics.max_positions, len(positions))
        metrics.updated_at = datetime.now().isoformat()
    
    def _calculate_metrics(self, strategy_id: str):
        """
        计算性能指标
        
        Args:
            strategy_id: 策略 ID
        """
        metrics = self.metrics[strategy_id]
        
        # 胜率
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
        
        # 平均盈亏
        if metrics.winning_trades > 0:
            metrics.average_win = metrics.total_profit / metrics.winning_trades
        
        if metrics.losing_trades > 0:
            metrics.average_loss = metrics.total_loss / metrics.losing_trades
        
        # 盈亏比
        if metrics.total_loss > 0:
            metrics.profit_factor = metrics.total_profit / metrics.total_loss
        
        # ROI
        metrics.roi = metrics.current_balance - metrics.initial_balance
        if metrics.initial_balance > 0:
            metrics.roi_percentage = (metrics.roi / metrics.initial_balance) * 100
        
        # 计算回撤
        self._calculate_drawdown(strategy_id)
        
        # 计算夏普比率和索提诺比率
        self._calculate_risk_ratios(strategy_id)
        
        # 计算平均持仓时间
        if strategy_id in self.trade_history and self.trade_history[strategy_id]:
            total_holding_time = sum(
                trade["holding_time_hours"]
                for trade in self.trade_history[strategy_id]
            )
            metrics.average_holding_time_hours = total_holding_time / len(self.trade_history[strategy_id])
        
        # 计算运行时间
        if metrics.first_trade_time and metrics.last_trade_time:
            first_time = datetime.fromisoformat(metrics.first_trade_time)
            last_time = datetime.fromisoformat(metrics.last_trade_time)
            metrics.total_runtime_hours = (last_time - first_time).total_seconds() / 3600
    
    def _calculate_drawdown(self, strategy_id: str):
        """
        计算回撤
        
        Args:
            strategy_id: 策略 ID
        """
        if strategy_id not in self.equity_curves:
            return
        
        equity_curve = self.equity_curves[strategy_id]
        if not equity_curve:
            return
        
        peak = equity_curve[0]["balance"]
        max_drawdown = 0.0
        current_drawdown = 0.0
        
        for point in equity_curve:
            balance = point["balance"]
            
            if balance > peak:
                peak = balance
                current_drawdown = 0.0
            else:
                current_drawdown = peak - balance
                max_drawdown = max(max_drawdown, current_drawdown)
        
        metrics = self.metrics[strategy_id]
        metrics.max_drawdown = max_drawdown
        metrics.current_drawdown = current_drawdown
    
    def _calculate_risk_ratios(self, strategy_id: str):
        """
        计算风险比率（夏普比率、索提诺比率）
        
        Args:
            strategy_id: 策略 ID
        """
        if strategy_id not in self.trade_history:
            return
        
        trades = self.trade_history[strategy_id]
        if len(trades) < 2:
            return
        
        returns = [trade["pnl"] for trade in trades]
        
        # 计算平均收益和标准差
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        # 夏普比率（假设无风险利率为 0）
        if std_dev > 0:
            self.metrics[strategy_id].sharpe_ratio = avg_return / std_dev
        
        # 索提诺比率（只考虑下行标准差）
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
            downside_std = downside_variance ** 0.5
            if downside_std > 0:
                self.metrics[strategy_id].sortino_ratio = avg_return / downside_std
    
    def get_metrics(self, strategy_id: str) -> Optional[PerformanceMetrics]:
        """
        获取策略指标
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            性能指标
        """
        return self.metrics.get(strategy_id)
    
    def get_trade_history(
        self,
        strategy_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取交易历史
        
        Args:
            strategy_id: 策略 ID
            limit: 返回数量限制
            
        Returns:
            交易历史列表
        """
        history = self.trade_history.get(strategy_id, [])
        
        if limit:
            return history[-limit:]
        
        return history
    
    def get_equity_curve(self, strategy_id: str) -> List[Dict]:
        """
        获取权益曲线
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            权益曲线数据
        """
        return self.equity_curves.get(strategy_id, [])
    
    def export_metrics(self, strategy_id: str, filepath: str):
        """
        导出指标到文件
        
        Args:
            strategy_id: 策略 ID
            filepath: 文件路径
        """
        if strategy_id not in self.metrics:
            return
        
        data = {
            "metrics": self.metrics[strategy_id].to_dict(),
            "trade_history": self.trade_history.get(strategy_id, []),
            "equity_curve": self.equity_curves.get(strategy_id, [])
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

