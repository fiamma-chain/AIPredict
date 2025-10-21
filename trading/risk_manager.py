"""
风险管理模块
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal


class RiskLimits:
    """风险限制配置"""
    
    def __init__(
        self,
        max_position_size: float = 1000.0,
        max_leverage: int = 5,
        daily_loss_limit: float = 500.0,
        max_open_positions: int = 5,
        min_account_balance: float = 100.0,
        stop_loss_percentage: float = 5.0,
        take_profit_percentage: float = 10.0
    ):
        self.max_position_size = max_position_size
        self.max_leverage = max_leverage
        self.daily_loss_limit = daily_loss_limit
        self.max_open_positions = max_open_positions
        self.min_account_balance = min_account_balance
        self.stop_loss_percentage = stop_loss_percentage
        self.take_profit_percentage = take_profit_percentage


class Position:
    """持仓信息"""
    
    def __init__(
        self,
        coin: str,
        size: float,
        entry_price: float,
        side: str,
        leverage: float = 1.0
    ):
        self.coin = coin
        self.size = size
        self.entry_price = entry_price
        self.side = side  # 'long' or 'short'
        self.leverage = leverage
        self.opened_at = datetime.now()
        self.unrealized_pnl = 0.0
        self.liquidation_price = 0.0
    
    def calculate_pnl(self, current_price: float) -> float:
        """
        计算未实现盈亏
        
        Args:
            current_price: 当前价格
            
        Returns:
            未实现盈亏
        """
        if self.side == "long":
            pnl = (current_price - self.entry_price) * self.size
        else:  # short
            pnl = (self.entry_price - current_price) * self.size
        
        self.unrealized_pnl = pnl
        return pnl
    
    def calculate_pnl_percentage(self, current_price: float) -> float:
        """计算盈亏百分比"""
        pnl = self.calculate_pnl(current_price)
        position_value = self.entry_price * self.size
        return (pnl / position_value) * 100 if position_value > 0 else 0.0


class RiskManager:
    """风险管理器"""
    
    def __init__(self, client, limits: Optional[RiskLimits] = None):
        """
        初始化风险管理器
        
        Args:
            client: Hyperliquid 客户端
            limits: 风险限制配置
        """
        self.client = client
        self.limits = limits or RiskLimits()
        self.positions: Dict[str, Position] = {}
        self.daily_pnl: List[Dict] = []
        self.last_reset = datetime.now().date()
    
    async def check_order_risk(
        self,
        coin: str,
        size: float,
        price: float,
        side: str
    ) -> tuple[bool, Optional[str]]:
        """
        检查订单风险
        
        Args:
            coin: 币种
            size: 数量
            price: 价格
            side: 方向
            
        Returns:
            (是否通过, 拒绝原因)
        """
        # 检查账户余额
        balance = await self.client.get_balance()
        if balance["available_balance"] < self.limits.min_account_balance:
            return False, "账户余额不足最小要求"
        
        # 检查持仓数量
        if len(self.positions) >= self.limits.max_open_positions:
            if coin not in self.positions:
                return False, f"已达到最大持仓数量限制 ({self.limits.max_open_positions})"
        
        # 检查持仓大小
        position_value = size * price
        if position_value > self.limits.max_position_size:
            return False, f"持仓价值超过限制 ({self.limits.max_position_size} USD)"
        
        # 检查日亏损限制
        await self._update_daily_pnl()
        today_loss = sum(p["pnl"] for p in self.daily_pnl if p["pnl"] < 0)
        if abs(today_loss) >= self.limits.daily_loss_limit:
            return False, f"已达到当日亏损限制 ({self.limits.daily_loss_limit} USD)"
        
        return True, None
    
    async def update_positions(self):
        """更新持仓信息"""
        try:
            positions = await self.client.get_positions()
            
            # 清空当前持仓
            self.positions.clear()
            
            # 更新持仓
            for pos_data in positions:
                pos_info = pos_data.get("position", {})
                coin = pos_info.get("coin")
                size = abs(float(pos_info.get("szi", 0)))
                
                if size > 0:
                    entry_price = float(pos_info.get("entryPx", 0))
                    side = "long" if float(pos_info.get("szi", 0)) > 0 else "short"
                    leverage = float(pos_info.get("leverage", {}).get("value", 1))
                    
                    position = Position(
                        coin=coin,
                        size=size,
                        entry_price=entry_price,
                        side=side,
                        leverage=leverage
                    )
                    
                    # 计算未实现盈亏
                    market_data = await self.client.get_market_data(coin)
                    current_price = float(market_data['ctx']['markPx'])
                    position.calculate_pnl(current_price)
                    
                    self.positions[coin] = position
        
        except Exception as e:
            print(f"更新持仓失败: {e}")
    
    async def check_stop_loss_take_profit(self) -> List[Dict]:
        """
        检查止损止盈
        
        Returns:
            需要平仓的列表
        """
        actions = []
        
        for coin, position in self.positions.items():
            try:
                # 获取当前价格
                market_data = await self.client.get_market_data(coin)
                current_price = float(market_data['ctx']['markPx'])
                
                # 计算盈亏百分比
                pnl_percentage = position.calculate_pnl_percentage(current_price)
                
                # 检查止损
                if pnl_percentage <= -self.limits.stop_loss_percentage:
                    actions.append({
                        "coin": coin,
                        "action": "stop_loss",
                        "reason": f"触发止损: {pnl_percentage:.2f}%"
                    })
                
                # 检查止盈
                elif pnl_percentage >= self.limits.take_profit_percentage:
                    actions.append({
                        "coin": coin,
                        "action": "take_profit",
                        "reason": f"触发止盈: {pnl_percentage:.2f}%"
                    })
            
            except Exception as e:
                print(f"检查止损止盈失败 {coin}: {e}")
        
        return actions
    
    async def execute_risk_actions(self, actions: List[Dict]):
        """
        执行风险控制动作
        
        Args:
            actions: 动作列表
        """
        for action in actions:
            try:
                coin = action["coin"]
                print(f"执行风险控制: {coin} - {action['reason']}")
                await self.client.close_position(coin)
            except Exception as e:
                print(f"执行风险控制失败 {coin}: {e}")
    
    async def _update_daily_pnl(self):
        """更新每日盈亏"""
        today = datetime.now().date()
        
        # 如果是新的一天，重置记录
        if today > self.last_reset:
            self.daily_pnl.clear()
            self.last_reset = today
        
        # 更新今日盈亏
        await self.update_positions()
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        self.daily_pnl.append({
            "timestamp": datetime.now(),
            "pnl": total_pnl
        })
    
    def get_risk_metrics(self) -> Dict:
        """获取风险指标"""
        total_exposure = sum(
            pos.size * pos.entry_price for pos in self.positions.values()
        )
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        daily_loss = sum(p["pnl"] for p in self.daily_pnl if p["pnl"] < 0)
        
        return {
            "total_positions": len(self.positions),
            "total_exposure": total_exposure,
            "total_unrealized_pnl": total_pnl,
            "daily_loss": daily_loss,
            "daily_loss_limit_usage": abs(daily_loss) / self.limits.daily_loss_limit * 100,
            "max_positions_usage": len(self.positions) / self.limits.max_open_positions * 100,
            "positions": [
                {
                    "coin": pos.coin,
                    "size": pos.size,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "leverage": pos.leverage
                }
                for pos in self.positions.values()
            ]
        }

