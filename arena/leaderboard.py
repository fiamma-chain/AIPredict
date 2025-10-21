"""
排行榜系统
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum


class LeaderboardMetric(Enum):
    """排行榜指标"""
    TOTAL_PNL = "total_pnl"
    ROI_PERCENTAGE = "roi_percentage"
    WIN_RATE = "win_rate"
    SHARPE_RATIO = "sharpe_ratio"
    PROFIT_FACTOR = "profit_factor"
    TOTAL_TRADES = "total_trades"


class LeaderboardPeriod(Enum):
    """排行榜周期"""
    ALL_TIME = "all_time"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"


class Leaderboard:
    """排行榜管理器"""
    
    def __init__(self, performance_tracker):
        """
        初始化排行榜
        
        Args:
            performance_tracker: 性能追踪器实例
        """
        self.performance_tracker = performance_tracker
        self.rankings: Dict[str, List[Dict]] = {}
        self.last_update = datetime.now()
    
    def calculate_rankings(
        self,
        metric: LeaderboardMetric = LeaderboardMetric.TOTAL_PNL,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME,
        limit: int = 50
    ) -> List[Dict]:
        """
        计算排行榜
        
        Args:
            metric: 排序指标
            period: 时间周期
            limit: 返回数量
            
        Returns:
            排行榜列表
        """
        # 获取所有策略的指标
        all_metrics = []
        
        for strategy_id, metrics in self.performance_tracker.metrics.items():
            # 根据时间周期过滤
            if not self._is_in_period(metrics, period):
                continue
            
            metric_value = self._get_metric_value(metrics, metric)
            
            all_metrics.append({
                "rank": 0,  # 将在排序后设置
                "strategy_id": strategy_id,
                "strategy_name": metrics.strategy_name,
                "metric_value": metric_value,
                "total_pnl": metrics.total_pnl,
                "roi_percentage": metrics.roi_percentage,
                "win_rate": metrics.win_rate,
                "sharpe_ratio": metrics.sharpe_ratio,
                "total_trades": metrics.total_trades,
                "current_balance": metrics.current_balance,
                "max_drawdown": metrics.max_drawdown,
                "last_trade_time": metrics.last_trade_time,
                "updated_at": metrics.updated_at
            })
        
        # 排序
        all_metrics.sort(key=lambda x: x["metric_value"], reverse=True)
        
        # 设置排名
        for i, item in enumerate(all_metrics[:limit], 1):
            item["rank"] = i
        
        # 缓存结果
        cache_key = f"{metric.value}_{period.value}"
        self.rankings[cache_key] = all_metrics[:limit]
        self.last_update = datetime.now()
        
        return all_metrics[:limit]
    
    def get_top_performers(
        self,
        metric: LeaderboardMetric = LeaderboardMetric.TOTAL_PNL,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取表现最好的策略
        
        Args:
            metric: 排序指标
            limit: 返回数量
            
        Returns:
            排行榜列表
        """
        return self.calculate_rankings(
            metric=metric,
            period=LeaderboardPeriod.ALL_TIME,
            limit=limit
        )
    
    def get_strategy_rank(
        self,
        strategy_id: str,
        metric: LeaderboardMetric = LeaderboardMetric.TOTAL_PNL
    ) -> Optional[int]:
        """
        获取策略排名
        
        Args:
            strategy_id: 策略 ID
            metric: 排序指标
            
        Returns:
            排名（None 如果未找到）
        """
        rankings = self.calculate_rankings(metric=metric, limit=1000)
        
        for item in rankings:
            if item["strategy_id"] == strategy_id:
                return item["rank"]
        
        return None
    
    def get_leaderboard_summary(self) -> Dict:
        """
        获取排行榜摘要
        
        Returns:
            摘要信息
        """
        total_strategies = len(self.performance_tracker.metrics)
        
        # 统计活跃策略
        active_strategies = sum(
            1 for m in self.performance_tracker.metrics.values()
            if m.total_trades > 0
        )
        
        # 统计总交易量
        total_trades = sum(
            m.total_trades
            for m in self.performance_tracker.metrics.values()
        )
        
        # 统计总盈亏
        total_pnl = sum(
            m.total_pnl
            for m in self.performance_tracker.metrics.values()
        )
        
        # 计算平均 ROI
        roi_values = [
            m.roi_percentage
            for m in self.performance_tracker.metrics.values()
            if m.total_trades > 0
        ]
        avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0.0
        
        # 找出最佳策略
        best_pnl_strategy = None
        best_roi_strategy = None
        
        if self.performance_tracker.metrics:
            best_pnl_metrics = max(
                self.performance_tracker.metrics.values(),
                key=lambda m: m.total_pnl
            )
            best_pnl_strategy = {
                "id": best_pnl_metrics.strategy_id,
                "name": best_pnl_metrics.strategy_name,
                "pnl": best_pnl_metrics.total_pnl
            }
            
            active_metrics = [
                m for m in self.performance_tracker.metrics.values()
                if m.total_trades > 0
            ]
            if active_metrics:
                best_roi_metrics = max(active_metrics, key=lambda m: m.roi_percentage)
                best_roi_strategy = {
                    "id": best_roi_metrics.strategy_id,
                    "name": best_roi_metrics.strategy_name,
                    "roi": best_roi_metrics.roi_percentage
                }
        
        return {
            "total_strategies": total_strategies,
            "active_strategies": active_strategies,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "average_roi": avg_roi,
            "best_pnl_strategy": best_pnl_strategy,
            "best_roi_strategy": best_roi_strategy,
            "last_update": self.last_update.isoformat()
        }
    
    def get_comparison(self, strategy_ids: List[str]) -> List[Dict]:
        """
        对比多个策略
        
        Args:
            strategy_ids: 策略 ID 列表
            
        Returns:
            对比数据
        """
        comparison = []
        
        for strategy_id in strategy_ids:
            metrics = self.performance_tracker.get_metrics(strategy_id)
            if not metrics:
                continue
            
            comparison.append({
                "strategy_id": strategy_id,
                "strategy_name": metrics.strategy_name,
                "total_pnl": metrics.total_pnl,
                "roi_percentage": metrics.roi_percentage,
                "win_rate": metrics.win_rate,
                "sharpe_ratio": metrics.sharpe_ratio,
                "profit_factor": metrics.profit_factor,
                "max_drawdown": metrics.max_drawdown,
                "total_trades": metrics.total_trades,
                "average_win": metrics.average_win,
                "average_loss": metrics.average_loss
            })
        
        return comparison
    
    def _get_metric_value(self, metrics, metric: LeaderboardMetric) -> float:
        """
        获取指标值
        
        Args:
            metrics: 性能指标对象
            metric: 指标类型
            
        Returns:
            指标值
        """
        if metric == LeaderboardMetric.TOTAL_PNL:
            return metrics.total_pnl
        elif metric == LeaderboardMetric.ROI_PERCENTAGE:
            return metrics.roi_percentage
        elif metric == LeaderboardMetric.WIN_RATE:
            return metrics.win_rate
        elif metric == LeaderboardMetric.SHARPE_RATIO:
            return metrics.sharpe_ratio
        elif metric == LeaderboardMetric.PROFIT_FACTOR:
            return metrics.profit_factor
        elif metric == LeaderboardMetric.TOTAL_TRADES:
            return float(metrics.total_trades)
        else:
            return 0.0
    
    def _is_in_period(self, metrics, period: LeaderboardPeriod) -> bool:
        """
        检查指标是否在指定时间周期内
        
        Args:
            metrics: 性能指标对象
            period: 时间周期
            
        Returns:
            是否在周期内
        """
        if period == LeaderboardPeriod.ALL_TIME:
            return True
        
        if not metrics.last_trade_time:
            return False
        
        last_trade = datetime.fromisoformat(metrics.last_trade_time)
        now = datetime.now()
        
        if period == LeaderboardPeriod.DAILY:
            return (now - last_trade).days < 1
        elif period == LeaderboardPeriod.WEEKLY:
            return (now - last_trade).days < 7
        elif period == LeaderboardPeriod.MONTHLY:
            return (now - last_trade).days < 30
        
        return True
    
    def export_leaderboard(
        self,
        filepath: str,
        metric: LeaderboardMetric = LeaderboardMetric.TOTAL_PNL,
        limit: int = 50
    ):
        """
        导出排行榜到文件
        
        Args:
            filepath: 文件路径
            metric: 排序指标
            limit: 返回数量
        """
        import json
        
        rankings = self.calculate_rankings(metric=metric, limit=limit)
        summary = self.get_leaderboard_summary()
        
        data = {
            "summary": summary,
            "rankings": rankings,
            "metric": metric.value,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

