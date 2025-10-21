"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # Hyperliquid Configuration
    hyperliquid_private_key: str = ""
    hyperliquid_testnet: bool = True
    hyperliquid_api_url: str = "https://api.hyperliquid-testnet.xyz"
    
    # Database Configuration
    database_url: str = "postgresql://localhost:5432/aitrading"
    redis_url: str = "redis://localhost:6379/0"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "your-secret-key-change-this"
    
    # Trading Configuration
    max_position_size: float = 1000.0  # USD
    max_leverage: int = 5
    stop_loss_percentage: float = 5.0
    take_profit_percentage: float = 10.0
    
    # Arena Configuration
    arena_update_interval: int = 60  # seconds
    leaderboard_size: int = 50
    
    # Risk Management
    daily_loss_limit: float = 500.0  # USD
    max_open_positions: int = 5
    min_account_balance: float = 100.0  # USD
    
    # 允许交易的币种（用逗号分隔，留空表示全部允许）
    allowed_trading_symbols: str = "BTC"  # 例如: "BTC,ETH,SOL"
    
    # AI 配置
    claude_api_key: str = ""
    openai_api_key: str = ""
    gpt_model: str = "gpt-4o"
    gemini_api_key: str = ""
    qwen_api_key: str = ""
    grok_api_key: str = ""
    deepseek_api_key: str = ""
    ai_initial_balance: float = 1000.0
    ai_max_position_size: float = 200.0
    
    # 多地址模式 - 每个 AI 的独立私钥（可选）
    claude_private_key: str = ""
    gpt_private_key: str = ""
    gemini_private_key: str = ""
    qwen_private_key: str = ""
    grok_private_key: str = ""
    deepseek_private_key: str = ""
    
    # 共识模式分组私钥（可选）
    group_a_private_key: str = ""
    group_b_private_key: str = ""
    
    # 共识模式 AI 分组配置（可选，留空则使用默认分组）
    # 格式：用逗号分隔的AI名称，可选值：claude,gpt4,gemini,qwen,grok,deepseek
    group_a_members: str = "claude,gpt4,gemini"  # 默认：国际AI组
    group_b_members: str = "qwen,grok,deepseek"  # 默认：国产AI组
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_allowed_symbols():
    """获取允许交易的币种列表"""
    if not settings.allowed_trading_symbols:
        return []  # 空列表表示全部允许
    
    symbols = [s.strip().upper() for s in settings.allowed_trading_symbols.split(',')]
    return [s for s in symbols if s]  # 过滤空字符串


def is_symbol_allowed(symbol: str) -> bool:
    """检查币种是否允许交易"""
    allowed = get_allowed_symbols()
    if not allowed:  # 空列表表示全部允许
        return True
    return symbol.upper() in allowed


