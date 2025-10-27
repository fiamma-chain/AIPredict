"""
Qwen AI Trading Model
Uses Alibaba Cloud Tongyi Qianwen API
Supports both China and International versions
"""
import httpx
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision


class QwenTrader(AITradingModel):
    """Qwen AI Trader"""
    
    def __init__(self, api_key: str, model: str = "qwen-max", use_international: bool = True, **kwargs):
        """
        Initialize Qwen Trader
        
        Args:
            api_key: Alibaba Cloud API key
            model: Qwen model version (default: qwen-max = Qwen3-MAX)
            use_international: Whether to use international version (True=International, False=China)
        """
        # Format model name display
        if "max" in model.lower():
            display_name = "Qwen (Max)"
        elif "turbo" in model.lower():
            display_name = "Qwen (Turbo)"
        elif "plus" in model.lower():
            display_name = "Qwen (Plus)"
        else:
            display_name = f"Qwen ({model.split('-')[-1].capitalize()})"
        
        super().__init__(
            model_name=display_name,
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.use_international = use_international
        
        # Select API endpoint based on version
        if use_international:
            # Alibaba Cloud International API
            self.api_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        else:
            # Alibaba Cloud China API
            self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        Analyze market using Qwen
        
        Args:
            coin: Coin symbol
            market_data: Market data
            orderbook: Order book
            recent_trades: Recent trades
            
        Returns:
            (decision, confidence, reasoning)
        """
        position_info = self.positions.get(coin)
        prompt = self.create_market_prompt(coin, market_data, orderbook, position_info)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                decision, confidence, reasoning = self.parse_ai_response(ai_response)
                self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                
                return decision, confidence, reasoning
            else:
                error_detail = response.text
                print(f"Qwen API error: {response.status_code} - {error_detail}")
                return TradingDecision.HOLD, 0.0, f"API call failed"
        
        except Exception as e:
            print(f"Qwen analysis failed: {e}")
            return TradingDecision.HOLD, 0.0, f"Analysis error: {str(e)}"

