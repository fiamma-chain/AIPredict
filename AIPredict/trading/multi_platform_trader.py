"""
Multi-Platform Trading Manager
Manages multiple trading platforms simultaneously, executes the same trading decisions and compares returns
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from ai_models.base_ai import TradingDecision
from trading.base_client import BaseExchangeClient
from trading.auto_trader import AutoTrader
from utils.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class PlatformTrader:
    """Trader for a single platform"""
    
    def __init__(self, client: BaseExchangeClient, name: str):
        """
        Initialize platform trader
        
        Args:
            client: Trading client
            name: Platform name
        """
        self.client = client
        self.name = name
        self.auto_trader = AutoTrader(client)
        self.start_balance = 0.0
        self.max_trades_in_stats = 1000  # Maximum number of trades to keep in stats
        self.stats = {
            "platform": client.platform_name,
            "name": name,
            "balance": 0.0,
            "initial_balance": 0.0,
            "pnl": 0.0,
            "roi": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
            "trades": [],
            "positions": {}
        }
        # Cache for account info to avoid frequent API calls
        self._account_info_cache = None
        self._account_info_cache_time = 0
        self._cache_ttl = 3  # Cache valid for 3 seconds
    
    async def initialize(self, initial_balance: float = None, group_name: str = ""):
        """
        Initialize platform trader
        
        Args:
            initial_balance: Initial balance (if None, get from account)
            group_name: Group name (used to restore trading records from Redis)
        """
        if initial_balance is not None:
            self.start_balance = initial_balance
        else:
            # Get current balance from account
            account = await self.client.get_account_info()
            self.start_balance = float(account.get('marginSummary', {}).get('accountValue', 0))
        
        self.stats["balance"] = self.start_balance
        self.stats["initial_balance"] = self.start_balance
        logger.info(f"[{self.name}] Initial balance: ${self.start_balance:,.2f}")
        
        # Restore historical trading records from Redis
        if group_name and redis_manager.is_connected():
            try:
                historical_trades = redis_manager.get_trades(group_name, self.name)
                if historical_trades:
                    # Limit restored trades to prevent memory issues
                    if len(historical_trades) > self.max_trades_in_stats:
                        historical_trades = historical_trades[-self.max_trades_in_stats:]
                        logger.info(f"[{self.name}] ⚠️  Trimmed historical trades to {self.max_trades_in_stats} most recent records")
                    self.stats["trades"] = historical_trades
                    logger.info(f"[{self.name}] 📚 Restored {len(historical_trades)} historical trades from Redis")
            except Exception as e:
                logger.error(f"[{self.name}] ❌ Failed to restore historical trades: {e}")
    
    async def execute_decision(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        current_price: float,
        group_name: str = ""
    ) -> Optional[Dict]:
        """
        Execute trading decision
        
        Args:
            coin: Coin symbol
            decision: Trading decision
            confidence: Confidence level
            reasoning: Reasoning
            current_price: Current price
            group_name: Group name (used to save to Redis)
            
        Returns:
            Trading result
        """
        # Get current balance (use cached data to reduce API calls)
        account = await self._get_account_info_cached(force_refresh=False)
        balance = float(account.get('marginSummary', {}).get('accountValue', 0))
        
        # Execute decision
        result = await self.auto_trader.execute_decision(
            coin, decision, confidence, reasoning, current_price, balance
        )
        
        # Update statistics
        if result:
            trade_record = {
                **result,
                "platform": self.client.platform_name
            }
            self.stats["trades"].append(trade_record)
            
            # Limit trades history to prevent memory leak
            if len(self.stats["trades"]) > self.max_trades_in_stats:
                self.stats["trades"] = self.stats["trades"][-self.max_trades_in_stats:]
            
            self.stats["total_trades"] = len([t for t in self.stats["trades"] if t.get('action') == 'close'])
            
            # Save to Redis (if it's a complete trade, i.e., contains px and action)
            if group_name and redis_manager.is_connected() and 'px' in result:
                try:
                    redis_manager.save_trade(group_name, self.name, trade_record)
                except Exception as e:
                    logger.error(f"[{self.name}] ❌ Failed to save trade to Redis: {e}")
        
        return result
    
    async def _get_account_info_cached(self, force_refresh: bool = False):
        """
        Get account info with caching
        
        Args:
            force_refresh: Force refresh cache (ignore TTL)
            
        Returns:
            Account info dict
        """
        import time
        current_time = time.time()
        
        # Check if cache is valid
        if (not force_refresh and 
            self._account_info_cache is not None and 
            (current_time - self._account_info_cache_time) < self._cache_ttl):
            return self._account_info_cache
        
        # Fetch fresh data
        account = await self.client.get_account_info()
        self._account_info_cache = account
        self._account_info_cache_time = current_time
        return account
    
    async def update_stats(self, force_refresh: bool = False):
        """
        Update statistics
        
        Args:
            force_refresh: Force refresh account data (ignore cache)
        """
        try:
            # Get current balance (with caching to avoid frequent API calls)
            account = await self._get_account_info_cached(force_refresh)
            current_balance = float(account.get('marginSummary', {}).get('accountValue', 0))
            
            self.stats["balance"] = current_balance
            self.stats["pnl"] = current_balance - self.start_balance
            self.stats["roi"] = (self.stats["pnl"] / self.start_balance * 100) if self.start_balance > 0 else 0
            self.stats["positions"] = self.auto_trader.get_all_positions()
            
            # Calculate win rate
            closed_trades = [t for t in self.stats["trades"] if t.get('action') == 'close']
            if closed_trades:
                winning_trades = sum(1 for t in closed_trades if t.get('pnl', 0) > 0)
                self.stats["win_rate"] = (winning_trades / len(closed_trades) * 100)
            
        except Exception as e:
            logger.error(f"[{self.name}] Failed to update statistics: {e}")


class MultiPlatformTrader:
    """Multi-platform trading manager"""
    
    def __init__(self):
        """Initialize multi-platform trading manager"""
        self.platform_traders: Dict[str, PlatformTrader] = {}
        self.decision_history: List[Dict] = []
    
    def add_platform(self, client: BaseExchangeClient, name: str = None):
        """
        Add trading platform
        
        Args:
            client: Trading client
            name: Platform name (if None, use client.platform_name)
        """
        platform_name = name or client.platform_name
        trader = PlatformTrader(client, platform_name)
        self.platform_traders[platform_name] = trader
        logger.info(f"✅ Added trading platform: {platform_name}")
    
    async def initialize_all(self, initial_balance: float = None, group_name: str = ""):
        """
        Initialize all platforms
        
        Args:
            initial_balance: Initial balance (if None, get from each platform account)
            group_name: Group name (used to restore data from Redis)
        """
        for name, trader in self.platform_traders.items():
            await trader.initialize(initial_balance, group_name)
    
    async def execute_decision_all(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        current_price: float,
        group_name: str = ""
    ) -> Dict[str, Optional[Dict]]:
        """
        Execute the same trading decision on all platforms
        
        Args:
            coin: Coin symbol
            decision: Trading decision
            confidence: Confidence level
            reasoning: Reasoning
            current_price: Current price
            group_name: Group name (used to save to Redis)
            
        Returns:
            Dictionary of trading results for each platform
        """
        results = {}
        
        # Record decision
        decision_record = {
            "time": datetime.now().isoformat(),
            "coin": coin,
            "decision": str(decision),
            "confidence": confidence,
            "reasoning": reasoning,
            "price": current_price,
            "results": {}
        }
        
        # Execute in parallel (optional: can also execute sequentially)
        import asyncio
        tasks = []
        for name, trader in self.platform_traders.items():
            tasks.append(trader.execute_decision(coin, decision, confidence, reasoning, current_price, group_name))
        
        platform_results = await asyncio.gather(*tasks)
        
        # Combine results
        for (name, trader), result in zip(self.platform_traders.items(), platform_results):
            results[name] = result
            decision_record["results"][name] = result
        
        self.decision_history.append(decision_record)
        
        return results
    
    async def update_all_stats(self, force_refresh: bool = False):
        """
        Update statistics for all platforms
        
        Args:
            force_refresh: Force refresh account data (ignore cache)
        """
        for trader in self.platform_traders.values():
            await trader.update_stats(force_refresh=force_refresh)
    
    def get_platform_trader(self, name: str) -> Optional[PlatformTrader]:
        """Get trader for a specific platform"""
        return self.platform_traders.get(name)
    
    def get_all_traders(self) -> Dict[str, PlatformTrader]:
        """Get all platform traders"""
        return self.platform_traders

