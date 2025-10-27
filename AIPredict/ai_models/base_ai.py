"""
AI Model Base Class
Used to call real AI APIs for trading decisions
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradingDecision(Enum):
    """Trading Decision"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class AITradingModel(ABC):
    """AI Trading Model Base Class"""
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        initial_balance: float = 1000.0,
        max_position_size: float = 200.0
    ):
        """
        Initialize AI Model
        
        Args:
            model_name: Model name
            api_key: API key
            initial_balance: Initial balance
            max_position_size: Maximum position size
        """
        self.model_name = model_name
        self.api_key = api_key
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_position_size = max_position_size
        
        # Trading state
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.total_trades = 0
        self.winning_trades = 0
        
        # AI response records
        self.ai_responses: List[Dict] = []
        
        # Load historical responses from Redis
        self._load_responses_from_redis()
    
    @abstractmethod
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        Analyze market and make trading decision
        
        Args:
            coin: Coin symbol
            market_data: Market data (price, volume, etc.)
            orderbook: Orderbook data
            recent_trades: Recent trade records
            
        Returns:
            (decision, confidence, reasoning)
        """
        pass
    
    def create_market_prompt(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        position_info: Optional[Dict] = None,
        kline_history: str = None
    ) -> str:
        """
        Create market analysis prompt
        
        Args:
            coin: Coin symbol
            market_data: Market data
            orderbook: Orderbook
            position_info: Current position info
            
        Returns:
            Prompt text
        """
        # Support multiple field names (Hyperliquid original API and normalized field names)
        current_price = float(market_data.get("price", market_data.get("markPx", market_data.get("mark_price", 0))))
        funding_rate = float(market_data.get("funding_rate", market_data.get("funding", 0)))
        volume_24h = float(market_data.get("volume", market_data.get("dayNtlVlm", 0)))
        open_interest = float(market_data.get("open_interest", market_data.get("openInterest", 0)))
        
        # Get orderbook depth (new format: {"bids": [...], "asks": [...]})
        bids = orderbook.get("bids", [])[:5] if orderbook else []
        asks = orderbook.get("asks", [])[:5] if orderbook else []
        
        # 24h change
        change_24h = market_data.get("change_24h", 0)
        
        # Basic market information
        prompt = f"""You are a cryptocurrency futures trading expert. Please analyze the following market data and provide trading advice.

Asset: {coin}
Current Price: ${current_price:,.2f}
24h Change: {change_24h:+.2f}%
24h Volume: ${volume_24h:,.0f}
Funding Rate: {funding_rate * 100:.4f}%
Open Interest: ${open_interest:,.0f}
"""
        
        # If K-line history data exists, add time series analysis
        if kline_history:
            prompt += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Intraday Price Time Series (15-minute Candles)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{kline_history}

Based on the above time series, you can:
• Identify price trends and momentum
• Assess validity of support and resistance levels
• Discover price patterns (breakouts, pullbacks, etc.)
• Evaluate current price position within the range
"""
        
        # Orderbook data
        prompt += f"""

Order Book (Top 5 Levels):
Bids:
{self._format_orderbook_levels(bids)}

Asks:
{self._format_orderbook_levels(asks)}
"""
        
        if position_info:
            entry_price = position_info.get("entry_price", 0)
            size = position_info.get("size", 0)
            pnl = (current_price - entry_price) * size
            pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            
            prompt += f"""
Current Position:
- Entry Price: ${entry_price:,.2f}
- Position Size: {size:.4f} {coin}
- Unrealized PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)
"""
        else:
            prompt += f"""
Current Position: None

Available Balance: ${self.current_balance:,.2f}
Max Position Size: ${self.max_position_size:,.2f}
"""
        
        prompt += """
⚡ Aggressive Swing Trading Strategy - Pursuing Greater Profit Potential ⚡

Your goal is to be an **aggressive swing trader**, achieving high returns through medium-to-high win rate.

Trading Philosophy:
• Stop Loss 15% / Take Profit 30%, Risk-Reward Ratio 1:2
• Only open positions when confidence ≥50% (strict quality control)
• Give trends enough room to develop, don't get shaken out by minor fluctuations
• Pursue higher win rate, reduce frequent stop losses
• Wider stop loss space allows capturing larger trends

Please Analyze:
1. Short-term price trend (rising/falling/ranging)
2. Order book buy/sell power comparison
3. Funding rate (positive = bulls strong, negative = bears strong)
4. Volume and momentum
5. Whether there's 15-30% volatility space (matching stop loss/take profit)

Decision Guidelines:
• Strong bullish signals (clear trend + strong buying pressure) → STRONG_BUY (confidence ≥70%)
• Moderate bullish signals (slight uptrend + buying advantage) → BUY (confidence 50-70%)
• Strong bearish signals (clear trend + strong selling pressure) → STRONG_SELL (confidence ≥70%)
• Moderate bearish signals (slight downtrend + selling advantage) → SELL (confidence 50-70%)
• Completely uncertain / dead market / extreme volatility → HOLD (confidence <50%)

⚠️ Quality Control: Only open positions when confidence ≥50%!
When confidence is below 50%, choose HOLD and wait for better opportunities.

Response Format (strictly follow this format):
DECISION: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL]
CONFIDENCE: [number from 0-100]
REASONING: [your analysis reasoning, 50-100 words]
"""
        
        return prompt
    
    def _format_orderbook_levels(self, levels: List) -> str:
        """Format orderbook levels"""
        if not levels:
            return "  No data"
        
        result = []
        for level in levels[:5]:
            if isinstance(level, dict):
                price = level.get("px", 0)
                size = level.get("sz", 0)
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                price = level[0]
                size = level[1]
            else:
                continue
            result.append(f"  Price: ${float(price):,.2f}, Amount: {float(size):.4f}")
        
        return "\n".join(result) if result else "  No data"
    
    def parse_ai_response(self, response: str) -> tuple[TradingDecision, float, str]:
        """
        Parse AI response
        
        Args:
            response: Response text from AI model
            
        Returns:
            (decision, confidence, reasoning)
        """
        decision = TradingDecision.HOLD
        confidence = 50.0
        reasoning = "Unable to parse AI response"
        
        try:
            response_text = response.strip()
            
            # Try to extract DECISION
            if 'DECISION:' in response_text:
                decision_line = response_text.split('DECISION:')[1].split('\n')[0].strip()
                decision_str = decision_line.upper()
                
                try:
                    # Remove possible trailing spaces and punctuation
                    decision_str = decision_str.strip().rstrip('.,;')
                    decision = TradingDecision(decision_str.lower())
                except ValueError:
                    # Try to match partial text
                    if 'STRONG_BUY' in decision_str or 'STRONG BUY' in decision_str:
                        decision = TradingDecision.STRONG_BUY
                    elif 'STRONG_SELL' in decision_str or 'STRONG SELL' in decision_str:
                        decision = TradingDecision.STRONG_SELL
                    elif 'BUY' in decision_str:
                        decision = TradingDecision.BUY
                    elif 'SELL' in decision_str:
                        decision = TradingDecision.SELL
                    else:
                        decision = TradingDecision.HOLD
            
            # Try to extract CONFIDENCE
            if 'CONFIDENCE:' in response_text:
                conf_line = response_text.split('CONFIDENCE:')[1].split('\n')[0].strip()
                # Extract numbers
                import re
                numbers = re.findall(r'\d+\.?\d*', conf_line)
                if numbers:
                    confidence = float(numbers[0])
                    confidence = max(0.0, min(100.0, confidence))
            
            # Try to extract REASONING (support multi-line)
            if 'REASONING:' in response_text:
                reasoning_part = response_text.split('REASONING:')[1]
                # Read until next uppercase field or end
                reasoning_lines = []
                for line in reasoning_part.split('\n'):
                    # Stop if markdown heading or new uppercase field
                    if line.strip().startswith('#') or (line.isupper() and ':' in line):
                        break
                    reasoning_lines.append(line.strip())
                
                reasoning = ' '.join(reasoning_lines).strip()
                
                # If too long, truncate to 200 characters
                if len(reasoning) > 200:
                    reasoning = reasoning[:200] + '...'
        
        except Exception as e:
            print(f"Error parsing AI response: {e}")
        
        return decision, confidence, reasoning
    
    def calculate_position_size(
        self,
        decision: TradingDecision,
        confidence: float,
        current_price: float
    ) -> float:
        """
        Calculate position size based on decision and confidence
        
        Args:
            decision: Trading decision
            confidence: Confidence level (0-100)
            current_price: Current price
            
        Returns:
            Position size (USD)
        """
        if decision == TradingDecision.HOLD:
            return 0.0
        
        # Base position ratio
        base_ratio = 0.1  # 10%
        
        # Adjust based on decision strength
        if decision in [TradingDecision.STRONG_BUY, TradingDecision.STRONG_SELL]:
            base_ratio = 0.15  # 15%
        
        # Adjust based on confidence
        confidence_multiplier = confidence / 100.0
        
        # Calculate position size
        position_value = self.current_balance * base_ratio * confidence_multiplier
        position_value = min(position_value, self.max_position_size)
        
        return position_value
    
    def _load_responses_from_redis(self):
        """Load historical responses from Redis"""
        try:
            from utils.redis_manager import redis_manager
            
            if redis_manager.is_connected():
                responses = redis_manager.get_ai_responses(self.model_name, limit=100)
                if responses:
                    self.ai_responses = responses
                    logger.info(f"✅ Loaded {len(responses)} historical responses for {self.model_name} from Redis")
                else:
                    logger.info(f"📭 No historical responses for {self.model_name}")
            else:
                logger.warning(f"⚠️  Redis not connected, unable to load historical responses for {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load {self.model_name} responses from Redis: {e}")
    
    def record_ai_response(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        raw_response: str
    ):
        """Record AI response and save to Redis"""
        response = {
            "timestamp": datetime.now().isoformat(),
            "coin": coin,
            "decision": decision.value,
            "confidence": confidence,
            "reasoning": reasoning,
            "raw_response": raw_response
        }
        
        self.ai_responses.append(response)
        
        # Keep only the last 100 entries
        if len(self.ai_responses) > 100:
            self.ai_responses = self.ai_responses[-100:]
        
        # Log complete response to log file
        logger.info(f"""
{'='*80}
🤖 AI Model: {self.model_name}
{'='*80}
📊 Coin: {coin}
⏰ Timestamp: {response['timestamp']}
🎯 Decision: {decision.value.upper()}
📈 Confidence: {confidence:.2f}%
💭 Reasoning: {reasoning}
{'─'*80}
📝 Raw Response:
{raw_response}
{'='*80}
""")
        
        # Save to Redis
        try:
            from utils.redis_manager import redis_manager
            if redis_manager.is_connected():
                redis_manager.append_ai_response(self.model_name, response)
        except Exception as e:
            logger.error(f"Failed to save {self.model_name} response to Redis: {e}")
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        total_pnl = self.current_balance - self.initial_balance
        roi = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        return {
            "model_name": self.model_name,
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "total_pnl": total_pnl,
            "roi_percentage": roi,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate": win_rate,
            "active_positions": len(self.positions),
            "recent_decisions": self.ai_responses[-5:] if self.ai_responses else []
        }

