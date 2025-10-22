"""
Redis 管理器
用于持久化存储 AI 模型响应数据
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis 数据管理器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """
        初始化 Redis 管理器
        
        Args:
            host: Redis 主机地址
            port: Redis 端口
            db: Redis 数据库编号
            password: Redis 密码
            decode_responses: 是否自动解码响应
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self.client: Optional[redis.Redis] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        连接到 Redis
        
        Returns:
            是否连接成功
        """
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self.client.ping()
            self._connected = True
            logger.info(f"✅ Redis 连接成功: {self.host}:{self.port}/{self.db}")
            return True
        except RedisError as e:
            logger.error(f"❌ Redis 连接失败: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"❌ Redis 连接异常: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if not self._connected or not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            self._connected = False
            return False
    
    def disconnect(self):
        """断开 Redis 连接"""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis 连接已关闭")
            except:
                pass
        self._connected = False
    
    def _make_key(self, platform: str, ai_model: str, coin: str) -> str:
        """
        生成 Redis 键名
        
        Args:
            platform: 交易平台名称
            ai_model: AI 模型名称
            coin: 币种
            
        Returns:
            Redis 键名
        """
        return f"ai_responses:{platform}:{ai_model}:{coin}"
    
    def save_ai_response(
        self,
        platform: str,
        ai_model: str,
        coin: str,
        decision: str,
        confidence: float,
        reasoning: str,
        raw_response: str,
        timestamp: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> bool:
        """
        保存 AI 响应到 Redis
        
        Args:
            platform: 交易平台名称（如 "hyperliquid", "aster"）
            ai_model: AI 模型名称（如 "DeepSeek", "Claude"）
            coin: 币种
            decision: 交易决策
            confidence: 信心度
            reasoning: 推理过程
            raw_response: 原始响应
            timestamp: 时间戳（可选，默认使用当前时间）
            extra_data: 额外数据（可选）
            
        Returns:
            是否保存成功
        """
        if not self.is_connected():
            logger.warning("Redis 未连接，无法保存数据")
            return False
        
        try:
            key = self._make_key(platform, ai_model, coin)
            
            # 构建数据对象
            response_data = {
                "timestamp": timestamp or datetime.now().isoformat(),
                "platform": platform,
                "ai_model": ai_model,
                "coin": coin,
                "decision": decision,
                "confidence": confidence,
                "reasoning": reasoning,
                "raw_response": raw_response
            }
            
            # 添加额外数据
            if extra_data:
                response_data.update(extra_data)
            
            # 将数据序列化为 JSON
            json_data = json.dumps(response_data, ensure_ascii=False)
            
            # 使用 LPUSH 将数据添加到列表头部（最新的在前面）
            self.client.lpush(key, json_data)
            
            # 限制列表长度，只保留最近 1000 条
            self.client.ltrim(key, 0, 999)
            
            # 设置过期时间为 30 天（可选，用于自动清理旧数据）
            self.client.expire(key, 30 * 24 * 60 * 60)
            
            logger.debug(f"✅ 已保存 AI 响应到 Redis: {key}")
            return True
            
        except RedisError as e:
            logger.error(f"❌ 保存 AI 响应到 Redis 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 保存 AI 响应异常: {e}")
            return False
    
    def get_ai_responses(
        self,
        platform: str,
        ai_model: str,
        coin: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取 AI 响应历史
        
        Args:
            platform: 交易平台名称
            ai_model: AI 模型名称
            coin: 币种
            limit: 获取数量限制
            
        Returns:
            AI 响应列表（按时间倒序）
        """
        if not self.is_connected():
            logger.warning("Redis 未连接，无法获取数据")
            return []
        
        try:
            key = self._make_key(platform, ai_model, coin)
            
            # 使用 LRANGE 获取列表数据
            json_list = self.client.lrange(key, 0, limit - 1)
            
            # 反序列化
            responses = []
            for json_str in json_list:
                try:
                    response = json.loads(json_str)
                    responses.append(response)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 解析失败: {e}")
                    continue
            
            return responses
            
        except RedisError as e:
            logger.error(f"❌ 从 Redis 获取 AI 响应失败: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ 获取 AI 响应异常: {e}")
            return []
    
    def get_all_platforms(self) -> List[str]:
        """
        获取所有平台列表
        
        Returns:
            平台名称列表
        """
        if not self.is_connected():
            return []
        
        try:
            # 扫描所有键
            keys = self.client.keys("ai_responses:*")
            platforms = set()
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 2:
                    platforms.add(parts[1])
            return sorted(list(platforms))
        except:
            return []
    
    def get_all_ai_models(self, platform: str = None) -> List[str]:
        """
        获取所有 AI 模型列表
        
        Args:
            platform: 平台名称（可选，用于过滤）
            
        Returns:
            AI 模型名称列表
        """
        if not self.is_connected():
            return []
        
        try:
            if platform:
                pattern = f"ai_responses:{platform}:*"
            else:
                pattern = "ai_responses:*"
            
            keys = self.client.keys(pattern)
            models = set()
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 3:
                    models.add(parts[2])
            return sorted(list(models))
        except:
            return []
    
    def get_all_coins(self, platform: str = None, ai_model: str = None) -> List[str]:
        """
        获取所有币种列表
        
        Args:
            platform: 平台名称（可选，用于过滤）
            ai_model: AI 模型名称（可选，用于过滤）
            
        Returns:
            币种列表
        """
        if not self.is_connected():
            return []
        
        try:
            if platform and ai_model:
                pattern = f"ai_responses:{platform}:{ai_model}:*"
            elif platform:
                pattern = f"ai_responses:{platform}:*"
            else:
                pattern = "ai_responses:*"
            
            keys = self.client.keys(pattern)
            coins = set()
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    coins.add(parts[3])
            return sorted(list(coins))
        except:
            return []
    
    def get_response_count(
        self,
        platform: str,
        ai_model: str,
        coin: str
    ) -> int:
        """
        获取响应数量
        
        Args:
            platform: 交易平台名称
            ai_model: AI 模型名称
            coin: 币种
            
        Returns:
            响应数量
        """
        if not self.is_connected():
            return 0
        
        try:
            key = self._make_key(platform, ai_model, coin)
            return self.client.llen(key)
        except:
            return 0
    
    def clear_responses(
        self,
        platform: str = None,
        ai_model: str = None,
        coin: str = None
    ) -> int:
        """
        清除响应数据
        
        Args:
            platform: 平台名称（可选）
            ai_model: AI 模型名称（可选）
            coin: 币种（可选）
            
        Returns:
            删除的键数量
        """
        if not self.is_connected():
            return 0
        
        try:
            # 构建匹配模式
            if platform and ai_model and coin:
                pattern = f"ai_responses:{platform}:{ai_model}:{coin}"
            elif platform and ai_model:
                pattern = f"ai_responses:{platform}:{ai_model}:*"
            elif platform:
                pattern = f"ai_responses:{platform}:*"
            else:
                pattern = "ai_responses:*"
            
            # 查找并删除匹配的键
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"已清除 {deleted} 个响应数据键")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"清除响应数据失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        if not self.is_connected():
            return {}
        
        try:
            stats = {
                "total_keys": 0,
                "total_responses": 0,
                "platforms": {},
                "ai_models": {},
                "coins": {}
            }
            
            # 获取所有键
            keys = self.client.keys("ai_responses:*")
            stats["total_keys"] = len(keys)
            
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    platform, ai_model, coin = parts[1], parts[2], parts[3]
                    
                    # 获取响应数量
                    count = self.client.llen(key)
                    stats["total_responses"] += count
                    
                    # 统计平台
                    if platform not in stats["platforms"]:
                        stats["platforms"][platform] = 0
                    stats["platforms"][platform] += count
                    
                    # 统计 AI 模型
                    if ai_model not in stats["ai_models"]:
                        stats["ai_models"][ai_model] = 0
                    stats["ai_models"][ai_model] += count
                    
                    # 统计币种
                    if coin not in stats["coins"]:
                        stats["coins"][coin] = 0
                    stats["coins"][coin] += count
            
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}


# 全局 Redis 管理器实例
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> Optional[RedisManager]:
    """获取全局 Redis 管理器实例"""
    return _redis_manager


def initialize_redis_manager(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None
) -> bool:
    """
    初始化全局 Redis 管理器
    
    Args:
        host: Redis 主机地址
        port: Redis 端口
        db: Redis 数据库编号
        password: Redis 密码
        
    Returns:
        是否初始化成功
    """
    global _redis_manager
    
    try:
        _redis_manager = RedisManager(
            host=host,
            port=port,
            db=db,
            password=password
        )
        
        if _redis_manager.connect():
            logger.info("🔥 Redis 管理器初始化成功")
            return True
        else:
            logger.warning("⚠️  Redis 管理器初始化失败，将不使用持久化功能")
            _redis_manager = None
            return False
    except Exception as e:
        logger.error(f"❌ Redis 管理器初始化异常: {e}")
        _redis_manager = None
        return False


def shutdown_redis_manager():
    """关闭全局 Redis 管理器"""
    global _redis_manager
    if _redis_manager:
        _redis_manager.disconnect()
        _redis_manager = None
        logger.info("Redis 管理器已关闭")

