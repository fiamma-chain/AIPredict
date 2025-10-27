"""
Grok AI Trading Model
Uses xAI Grok API
"""
import httpx
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision


class GrokTrader(AITradingModel):
    """Grok AI Trader"""
    
    def __init__(self, api_key: str, model: str = "grok-4", **kwargs):
        """
        Initialize Grok Trader
        
        Args:
            api_key: xAI API key
            model: Grok model version
        """
        super().__init__(
            model_name=f"Grok ({model.split('-')[1].capitalize() if '-' in model else 'Beta'})",
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.api_url = "https://api.x.ai/v1/chat/completions"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        Analyze market using Grok
        
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
        
        # Add retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:  # Increased timeout
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
                            "temperature": 0.7,
                            "max_tokens": 500
                        }
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result["choices"][0]["message"]["content"]
                    
                    decision, confidence, reasoning = self.parse_ai_response(ai_response)
                    self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                    
                    if attempt > 0:
                        print(f"✅ Grok API retry succeeded (attempt {attempt+1})")
                    
                    return decision, confidence, reasoning
                else:
                    error_detail = response.text
                    print(f"❌ Grok API error (attempt {attempt+1}/{max_retries}): {response.status_code} - {error_detail[:200]}")
                    
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s
                        continue
                    
                    return TradingDecision.HOLD, 0.0, f"API call failed: {response.status_code}"
            
            except httpx.TimeoutException as e:
                print(f"⏱️ Grok API timeout (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                return TradingDecision.HOLD, 0.0, f"API timeout"
            
            except Exception as e:
                print(f"❌ Grok analysis error (attempt {attempt+1}/{max_retries}): {type(e).__name__}: {str(e)[:200]}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                return TradingDecision.HOLD, 0.0, f"Analysis error: {str(e)[:100]}"
        
        return TradingDecision.HOLD, 0.0, f"Retry failed"

