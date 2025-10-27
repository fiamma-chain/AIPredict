"""
Configuration Management Module
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Configuration"""
    
    # Trading platform configuration
    enabled_platforms: str = "hyperliquid,aster"  # Enabled platforms, comma-separated
    
    # Hyperliquid configuration (mainnet by default)
    hyperliquid_testnet: bool = False
    hyperliquid_api_url: str = "https://api.hyperliquid.xyz"
    
    # Aster configuration (mainnet only)
    aster_testnet: bool = False
    aster_api_url: str = "https://fapi.asterdex.com"
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 46000
    
    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    balance_history_ttl: int = 86400 * 7  # 7 days expiration
    
    # Allowed trading symbols
    allowed_trading_symbols: str = "BTC"
    
    # AI API Keys
    claude_api_key: str = ""
    openai_api_key: str = ""
    gpt_model: str = "gpt-4o"
    gemini_api_key: str = ""
    qwen_api_key: str = ""
    qwen_use_international: bool = True  # Whether to use Alibaba Cloud International version (True=International, False=China)
    grok_api_key: str = ""
    deepseek_api_key: str = ""
    
    # AI Trading configuration
    ai_initial_balance: float = 1000.0  # Group account initial balance (Alpha and Beta groups)
    individual_ai_initial_balance: float = 1000.0  # Individual AI trader initial balance
    ai_min_margin: float = 200.0  # Minimum margin (USDT)
    ai_max_margin: float = 500.0  # Maximum margin (USDT)
    ai_min_leverage: float = 5.0  # Minimum leverage (AI adjusts dynamically based on confidence)
    ai_max_leverage: float = 20.0  # Maximum leverage (AI adjusts dynamically 5-20x based on confidence)
    ai_stop_loss_pct: float = 0.02  # Stop loss percentage 2% (short-term strategy)
    ai_take_profit_pct: float = 0.03  # Take profit percentage 3% (short-term strategy)
    
    # Group consensus configuration (mainnet by default)
    group_1_name: str = "Alpha Group"
    group_1_ais: str = ""
    group_1_private_key: str = ""
    group_2_name: str = "Beta Group"
    group_2_ais: str = ""
    group_2_private_key: str = ""
    consensus_min_votes: int = 2
    consensus_interval: int = 300
    min_confidence: float = 60.0
    
    # Multi-platform comparison mode
    multi_platform_mode: bool = True  # Whether to enable multi-platform comparison mode
    platform_comparison_enabled: bool = True  # Whether to display platform comparison
    
    # Individual AI trader private key configuration (optional, for AI Arena mode)
    # If a private key is configured, the AI will start as an independent trader
    # Leave empty to not enable this AI as an independent trader
    individual_deepseek_private_key: str = ""
    individual_claude_private_key: str = ""
    individual_grok_private_key: str = ""
    individual_gpt_private_key: str = ""
    individual_gemini_private_key: str = ""
    individual_qwen_private_key: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global configuration instance
settings = Settings()


def get_allowed_symbols():
    """Get list of allowed trading symbols"""
    if not settings.allowed_trading_symbols:
        return []  # Empty list means all allowed
    
    symbols = [s.strip().upper() for s in settings.allowed_trading_symbols.split(',')]
    return [s for s in symbols if s]  # Filter empty strings


def is_symbol_allowed(symbol: str) -> bool:
    """Check if symbol is allowed for trading"""
    allowed = get_allowed_symbols()
    if not allowed:  # Empty list means all allowed
        return True
    return symbol.upper() in allowed


def get_enabled_platforms():
    """Get list of enabled trading platforms"""
    if not settings.enabled_platforms:
        return ["hyperliquid"]  # Default only enable Hyperliquid
    
    platforms = [p.strip().lower() for p in settings.enabled_platforms.split(',')]
    return [p for p in platforms if p]  # Filter empty strings


def is_platform_enabled(platform: str) -> bool:
    """Check if platform is enabled"""
    enabled = get_enabled_platforms()
    return platform.lower() in enabled


def get_individual_traders_config():
    """
    Get individual AI trader configuration
    
    Returns:
        List[Dict]: [{"ai_name": "DeepSeek", "private_key": "0x123"}, ...]
    
    Raises:
        ValueError: If private key is configured but has invalid format
    """
    traders = []
    
    # AI model configuration mapping
    ai_configs = [
        ("DeepSeek", settings.individual_deepseek_private_key),
        ("Claude", settings.individual_claude_private_key),
        ("Grok", settings.individual_grok_private_key),
        ("GPT", settings.individual_gpt_private_key),
        ("Gemini", settings.individual_gemini_private_key),
        ("Qwen", settings.individual_qwen_private_key),
    ]
    
    for ai_name, private_key in ai_configs:
        if private_key and private_key.strip():
            private_key = private_key.strip()
            
            # Validate private key format
            if not private_key.startswith('0x'):
                raise ValueError(
                    f"❌ {ai_name} independent trader private key format error: must start with '0x'\n"
                    f"   Config item: INDIVIDUAL_{ai_name.upper()}_PRIVATE_KEY"
                )
            
            if len(private_key) != 66:  # 0x + 64 hex characters
                raise ValueError(
                    f"❌ {ai_name} independent trader private key format error: length must be 66 characters (0x + 64 hex)\n"
                    f"   Config item: INDIVIDUAL_{ai_name.upper()}_PRIVATE_KEY\n"
                    f"   Current length: {len(private_key)}"
                )
            
            traders.append({
                "ai_name": ai_name,
                "private_key": private_key
            })
    
    return traders


