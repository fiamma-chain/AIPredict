"""
Hyperliquid 交易客户端（使用官方SDK）
"""
import logging
from typing import Dict, List, Optional
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

logger = logging.getLogger(__name__)


class HyperliquidClient:
    """Hyperliquid 交易客户端（官方SDK版本）"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        初始化 Hyperliquid 客户端
        
        Args:
            private_key: 以太坊私钥（可以带或不带0x前缀）
            testnet: 是否使用测试网
        """
        self.testnet = testnet
        
        # 确保私钥格式正确
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # 使用官方SDK
        if testnet:
            base_url = constants.TESTNET_API_URL
        else:
            base_url = constants.MAINNET_API_URL
        
        # 初始化 Info（查询）和 Exchange（交易）
        self.info = Info(base_url, skip_ws=True)
        self.exchange = Exchange(
            wallet=None,  # 使用私钥
            base_url=base_url,
            account_address=None  # SDK会从私钥推导
        )
        
        # 从私钥设置账户
        from eth_account import Account
        account = Account.from_key(private_key)
        self.address = account.address
        self.exchange.wallet = account
        self.exchange.account_address = self.address
        
        logger.info(f"✅ Hyperliquid 客户端初始化成功")
        logger.info(f"   地址: {self.address}")
        logger.info(f"   网络: {'测试网' if testnet else '主网'}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        pass
    
    async def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典
        """
        try:
            user_state = self.info.user_state(self.address)
            return user_state
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {}
    
    async def get_market_data(self, coin: str) -> Dict:
        """
        获取市场数据
        
        Args:
            coin: 币种符号 (如 'BTC', 'ETH')
            
        Returns:
            市场数据
        """
        try:
            # 获取所有市场数据
            all_mids = self.info.all_mids()
            meta = self.info.meta()
            
            # 查找指定币种
            if coin not in all_mids:
                raise ValueError(f"Coin {coin} not found")
            
            current_price = float(all_mids[coin])
            
            # 获取详细的市场上下文
            meta_and_asset_ctxs = self.info.meta_and_asset_ctxs()
            
            # 查找币种索引
            asset_index = None
            for i, asset in enumerate(meta_and_asset_ctxs[0]['universe']):
                if asset['name'] == coin:
                    asset_index = i
                    break
            
            if asset_index is None:
                raise ValueError(f"Coin {coin} not found in universe")
            
            ctx = meta_and_asset_ctxs[1][asset_index]
            
            # 提取数据
            mark_price = float(ctx.get('markPx', current_price))
            funding = float(ctx.get('funding', 0))
            open_interest = float(ctx.get('openInterest', 0))
            prev_mark_px = float(ctx.get('prevDayPx', mark_price))
            volume_usd = float(ctx.get('dayNtlVlm', 0))
            
            # 计算24h涨跌幅
            change_24h = ((mark_price - prev_mark_px) / prev_mark_px * 100) if prev_mark_px > 0 else 0
            
            return {
                "coin": coin,
                "price": mark_price,
                "mark_price": mark_price,
                "funding_rate": funding,
                "open_interest": open_interest,
                "change_24h": change_24h,
                "volume": volume_usd,
                "raw_ctx": ctx
            }
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            raise
    
    async def get_orderbook(self, coin: str) -> Dict:
        """
        获取订单簿
        
        Args:
            coin: 币种符号
            
        Returns:
            订单簿数据
        """
        try:
            l2_snapshot = self.info.l2_snapshot(coin)
            return l2_snapshot
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            return {"levels": [[], []]}
    
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """
        获取最近成交记录
        
        Args:
            coin: 币种符号
            limit: 返回数量
            
        Returns:
            成交记录列表
        """
        try:
            # 官方SDK暂时可能不支持此功能，返回空列表
            return []
        except Exception as e:
            logger.error(f"获取最近成交失败: {e}")
            return []
    
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "Limit",
        reduce_only: bool = False
    ) -> Dict:
        """
        下单
        
        Args:
            coin: 币种符号
            is_buy: 是否买入
            size: 数量
            price: 价格
            order_type: 订单类型 ("Limit" 或 "Market")
            reduce_only: 是否只减仓
            
        Returns:
            订单结果
        """
        try:
            # 使用官方SDK下单
            # 官方SDK参数: name, is_buy, sz, limit_px, order_type, reduce_only
            
            # 对size和price进行精度处理
            from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
            
            # BTC使用5位小数
            size_decimal = Decimal(str(size))
            size_rounded = float(size_decimal.quantize(Decimal('0.00001'), rounding=ROUND_DOWN))
            
            # 价格取整到最近的整数（BTC价格不支持小数）
            price_decimal = Decimal(str(price))
            price_rounded = float(price_decimal.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
            
            logger.info(f"📊 原始数量: {size}, 处理后: {size_rounded}")
            logger.info(f"📊 原始价格: {price}, 处理后: {price_rounded}")
            
            order_result = self.exchange.order(
                name=coin,
                is_buy=is_buy,
                sz=size_rounded,
                limit_px=price_rounded,
                order_type={"limit": {"tif": "Gtc"}} if order_type == "Limit" else {"market": {}},
                reduce_only=reduce_only
            )
            
            logger.info(f"📝 官方SDK订单结果: {order_result}")
            
            return order_result
            
        except Exception as e:
            logger.error(f"下单失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "err", "response": str(e)}
    
    async def cancel_order(self, coin: str, oid: int) -> Dict:
        """
        取消订单
        
        Args:
            coin: 币种符号
            oid: 订单ID
            
        Returns:
            取消结果
        """
        try:
            result = self.exchange.cancel(coin, oid)
            return result
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {"status": "err", "response": str(e)}
    
    async def get_open_orders(self) -> List[Dict]:
        """
        获取未成交订单
        
        Returns:
            订单列表
        """
        try:
            user_state = await self.get_account_info()
            return user_state.get('assetPositions', [])
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            return []

