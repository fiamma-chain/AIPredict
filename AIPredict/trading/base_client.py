"""
Base Trading Client Class
Defines a unified interface for different trading platforms to implement
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseExchangeClient(ABC):
    """Base Exchange Client Class"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        Initialize client
        
        Args:
            private_key: Private key
            testnet: Whether to use testnet
        """
        self.testnet = testnet
        self.address = None
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform name"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Account information dict, including balance and other info
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, coin: str) -> Dict:
        """
        Get market data
        
        Args:
            coin: Coin symbol
            
        Returns:
            Market data dict, including:
            - coin: Coin symbol
            - price: Current price
            - mark_price: Mark price
            - funding_rate: Funding rate
            - open_interest: Open interest
            - change_24h: 24-hour change percentage
            - volume: 24-hour trading volume
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, coin: str) -> Dict:
        """
        Get order book
        
        Args:
            coin: Coin symbol
            
        Returns:
            Order book data {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """
        pass
    
    @abstractmethod
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """
        Get recent trades
        
        Args:
            coin: Coin symbol
            limit: Number of records to return
            
        Returns:
            List of trade records
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "Limit",
        reduce_only: bool = False
    ) -> Dict:
        """
        Place order
        
        Args:
            coin: Coin symbol
            is_buy: Whether to buy
            size: Order size
            price: Order price (None for market order)
            order_type: Order type
            reduce_only: Whether to reduce position only
            
        Returns:
            Order result
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, coin: str, order_id: str) -> Dict:
        """
        Cancel order
        
        Args:
            coin: Coin symbol
            order_id: Order ID
            
        Returns:
            Cancellation result
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """
        Get open orders
        
        Args:
            coin: Coin symbol (optional)
            
        Returns:
            List of orders
        """
        pass
    
    @abstractmethod
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """
        Get user historical fill records
        
        Args:
            limit: Number of records limit
            start_time_ms: Start time (millisecond timestamp)
            
        Returns:
            List of fill records
        """
        pass
    
    @abstractmethod
    async def get_candles(
        self,
        coin: str,
        interval: str = "15m",
        lookback: int = 100,
        timeout: int = 30
    ) -> List[Dict]:
        """
        Get candlestick (K-line) data
        
        Args:
            coin: Coin symbol
            interval: Candlestick interval
            lookback: Number of candlesticks to look back
            timeout: Timeout in seconds
            
        Returns:
            List of candlestick data [{"time": timestamp, "open": o, "high": h, "low": l, "close": c, "volume": v}, ...]
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass
    
    async def close_session(self):
        """Close session (optional implementation)"""
        pass

