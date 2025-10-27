"""
Trading symbol filter
Used to restrict trading to specified cryptocurrencies only
"""
from typing import List, Optional
from config.settings import settings, get_allowed_symbols, is_symbol_allowed
import logging

logger = logging.getLogger(__name__)


class SymbolFilter:
    """Symbol filter"""
    
    def __init__(self):
        self.allowed_symbols = get_allowed_symbols()
        self._log_configuration()
    
    def _log_configuration(self):
        """Log configuration information"""
        if not self.allowed_symbols:
            logger.info("🌐 Trading symbols: All allowed")
        else:
            logger.info(f"🎯 Trading symbol restrictions: {', '.join(self.allowed_symbols)}")
    
    def is_allowed(self, symbol: str) -> bool:
        """
        Check if symbol is allowed for trading
        
        Args:
            symbol: Symbol code (e.g. BTC, ETH)
            
        Returns:
            Whether trading is allowed
        """
        return is_symbol_allowed(symbol)
    
    def filter_symbols(self, symbols: List[str]) -> List[str]:
        """
        Filter symbol list, keeping only allowed ones
        
        Args:
            symbols: Symbol list
            
        Returns:
            Filtered symbol list
        """
        if not self.allowed_symbols:
            return symbols  # All allowed
        
        filtered = [s for s in symbols if self.is_allowed(s)]
        
        if len(filtered) < len(symbols):
            removed = set(symbols) - set(filtered)
            logger.debug(f"Filtered out disallowed symbols: {', '.join(removed)}")
        
        return filtered
    
    def get_default_symbol(self) -> str:
        """
        Get default trading symbol
        
        Returns:
            Default symbol (returns first allowed symbol if restricted, otherwise returns BTC)
        """
        if self.allowed_symbols:
            return self.allowed_symbols[0]
        return "BTC"
    
    def get_allowed_list(self) -> List[str]:
        """Get list of allowed trading symbols"""
        return self.allowed_symbols.copy() if self.allowed_symbols else []
    
    def validate_symbol(self, symbol: str) -> tuple[bool, Optional[str]]:
        """
        Validate symbol and return error message
        
        Args:
            symbol: Symbol code
            
        Returns:
            (is_valid, error_message)
        """
        symbol_upper = symbol.upper()
        
        if not self.is_allowed(symbol_upper):
            if self.allowed_symbols:
                allowed_str = ', '.join(self.allowed_symbols)
                return False, f"Symbol {symbol_upper} is not in the allowed list. Allowed symbols: {allowed_str}"
            else:
                return False, f"Symbol {symbol_upper} is invalid"
        
        return True, None


# Global instance
symbol_filter = SymbolFilter()


def check_symbol_before_trade(symbol: str) -> bool:
    """
    Check if symbol is allowed before trading (decorator helper function)
    
    Args:
        symbol: Symbol code
        
    Returns:
        Whether trading is allowed
    """
    is_valid, error_msg = symbol_filter.validate_symbol(symbol)
    
    if not is_valid:
        logger.warning(f"⚠️  Trade blocked: {error_msg}")
        return False
    
    return True

