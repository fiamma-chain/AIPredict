"""
AI 模型配置
"""
from pydantic_settings import BaseSettings


class AIConfig(BaseSettings):
    """AI API 配置"""
    
    # Claude API
    claude_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    # GPT API
    openai_api_key: str = ""
    gpt_model: str = "gpt-4-turbo-preview"
    
    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-pro"
    
    # AI 交易配置
    ai_initial_balance: float = 1000.0
    ai_max_position_size: float = 200.0
    arena_update_interval: int = 300  # 5分钟
    
    class Config:
        env_file = ".env"
        case_sensitive = False


ai_config = AIConfig()

