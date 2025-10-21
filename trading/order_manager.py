"""
订单管理模块
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
from decimal import Decimal


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class Order:
    """订单对象"""
    
    def __init__(
        self,
        order_id: str,
        strategy_id: str,
        coin: str,
        side: OrderSide,
        size: float,
        price: float,
        order_type: str = "limit"
    ):
        self.order_id = order_id
        self.strategy_id = strategy_id
        self.coin = coin
        self.side = side
        self.size = size
        self.price = price
        self.order_type = order_type
        self.status = OrderStatus.PENDING
        self.filled_size = 0.0
        self.average_price = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.exchange_order_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "strategy_id": self.strategy_id,
            "coin": self.coin,
            "side": self.side.value,
            "size": self.size,
            "price": self.price,
            "order_type": self.order_type,
            "status": self.status.value,
            "filled_size": self.filled_size,
            "average_price": self.average_price,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "exchange_order_id": self.exchange_order_id
        }


class OrderManager:
    """订单管理器"""
    
    def __init__(self, client):
        """
        初始化订单管理器
        
        Args:
            client: Hyperliquid 客户端
        """
        self.client = client
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
    
    async def create_order(
        self,
        strategy_id: str,
        coin: str,
        side: OrderSide,
        size: float,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Order:
        """
        创建订单
        
        Args:
            strategy_id: 策略 ID
            coin: 币种
            side: 买卖方向
            size: 数量
            price: 价格（限价单需要）
            order_type: 订单类型
            
        Returns:
            订单对象
        """
        # 生成订单 ID
        order_id = f"{strategy_id}_{coin}_{int(datetime.now().timestamp() * 1000)}"
        
        # 如果是市价单，获取当前价格
        if order_type == "market" and price is None:
            market_data = await self.client.get_market_data(coin)
            price = float(market_data['ctx']['markPx'])
        
        # 创建订单对象
        order = Order(
            order_id=order_id,
            strategy_id=strategy_id,
            coin=coin,
            side=side,
            size=size,
            price=price,
            order_type=order_type
        )
        
        self.orders[order_id] = order
        
        return order
    
    async def submit_order(self, order: Order) -> bool:
        """
        提交订单到交易所
        
        Args:
            order: 订单对象
            
        Returns:
            是否成功
        """
        try:
            result = await self.client.place_order(
                coin=order.coin,
                is_buy=(order.side == OrderSide.BUY),
                size=order.size,
                price=order.price,
                order_type="Limit" if order.order_type == "limit" else "Market"
            )
            
            if result.get("status") == "ok":
                order.status = OrderStatus.OPEN
                order.exchange_order_id = str(result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting"))
                order.updated_at = datetime.now()
                return True
            else:
                order.status = OrderStatus.REJECTED
                order.updated_at = datetime.now()
                return False
        
        except Exception as e:
            print(f"提交订单失败: {e}")
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.now()
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
            
        Returns:
            是否成功
        """
        order = self.orders.get(order_id)
        if not order or not order.exchange_order_id:
            return False
        
        try:
            result = await self.client.cancel_order(
                coin=order.coin,
                oid=int(order.exchange_order_id)
            )
            
            if result.get("status") == "ok":
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now()
                self.order_history.append(order)
                del self.orders[order_id]
                return True
            
            return False
        
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False
    
    async def update_order_status(self):
        """更新所有订单状态"""
        try:
            open_orders = await self.client.get_open_orders()
            exchange_order_ids = {str(o.get("oid")): o for o in open_orders}
            
            for order_id, order in list(self.orders.items()):
                if order.exchange_order_id in exchange_order_ids:
                    # 订单仍在交易所
                    exchange_order = exchange_order_ids[order.exchange_order_id]
                    order.filled_size = float(exchange_order.get("filledSz", 0))
                    order.updated_at = datetime.now()
                else:
                    # 订单已完成或取消
                    if order.status == OrderStatus.OPEN:
                        order.status = OrderStatus.FILLED
                        order.filled_size = order.size
                        order.updated_at = datetime.now()
                        self.order_history.append(order)
                        del self.orders[order_id]
        
        except Exception as e:
            print(f"更新订单状态失败: {e}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)
    
    def get_strategy_orders(self, strategy_id: str) -> List[Order]:
        """获取策略的所有订单"""
        return [o for o in self.orders.values() if o.strategy_id == strategy_id]
    
    def get_order_history(self, strategy_id: Optional[str] = None, limit: int = 100) -> List[Order]:
        """获取历史订单"""
        if strategy_id:
            history = [o for o in self.order_history if o.strategy_id == strategy_id]
        else:
            history = self.order_history
        
        return sorted(history, key=lambda x: x.created_at, reverse=True)[:limit]

