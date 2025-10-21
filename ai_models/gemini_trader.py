"""
Gemini AI 交易模型
使用 Google Gemini API
"""
import httpx
from typing import Dict, List
from .base_ai import AITradingModel, TradingDecision


class GeminiTrader(AITradingModel):
    """Gemini AI 交易员"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro", **kwargs):
        """
        初始化 Gemini 交易员
        
        Args:
            api_key: Google API 密钥
            model: Gemini 模型版本
        """
        super().__init__(
            model_name=f"Gemini ({model.split('-')[1].capitalize()})",
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict]
    ) -> tuple[TradingDecision, float, str]:
        """
        使用 Gemini 分析市场
        
        Args:
            coin: 币种
            market_data: 市场数据
            orderbook: 订单簿
            recent_trades: 最近交易
            
        Returns:
            (决策, 置信度, 理由)
        """
        position_info = self.positions.get(coin)
        prompt = self.create_market_prompt(coin, market_data, orderbook, position_info)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 500
                        }
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["candidates"][0]["content"]["parts"][0]["text"]
                
                decision, confidence, reasoning = self.parse_ai_response(ai_response)
                self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                
                return decision, confidence, reasoning
            else:
                print(f"Gemini API 错误: {response.status_code}")
                return TradingDecision.HOLD, 0.0, f"API 调用失败"
        
        except Exception as e:
            print(f"Gemini 分析失败: {e}")
            return TradingDecision.HOLD, 0.0, f"分析异常: {str(e)}"

