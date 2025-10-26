"""
Claude AI 交易模型
使用 Anthropic Claude API
"""
import httpx
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision


class ClaudeTrader(AITradingModel):
    """Claude AI 交易员"""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5", **kwargs):
        """
        初始化 Claude 交易员
        
        Args:
            api_key: Anthropic API 密钥
            model: Claude 模型版本
        """
        super().__init__(
            model_name=f"Claude ({model.split('-')[2]})",
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        使用 Claude 分析市场
        
        Args:
            coin: 币种
            market_data: 市场数据
            orderbook: 订单簿
            recent_trades: 最近交易
            
        Returns:
            (决策, 置信度, 理由)
        """
        # 获取当前持仓信息
        position_info = self.positions.get(coin)
        
        # 创建提示词
        prompt = self.create_market_prompt(coin, market_data, orderbook, position_info)
        
        try:
            # 调用 Claude API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 500,
                        "temperature": 0.7,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["content"][0]["text"]
                
                # Parse response
                decision, confidence, reasoning = self.parse_ai_response(ai_response)
                
                # Record response
                self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                
                return decision, confidence, reasoning
            else:
                print(f"Claude API error: {response.status_code} - {response.text}")
                return TradingDecision.HOLD, 0.0, f"API call failed: {response.status_code}"
        
        except Exception as e:
            print(f"Claude analysis failed: {e}")
            return TradingDecision.HOLD, 0.0, f"Analysis error: {str(e)}"

