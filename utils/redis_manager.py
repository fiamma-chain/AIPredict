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
    
    def save_ai_responses(self, model_name: str, responses: List[Dict]):
        """
        保存 AI 模型的响应历史
        
        Args:
            model_name: 模型名称
            responses: 响应列表（最近100条）
        """
        if not self.is_connected():
            logger.warning(f"Redis 未连接，跳过保存 {model_name} 的响应")
            return
        
        try:
            key = f"ai_responses:{model_name}"
            
            # 清空旧数据
            self.redis_client.delete(key)
            
            # 保存新数据（从旧到新的顺序）
            if responses:
                for response in responses:
                    self.redis_client.rpush(key, json.dumps(response))
            
            # 设置过期时间（30天）
            self.redis_client.expire(key, 30 * 24 * 60 * 60)
            
            logger.debug(f"💾 已保存 {model_name} 的响应历史: {len(responses)} 条")
            
        except Exception as e:
            logger.error(f"保存 {model_name} 响应失败: {e}")
    
    def get_ai_responses(self, model_name: str, limit: int = 100) -> List[Dict]:
        """
        获取 AI 模型的响应历史
        
        Args:
            model_name: 模型名称
            limit: 返回最近的N条记录（默认100）
            
        Returns:
            响应历史列表
        """
        if not self.is_connected():
            logger.warning(f"Redis 未连接，返回空响应历史")
            return []
        
        try:
            key = f"ai_responses:{model_name}"
            # 获取最近的 limit 条记录（从右侧取，即最新的）
            raw_data = self.redis_client.lrange(key, -limit, -1)
            
            responses = []
            for item in raw_data:
                try:
                    response = json.loads(item)
                    responses.append(response)
                except json.JSONDecodeError as e:
                    logger.error(f"解析 {model_name} 响应失败: {e}")
                    continue
            
            logger.info(f"📊 获取 {model_name} 响应历史: {len(responses)} 条记录")
            return responses
            
        except Exception as e:
            logger.error(f"获取 {model_name} 响应历史失败: {e}")
            return []
    
    def append_ai_response(self, model_name: str, response: Dict):
        """
        追加单条 AI 响应到历史记录
        
        Args:
            model_name: 模型名称
            response: 响应数据
        """
        if not self.is_connected():
            return
        
        try:
            key = f"ai_responses:{model_name}"
            
            # 追加到列表末尾
            self.redis_client.rpush(key, json.dumps(response))
            
            # 只保留最近100条
            self.redis_client.ltrim(key, -100, -1)
            
            # 设置过期时间（30天）
            self.redis_client.expire(key, 30 * 24 * 60 * 60)
            
            logger.debug(f"💾 已追加 {model_name} 的响应")
            
        except Exception as e:
            logger.error(f"追加 {model_name} 响应失败: {e}")
    
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

