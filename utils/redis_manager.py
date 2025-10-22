"""
Redis 数据管理器
用于存储和获取余额历史数据
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

# 尝试使用真实Redis，如果不可用则使用FakeRedis
try:
    import redis
    USE_REAL_REDIS = True
except ImportError:
    import fakeredis as redis
    USE_REAL_REDIS = False

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False


class RedisManager:
    """Redis 数据管理器"""
    
    def __init__(self):
        """初始化 Redis 连接"""
        self.redis_client = None
        
        # 优先尝试真实Redis
        if USE_REAL_REDIS:
            try:
                self.redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password if settings.redis_password else None,
                    decode_responses=True
                )
                # 测试连接
                self.redis_client.ping()
                logger.info(f"✅ Redis 连接成功 (真实Redis): {settings.redis_host}:{settings.redis_port}")
                return
            except Exception as e:
                logger.warning(f"⚠️  真实Redis连接失败: {e}")
                self.redis_client = None
        
        # 回退到FakeRedis
        if HAS_FAKEREDIS:
            try:
                logger.info("🔄 切换到 FakeRedis (内存模式)...")
                self.redis_client = fakeredis.FakeRedis(decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ FakeRedis 已启用 (数据存储在内存中)")
            except Exception as e:
                logger.error(f"❌ FakeRedis 初始化失败: {e}")
                self.redis_client = None
        else:
            logger.error("❌ Redis和FakeRedis都不可用")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """检查 Redis 是否连接"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def save_balance_snapshot(self, accounts: List[Dict]):
        """
        保存余额快照
        
        Args:
            accounts: 账户列表，每个账户包含 group, platform, balance, pnl, roi
        """
        if not self.is_connected():
            logger.warning("Redis 未连接，跳过保存余额快照")
            return
        
        try:
            timestamp = datetime.now().isoformat()
            snapshot = {
                "timestamp": timestamp,
                "accounts": accounts
            }
            
            # 使用 LPUSH 添加到列表头部（最新数据在前）
            key = "balance_history"
            self.redis_client.lpush(key, json.dumps(snapshot))
            
            # 限制列表长度（保留最近 1000 个数据点，约 83 小时的数据，5秒一个点）
            self.redis_client.ltrim(key, 0, 999)
            
            # 设置过期时间
            self.redis_client.expire(key, settings.balance_history_ttl)
            
            logger.debug(f"💾 已保存余额快照: {len(accounts)} 个账户")
            
        except Exception as e:
            logger.error(f"保存余额快照失败: {e}")
    
    def get_balance_history(self, limit: int = 100) -> List[Dict]:
        """
        获取余额历史
        
        Args:
            limit: 返回最近的N条记录
            
        Returns:
            余额历史列表，按时间倒序（最新的在前）
        """
        if not self.is_connected():
            logger.warning("Redis 未连接，返回空历史")
            return []
        
        try:
            key = "balance_history"
            # 获取最近的 limit 条记录
            raw_data = self.redis_client.lrange(key, 0, limit - 1)
            
            history = []
            for item in raw_data:
                try:
                    snapshot = json.loads(item)
                    history.append(snapshot)
                except json.JSONDecodeError as e:
                    logger.error(f"解析余额快照失败: {e}")
                    continue
            
            logger.info(f"📊 获取余额历史: {len(history)} 条记录")
            return history
            
        except Exception as e:
            logger.error(f"获取余额历史失败: {e}")
            return []
    
    def clear_balance_history(self):
        """清空余额历史"""
        if not self.is_connected():
            return
        
        try:
            self.redis_client.delete("balance_history")
            logger.info("🗑️  已清空余额历史")
        except Exception as e:
            logger.error(f"清空余额历史失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取 Redis 统计信息"""
        if not self.is_connected():
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            history_count = self.redis_client.llen("balance_history")
            
            return {
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "balance_history_count": history_count,
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except Exception as e:
            logger.error(f"获取 Redis 统计失败: {e}")
            return {"connected": False, "error": str(e)}


# 全局 Redis 管理器实例
redis_manager = RedisManager()

