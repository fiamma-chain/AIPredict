"""
Aster 交易客户端实现
基于 AsterDex Futures API V3
文档: https://github.com/asterdex/api-docs
"""
import logging
import time
import asyncio
import json
import math
from typing import Dict, List, Optional
import aiohttp
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode
from web3 import Web3
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from trading.base_client import BaseExchangeClient

logger = logging.getLogger(__name__)


class AsterClient(BaseExchangeClient):
    """Aster 交易客户端 - 基于 AsterDex Futures API V3"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        初始化 Aster 客户端
        
        Args:
            private_key: 以太坊私钥（可以带或不带0x前缀）
            testnet: 是否使用测试网
        
        注意：需要从 https://www.asterdex.com/en/api-wallet 创建 API Wallet (AGENT)
        """
        super().__init__(private_key, testnet)
        
        # 确保私钥格式正确
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # API 基础 URL (AsterDex 官方)
        self.base_url = "https://fapi.asterdex.com"
        
        # 从私钥生成账户
        account = Account.from_key(private_key)
        self.address = account.address  # 这是 user 地址
        self.account = account
        self.private_key = private_key
        
        # 注意：AsterDex 需要 signer 和 user 分离
        # signer 是 API Wallet 地址，需要从 https://www.asterdex.com/en/api-wallet 获取
        # 这里默认使用同一个地址，实际使用时需要配置正确的 signer
        self.signer = account.address
        
        # 会话管理
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"✅ Aster 客户端初始化成功")
        logger.info(f"   User地址: {self.address}")
        logger.info(f"   Signer地址: {self.signer}")
        logger.info(f"   ⚠️  请确保已在 https://www.asterdex.com/en/api-wallet 创建 API Wallet")
    
    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "Aster"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _trim_dict(self, my_dict: Dict) -> Dict:
        """转换字典值为字符串（AsterDex 要求）"""
        for key in my_dict:
            value = my_dict[key]
            if isinstance(value, list):
                new_value = []
                for item in value:
                    if isinstance(item, dict):
                        new_value.append(json.dumps(self._trim_dict(item)))
                    else:
                        new_value.append(str(item))
                my_dict[key] = json.dumps(new_value)
                continue
            if isinstance(value, dict):
                my_dict[key] = json.dumps(self._trim_dict(value))
                continue
            my_dict[key] = str(value)
        return my_dict
    
    def _trim_param(self, params: Dict, nonce: int) -> str:
        """生成签名消息 hash"""
        self._trim_dict(params)
        json_str = json.dumps(params, sort_keys=True).replace(' ', '').replace('\'', '\"')
        
        # 使用 eth_abi 编码
        encoded = encode(
            ['string', 'address', 'address', 'uint256'],
            [json_str, self.address, self.signer, nonce]
        )
        
        # 计算 keccak256 hash
        keccak_hex = Web3.keccak(encoded).hex()
        return keccak_hex
    
    def _sign_request(self, params: Dict) -> Dict:
        """
        签名请求（AsterDex 签名算法）
        
        Args:
            params: 请求参数
            
        Returns:
            签名后的参数（包含 signature, nonce, user, signer）
        """
        # 生成 nonce (微秒级时间戳)
        nonce = math.trunc(time.time() * 1000000)
        
        # 移除 None 值
        params = {key: value for key, value in params.items() if value is not None}
        
        # 添加必需参数
        params['recvWindow'] = 50000
        params['timestamp'] = int(round(time.time() * 1000))
        
        # 生成签名消息
        msg = self._trim_param(params.copy(), nonce)
        signable_msg = encode_defunct(hexstr=msg)
        signed_message = Account.sign_message(signable_message=signable_msg, private_key=self.private_key)
        
        # 添加签名相关参数
        params['nonce'] = nonce
        params['user'] = self.address
        params['signer'] = self.signer
        params['signature'] = '0x' + signed_message.signature.hex()
        
        return params
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        signed: bool = False
    ) -> Dict:
        """
        发送 API 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 请求参数
            signed: 是否需要签名
            
        Returns:
            响应数据
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        # 如果需要签名，添加签名参数
        if signed:
            params = self._sign_request(params)
        
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'AIPredict/1.0'
            }
            
            if method == "GET":
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method == "POST":
                async with session.post(url, data=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, data=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        except aiohttp.ClientError as e:
            logger.error(f"[Aster] API 请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"[Aster] 请求异常: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """获取账户信息"""
        try:
            # 获取账户信息 (V3)
            result = await self._request("GET", "/fapi/v3/account", signed=True)
            
            # 获取余额
            balance = 0.0
            if 'assets' in result:
                for asset in result['assets']:
                    if asset.get('asset') == 'USDT':
                        balance = float(asset.get('walletBalance', 0))
                        break
            
            # 标准化返回格式，兼容 Hyperliquid 格式
            return {
                "marginSummary": {
                    "accountValue": balance
                },
                "assetPositions": result.get('positions', []),
                "raw": result
            }
        except Exception as e:
            logger.error(f"[Aster] 获取账户信息失败: {e}")
            return {"marginSummary": {"accountValue": 0}, "assetPositions": []}
    
    async def get_market_data(self, coin: str) -> Dict:
        """获取市场数据"""
        try:
            # 转换币种格式 (BTC -> BTCUSDT)
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            # 获取 24小时行情
            result = await self._request("GET", "/fapi/v1/ticker/24hr", params={"symbol": symbol})
            
            return {
                "coin": coin,
                "price": float(result.get('lastPrice', 0)),
                "mark_price": float(result.get('lastPrice', 0)),  # Aster 没有单独的 mark price 接口
                "funding_rate": 0.0,  # 需要单独获取
                "open_interest": float(result.get('openInterest', 0)),
                "change_24h": float(result.get('priceChangePercent', 0)),
                "volume": float(result.get('volume', 0)),
                "raw_ctx": result
            }
        except Exception as e:
            logger.error(f"[Aster] 获取市场数据失败: {e}")
            raise
    
    async def get_orderbook(self, coin: str) -> Dict:
        """获取订单簿"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request("GET", "/fapi/v1/depth", params={"symbol": symbol, "limit": 20})
            
            bids = [[float(b[0]), float(b[1])] for b in result.get('bids', [])]
            asks = [[float(a[0]), float(a[1])] for a in result.get('asks', [])]
            
            return {"bids": bids, "asks": asks}
        except Exception as e:
            logger.error(f"[Aster] 获取订单簿失败: {e}")
            return {"bids": [], "asks": []}
    
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """获取最近成交记录"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request("GET", "/fapi/v1/trades", params={"symbol": symbol, "limit": limit})
            
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"[Aster] 获取最近成交失败: {e}")
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
        """下单"""
        try:
            # 转换币种格式
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            # 处理精度
            size_decimal = Decimal(str(size))
            if reduce_only:
                size_rounded = float(size_decimal.quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP))
            else:
                size_rounded = float(size_decimal.quantize(Decimal('0.00001'), rounding=ROUND_DOWN))
            
            # 处理价格
            if price is None:
                # 市价单
                orderbook = await self.get_orderbook(coin)
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                
                if is_buy:
                    price = float(asks[0][0]) if asks else None
                else:
                    price = float(bids[0][0]) if bids else None
                
                if price is None:
                    raise ValueError(f"无法获取 {coin} 的市价")
                
                logger.info(f"[Aster] 市价单价格: ${price:,.2f}")
            
            # 价格精度处理
            price_decimal = Decimal(str(price))
            price_rounded = float(price_decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            logger.info(f"[Aster] 📊 下单: {symbol} {'BUY' if is_buy else 'SELL'} {size_rounded} @ ${price_rounded}")
            
            # 构建订单请求 (AsterDex V3 格式)
            order_params = {
                "symbol": symbol,
                "positionSide": "BOTH",  # 单向持仓模式
                "side": "BUY" if is_buy else "SELL",
                "type": "LIMIT" if order_type == "Limit" else "MARKET",
                "timeInForce": "GTC" if not reduce_only else "IOC",  # 平仓使用 IOC
                "quantity": str(size_rounded),
                "price": price_rounded,
                "reduceOnly": reduce_only
            }
            
            # 发送订单请求 (使用 V3 端点)
            result = await self._request("POST", "/fapi/v3/order", params=order_params, signed=True)
            
            logger.info(f"[Aster] 📝 订单结果: {result}")
            
            # 标准化返回格式
            if result.get('orderId'):
                return {
                    "status": "ok",
                    "response": {
                        "data": {
                            "statuses": [{
                                "filled": {
                                    "oid": result.get('orderId')
                                }
                            }]
                        }
                    },
                    "raw": result
                }
            else:
                return {"status": "err", "response": result}
            
        except Exception as e:
            logger.error(f"[Aster] ❌ 下单失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "err", "response": str(e)}
    
    async def cancel_order(self, coin: str, order_id: str) -> Dict:
        """取消订单"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request(
                "DELETE",
                "/fapi/v1/order",
                params={"symbol": symbol, "orderId": order_id},
                signed=True
            )
            return result
        except Exception as e:
            logger.error(f"[Aster] 取消订单失败: {e}")
            return {"status": "err", "response": str(e)}
    
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """获取未成交订单"""
        try:
            params = {}
            if coin:
                symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
                params["symbol"] = symbol
            
            result = await self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"[Aster] 获取未成交订单失败: {e}")
            return []
    
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """获取用户历史成交记录"""
        try:
            params = {"limit": limit}
            if start_time_ms:
                params["startTime"] = start_time_ms
            
            # AsterDex 使用 userTrades 端点
            result = await self._request("GET", "/fapi/v1/userTrades", params=params, signed=True)
            
            fills = result if isinstance(result, list) else []
            logger.info(f"[Aster] 📊 获取了 {len(fills)} 条历史成交记录")
            return fills
        except Exception as e:
            logger.error(f"[Aster] 获取历史成交失败: {e}")
            return []
    
    async def get_candles(
        self,
        coin: str,
        interval: str = "15m",
        lookback: int = 100,
        timeout: int = 30
    ) -> List[Dict]:
        """获取 K 线数据"""
        async def _fetch_candles():
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": lookback
            }
            result = await self._request("GET", "/fapi/v1/klines", params=params)
            
            # 转换 AsterDex K线格式
            # [openTime, open, high, low, close, volume, closeTime, ...]
            candles = []
            if isinstance(result, list):
                for candle in result:
                    candles.append({
                        "time": int(candle[0]),  # openTime (毫秒)
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5])
                    })
            
            logger.info(f"[Aster] 📊 获取了 {len(candles)} 根 {interval} K线数据")
            return candles
        
        try:
            candles = await asyncio.wait_for(_fetch_candles(), timeout=timeout)
            return candles
        except asyncio.TimeoutError:
            logger.warning(f"[Aster] ⚠️  获取K线数据超时（{timeout}秒）")
            return []
        except Exception as e:
            logger.warning(f"[Aster] ⚠️  获取K线数据失败: {e}")
            return []
    
    async def close_session(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[Aster] ✅ 会话已关闭")
