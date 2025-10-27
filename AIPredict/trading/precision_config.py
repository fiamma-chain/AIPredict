"""
Trading precision configuration module

Unified management of precision requirements for different exchanges and coins
"""
from decimal import Decimal
from typing import Dict, Tuple


class PrecisionConfig:
    """Precision configuration manager"""
    
    # Aster precision configuration
    ASTER_PRECISION = {
        "BTC": {
            "quantity_precision": 3,  # Quantity precision: 3 decimal places
            "price_precision": 1,     # Price precision: 1 decimal place
            "quantity_step": "0.001", # Quantity step size
            "price_tick": "0.1",      # Price tick size
            "min_quantity": "0.001",  # Minimum quantity
            "min_notional": "50"      # Minimum notional value (USDT) - consistent with AI_MIN_POSITION_SIZE
        },
        "ETH": {
            "quantity_precision": 3,
            "price_precision": 2,
            "quantity_step": "0.001",
            "price_tick": "0.01",
            "min_quantity": "0.001",
            "min_notional": "50"      # Minimum notional value (USDT) - consistent with AI_MIN_POSITION_SIZE
        }
    }
    
    # Hyperliquid precision configuration
    HYPERLIQUID_PRECISION = {
        "BTC": {
            "quantity_precision": 5,  # Quantity precision: 5 decimal places
            "price_precision": 0,     # Price precision: integer
            "quantity_step": "0.00001",
            "price_tick": "1",
            "min_quantity": "0.00001",
            "min_notional": "50"      # Minimum notional value (USD) - consistent with AI_MIN_POSITION_SIZE
        },
        "ETH": {
            "quantity_precision": 4,
            "price_precision": 0,
            "quantity_step": "0.0001",
            "price_tick": "1",
            "min_quantity": "0.0001",
            "min_notional": "50"      # Minimum notional value (USD) - consistent with AI_MIN_POSITION_SIZE
        }
    }
    
    @classmethod
    def get_aster_precision(cls, coin: str) -> Dict:
        """
        Get precision configuration for Aster platform
        
        Args:
            coin: Coin symbol (e.g., BTC, ETH)
            
        Returns:
            Precision configuration dictionary
        """
        return cls.ASTER_PRECISION.get(coin, cls.ASTER_PRECISION["BTC"])
    
    @classmethod
    def get_hyperliquid_precision(cls, coin: str) -> Dict:
        """
        Get precision configuration for Hyperliquid platform
        
        Args:
            coin: Coin symbol (e.g., BTC, ETH)
            
        Returns:
            Precision configuration dictionary
        """
        return cls.HYPERLIQUID_PRECISION.get(coin, cls.HYPERLIQUID_PRECISION["BTC"])
    
    @classmethod
    def format_aster_quantity(cls, coin: str, quantity: float, round_down: bool = True) -> Tuple[float, str]:
        """
        Format Aster quantity
        
        Args:
            coin: Coin symbol
            quantity: Original quantity
            round_down: Whether to round down (for opening positions), otherwise round half up (for closing positions)
            
        Returns:
            (Formatted quantity, quantity string)
        """
        from decimal import ROUND_DOWN, ROUND_HALF_UP
        
        config = cls.get_aster_precision(coin)
        step = Decimal(config["quantity_step"])
        
        decimal_qty = Decimal(str(quantity))
        
        if round_down:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_DOWN))
        else:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_HALF_UP))
        
        # Ensure not less than minimum quantity
        min_qty = float(config["min_quantity"])
        if formatted < min_qty and formatted > 0:
            formatted = min_qty
        
        return formatted, str(formatted)
    
    @classmethod
    def format_aster_price(cls, coin: str, price: float) -> Tuple[float, str]:
        """
        Format Aster price
        
        Args:
            coin: Coin symbol
            price: Original price
            
        Returns:
            (Formatted price, price string)
        """
        from decimal import ROUND_HALF_UP
        
        config = cls.get_aster_precision(coin)
        tick = Decimal(config["price_tick"])
        
        decimal_price = Decimal(str(price))
        formatted = float(decimal_price.quantize(tick, rounding=ROUND_HALF_UP))
        
        return formatted, str(formatted)
    
    @classmethod
    def format_hyperliquid_quantity(cls, coin: str, quantity: float, round_down: bool = True) -> Tuple[float, str]:
        """
        Format Hyperliquid quantity
        
        Args:
            coin: Coin symbol
            quantity: Original quantity
            round_down: Whether to round down (for opening positions), otherwise round half up (for closing positions)
            
        Returns:
            (Formatted quantity, quantity string)
        """
        from decimal import ROUND_DOWN, ROUND_HALF_UP
        
        config = cls.get_hyperliquid_precision(coin)
        step = Decimal(config["quantity_step"])
        
        decimal_qty = Decimal(str(quantity))
        
        if round_down:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_DOWN))
        else:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_HALF_UP))
        
        # Ensure not less than minimum quantity
        min_qty = float(config["min_quantity"])
        if formatted < min_qty and formatted > 0:
            formatted = min_qty
        
        return formatted, str(formatted)
    
    @classmethod
    def format_hyperliquid_price(cls, coin: str, price: float) -> Tuple[float, str]:
        """
        Format Hyperliquid price
        
        Args:
            coin: Coin symbol
            price: Original price
            
        Returns:
            (Formatted price, price string)
        """
        from decimal import ROUND_HALF_UP
        
        config = cls.get_hyperliquid_precision(coin)
        tick = Decimal(config["price_tick"])
        
        decimal_price = Decimal(str(price))
        formatted = float(decimal_price.quantize(tick, rounding=ROUND_HALF_UP))
        
        return formatted, str(formatted)
    
    @classmethod
    def validate_aster_order(cls, coin: str, quantity: float, price: float = None) -> Tuple[bool, str]:
        """
        Validate Aster order parameters
        
        Returns:
            (Whether valid, error message)
        """
        config = cls.get_aster_precision(coin)
        
        # Check minimum quantity
        min_qty = float(config["min_quantity"])
        if quantity < min_qty:
            return False, f"Quantity {quantity} is less than minimum {min_qty}"
        
        # Check minimum notional value
        if price:
            notional = quantity * price
            min_notional = float(config["min_notional"])
            if notional < min_notional:
                return False, f"Notional value {notional:.2f} USDT is less than minimum {min_notional} USDT"
        
        return True, ""
    
    @classmethod
    def validate_hyperliquid_order(cls, coin: str, quantity: float, price: float = None) -> Tuple[bool, str]:
        """
        Validate Hyperliquid order parameters
        
        Returns:
            (Whether valid, error message)
        """
        config = cls.get_hyperliquid_precision(coin)
        
        # Check minimum quantity
        min_qty = float(config["min_quantity"])
        if quantity < min_qty:
            return False, f"Quantity {quantity} is less than minimum {min_qty}"
        
        # Check minimum notional value
        if price:
            notional = quantity * price
            min_notional = float(config["min_notional"])
            if notional < min_notional:
                return False, f"Notional value {notional:.2f} USD is less than minimum {min_notional} USD"
        
        return True, ""


# Global instance
precision_config = PrecisionConfig()

