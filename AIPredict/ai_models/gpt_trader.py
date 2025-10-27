"""
GPT AI Trading Model
Uses OpenAI GPT API
"""
import httpx
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision


class GPTTrader(AITradingModel):
    """GPT AI Trader"""
    
    def __init__(self, api_key: str, model: str = "gpt-5", **kwargs):
        """
        Initialize GPT Trader
        
        Args:
            api_key: OpenAI API key
            model: GPT model version
        """
        super().__init__(
            model_name=f"GPT-5 Mini" if "mini" in model.lower() else (f"GPT-5" if model.startswith("gpt-5") else f"GPT-4 ({model.split('-')[1]})"),
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        Analyze market using GPT
        
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
                                "role": "system",
                                "content": "You are a professional cryptocurrency futures trading analyst."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_completion_tokens": 2000
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                decision, confidence, reasoning = self.parse_ai_response(ai_response)
                self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                
                return decision, confidence, reasoning
            else:
                print(f"GPT API error: {response.status_code}")
                return TradingDecision.HOLD, 0.0, f"API call failed"
        
        except Exception as e:
            print(f"GPT analysis failed: {e}")
            return TradingDecision.HOLD, 0.0, f"Analysis error: {str(e)}"

