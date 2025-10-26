"""
Hyperliquid 交易客户端（使用官方SDK）
"""
import logging
from typing import Dict, List, Optional
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

from trading.base_client import BaseExchangeClient
from trading.precision_config import precision_config

logger = logging.getLogger(__name__)


class HyperliquidClient(BaseExchangeClient):
    """Hyperliquid 交易客户端（官方SDK版本）"""
    
    def __init__(self, private_key: str, testnet: bool = True, max_retries: int = 3):
        """
        初始化 Hyperliquid 客户端
        
        Args:
            private_key: 以太坊私钥（可以带或不带0x前缀）
            testnet: 是否使用测试网
            max_retries: 最大重试次数
        """
        super().__init__(private_key, testnet)
        self.testnet = testnet
        
        # 确保私钥格式正确
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # 使用官方SDK
        if testnet:
            base_url = constants.TESTNET_API_URL
        else:
            base_url = constants.MAINNET_API_URL
        
        # 添加重试机制初始化客户端
        import time
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 尝试连接 Hyperliquid API (尝试 {attempt + 1}/{max_retries})...")
                
                # 初始化 Info（查询）和 Exchange（交易）
                # 使用更长的超时时间
                self.info = Info(base_url, skip_ws=True, timeout=30)
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
                return  # 成功，退出重试循环
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    # 指数退避：等待 2^attempt 秒
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 所有重试都失败了
                    error_msg = (
                        f"❌ Hyperliquid API 连接失败（已重试 {max_retries} 次）\n"
                        f"   错误: {str(last_error)}\n"
                        f"   这可能是由于：\n"
                        f"   1. 网络连接问题\n"
                        f"   2. SSL/TLS 握手失败\n"
                        f"   3. Hyperliquid API 暂时不可用\n"
                        f"   建议：使用备用数据源或稍后重试"
                    )
                    logger.error(error_msg)
                    raise last_error
    
    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "Hyperliquid"
    
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
            订单簿数据 {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """
        try:
            l2_snapshot = self.info.l2_snapshot(coin)
            # l2_snapshot 格式: {"levels": [[{"px": price, "sz": size, "n": count},...], [...]]}
            levels = l2_snapshot.get('levels', [[], []])
            
            # 转换成标准格式 [[price, size], ...]
            bids = [[float(level['px']), float(level['sz'])] for level in levels[0]] if len(levels) > 0 else []
            asks = [[float(level['px']), float(level['sz'])] for level in levels[1]] if len(levels) > 1 else []
            
            return {
                "bids": bids,
                "asks": asks
            }
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"bids": [], "asks": []}
    
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """
        获取最近成交记录
        
        Args:
            coin: 币种符号
            limit: 返回数量
            
        Returns:
            成交记录列表 [{"time": ts, "px": price, "sz": size, "side": "A/B"}, ...]
        """
        try:
            # 使用官方SDK的 recent_trades 方法
            trades = self.info.recent_trades(coin)
            if not trades:
                return []
            
            # 限制返回数量
            if len(trades) > limit:
                trades = trades[:limit]
            
            return trades
        except Exception as e:
            logger.warning(f"获取最近成交失败: {e}, 返回空列表")
            return []
    
    def update_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> Dict:
        """
        更新杠杆倍数
        
        Args:
            coin: 币种
            leverage: 杠杆倍数 (1-50)
            is_cross: 是否全仓模式 (True=全仓, False=逐仓)
            
        Returns:
            更新结果
        """
        try:
            # 使用官方SDK的 update_leverage 方法
            result = self.exchange.update_leverage(leverage, coin, is_cross)
            logger.info(f"✅ 杠杆已更新: {coin} -> {leverage}x ({'全仓' if is_cross else '逐仓'})")
            return result
        except Exception as e:
            logger.error(f"❌ 更新杠杆失败: {e}")
            raise
    
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "Limit",
        reduce_only: bool = False,
        max_retries: int = 3,
        leverage: int = None
    ) -> Dict:
        """
        下单（支持失败重试和杠杆设置）
        
        Args:
            coin: 币种符号
            is_buy: 是否买入
            size: 数量
            price: 价格
            order_type: 订单类型 ("Limit" 或 "Market")
            reduce_only: 是否只减仓
            max_retries: 最大重试次数（默认3次）
            leverage: 杠杆倍数（1-50，None表示使用当前设置）
            
        Returns:
            订单结果
        """
        # 如果指定了杠杆，先设置杠杆
        if leverage is not None and not reduce_only:
            try:
                self.update_leverage(coin, leverage, is_cross=True)
            except Exception as e:
                logger.warning(f"⚠️ 设置杠杆失败，使用当前杠杆: {e}")
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 第 {attempt + 1} 次尝试下单...")
                    await asyncio.sleep(0.5)  # 重试前等待0.5秒
                
                # 使用官方SDK下单
                # 官方SDK参数: name, is_buy, sz, limit_px, order_type, reduce_only
                
                # 使用统一的精度配置处理数量
                size_rounded, _ = precision_config.format_hyperliquid_quantity(
                    coin, size, round_down=(not reduce_only)
                )
                
                # 处理价格：如果为 None（市价单），则获取当前市价
                if price is None:
                    logger.info("📊 市价单，正在获取当前市价...")
                    orderbook = await self.get_orderbook(coin)
                    bids = orderbook.get("bids", [])
                    asks = orderbook.get("asks", [])
                    
                    # 买单用卖一价，卖单用买一价（确保立即成交）
                    if is_buy:
                        base_price = float(asks[0][0]) if asks else None
                    else:
                        base_price = float(bids[0][0]) if bids else None
                    
                    if base_price is None:
                        raise ValueError(f"无法获取 {coin} 的市价")
                    
                    # 添加价格滑点保护，重试时增加滑点
                    # 第1次: 0.1%, 第2次: 0.15%, 第3次: 0.2%
                    slippage = 0.001 * (1 + attempt * 0.5)  # 0.1%, 0.15%, 0.2%
                    if is_buy:
                        # 买入时向上滑点，确保能买到
                        price = base_price * (1 + slippage)
                    else:
                        # 卖出时向下滑点，确保能卖出
                        price = base_price * (1 - slippage)
                    
                    logger.info(f"📊 市价单基准价格: ${base_price:,.2f}")
                    logger.info(f"📊 添加{slippage*100:.2f}%滑点后: ${price:,.2f} ({'买入向上' if is_buy else '卖出向下'})")
                
                # 使用统一的精度配置处理价格
                price_rounded, _ = precision_config.format_hyperliquid_price(coin, price)
                
                # 验证订单参数
                is_valid, error_msg = precision_config.validate_hyperliquid_order(coin, size_rounded, price_rounded)
                if not is_valid:
                    raise ValueError(f"订单参数验证失败: {error_msg}")
                
                logger.info(f"📊 原始数量: {size}, 处理后: {size_rounded}")
                logger.info(f"📊 原始价格: {price}, 处理后: {price_rounded}")
                
                # 平仓单使用 Ioc（立即成交或取消），开仓单使用 Gtc（有效直到取消）
                if reduce_only:
                    # 平仓单：使用 Ioc 确保立即成交
                    order_type_param = {"limit": {"tif": "Ioc"}}
                else:
                    # 开仓单：根据 order_type 参数决定
                    if order_type == "Limit":
                        order_type_param = {"limit": {"tif": "Gtc"}}
                    else:
                        order_type_param = {"limit": {"tif": "Ioc"}}  # 市价单也用 Ioc
                
                order_result = self.exchange.order(
                    name=coin,
                    is_buy=is_buy,
                    sz=size_rounded,
                    limit_px=price_rounded,
                    order_type=order_type_param,
                    reduce_only=reduce_only
                )
                
                logger.info(f"📝 官方SDK订单结果: {order_result}")
                
                # 检查订单是否成功
                if order_result.get('status') == 'ok':
                    response = order_result.get('response', {})
                    data = response.get('data', {})
                    statuses = data.get('statuses', [])
                    
                    # 检查是否有错误
                    if statuses and 'error' in statuses[0]:
                        error_msg = statuses[0]['error']
                        last_error = error_msg
                        logger.warning(f"⚠️  订单失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                        
                        # 如果不是最后一次尝试，继续重试
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error(f"❌ 所有重试均失败，最后错误: {error_msg}")
                            return order_result
                    else:
                        # 成功，直接返回
                        logger.info(f"✅ 订单成功 (尝试 {attempt + 1}/{max_retries})")
                        return order_result
                else:
                    # 订单被拒绝
                    last_error = order_result.get('response', 'Unknown error')
                    logger.warning(f"⚠️  订单被拒绝 (尝试 {attempt + 1}/{max_retries}): {last_error}")
                    
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return order_result
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️  下单异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    continue
                else:
                    logger.error(f"❌ 所有重试均失败")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {"status": "err", "response": str(e)}
        
        # 如果所有重试都失败
        logger.error(f"❌ 订单最终失败，已尝试 {max_retries} 次")
        return {"status": "err", "response": f"All {max_retries} attempts failed. Last error: {last_error}"}
    
    async def cancel_order(self, coin: str, order_id) -> Dict:
        """
        取消订单
        
        Args:
            coin: 币种符号
            order_id: 订单ID
            
        Returns:
            取消结果
        """
        try:
            oid = int(order_id) if isinstance(order_id, str) else order_id
            result = self.exchange.cancel(coin, oid)
            return result
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {"status": "err", "response": str(e)}
    
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """
        获取未成交订单
        
        Args:
            coin: 币种符号（可选，Hyperliquid 不支持按币种过滤）
        
        Returns:
            订单列表
        """
        try:
            user_state = await self.get_account_info()
            orders = user_state.get('assetPositions', [])
            # 如果指定了币种，过滤结果
            if coin:
                orders = [o for o in orders if o.get('position', {}).get('coin') == coin]
            return orders
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            return []
    
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """
        获取用户历史成交记录
        
        Args:
            limit: 返回数量限制
            start_time_ms: 开始时间（毫秒时间戳），如果为None则获取所有
            
        Returns:
            成交记录列表
        """
        try:
            if start_time_ms:
                # 使用时间范围查询
                fills = self.info.user_fills_by_time(self.address, start_time_ms)
            else:
                # 获取所有交易记录
                fills = self.info.user_fills(self.address)
            
            if not fills:
                return []
            
            # 限制返回数量
            if len(fills) > limit:
                fills = fills[:limit]
            
            logger.info(f"📊 从 Hyperliquid 获取了 {len(fills)} 条历史成交记录")
            return fills
        except Exception as e:
            logger.error(f"获取历史成交失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def get_candles(self, coin: str, interval: str = "15m", lookback: int = 100, timeout: int = 30) -> List[Dict]:
        """
        获取 K 线数据（带超时保护）
        
        Args:
            coin: 币种符号
            interval: K线周期 ("1m", "5m", "15m", "1h", "4h", "1d")
            lookback: 回溯K线数量
            timeout: 超时时间（秒），默认30秒
            
        Returns:
            K线数据列表 [{"time": timestamp, "open": o, "high": h, "low": l, "close": c, "volume": v}, ...]
        """
        import asyncio
        import time
        
        async def _fetch_candles():
            """内部异步获取函数"""
            # 使用官方SDK获取K线数据，endTime为当前时间戳（毫秒）
            end_time_ms = int(time.time() * 1000)
            
            # SDK调用是同步的，需要在executor中运行
            loop = asyncio.get_event_loop()
            candles = await loop.run_in_executor(
                None,
                self.info.candles_snapshot,
                coin, interval, lookback, end_time_ms
            )
            return candles
        
        try:
            # 使用asyncio.wait_for添加超时保护
            candles = await asyncio.wait_for(_fetch_candles(), timeout=timeout)
            
            if not candles:
                logger.warning(f"⚠️  未获取到K线数据，返回空列表")
                return []
            
            # 转换成标准格式
            result = []
            for candle in candles:
                result.append({
                    "time": candle.get('t', 0),  # 时间戳（毫秒）
                    "open": float(candle.get('o', 0)),
                    "high": float(candle.get('h', 0)),
                    "low": float(candle.get('l', 0)),
                    "close": float(candle.get('c', 0)),
                    "volume": float(candle.get('v', 0))
                })
            
            logger.info(f"📊 获取了 {len(result)} 根 {interval} K线数据")
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️  获取K线数据超时（{timeout}秒），返回空列表")
            return []
        except Exception as e:
            logger.warning(f"⚠️  获取K线数据失败: {e}, 返回空列表")
            return []

