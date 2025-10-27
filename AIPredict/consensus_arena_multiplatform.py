"""
AI Consensus Trading System - Multi-Platform Comparison Version
Supports trading on both Hyperliquid and Aster platforms simultaneously for performance comparison
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from config.settings import settings, get_enabled_platforms, get_individual_traders_config
from ai_models.deepseek_trader import DeepSeekTrader
from ai_models.claude_trader import ClaudeTrader
from ai_models.grok_trader import GrokTrader
from ai_models.gpt_trader import GPTTrader
from ai_models.gemini_trader import GeminiTrader
from ai_models.qwen_trader import QwenTrader
from trading.hyperliquid.client import HyperliquidClient
from trading.aster.client import AsterClient
from trading.multi_platform_trader import MultiPlatformTrader
from utils.symbol_filter import symbol_filter
from trading.kline_manager import KlineManager
from ai_models.base_ai import TradingDecision
from utils.redis_manager import redis_manager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()


class IndividualAITrader:
    """Individual AI Trader - Single AI makes independent decisions and trades"""
    
    def __init__(self, name: str, ai_trader, private_key: str):
        """
        Initialize individual AI trader
        
        Args:
            name: Trader name
            ai_trader: AI trader instance
            private_key: Private key
        """
        self.name = name
        self.ai_trader = ai_trader
        self.ai_name = ai_trader.__class__.__name__.replace('Trader', '')
        self.kline_manager = KlineManager(max_klines=16)
        self.start_time = datetime.now()
        
        # Create multi-platform trading manager
        self.multi_trader = MultiPlatformTrader()
        
        # 🎯 Individual AI trader: only trade on Aster platform
        logger.info(f"[{name}] Individual AI Trader - Trading only on Aster platform")
        client = AsterClient(private_key, settings.aster_testnet)
        self.multi_trader.add_platform(client, f"{name}-Aster")
        
        # Create Hyperliquid client for market data (not for trading)
        # If it fails, use Aster as data source
        self.data_source_client = None
        try:
            logger.info(f"[{name}] 📊 Attempting to create Hyperliquid data source client (for market data only)")
            self.data_source_client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
            logger.info(f"[{name}] ✅ Hyperliquid data source client created successfully")
        except Exception as e:
            logger.warning(f"[{name}] ⚠️  Hyperliquid data source connection failed: {str(e)[:100]}")
            logger.info(f"[{name}] 📌 Will use Aster as market data source")
        
        # Save the client used for market data
        if self.data_source_client:
            self.primary_client = self.data_source_client
        else:
            # If Hyperliquid is not available, use Aster client as data source
            self.primary_client = list(self.multi_trader.platform_traders.values())[0].client if self.multi_trader.platform_traders else None
        
        # Statistics data
        self.stats = {
            "trader_name": name,
            "ai_name": self.ai_name,
            "type": "individual",
            "platforms": {},
            "decisions": [],
            "platform_comparison": {}
        }
    
    async def initialize(self):
        """Initialize trader"""
        # Individual AI traders use separate initial balance configuration (200 USDT)
        await self.multi_trader.initialize_all(settings.individual_ai_initial_balance, self.name)
        
        # Sync positions across platforms
        for platform_name, trader in self.multi_trader.platform_traders.items():
            await self._sync_existing_positions(trader)
    
    async def _sync_existing_positions(self, trader):
        """Sync platform positions"""
        try:
            logger.info(f"[{trader.name}] 🔄 Syncing existing positions...")
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            synced_count = 0
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    coin = pos['position']['coin']
                    size = float(pos['position']['szi'])
                    
                    if size == 0:
                        continue
                    
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    trader.auto_trader.positions[coin] = {
                        'side': 'long' if is_long else 'short',
                        'entry_price': entry_px,
                        'size': abs_size,
                        'entry_time': datetime.now(),
                        'confidence': 0,
                        'reasoning': 'Historical position synced at system startup',
                        'order_id': 'synced'
                    }
                    
                    synced_count += 1
                    logger.info(f"[{trader.name}]    ✅ {coin} {'LONG' if is_long else 'SHORT'} {abs_size:.5f} @ ${entry_px:,.2f}")
                
                except Exception as e:
                    logger.warning(f"[{trader.name}] Failed to parse position: {e}")
                    continue
            
            if synced_count > 0:
                logger.info(f"[{trader.name}] ✅ Synced {synced_count} existing position(s)")
            else:
                logger.info(f"[{trader.name}] 📭 No existing positions")
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ Failed to sync positions: {e}")
    
    async def get_decision(
        self, 
        coin: str, 
        market_data: Dict, 
        orderbook: Dict, 
        recent_trades: List,
        position_info: Optional[Dict] = None
    ) -> Tuple[Optional[TradingDecision], float, str]:
        """Get AI decision (no consensus needed)"""
        kline_history_data = self.kline_manager.format_for_prompt(max_rows=16)
        
        try:
            logger.info(f"[{self.name}] 🤖 Getting {self.ai_name} decision...")
            
            # Inject K-line data
            original_create_prompt = self.ai_trader.create_market_prompt
            def wrapped_prompt(c, m, o, p=None, kline_history=None):
                return original_create_prompt(c, m, o, p, kline_history=kline_history_data)
            self.ai_trader.create_market_prompt = wrapped_prompt
            
            decision, confidence, reasoning = await self.ai_trader.analyze_market(
                coin, market_data, orderbook, recent_trades, position_info
            )
            
            # Restore original method
            self.ai_trader.create_market_prompt = original_create_prompt
            
            logger.info(f"[{self.name}]    {self.ai_name}: {decision} (confidence: {confidence:.1f}%)")
            
            return decision, confidence, reasoning
        
        except Exception as e:
            logger.error(f"[{self.name}] ❌ {self.ai_name} decision failed: {e}")
            return None, 0, f"Decision failed: {str(e)}"
    
    async def execute_decision_on_all_platforms(
        self, 
        coin: str, 
        decision: TradingDecision, 
        confidence: float, 
        reasoning: str, 
        current_price: float
    ):
        """Execute decision on all platforms"""
        if decision == TradingDecision.HOLD:
            logger.debug(f"[{self.name}] 💤 AI suggests hold, no trade executed")
            return
        
        logger.info(f"[{self.name}] 🚀 Executing decision on all platforms: {decision}")
        results = await self.multi_trader.execute_decision_all(
            coin, decision, confidence, reasoning, current_price, self.name
        )
        
        for platform_name, result in results.items():
            if result:
                logger.info(f"[{platform_name}] ✅ Trade executed")
            else:
                logger.info(f"[{platform_name}] ⚠️  Trade not executed")
    
    async def update_stats(self):
        """Update statistics"""
        await self.multi_trader.update_all_stats()
        
        # Update statistics
        comparison = self.multi_trader.get_comparison_stats()
        self.stats["platform_comparison"] = comparison
        
        # Update statistics for each platform
        for platform_name, trader in self.multi_trader.platform_traders.items():
            self.stats["platforms"][platform_name] = trader.stats


class AIGroup:
    """AI Group - Multi-Platform Version"""
    
    def __init__(self, name: str, ai_traders: List, private_key: str):
        """
        Initialize AI group
        
        Args:
            name: Group name
            ai_traders: List of AI traders
            private_key: Private key
        """
        self.name = name
        self.ai_traders = ai_traders
        self.kline_manager = KlineManager(max_klines=16)
        self.start_time = datetime.now()
        
        # Create multi-platform trading manager
        self.multi_trader = MultiPlatformTrader()
        
        # 🎯 AI consensus group (Alpha/Beta): trade on multiple platforms
        enabled_platforms = get_enabled_platforms()
        logger.info(f"[{name}] AI Consensus Group - Trading on platforms: {enabled_platforms}")
        
        for platform in enabled_platforms:
            if platform == "hyperliquid":
                try:
                    client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
                    self.multi_trader.add_platform(client, f"{name}-Hyperliquid")
                except Exception as e:
                    logger.error(f"[{name}] ❌ Hyperliquid platform initialization failed: {str(e)[:100]}")
                    logger.warning(f"[{name}] ⚠️  Skipping Hyperliquid platform, continuing with other platforms")
            elif platform == "aster":
                try:
                    client = AsterClient(private_key, settings.aster_testnet)
                    self.multi_trader.add_platform(client, f"{name}-Aster")
                except Exception as e:
                    logger.error(f"[{name}] ❌ Aster platform initialization failed: {str(e)[:100]}")
                    logger.warning(f"[{name}] ⚠️  Skipping Aster platform, continuing with other platforms")
        
        # Create Hyperliquid client for market data (even if not used for trading)
        # This allows using Hyperliquid's depth data without trading on it
        self.data_source_client = None
        if "hyperliquid" not in enabled_platforms:
            try:
                logger.info(f"[{name}] 📊 Attempting to create Hyperliquid data source client (for market data only)")
                self.data_source_client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
                logger.info(f"[{name}] ✅ Hyperliquid data source client created successfully")
            except Exception as e:
                logger.warning(f"[{name}] ⚠️  Hyperliquid data source connection failed: {str(e)[:100]}")
                logger.info(f"[{name}] 📌 Will use enabled platforms as market data source")
        
        # Save the client used for market data
        if self.data_source_client:
            self.primary_client = self.data_source_client
        else:
            self.primary_client = list(self.multi_trader.platform_traders.values())[0].client if self.multi_trader.platform_traders else None
        
        # Statistics data
        self.stats = {
            "group_name": name,
            "platforms": {},
            "consensus_decisions": [],
            "platform_comparison": {}
        }
    
    async def initialize(self):
        """Initialize group"""
        # Pass group name to restore trading records from Redis
        await self.multi_trader.initialize_all(settings.ai_initial_balance, self.name)
        
        # Sync positions across platforms
        for platform_name, trader in self.multi_trader.platform_traders.items():
            await self._sync_existing_positions(trader)
    
    async def _sync_existing_positions(self, trader):
        """同步平台持仓"""
        try:
            logger.info(f"[{trader.name}] 🔄 正在同步现有持仓...")
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            synced_count = 0
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    coin = pos['position']['coin']
                    size = float(pos['position']['szi'])
                    
                    if size == 0:
                        continue
                    
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    trader.auto_trader.positions[coin] = {
                        'side': 'long' if is_long else 'short',
                        'entry_price': entry_px,
                        'size': abs_size,
                        'entry_time': datetime.now(),
                        'confidence': 0,
                        'reasoning': 'Historical position synced at system startup',
                        'order_id': 'synced'
                    }
                    
                    synced_count += 1
                    logger.info(f"[{trader.name}]    ✅ {coin} {'LONG' if is_long else 'SHORT'} {abs_size:.5f} @ ${entry_px:,.2f}")
                
                except Exception as e:
                    logger.warning(f"[{trader.name}] Failed to parse position: {e}")
                    continue
            
            if synced_count > 0:
                logger.info(f"[{trader.name}] ✅ Synced {synced_count} existing position(s)")
            else:
                logger.info(f"[{trader.name}] 📭 No existing positions")
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ Failed to sync positions: {e}")
    
    async def _sync_and_clean_positions(self, trader, coin: str):
        """
        Sync and clean positions (handle manual operations and residual positions)
        
        Args:
            trader: Platform trader
            coin: Trading symbol
        """
        try:
            # Get actual exchange position
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            actual_position = None
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    if pos['position']['coin'] == coin:
                        size = float(pos['position']['szi'])
                        if size != 0:
                            actual_position = {
                                'coin': coin,
                                'size': abs(size),
                                'side': 'long' if size > 0 else 'short',
                                'entry_px': float(pos['position']['entryPx'])
                            }
                        break
                except Exception as e:
                    logger.warning(f"[{trader.name}] Failed to parse position: {e}")
                    continue
            
            # Get system recorded position
            system_position = trader.auto_trader.positions.get(coin)
            
            # 🔥 Case 1: Exchange has no position but system has record (manual close)
            if not actual_position and system_position:
                logger.warning(f"[{trader.name}] ⚠️  Detected manual position close: {coin}")
                logger.warning(f"[{trader.name}]    System record: {system_position['side'].upper()} {system_position['size']:.8f}")
                logger.warning(f"[{trader.name}]    Exchange actual: No position")
                logger.info(f"[{trader.name}] 🧹 Cleaning up system position record")
                del trader.auto_trader.positions[coin]
            
            # 🔥 Case 2: Exchange has position but system has no record (manual open)
            elif actual_position and not system_position:
                logger.warning(f"[{trader.name}] ⚠️  Detected manual position open: {coin}")
                logger.warning(f"[{trader.name}]    System record: No position")
                logger.warning(f"[{trader.name}]    Exchange actual: {actual_position['side'].upper()} {actual_position['size']:.8f}")
                logger.info(f"[{trader.name}] 📥 Syncing to system record")
                trader.auto_trader.positions[coin] = {
                    'side': actual_position['side'],
                    'entry_price': actual_position['entry_px'],
                    'size': actual_position['size'],
                    'entry_time': datetime.now(),
                    'confidence': 0,
                    'reasoning': 'Manual position detected and synced',
                    'order_id': 'manual'
                }
            
            # 🔥 Case 3: Both have positions but sizes don't match (partial close or residual)
            elif actual_position and system_position:
                size_diff = abs(actual_position['size'] - system_position['size'])
                if size_diff > 0.00001:  # Allow tiny error
                    logger.warning(f"[{trader.name}] ⚠️  Position size mismatch: {coin}")
                    logger.warning(f"[{trader.name}]    System record: {system_position['size']:.8f}")
                    logger.warning(f"[{trader.name}]    Exchange actual: {actual_position['size']:.8f}")
                    logger.warning(f"[{trader.name}]    Difference: {size_diff:.8f}")
                    
                    # 🧹 Check if it's a residual position (less than 2x minimum trade unit)
                    min_size = 0.002  # 2x BTC minimum unit of 0.001
                    if actual_position['size'] < min_size:
                        logger.warning(f"[{trader.name}] 🧹 Detected residual position ({actual_position['size']:.8f} < {min_size})")
                        logger.info(f"[{trader.name}] Attempting to clean residual position...")
                        
                        # Try to close residual position
                        try:
                            platform_name = getattr(trader.client, 'platform_name', 'Unknown')
                            is_buy = (actual_position['side'] == 'short')
                            
                            # Get current price
                            market_data = await trader.client.get_market_data(coin)
                            current_price = market_data['price']
                            
                            if platform_name == 'Aster':
                                # Aster uses market orders
                                order_result = await trader.client.place_order(
                                    coin=coin,
                                    is_buy=is_buy,
                                    size=actual_position['size'],
                                    price=None,
                                    order_type="Market",
                                    reduce_only=True
                                )
                            else:
                                # Other platforms use limit orders
                                order_price = current_price * 1.001 if is_buy else current_price * 0.999
                                order_result = await trader.client.place_order(
                                    coin=coin,
                                    is_buy=is_buy,
                                    size=actual_position['size'],
                                    price=order_price,
                                    order_type="Limit",
                                    reduce_only=True
                                )
                            
                            if order_result.get('status') == 'ok':
                                logger.info(f"[{trader.name}] ✅ Residual position cleaned successfully")
                                # Clear system record
                                if coin in trader.auto_trader.positions:
                                    del trader.auto_trader.positions[coin]
                            else:
                                logger.warning(f"[{trader.name}] ⚠️  Failed to clean residual position: {order_result.get('response')}")
                                # Sync actual size
                                system_position['size'] = actual_position['size']
                        
                        except Exception as e:
                            logger.error(f"[{trader.name}] ❌ Failed to clean residual position: {e}")
                            # Sync actual size
                            system_position['size'] = actual_position['size']
                    else:
                        # Not a residual position, directly sync size
                        logger.info(f"[{trader.name}] 🔄 Syncing position size: {system_position['size']:.8f} → {actual_position['size']:.8f}")
                        system_position['size'] = actual_position['size']
            
            # Case 4: Both have no position (normal)
            # No action needed
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ Failed to sync and clean positions: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def get_consensus_decision(
        self, 
        coin: str, 
        market_data: Dict, 
        orderbook: Dict, 
        recent_trades: List,
        position_info: Optional[Dict] = None,
        pre_computed_decisions: Optional[Dict[str, Dict]] = None
    ) -> Tuple[Optional[TradingDecision], float, str, List[Dict]]:
        """
        Get group consensus decision
        
        Args:
            pre_computed_decisions: Optional pre-computed decisions in format {ai_name: decision_dict}
                                   If provided, use these decisions directly instead of calling API again
        """
        kline_history_data = self.kline_manager.format_for_prompt(max_rows=16)
        
        # 🎯 If pre-computed decisions are provided, use them directly
        if pre_computed_decisions:
            logger.info(f"[{self.name}] 📋 Using pre-computed AI decision results...")
            ai_decisions = []
            for ai_trader in self.ai_traders:
                ai_name = ai_trader.__class__.__name__.replace('Trader', '')
                if ai_name in pre_computed_decisions:
                    decision_data = pre_computed_decisions[ai_name]
                    logger.info(f"[{self.name}]    {ai_name}: {decision_data['decision']} (confidence: {decision_data['confidence']:.1f}%) [reused]")
                    ai_decisions.append(decision_data)
                else:
                    logger.warning(f"[{self.name}]    ⚠️ Pre-computed decision for {ai_name} not found")
        else:
            # Original logic: call API to get decisions
            async def get_ai_decision(ai_trader):
                try:
                    ai_name = ai_trader.__class__.__name__.replace('Trader', '')
                    logger.info(f"[{self.name}] 🤖 Getting {ai_name} decision...")
                    
                    original_create_prompt = ai_trader.create_market_prompt
                    def wrapped_prompt(c, m, o, p=None, kline_history=None):
                        return original_create_prompt(c, m, o, p, kline_history=kline_history_data)
                    ai_trader.create_market_prompt = wrapped_prompt
                    
                    decision, confidence, reasoning = await ai_trader.analyze_market(
                        coin, market_data, orderbook, recent_trades, position_info
                    )
                    
                    ai_trader.create_market_prompt = original_create_prompt
                    
                    logger.info(f"[{self.name}]    {ai_name}: {decision} (confidence: {confidence:.1f}%)")
                    
                    return {
                        'ai_name': ai_name,
                        'decision': decision,
                        'confidence': confidence,
                        'reasoning': reasoning
                    }
                
                except Exception as e:
                    logger.error(f"[{self.name}] ❌ {ai_trader.__class__.__name__} decision failed: {e}")
                    return None
            
            logger.info(f"[{self.name}] 🚀 Starting parallel calls to {len(self.ai_traders)} AI models...")
            results = await asyncio.gather(*[get_ai_decision(ai) for ai in self.ai_traders])
            
            ai_decisions = [r for r in results if r is not None]
        
        if not ai_decisions:
            return None, 0, "All AI decisions failed", []
        
        # Count votes
        buy_votes = []
        sell_votes = []
        hold_votes = []
        
        for d in ai_decisions:
            if d['decision'] in [TradingDecision.BUY, TradingDecision.STRONG_BUY]:
                buy_votes.append(d)
            elif d['decision'] in [TradingDecision.SELL, TradingDecision.STRONG_SELL]:
                sell_votes.append(d)
            else:
                hold_votes.append(d)
        
        buy_count = len(buy_votes)
        sell_count = len(sell_votes)
        hold_count = len(hold_votes)
        
        vote_counts = [
            (buy_count, TradingDecision.BUY, buy_votes, "Buy"),
            (sell_count, TradingDecision.SELL, sell_votes, "Sell"),
            (hold_count, TradingDecision.HOLD, hold_votes, "Hold")
        ]
        vote_counts.sort(key=lambda x: x[0], reverse=True)
        
        vote_count, consensus_decision, supporting_ais, direction_name = vote_counts[0]
        
        if supporting_ais:
            avg_confidence = sum(d['confidence'] for d in supporting_ais) / len(supporting_ais)
        else:
            avg_confidence = 0
        
        vote_summary = f"Buy: {buy_count}, Sell: {sell_count}, Hold: {hold_count}"
        consensus_summary = f"Consensus: {direction_name} ({vote_count}/{len(ai_decisions)} votes, Avg Confidence {avg_confidence:.1f}%)\nVoting Details: {vote_summary}"
        
        logger.info(f"[{self.name}] 📊 {consensus_summary}")
        
        min_votes = settings.consensus_min_votes
        if vote_count >= min_votes:
            logger.info(f"[{self.name}] ✅ Consensus reached! Executing: {direction_name} ({consensus_decision})")
            return consensus_decision, avg_confidence, consensus_summary, ai_decisions
        else:
            logger.info(f"[{self.name}] ⚠️  No consensus reached (need at least {min_votes} votes), holding position")
            return TradingDecision.HOLD, avg_confidence, f"No consensus reached (need {min_votes} votes, got {vote_count} votes max), holding\n{vote_summary}", ai_decisions
    
    async def execute_decision_on_all_platforms(
        self, 
        coin: str, 
        decision: TradingDecision, 
        confidence: float, 
        reasoning: str, 
        current_price: float
    ):
        """Execute decision on all platforms"""
        if decision == TradingDecision.HOLD:
            logger.debug(f"[{self.name}] 💤 AI suggests hold, no trade executed")
            return
        
        logger.info(f"[{self.name}] 🚀 Executing decision on all platforms: {decision}")
        results = await self.multi_trader.execute_decision_all(
            coin, decision, confidence, reasoning, current_price, self.name
        )
        
        for platform_name, result in results.items():
            if result:
                logger.info(f"[{platform_name}] ✅ Trade executed")
            else:
                logger.info(f"[{platform_name}] ⚠️  Trade not executed")
    
    async def update_stats(self):
        """Update statistics"""
        await self.multi_trader.update_all_stats()
        
        # Update group statistics
        comparison = self.multi_trader.get_comparison_stats()
        self.stats["platform_comparison"] = comparison
        
        # Update statistics for each platform
        for platform_name, trader in self.multi_trader.platform_traders.items():
            self.stats["platforms"][platform_name] = trader.stats


class ConsensusArena:
    """Consensus Arena - Multi-Platform Version (supports group consensus + individual AI traders)"""
    
    def __init__(self):
        self.groups: List[AIGroup] = []
        self.individual_traders: List[IndividualAITrader] = []
        self.running = False
        self.update_interval = settings.consensus_interval
        self.decision_history = []  # Decision history (global)
        self.balance_history = []   # Balance history (global)
    
    async def initialize(self):
        """Initialize system"""
        logger.info("=" * 80)
        logger.info("🤖 AI Consensus Trading System - Multi-Platform Comparison Version")
        logger.info("=" * 80)
        
        enabled_platforms = get_enabled_platforms()
        logger.info(f"Enabled trading platforms: {', '.join(enabled_platforms)}")
        logger.info(f"Trading symbol: {symbol_filter.get_default_symbol()}")
        logger.info(f"⏱️  Decision cycle: {self.update_interval//60} minute(s)")
        logger.info(f"🎯 Consensus rule: At least {settings.consensus_min_votes} AIs must agree per group")
        logger.info(f"Initial capital per group: ${settings.ai_initial_balance}")
        logger.info("=" * 80)
        
        # Initialize Alpha group
        logger.info("\n📊 Initializing Alpha Group (DeepSeek + Claude + Grok)...")
        alpha_ais = [
            DeepSeekTrader(api_key=settings.deepseek_api_key),
            ClaudeTrader(api_key=settings.claude_api_key),
            GrokTrader(api_key=settings.grok_api_key)
        ]
        alpha_group = AIGroup(
            settings.group_1_name,
            alpha_ais,
            settings.group_1_private_key
        )
        await alpha_group.initialize()
        await alpha_group.update_stats()  # Update initial statistics
        self.groups.append(alpha_group)
        logger.info(f"✅ Alpha Group initialization complete")
        
        # Initialize Beta group
        logger.info("\n📊 Initializing Beta Group (GPT-4 + Gemini + Qwen)...")
        beta_ais = [
            GPTTrader(api_key=settings.openai_api_key, model=settings.gpt_model),
            GeminiTrader(api_key=settings.gemini_api_key),
            QwenTrader(api_key=settings.qwen_api_key, use_international=settings.qwen_use_international)
        ]
        beta_group = AIGroup(
            settings.group_2_name,
            beta_ais,
            settings.group_2_private_key
        )
        await beta_group.initialize()
        await beta_group.update_stats()  # Update initial statistics
        self.groups.append(beta_group)
        logger.info(f"✅ Beta Group initialization complete")
        
        # Initialize individual AI traders
        try:
            individual_configs = get_individual_traders_config()
        except ValueError as e:
            logger.error(f"\n❌ Individual AI trader configuration error:")
            logger.error(str(e))
            logger.error("\nPlease check individual AI trader private key configuration in .env file")
            return False
        
        if individual_configs:
            logger.info(f"\n🎯 Initializing {len(individual_configs)} individual AI trader(s)...")
            for config in individual_configs:
                ai_name = config["ai_name"]
                private_key = config["private_key"]
                
                logger.info(f"\n  Initializing {ai_name}-Solo...")
                
                # Create AI instance
                ai_instance = self._create_ai_instance(ai_name)
                if not ai_instance:
                    error_msg = (
                        f"❌ Unable to create {ai_name} AI instance\n"
                        f"   Possible causes:\n"
                        f"   1. AI model name not supported\n"
                        f"   2. Corresponding API key not configured or invalid\n"
                        f"   Please check {ai_name.upper()}_API_KEY configuration in .env file"
                    )
                    logger.error(error_msg)
                    return False
                
                # Create individual trader
                try:
                    trader = IndividualAITrader(
                        name=f"{ai_name}-Solo",
                        ai_trader=ai_instance,
                        private_key=private_key
                    )
                    await trader.initialize()
                    await trader.update_stats()  # Update initial statistics
                    self.individual_traders.append(trader)
                    logger.info(f"  ✅ {ai_name}-Solo initialization successful")
                except Exception as e:
                    error_msg = (
                        f"❌ {ai_name}-Solo initialization failed: {e}\n"
                        f"   Possible causes:\n"
                        f"   1. Private key format error\n"
                        f"   2. Insufficient account balance\n"
                        f"   3. Network connection issue\n"
                        f"   Please check private key and account status"
                    )
                    logger.error(error_msg)
                    import traceback
                    logger.error(traceback.format_exc())
                    return False
        
        total_participants = len(self.groups) + len(self.individual_traders)
        logger.info(f"\n🚀 System initialization complete! {len(self.groups)} groups + {len(self.individual_traders)} individual traders = {total_participants} total participants")
        return True
    
    def _create_ai_instance(self, ai_name: str):
        """Create AI instance based on AI name"""
        ai_name_lower = ai_name.lower()
        
        if ai_name_lower == "deepseek":
            return DeepSeekTrader(api_key=settings.deepseek_api_key)
        elif ai_name_lower == "claude":
            return ClaudeTrader(api_key=settings.claude_api_key)
        elif ai_name_lower == "grok":
            return GrokTrader(api_key=settings.grok_api_key)
        elif ai_name_lower in ["gpt", "gpt4", "gpt-4"]:
            return GPTTrader(api_key=settings.openai_api_key, model=settings.gpt_model)
        elif ai_name_lower == "gemini":
            return GeminiTrader(api_key=settings.gemini_api_key)
        elif ai_name_lower == "qwen":
            return QwenTrader(api_key=settings.qwen_api_key, use_international=settings.qwen_use_international)
        else:
            return None
    
    async def _sync_and_clean_positions(self, trader, coin: str):
        """
        Sync and clean positions (handle manual operations and residual positions)
        
        Args:
            trader: Platform trader
            coin: Trading symbol
        """
        try:
            # Get actual exchange position
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            actual_position = None
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    if pos['position']['coin'] == coin:
                        size = float(pos['position']['szi'])
                        if size != 0:
                            actual_position = {
                                'coin': coin,
                                'size': abs(size),
                                'side': 'long' if size > 0 else 'short',
                                'entry_px': float(pos['position']['entryPx'])
                            }
                        break
                except Exception as e:
                    logger.warning(f"[{trader.name}] Failed to parse position: {e}")
                    continue
            
            # Get system recorded position
            system_position = trader.auto_trader.positions.get(coin)
            
            # 🔥 Case 1: Exchange has no position but system has record (manual close)
            if not actual_position and system_position:
                logger.warning(f"[{trader.name}] ⚠️  Detected manual position close: {coin}")
                logger.warning(f"[{trader.name}]    System record: {system_position['side'].upper()} {system_position['size']:.8f}")
                logger.warning(f"[{trader.name}]    Exchange actual: No position")
                logger.info(f"[{trader.name}] 🧹 Cleaning up system position record")
                del trader.auto_trader.positions[coin]
            
            # 🔥 Case 2: Exchange has position but system has no record (manual open)
            elif actual_position and not system_position:
                logger.warning(f"[{trader.name}] ⚠️  Detected manual position open: {coin}")
                logger.warning(f"[{trader.name}]    System record: No position")
                logger.warning(f"[{trader.name}]    Exchange actual: {actual_position['side'].upper()} {actual_position['size']:.8f}")
                logger.info(f"[{trader.name}] 📥 Syncing to system record")
                trader.auto_trader.positions[coin] = {
                    'side': actual_position['side'],
                    'entry_price': actual_position['entry_px'],
                    'size': actual_position['size'],
                    'entry_time': datetime.now(),
                    'confidence': 0,
                    'reasoning': 'Manual position detected and synced',
                    'order_id': 'manual'
                }
            
            # 🔥 Case 3: Both have positions but sizes don't match (partial close or residual)
            elif actual_position and system_position:
                size_diff = abs(actual_position['size'] - system_position['size'])
                if size_diff > 0.00001:  # Allow tiny error
                    logger.warning(f"[{trader.name}] ⚠️  Position size mismatch: {coin}")
                    logger.warning(f"[{trader.name}]    System record: {system_position['size']:.8f}")
                    logger.warning(f"[{trader.name}]    Exchange actual: {actual_position['size']:.8f}")
                    logger.warning(f"[{trader.name}]    Difference: {size_diff:.8f}")
                    
                    # 🧹 Check if it's a residual position (less than 2x minimum trade unit)
                    min_size = 0.002  # 2x BTC minimum unit of 0.001
                    if actual_position['size'] < min_size:
                        logger.warning(f"[{trader.name}] 🧹 Detected residual position ({actual_position['size']:.8f} < {min_size})")
                        logger.info(f"[{trader.name}] Attempting to clean residual position...")
                        
                        # Try to close residual position
                        try:
                            platform_name = getattr(trader.client, 'platform_name', 'Unknown')
                            is_buy = (actual_position['side'] == 'short')
                            
                            # Get current price
                            market_data = await trader.client.get_market_data(coin)
                            current_price = market_data['price']
                            
                            if platform_name == 'Aster':
                                # Aster uses market orders
                                order_result = await trader.client.place_order(
                                    coin=coin,
                                    is_buy=is_buy,
                                    size=actual_position['size'],
                                    price=None,
                                    order_type="Market",
                                    reduce_only=True
                                )
                            else:
                                # Other platforms use limit orders
                                order_price = current_price * 1.001 if is_buy else current_price * 0.999
                                order_result = await trader.client.place_order(
                                    coin=coin,
                                    is_buy=is_buy,
                                    size=actual_position['size'],
                                    price=order_price,
                                    order_type="Limit",
                                    reduce_only=True
                                )
                            
                            if order_result.get('status') == 'ok':
                                logger.info(f"[{trader.name}] ✅ Residual position cleaned successfully")
                                # Clear system record
                                if coin in trader.auto_trader.positions:
                                    del trader.auto_trader.positions[coin]
                            else:
                                logger.warning(f"[{trader.name}] ⚠️  Failed to clean residual position: {order_result.get('response')}")
                                # Sync actual size
                                system_position['size'] = actual_position['size']
                        
                        except Exception as e:
                            logger.error(f"[{trader.name}] ❌ Failed to clean residual position: {e}")
                            # Sync actual size
                            system_position['size'] = actual_position['size']
                    else:
                        # Not a residual position, directly sync size
                        logger.info(f"[{trader.name}] 🔄 Syncing position size: {system_position['size']:.8f} → {actual_position['size']:.8f}")
                        system_position['size'] = actual_position['size']
            
            # Case 4: Both have no position (normal)
            # No action needed
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ Failed to sync and clean positions: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def decision_loop(self):
        """Consensus decision loop"""
        loop_count = 0
        trading_symbol = symbol_filter.get_default_symbol()
        
        while self.running:
            try:
                loop_count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"🤖 Consensus Decision Loop #{loop_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*80}")
                
                # Get market data (using the first group's first platform client)
                try:
                    primary_client = self.groups[0].primary_client
                    if not primary_client:
                        logger.error("❌ No available trading client")
                        await asyncio.sleep(30)
                        continue
                    
                    market_data = await primary_client.get_market_data(trading_symbol)
                    current_price = market_data['price']
                    logger.info(f"💰 {trading_symbol} Price: ${current_price:,.2f}")
                    logger.info(f"📈 24h Change: {market_data.get('change_24h', 0):+.2f}%")
                    
                    orderbook_data = await primary_client.get_orderbook(trading_symbol)
                    recent_trades = await primary_client.get_recent_trades(trading_symbol, limit=10)
                except Exception as e:
                    logger.error(f"❌ Failed to get market data: {e}")
                    await asyncio.sleep(30)
                    continue
                
                # ========================================
                # 🎯 Step 1: Let individual AI models make decisions first
                # ========================================
                individual_ai_decisions = {}  # {ai_name: decision_dict}
                
                if self.individual_traders:
                    logger.info(f"\n{'='*80}")
                    logger.info(f"🎯 Step 1: Individual AI Model Decisions ({len(self.individual_traders)} traders)")
                    logger.info(f"{'='*80}")
                    
                    async def get_individual_decision(trader):
                        try:
                            logger.info(f"\n{'─'*80}")
                            logger.info(f"🎯 {trader.name} Starting Individual Decision")
                            logger.info(f"{'─'*80}")
                            
                            # 🔥 Sync exchange actual positions before each decision round
                            for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
                                await self._sync_and_clean_positions(platform_trader, trading_symbol)
                            
                            # Update K-line
                            trader.kline_manager.update_price(
                                price=current_price,
                                volume=market_data.get('volume', 0)
                            )
                            
                            # Get position info
                            first_trader = list(trader.multi_trader.platform_traders.values())[0]
                            position_info = first_trader.auto_trader.positions.get(trading_symbol)
                            
                            # Get AI decision
                            decision, confidence, reasoning = await trader.get_decision(
                                trading_symbol, market_data, orderbook_data, recent_trades, position_info
                            )
                            
                            # Return AI name and decision result
                            return (trader.ai_name, {
                                'ai_name': trader.ai_name,
                                'decision': decision,
                                'confidence': confidence,
                                'reasoning': reasoning,
                                'trader': trader
                            })
                        except Exception as e:
                            logger.error(f"[{trader.name}] ❌ Decision failed: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            return (trader.ai_name, None)
                    
                    # Get all individual AI decisions in parallel
                    results = await asyncio.gather(*[get_individual_decision(trader) for trader in self.individual_traders])
                    
                    # Save decision results
                    for ai_name, result in results:
                        if result:
                            individual_ai_decisions[ai_name] = result
                    
                    logger.info(f"\n✅ Individual AI decisions complete, collected {len(individual_ai_decisions)} decision results")
                
                # ========================================
                # 🎯 Step 2: Based on individual AI decisions, derive Alpha and Beta group consensus
                # ========================================
                logger.info(f"\n{'='*80}")
                logger.info(f"📊 Step 2: Group Consensus Decisions (based on individual AI decision results)")
                logger.info(f"{'='*80}")
                
                # Process groups in parallel (using pre-computed decisions)
                async def process_group(group):
                    try:
                        logger.info(f"\n{'─'*80}")
                        logger.info(f"📊 {group.name} Starting Consensus Decision")
                        logger.info(f"{'─'*80}")
                        
                        # 🔥 Sync exchange actual positions before each decision round (handle manual operations)
                        for platform_name, trader in group.multi_trader.platform_traders.items():
                            await self._sync_and_clean_positions(trader, trading_symbol)
                        
                        # Update K-line
                        group.kline_manager.update_price(
                            price=current_price,
                            volume=market_data.get('volume', 0)
                        )
                        
                        # Get consensus decision (can use position info from any platform)
                        first_trader = list(group.multi_trader.platform_traders.values())[0]
                        position_info = first_trader.auto_trader.positions.get(trading_symbol)
                        
                        # 🎯 Use pre-computed decision results
                        consensus_decision, confidence, summary, ai_votes = await group.get_consensus_decision(
                            trading_symbol, market_data, orderbook_data, recent_trades, position_info,
                            pre_computed_decisions=individual_ai_decisions
                        )
                        
                        # Record decision
                        decision_record = {
                            "time": datetime.now().isoformat(),
                            "decision": str(consensus_decision),
                            "confidence": confidence,
                            "summary": summary,
                            "ai_votes": ai_votes,
                            "price": current_price
                        }
                        group.stats["consensus_decisions"].insert(0, decision_record)
                        group.stats["consensus_decisions"] = group.stats["consensus_decisions"][:100]
                        
                        # Record to global decision history (for frontend display)
                        # ai_votes is a list, each element is {'ai_name': xx, 'decision': xx, ...}
                        votes_count = sum(1 for vote in ai_votes if vote and vote.get('decision') == consensus_decision)
                        
                        # Format AI vote info (for frontend display)
                        formatted_ai_votes = []
                        for vote in ai_votes:
                            if vote:
                                formatted_ai_votes.append({
                                    "ai_name": vote.get('ai_name', 'Unknown'),
                                    "decision": str(vote.get('decision', '')),
                                    "confidence": round(vote.get('confidence', 0), 1),
                                    "reasoning": vote.get('reasoning', '')[:200]  # Limit length
                                })
                        
                        global_decision = {
                            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "group": group.name,
                            "direction": str(consensus_decision),
                            "confidence": round(confidence, 1),
                            "votes": votes_count,
                            "total_ais": len([v for v in ai_votes if v]),  # Filter out None
                            "price": current_price,
                            "platforms": [],
                            "ai_votes": formatted_ai_votes,
                            "summary": summary  # Add consensus summary
                        }
                        self.decision_history.insert(0, global_decision)
                        self.decision_history = self.decision_history[:100]  # Keep recent 100 entries
                        
                        # Execute decision on all platforms
                        await group.execute_decision_on_all_platforms(
                            trading_symbol,
                            consensus_decision,
                            confidence,
                            summary,
                            current_price
                        )
                        
                        # Update statistics
                        await group.update_stats()
                        
                        # Display platform comparison
                        if settings.platform_comparison_enabled:
                            logger.info(f"\n[{group.name}] 📊 Platform Performance Comparison:")
                            comparison = group.stats["platform_comparison"]
                            for platform_stats in comparison.get("platforms", []):
                                logger.info(f"  {platform_stats['name']}: "
                                          f"Balance=${platform_stats['balance']:.2f}, "
                                          f"PnL=${platform_stats['pnl']:+.2f}, "
                                          f"ROI={platform_stats['roi']:+.2f}%, "
                                          f"Win Rate={platform_stats['win_rate']:.1f}%")
                        
                    except Exception as e:
                        logger.error(f"[{group.name}] ❌ Decision execution error: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # Process all groups in parallel
                await asyncio.gather(*[process_group(group) for group in self.groups])
                
                # ========================================
                # 🎯 Step 3: Individual AI traders execute decisions (using Step 1 decision results)
                # ========================================
                logger.info(f"\n{'='*80}")
                logger.info(f"⚡ Step 3: Individual AI Traders Execute Trades (based on Step 1 decisions)")
                logger.info(f"{'='*80}")
                
                # Process all individual AI traders in parallel (execute existing decisions)
                async def process_individual_trader_execution(decision_data):
                    trader = decision_data['trader']
                    try:
                        logger.info(f"\n{'─'*80}")
                        logger.info(f"⚡ {trader.name} Executing Trade Decision")
                        logger.info(f"{'─'*80}")
                        
                        # Get existing decision
                        decision = decision_data['decision']
                        confidence = decision_data['confidence']
                        reasoning = decision_data['reasoning']
                        
                        # Record decision
                        decision_record = {
                            "time": datetime.now().isoformat(),
                            "decision": str(decision),
                            "confidence": confidence,
                            "reasoning": reasoning,
                            "price": current_price
                        }
                        trader.stats["decisions"].insert(0, decision_record)
                        trader.stats["decisions"] = trader.stats["decisions"][:100]
                        
                        # Record to global decision history (for frontend display)
                        global_decision = {
                            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "trader": trader.name,
                            "ai_name": trader.ai_name,
                            "type": "individual",
                            "direction": str(decision),
                            "confidence": round(confidence, 1),
                            "price": current_price,
                            "reasoning": reasoning[:200]  # Limit length
                        }
                        self.decision_history.insert(0, global_decision)
                        self.decision_history = self.decision_history[:100]  # Keep recent 100 entries
                        
                        # Execute decision on all platforms
                        await trader.execute_decision_on_all_platforms(
                            trading_symbol,
                            decision,
                            confidence,
                            reasoning,
                            current_price
                        )
                        
                        # Update statistics
                        await trader.update_stats()
                        
                        # Display platform comparison
                        if settings.platform_comparison_enabled:
                            logger.info(f"\n[{trader.name}] 📊 Platform Performance Comparison:")
                            comparison = trader.stats["platform_comparison"]
                            for platform_stats in comparison.get("platforms", []):
                                logger.info(f"  {platform_stats['name']}: "
                                          f"Balance=${platform_stats['balance']:.2f}, "
                                          f"PnL=${platform_stats['pnl']:+.2f}, "
                                          f"ROI={platform_stats['roi']:+.2f}%, "
                                          f"Win Rate={platform_stats['win_rate']:.1f}%")
                        
                    except Exception as e:
                        logger.error(f"[{trader.name}] ❌ Trade execution error: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # Execute trades for all individual AI traders in parallel
                if individual_ai_decisions:
                    await asyncio.gather(*[
                        process_individual_trader_execution(decision_data) 
                        for decision_data in individual_ai_decisions.values()
                    ])
                
                # Save balance snapshot to Redis
                try:
                    accounts = []
                    # Add group accounts
                    for group in self.groups:
                        for platform_name, trader in group.multi_trader.platform_traders.items():
                            accounts.append({
                                "group": group.name,
                                "platform": platform_name,
                                "type": "group",
                                "balance": trader.stats.get("balance", 0),
                                "pnl": trader.stats.get("pnl", 0),
                                "roi": trader.stats.get("roi", 0),
                                "total_trades": trader.stats.get("total_trades", 0)
                            })
                    
                    # Add individual trader accounts
                    for individual_trader in self.individual_traders:
                        for platform_name, trader in individual_trader.multi_trader.platform_traders.items():
                            accounts.append({
                                "trader": individual_trader.name,
                                "ai_name": individual_trader.ai_name,
                                "platform": platform_name,
                                "type": "individual",
                                "balance": trader.stats.get("balance", 0),
                                "pnl": trader.stats.get("pnl", 0),
                                "roi": trader.stats.get("roi", 0),
                                "total_trades": trader.stats.get("total_trades", 0)
                            })
                    
                    if accounts:
                        redis_manager.save_balance_snapshot(accounts)
                except Exception as e:
                    logger.error(f"Failed to save balance snapshot: {e}")
                
                # Output all account balance summary (helps diagnose insufficient balance issues)
                logger.info(f"\n{'='*80}")
                logger.info(f"💰 Account Balance Summary")
                logger.info(f"{'='*80}")
                
                # Output group accounts
                for group in self.groups:
                    logger.info(f"\n[{group.name}]")
                    for platform_name, trader in group.multi_trader.platform_traders.items():
                        try:
                            account_info = await trader.client.get_account_info()
                            total_balance = float(account_info.get('marginSummary', {}).get('accountValue', 0))
                            available_balance = float(account_info.get('availableBalance', 0))
                            used_margin = total_balance - available_balance
                            positions_count = len(account_info.get('assetPositions', []))
                            
                            logger.info(f"  {platform_name}:")
                            logger.info(f"    Total Balance: ${total_balance:.2f}")
                            logger.info(f"    Available: ${available_balance:.2f}")
                            logger.info(f"    Used: ${used_margin:.2f}")
                            logger.info(f"    Positions: {positions_count}")
                        except Exception as e:
                            logger.warning(f"  {platform_name}: Failed to get balance - {e}")
                
                # Output individual AI trader accounts
                for individual_trader in self.individual_traders:
                    logger.info(f"\n[{individual_trader.name}]")
                    for platform_name, trader in individual_trader.multi_trader.platform_traders.items():
                        try:
                            account_info = await trader.client.get_account_info()
                            total_balance = float(account_info.get('marginSummary', {}).get('accountValue', 0))
                            available_balance = float(account_info.get('availableBalance', 0))
                            used_margin = total_balance - available_balance
                            positions_count = len(account_info.get('assetPositions', []))
                            
                            logger.info(f"  {platform_name}:")
                            logger.info(f"    Total Balance: ${total_balance:.2f}")
                            logger.info(f"    Available: ${available_balance:.2f}")
                            logger.info(f"    Used: ${used_margin:.2f}")
                            logger.info(f"    Positions: {positions_count}")
                        except Exception as e:
                            logger.warning(f"  {platform_name}: Failed to get balance - {e}")
                
                logger.info(f"{'='*80}\n")
                
                logger.info(f"⏰ Waiting {self.update_interval} seconds before next decision round...")
                await asyncio.sleep(self.update_interval)
            
            except asyncio.CancelledError:
                logger.info("⏹️  Decision loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Decision loop error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(30)
    
    async def start(self):
        """Start system"""
        if await self.initialize():
            self.running = True
            logger.info("🚀 Consensus trading system started")
            await self.decision_loop()
    
    async def stop(self):
        """Stop system"""
        self.running = False
        logger.info("🛑 Consensus trading system stopping...")
        
        # Close group clients
        for group in self.groups:
            # Close trading platform clients
            for trader in group.multi_trader.platform_traders.values():
                await trader.client.close_session()
            # Close data source client (if exists)
            if hasattr(group, 'data_source_client') and group.data_source_client:
                await group.data_source_client.close_session()
        
        # Close individual AI trader clients
        for individual_trader in self.individual_traders:
            # Close trading platform clients
            for trader in individual_trader.multi_trader.platform_traders.values():
                await trader.client.close_session()
            # Close data source client (if exists)
            if hasattr(individual_trader, 'data_source_client') and individual_trader.data_source_client:
                await individual_trader.data_source_client.close_session()
        
        logger.info("✅ Consensus trading system stopped")


arena: Optional[ConsensusArena] = None


@app.on_event("startup")
async def startup_event():
    global arena
    arena = ConsensusArena()
    asyncio.create_task(arena.start())


@app.on_event("shutdown")
async def shutdown_event():
    if arena:
        await arena.stop()


def _sanitize_for_json(obj):
    """
    Sanitize data structure to ensure it can be serialized to JSON
    Remove any type annotations or non-serializable objects
    """
    import json
    from enum import Enum
    
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, Enum):
        # Handle Enum types (like TradingDecision)
        return str(obj.value) if hasattr(obj, 'value') else str(obj)
    elif isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        # Try to convert to dict, but filter out methods and private attributes
        try:
            return _sanitize_for_json(obj.__dict__)
        except:
            return str(obj)
    else:
        # For any other type, try to convert to string
        try:
            json.dumps(obj)
            return obj
        except:
            return str(obj)


@app.get("/api/status")
async def get_status():
    """Get system status"""
    if not arena:
        return {"status": "not_started"}
    
    try:
        # Update statistics for all groups and traders (ensure latest data is returned)
        for group in arena.groups:
            await group.update_stats()
        for trader in arena.individual_traders:
            await trader.update_stats()
        
        groups_data = []
        for group in arena.groups:
            group_info = {
                "type": "group",
                "group_name": group.stats.get("group_name", ""),
                "platforms": _sanitize_for_json(group.stats.get("platforms", {})),
                "platform_comparison": _sanitize_for_json(group.stats.get("platform_comparison", {})),
                "consensus_decisions": _sanitize_for_json(group.stats.get("consensus_decisions", []))
            }
            groups_data.append(group_info)
        
        individual_traders_data = []
        for trader in arena.individual_traders:
            # 获取平台地址信息
            platform_addresses = {}
            for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
                if hasattr(platform_trader.client, 'address'):
                    platform_addresses[platform_name] = platform_trader.client.address
            
            trader_info = {
                "type": "individual",
                "trader_name": trader.stats.get("trader_name", ""),
                "ai_name": trader.stats.get("ai_name", ""),
                "platforms": _sanitize_for_json(trader.stats.get("platforms", {})),
                "platform_comparison": _sanitize_for_json(trader.stats.get("platform_comparison", {})),
                "decisions": _sanitize_for_json(trader.stats.get("decisions", [])),
                "addresses": platform_addresses  # 添加地址信息
            }
            individual_traders_data.append(trader_info)
        
        return {
            "status": "running" if arena.running else "stopped",
            "groups": groups_data,
            "individual_traders": individual_traders_data,
            "update_interval": f"{arena.update_interval//60} minute(s)",
            "consensus_rule": f"At least {settings.consensus_min_votes} AIs must agree",
            "enabled_platforms": get_enabled_platforms(),
            "total_participants": len(arena.groups) + len(arena.individual_traders)
        }
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "groups": [],
            "individual_traders": []
        }


@app.get("/api/platform_comparison")
async def get_platform_comparison():
    """Get platform comparison data"""
    if not arena:
        return {"platforms": []}
    
    # Aggregate multi-platform data from all groups
    platform_summary = {}
    
    for group in arena.groups:
        platforms = group.stats.get("platforms", {})
        for platform_name, platform_stats in platforms.items():
            # Extract platform abbreviation (e.g. Hyperliquid or Aster)
            platform_key = "Hyperliquid" if "Hyperliquid" in platform_name else "Aster"
            
            if platform_key not in platform_summary:
                platform_summary[platform_key] = {
                    "platform": platform_key,
                    "total_pnl": 0,
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "initial_balance": 0,
                    "current_balance": 0
                }
            
            summary = platform_summary[platform_key]
            summary["total_pnl"] += platform_stats.get("total_pnl", 0)
            summary["total_trades"] += platform_stats.get("total_trades", 0)
            summary["wins"] += platform_stats.get("total_wins", 0)
            summary["losses"] += platform_stats.get("total_losses", 0)
            summary["initial_balance"] += platform_stats.get("initial_balance", 0)
            summary["current_balance"] += platform_stats.get("current_balance", 0)
    
    # Calculate derived metrics
    platforms_list = []
    for platform_data in platform_summary.values():
        total_trades = platform_data["total_trades"]
        win_rate = (platform_data["wins"] / total_trades * 100) if total_trades > 0 else 0
        roi = (platform_data["total_pnl"] / platform_data["initial_balance"] * 100) if platform_data["initial_balance"] > 0 else 0
        
        platforms_list.append({
            "platform": platform_data["platform"],
            "total_pnl": platform_data["total_pnl"],
            "current_balance": platform_data["current_balance"],
            "initial_balance": platform_data["initial_balance"],
            "roi_percentage": roi,
            "win_rate": win_rate,
            "total_trades": total_trades
        })
    
    return {"platforms": platforms_list}


@app.get("/api/chart")
async def get_chart_data(
    symbol: str = settings.allowed_trading_symbols,
    interval: str = "15m",
    lookback: int = 100
):
    """Get K-line chart data (including multi-platform trade markers)"""
    try:
        if not arena or len(arena.groups) == 0:
            return {"error": "System not started"}
        
        # Get K-line data from first group's first platform
        first_group = arena.groups[0]
        candles = []
        
        if first_group.primary_client:
            candles = await first_group.primary_client.get_candles(
                symbol,
                interval=interval,
                lookback=lookback
            )
        
        # Collect trade markers from all platforms of all groups
        trade_markers = []
        from datetime import datetime
        
        # 1. Collect group trades (Alpha group, Beta group)
        for group in arena.groups:
            group_start_time = group.start_time
            
            # Iterate through all platforms of this group
            for platform_name, platform_stats in group.stats.get("platforms", {}).items():
                for trade in platform_stats.get("trades", []):
                    try:
                        trade_time = datetime.fromisoformat(trade.get("time", ""))
                        
                        # Only show trades after system startup
                        if trade_time < group_start_time:
                            continue
                        
                        timestamp_ms = int(trade_time.timestamp() * 1000)
                        
                        # Use price for open, exit_price for close
                        price = trade.get("price", 0) if trade.get("action") == "open" else trade.get("exit_price", 0)
                        
                        trade_markers.append({
                            "time": timestamp_ms,
                            "price": price,
                            "group": group.stats["group_name"],
                            "platform": platform_name,  # Add platform info
                            "action": trade.get("action", ""),
                            "side": trade.get("side", ""),
                            "size": trade.get("size", 0),
                            "pnl": trade.get("pnl", 0)  # Only close trades have pnl
                        })
                    except:
                        continue
        
        # 2. Collect individual trader trades (DeepSeek-Solo, Claude-Solo, etc.)
        for trader in arena.individual_traders:
            trader_start_time = trader.start_time
            
            # Iterate through all platforms of this trader
            for platform_name, platform_stats in trader.stats.get("platforms", {}).items():
                for trade in platform_stats.get("trades", []):
                    try:
                        trade_time = datetime.fromisoformat(trade.get("time", ""))
                        
                        # Only show trades after system startup
                        if trade_time < trader_start_time:
                            continue
                        
                        timestamp_ms = int(trade_time.timestamp() * 1000)
                        
                        # Use price for open, exit_price for close
                        price = trade.get("price", 0) if trade.get("action") == "open" else trade.get("exit_price", 0)
                        
                        trade_markers.append({
                            "time": timestamp_ms,
                            "price": price,
                            "group": trader.stats["trader_name"],  # Use trader name (e.g. "Grok-Solo")
                            "platform": platform_name,
                            "action": trade.get("action", ""),
                            "side": trade.get("side", ""),
                            "size": trade.get("size", 0),
                            "pnl": trade.get("pnl", 0)  # Only close trades have pnl
                        })
                    except:
                        continue
        
        # 🔍 Count trades by platform
        hl_count = sum(1 for m in trade_markers if 'Hyperliquid' in m.get('platform', ''))
        aster_count = sum(1 for m in trade_markers if 'Aster' in m.get('platform', ''))
        logger.info(f"📊 [K-line Markers] Total: {len(trade_markers)}, Hyperliquid: {hl_count}, Aster: {aster_count}")
        
        return {
            "candles": candles,
            "trade_markers": trade_markers,
            "symbol": symbol,
            "interval": interval
        }
    except Exception as e:
        logger.error(f"Failed to get K-line data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}


@app.get("/leaderboard")
async def get_leaderboard(metric: str = "total_pnl", limit: int = 10):
    """Get AI leaderboard"""
    if not arena:
        return {"rankings": []}
    
    # Collect statistics for all AIs
    ai_stats = []
    
    # Add group AIs (note: group AIs use consensus decisions, PnL not tracked individually)
    for group in arena.groups:
        for ai_trader in group.ai_traders:
            ai_name = ai_trader.__class__.__name__.replace('Trader', '')
            stats = {
                "ai_name": ai_name,
                "type": "group_member",
                "group": group.stats["group_name"],
                "total_pnl": 0,
                "roi_percentage": 0,
                "win_rate": 0,
                "total_trades": 0
            }
            ai_stats.append(stats)
    
    # Add individual AI traders (have actual trading statistics)
    for trader in arena.individual_traders:
        # Aggregate statistics from all platforms for this trader
        total_pnl = 0
        total_trades = 0
        total_wins = 0
        total_initial = 0
        
        for platform_stats in trader.stats.get("platforms", {}).values():
            total_pnl += platform_stats.get("total_pnl", 0)
            total_trades += platform_stats.get("total_trades", 0)
            total_wins += platform_stats.get("total_wins", 0)
            total_initial += platform_stats.get("initial_balance", 0)
        
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        roi = (total_pnl / total_initial * 100) if total_initial > 0 else 0
        
        stats = {
            "ai_name": trader.ai_name,
            "type": "individual",
            "trader": trader.name,
            "total_pnl": total_pnl,
            "roi_percentage": roi,
            "win_rate": win_rate,
            "total_trades": total_trades
        }
        ai_stats.append(stats)
    
    # Sort by metric
    ai_stats.sort(key=lambda x: x.get(metric, 0), reverse=True)
    
    # Add rankings
    for i, stats in enumerate(ai_stats[:limit]):
        stats["rank"] = i + 1
    
    return {"rankings": ai_stats[:limit]}


@app.get("/leaderboard/summary")
async def get_leaderboard_summary():
    """Get leaderboard summary"""
    if not arena:
        return {}
    
    total_trades = 0
    total_pnl = 0
    
    # Collect group data
    for group in arena.groups:
        for platform_stats in group.stats.get("platforms", {}).values():
            total_trades += platform_stats.get("total_trades", 0)
            total_pnl += platform_stats.get("total_pnl", 0)
    
    # Collect individual AI trader data
    for trader in arena.individual_traders:
        for platform_stats in trader.stats.get("platforms", {}).values():
            total_trades += platform_stats.get("total_trades", 0)
            total_pnl += platform_stats.get("total_pnl", 0)
    
    # Calculate total number of AIs (group AIs + individual AIs)
    group_ais = len(arena.groups[0].ai_traders) * len(arena.groups) if arena.groups else 0
    individual_ais = len(arena.individual_traders)
    
    return {
        "total_ais": group_ais + individual_ais,
        "group_ais": group_ais,
        "individual_ais": individual_ais,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "active_groups": len(arena.groups),
        "active_individual_traders": len(arena.individual_traders)
    }


@app.get("/strategies")
async def get_strategies():
    """Get strategy details"""
    if not arena:
        return {"strategies": []}
    
    strategies = []
    
    # Add group AI strategies
    for group in arena.groups:
        for ai_trader in group.ai_traders:
            ai_name = ai_trader.__class__.__name__.replace('Trader', '')
            strategy = {
                "name": ai_name,
                "type": "group_member",
                "group": group.stats["group_name"],
                "status": "active",
                "description": f"{ai_name} AI Trading Strategy (group consensus)"
            }
            strategies.append(strategy)
    
    # Add individual AI trader strategies
    for trader in arena.individual_traders:
        strategy = {
            "name": trader.ai_name,
            "type": "individual",
            "trader": trader.name,
            "status": "active",
            "description": f"{trader.ai_name} AI Trading Strategy (independent decision)"
        }
        strategies.append(strategy)
    
    return {"strategies": strategies}


@app.get("/api/realtime_balance")
async def get_realtime_balance():
    """Get real-time balance for all accounts"""
    if not arena:
        return {"accounts": []}
    
    accounts = []
    
    # Add group accounts
    for group in arena.groups:
        group_name = group.stats["group_name"]
        
        # Get balances for all platforms of this group
        for platform_name, platform_stats in group.stats.get("platforms", {}).items():
            # Extract platform abbreviation (remove group name prefix)
            platform_display = platform_name.replace(f"{group_name}-", "")
            
            account = {
                "type": "group",
                "group": group_name,
                "platform": platform_display,
                "balance": platform_stats.get("balance", 0),
                "initial_balance": platform_stats.get("initial_balance", 0),
                "pnl": platform_stats.get("pnl", 0),
                "roi": platform_stats.get("roi", 0),
                "trades": platform_stats.get("total_trades", 0)
            }
            accounts.append(account)
    
    # Add individual AI trader accounts
    for trader in arena.individual_traders:
        trader_name = trader.stats["trader_name"]
        ai_name = trader.stats["ai_name"]
        
        # Get balances for all platforms of this trader
        for platform_name, platform_stats in trader.stats.get("platforms", {}).items():
            # Extract platform abbreviation (remove trader name prefix)
            platform_display = platform_name.replace(f"{trader_name}-", "")
            
            account = {
                "type": "individual",
                "trader": trader_name,
                "ai_name": ai_name,
                "platform": platform_display,
                "balance": platform_stats.get("balance", 0),
                "initial_balance": platform_stats.get("initial_balance", 0),
                "pnl": platform_stats.get("pnl", 0),
                "roi": platform_stats.get("roi", 0),
                "trades": platform_stats.get("total_trades", 0)
            }
            accounts.append(account)
    
    return {"accounts": accounts}


@app.get("/api/balance_history")
async def get_balance_history(limit: int = -1):
    """Get balance history data (from Redis) - returns all historical data by default"""
    try:
        history = redis_manager.get_balance_history(limit=limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Failed to get balance history: {e}")
        return {"history": [], "count": 0, "error": str(e)}


@app.get("/api/decisions")
async def get_decisions():
    """Get decision history"""
    if not arena:
        return {"decisions": []}
    
    return {"decisions": arena.decision_history}


@app.get("/")
async def root():
    """Root path"""
    from fastapi.responses import FileResponse
    response = FileResponse("web/consensus_arena.html")
    # Disable caching to ensure latest version is always loaded
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.mount("/web", StaticFiles(directory="web"), name="web")


if __name__ == "__main__":
    logger.info(f"🌐 Starting AI Consensus Trading System - Multi-Platform Comparison Version")
    logger.info(f"Enabled platforms: {', '.join(get_enabled_platforms())}")
    logger.info(f"⏱️  Decision cycle: {settings.consensus_interval//60} minute(s)")
    logger.info(f"🎯 Consensus rule: At least {settings.consensus_min_votes} AIs must agree per group")
    logger.info(f"🌐 Frontend page: http://localhost:{settings.api_port}/")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )

