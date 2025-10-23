"""
配置管理模块
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 交易平台配置
    enabled_platforms: str = "hyperliquid,aster"  # 启用的平台，逗号分隔
    
    # Hyperliquid 配置（默认主网）
    hyperliquid_testnet: bool = False
    hyperliquid_api_url: str = "https://api.hyperliquid.xyz"
    
    # Aster 配置（仅支持主网）
    aster_testnet: bool = False
    aster_api_url: str = "https://fapi.asterdex.com"
    
    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 46000
    
    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    balance_history_ttl: int = 86400 * 7  # 7天过期
    
    # 允许交易的币种
    allowed_trading_symbols: str = "BTC"
    
    # AI API Keys
    claude_api_key: str = ""
    openai_api_key: str = ""
    gpt_model: str = "gpt-4o"
    gemini_api_key: str = ""
    qwen_api_key: str = ""
    grok_api_key: str = ""
    deepseek_api_key: str = ""
    
    # AI 交易配置
    ai_initial_balance: float = 240.0  # 根据实际USDC余额设置
    ai_min_margin: float = 120.0  # 最小保证金（U）
    ai_max_margin: float = 240.0  # 最大保证金（U）
    ai_max_leverage: float = 5.0  # 最大杠杆倍数（AI可根据信心度动态调整1-5x）
    
    # 分组共识配置（默认主网）
    group_1_name: str = "Alpha组"
    group_1_ais: str = ""
    group_1_private_key: str = ""
    group_2_name: str = "Beta组"
    group_2_ais: str = ""
    group_2_private_key: str = ""
    consensus_min_votes: int = 2
    consensus_interval: int = 300
    min_confidence: float = 60.0
    
    # 多平台对比模式
    multi_platform_mode: bool = True  # 是否启用多平台对比模式
    platform_comparison_enabled: bool = True  # 是否显示平台对比
    
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


def get_enabled_platforms():
    """获取启用的交易平台列表"""
    if not settings.enabled_platforms:
        return ["hyperliquid"]  # 默认只启用 Hyperliquid
    
    platforms = [p.strip().lower() for p in settings.enabled_platforms.split(',')]
    return [p for p in platforms if p]  # 过滤空字符串


def is_platform_enabled(platform: str) -> bool:
    """检查平台是否启用"""
    enabled = get_enabled_platforms()
    return platform.lower() in enabled


