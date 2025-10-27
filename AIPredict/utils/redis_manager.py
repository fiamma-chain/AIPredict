"""
Redis Data Manager
Used for storing and retrieving balance history data
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

# Try to use real Redis, fall back to FakeRedis if unavailable
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
    """Redis Data Manager"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = None
        
        # Try real Redis first
        if USE_REAL_REDIS:
            try:
                self.redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password if settings.redis_password else None,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"✅ Redis connection successful (Real Redis): {settings.redis_host}:{settings.redis_port}")
                return
            except Exception as e:
                logger.warning(f"⚠️  Real Redis connection failed: {e}")
                self.redis_client = None
        
        # Fall back to FakeRedis
        if HAS_FAKEREDIS:
            try:
                logger.info("🔄 Switching to FakeRedis (in-memory mode)...")
                self.redis_client = fakeredis.FakeRedis(decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ FakeRedis enabled (data stored in memory)")
            except Exception as e:
                logger.error(f"❌ FakeRedis initialization failed: {e}")
                self.redis_client = None
        else:
            logger.error("❌ Neither Redis nor FakeRedis is available")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def save_balance_snapshot(self, accounts: List[Dict]):
        """
        Save balance snapshot
        
        Args:
            accounts: List of accounts, each containing group, platform, balance, pnl, roi
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping balance snapshot save")
            return
        
        try:
            timestamp = datetime.now().isoformat()
            snapshot = {
                "timestamp": timestamp,
                "accounts": accounts
            }
            
            # Use LPUSH to add to the head of the list (newest data first)
            key = "balance_history"
            self.redis_client.lpush(key, json.dumps(snapshot))
            
            # Limit list length (keep the most recent 10000 data points, approximately 34.7 days of data at 5 seconds per point)
            self.redis_client.ltrim(key, 0, 9999)
            
            # Set expiration time
            self.redis_client.expire(key, settings.balance_history_ttl)
            
            logger.debug(f"💾 Balance snapshot saved: {len(accounts)} accounts")
            
        except Exception as e:
            logger.error(f"Failed to save balance snapshot: {e}")
    
    def get_balance_history(self, limit: int = -1) -> List[Dict]:
        """
        Get balance history
        
        Args:
            limit: Return the most recent N records, -1 means return all records
            
        Returns:
            Balance history list, sorted by time in descending order (newest first)
        """
        if not self.is_connected():
            logger.warning("Redis not connected, returning empty history")
            return []
        
        try:
            key = "balance_history"
            # Get the most recent limit records, -1 means get all
            if limit == -1:
                raw_data = self.redis_client.lrange(key, 0, -1)
            else:
                raw_data = self.redis_client.lrange(key, 0, limit - 1)
            
            history = []
            for item in raw_data:
                try:
                    snapshot = json.loads(item)
                    history.append(snapshot)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse balance snapshot: {e}")
                    continue
            
            logger.info(f"📊 Retrieved balance history: {len(history)} records")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get balance history: {e}")
            return []
    
    def clear_balance_history(self):
        """Clear balance history"""
        if not self.is_connected():
            return
        
        try:
            self.redis_client.delete("balance_history")
            logger.info("🗑️  Balance history cleared")
        except Exception as e:
            logger.error(f"Failed to clear balance history: {e}")
    
    def save_ai_responses(self, model_name: str, responses: List[Dict]):
        """
        Save AI model response history
        
        Args:
            model_name: Model name
            responses: Response list (most recent 100 entries)
        """
        if not self.is_connected():
            logger.warning(f"Redis not connected, skipping save of {model_name} responses")
            return
        
        try:
            key = f"ai_responses:{model_name}"
            
            # Clear old data
            self.redis_client.delete(key)
            
            # Save new data (from oldest to newest)
            if responses:
                for response in responses:
                    self.redis_client.rpush(key, json.dumps(response))
            
            # Set expiration time (30 days)
            self.redis_client.expire(key, 30 * 24 * 60 * 60)
            
            logger.debug(f"💾 Saved {model_name} response history: {len(responses)} entries")
            
        except Exception as e:
            logger.error(f"Failed to save {model_name} responses: {e}")
    
    def get_ai_responses(self, model_name: str, limit: int = 100) -> List[Dict]:
        """
        Get AI model response history
        
        Args:
            model_name: Model name
            limit: Return the most recent N records (default 100)
            
        Returns:
            Response history list
        """
        if not self.is_connected():
            logger.warning(f"Redis not connected, returning empty response history")
            return []
        
        try:
            key = f"ai_responses:{model_name}"
            # Get the most recent limit records (from the right side, i.e., the newest)
            raw_data = self.redis_client.lrange(key, -limit, -1)
            
            responses = []
            for item in raw_data:
                try:
                    response = json.loads(item)
                    responses.append(response)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse {model_name} response: {e}")
                    continue
            
            logger.info(f"📊 Retrieved {model_name} response history: {len(responses)} records")
            return responses
            
        except Exception as e:
            logger.error(f"Failed to get {model_name} response history: {e}")
            return []
    
    def append_ai_response(self, model_name: str, response: Dict):
        """
        Append a single AI response to history
        
        Args:
            model_name: Model name
            response: Response data
        """
        if not self.is_connected():
            return
        
        try:
            key = f"ai_responses:{model_name}"
            
            # Append to the end of the list
            self.redis_client.rpush(key, json.dumps(response))
            
            # Keep only the most recent 100 entries
            self.redis_client.ltrim(key, -100, -1)
            
            # Set expiration time (30 days)
            self.redis_client.expire(key, 30 * 24 * 60 * 60)
            
            logger.debug(f"💾 Appended {model_name} response")
            
        except Exception as e:
            logger.error(f"Failed to append {model_name} response: {e}")
    
    def save_trade(self, group_name: str, platform_name: str, trade: Dict):
        """
        Save a single trade record
        
        Args:
            group_name: Group name
            platform_name: Platform name
            trade: Trade record
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping trade record save")
            return
        
        try:
            key = f"trades:{group_name}:{platform_name}"
            
            # Add timestamp (if not present)
            if 'time' not in trade:
                trade['time'] = datetime.now().isoformat()
            
            # Append to list
            self.redis_client.rpush(key, json.dumps(trade))
            
            # Keep only the most recent 1000 trades
            self.redis_client.ltrim(key, -1000, -1)
            
            # Set expiration time (30 days)
            self.redis_client.expire(key, 30 * 24 * 60 * 60)
            
            logger.debug(f"💾 Trade record saved: {group_name}/{platform_name}")
            
        except Exception as e:
            logger.error(f"Failed to save trade record: {e}")
    
    def get_trades(self, group_name: str, platform_name: str, limit: int = -1) -> List[Dict]:
        """
        Get trade records
        
        Args:
            group_name: Group name
            platform_name: Platform name
            limit: Return the most recent N records, -1 means return all records
            
        Returns:
            Trade record list, sorted by time (earliest first)
        """
        if not self.is_connected():
            logger.warning("Redis not connected, returning empty trade records")
            return []
        
        try:
            key = f"trades:{group_name}:{platform_name}"
            
            # Get records
            if limit == -1:
                raw_data = self.redis_client.lrange(key, 0, -1)
            else:
                raw_data = self.redis_client.lrange(key, -limit, -1)
            
            trades = []
            for item in raw_data:
                try:
                    trade = json.loads(item)
                    trades.append(trade)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse trade record: {e}")
                    continue
            
            logger.info(f"📊 Retrieved {group_name}/{platform_name} trade records: {len(trades)} entries")
            return trades
            
        except Exception as e:
            logger.error(f"Failed to get trade records: {e}")
            return []
    
    def clear_trades(self, group_name: str = None, platform_name: str = None):
        """
        Clear trade records
        
        Args:
            group_name: Group name, None means clear all
            platform_name: Platform name, None means clear all platforms in the group
        """
        if not self.is_connected():
            return
        
        try:
            if group_name is None:
                # Clear all trade records
                pattern = "trades:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                logger.info("🗑️  All trade records cleared")
            elif platform_name is None:
                # Clear all trade records for a group
                pattern = f"trades:{group_name}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                logger.info(f"🗑️  All trade records cleared for {group_name}")
            else:
                # Clear trade records for a specific platform
                key = f"trades:{group_name}:{platform_name}"
                self.redis_client.delete(key)
                logger.info(f"🗑️  Trade records cleared for {group_name}/{platform_name}")
        except Exception as e:
            logger.error(f"Failed to clear trade records: {e}")
    
    def get_stats(self) -> Dict:
        """Get Redis statistics"""
        if not self.is_connected():
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            history_count = self.redis_client.llen("balance_history")
            
            # Count trade records
            trade_keys = self.redis_client.keys("trades:*")
            total_trades = sum(self.redis_client.llen(key) for key in trade_keys)
            
            return {
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "balance_history_count": history_count,
                "trade_records_count": total_trades,
                "trade_keys_count": len(trade_keys),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis statistics: {e}")
            return {"connected": False, "error": str(e)}


# Global Redis manager instance
redis_manager = RedisManager()

