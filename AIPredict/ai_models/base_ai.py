"""
AI 模型基类
用于调用真实的 AI API 进行交易决策
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradingDecision(Enum):
    """交易决策"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class AITradingModel(ABC):
    """AI 交易模型基类"""
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        initial_balance: float = 1000.0,
        max_position_size: float = 200.0
    ):
        """
        初始化 AI 模型
        
        Args:
            model_name: 模型名称
            api_key: API 密钥
            initial_balance: 初始资金
            max_position_size: 最大仓位大小
        """
        self.model_name = model_name
        self.api_key = api_key
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_position_size = max_position_size
        
        # 交易状态
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.total_trades = 0
        self.winning_trades = 0
        
        # AI 响应记录
        self.ai_responses: List[Dict] = []
        
        # 从 Redis 加载历史响应
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
        分析市场并做出交易决策
        
        Args:
            coin: 币种
            market_data: 市场数据（价格、成交量等）
            orderbook: 订单簿数据
            recent_trades: 最近的交易记录
            
        Returns:
            (决策, 置信度, 理由说明)
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
        创建市场分析提示词
        
        Args:
            coin: 币种
            market_data: 市场数据
            orderbook: 订单簿
            position_info: 当前持仓信息
            
        Returns:
            提示词文本
        """
        # 支持多种字段名（Hyperliquid 原始 API 和规范化字段名）
        current_price = float(market_data.get("price", market_data.get("markPx", market_data.get("mark_price", 0))))
        funding_rate = float(market_data.get("funding_rate", market_data.get("funding", 0)))
        volume_24h = float(market_data.get("volume", market_data.get("dayNtlVlm", 0)))
        open_interest = float(market_data.get("open_interest", market_data.get("openInterest", 0)))
        
        # 获取订单簿深度（新格式：{"bids": [...], "asks": [...]}）
        bids = orderbook.get("bids", [])[:5] if orderbook else []
        asks = orderbook.get("asks", [])[:5] if orderbook else []
        
        # 24h涨跌幅
        change_24h = market_data.get("change_24h", 0)
        
        # 基础市场信息
        prompt = f"""You are a cryptocurrency futures trading expert. Please analyze the following market data and provide trading advice.

Asset: {coin}
Current Price: ${current_price:,.2f}
24h Change: {change_24h:+.2f}%
24h Volume: ${volume_24h:,.0f}
Funding Rate: {funding_rate * 100:.4f}%
Open Interest: ${open_interest:,.0f}
"""
        
        # 如果有K线历史数据，添加时间序列分析
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
        
        # 订单簿数据
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
        """格式化订单簿档位"""
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
        解析 AI 响应
        
        Args:
            response: AI 模型的响应文本
            
        Returns:
            (决策, 置信度, 理由)
        """
        decision = TradingDecision.HOLD
        confidence = 50.0
        reasoning = "Unable to parse AI response"
        
        try:
            response_text = response.strip()
            
            # 尝试提取 DECISION
            if 'DECISION:' in response_text:
                decision_line = response_text.split('DECISION:')[1].split('\n')[0].strip()
                decision_str = decision_line.upper()
                
                try:
                    # 移除可能的末尾空格和标点
                    decision_str = decision_str.strip().rstrip('.,;')
                    decision = TradingDecision(decision_str.lower())
                except ValueError:
                    # 尝试匹配部分文本
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
            
            # 尝试提取 CONFIDENCE
            if 'CONFIDENCE:' in response_text:
                conf_line = response_text.split('CONFIDENCE:')[1].split('\n')[0].strip()
                # 提取数字
                import re
                numbers = re.findall(r'\d+\.?\d*', conf_line)
                if numbers:
                    confidence = float(numbers[0])
                    confidence = max(0.0, min(100.0, confidence))
            
            # 尝试提取 REASONING（支持多行）
            if 'REASONING:' in response_text:
                reasoning_part = response_text.split('REASONING:')[1]
                # 取到下一个大写字段或结束
                reasoning_lines = []
                for line in reasoning_part.split('\n'):
                    # 如果遇到markdown标题或新的大写字段，停止
                    if line.strip().startswith('#') or (line.isupper() and ':' in line):
                        break
                    reasoning_lines.append(line.strip())
                
                reasoning = ' '.join(reasoning_lines).strip()
                
                # 如果太长，截取前200个字符
                if len(reasoning) > 200:
                    reasoning = reasoning[:200] + '...'
        
        except Exception as e:
            print(f"解析 AI 响应时出错: {e}")
        
        return decision, confidence, reasoning
    
    def calculate_position_size(
        self,
        decision: TradingDecision,
        confidence: float,
        current_price: float
    ) -> float:
        """
        根据决策和置信度计算仓位大小
        
        Args:
            decision: 交易决策
            confidence: 置信度 (0-100)
            current_price: 当前价格
            
        Returns:
            仓位大小（USD）
        """
        if decision == TradingDecision.HOLD:
            return 0.0
        
        # 基础仓位比例
        base_ratio = 0.1  # 10%
        
        # 根据决策强度调整
        if decision in [TradingDecision.STRONG_BUY, TradingDecision.STRONG_SELL]:
            base_ratio = 0.15  # 15%
        
        # 根据置信度调整
        confidence_multiplier = confidence / 100.0
        
        # 计算仓位大小
        position_value = self.current_balance * base_ratio * confidence_multiplier
        position_value = min(position_value, self.max_position_size)
        
        return position_value
    
    def _load_responses_from_redis(self):
        """从 Redis 加载历史响应"""
        try:
            from utils.redis_manager import redis_manager
            
            if redis_manager.is_connected():
                responses = redis_manager.get_ai_responses(self.model_name, limit=100)
                if responses:
                    self.ai_responses = responses
                    logger.info(f"✅ 从 Redis 加载 {self.model_name} 的历史响应: {len(responses)} 条")
                else:
                    logger.info(f"📭 {self.model_name} 没有历史响应")
            else:
                logger.warning(f"⚠️  Redis 未连接，{self.model_name} 无法加载历史响应")
        except Exception as e:
            logger.error(f"从 Redis 加载 {self.model_name} 响应失败: {e}")
    
    def record_ai_response(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        raw_response: str
    ):
        """记录 AI 响应并保存到 Redis"""
        response = {
            "timestamp": datetime.now().isoformat(),
            "coin": coin,
            "decision": decision.value,
            "confidence": confidence,
            "reasoning": reasoning,
            "raw_response": raw_response
        }
        
        self.ai_responses.append(response)
        
        # 只保留最近 100 条
        if len(self.ai_responses) > 100:
            self.ai_responses = self.ai_responses[-100:]
        
        # 保存到 Redis
        try:
            from utils.redis_manager import redis_manager
            if redis_manager.is_connected():
                redis_manager.append_ai_response(self.model_name, response)
        except Exception as e:
            logger.error(f"保存 {self.model_name} 响应到 Redis 失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
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

