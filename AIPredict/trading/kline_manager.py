"""
Kline Data Manager
Used to collect and maintain intraday time series data
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from collections import deque

logger = logging.getLogger(__name__)


class KlineManager:
    """Kline Data Manager"""
    
    def __init__(self, max_klines: int = 16):
        """
        Initialize Kline Manager
        
        Args:
            max_klines: Maximum number of klines to keep (default 16, i.e., 4 hours of 15-minute klines)
        """
        self.max_klines = max_klines
        self.klines: deque = deque(maxlen=max_klines)
        self.current_kline: Dict = None
        self.last_update_time: datetime = None
        
    def update_price(self, price: float, volume: float = 0):
        """
        Update price data
        
        Args:
            price: Current price
            volume: Trading volume
        """
        now = datetime.now()
        
        # Get current 15-minute timestamp (round down to 15 minutes)
        current_period = now.replace(second=0, microsecond=0)
        minute = current_period.minute
        period_minute = (minute // 15) * 15
        current_period = current_period.replace(minute=period_minute)
        
        # If it's a new 15-minute period, save the old kline and start a new one
        if self.current_kline is None or self.current_kline['time'] != current_period:
            if self.current_kline is not None:
                # Save completed kline
                self.klines.append(self.current_kline.copy())
                logger.info(f"📊 Kline completed: {self.current_kline['time'].strftime('%H:%M')} "
                           f"O:{self.current_kline['open']:.0f} H:{self.current_kline['high']:.0f} "
                           f"L:{self.current_kline['low']:.0f} C:{self.current_kline['close']:.0f}")
            
            # Start new kline
            self.current_kline = {
                'time': current_period,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
        else:
            # Update current kline
            self.current_kline['high'] = max(self.current_kline['high'], price)
            self.current_kline['low'] = min(self.current_kline['low'], price)
            self.current_kline['close'] = price
            self.current_kline['volume'] += volume
        
        self.last_update_time = now
    
    def get_klines(self, count: int = None) -> List[Dict]:
        """
        Get kline list
        
        Args:
            count: Number of klines to get, None means all
            
        Returns:
            List of klines
        """
        if count is None:
            return list(self.klines)
        else:
            return list(self.klines)[-count:]
    
    def get_summary(self) -> Dict:
        """
        Get kline statistics summary
        
        Returns:
            Dictionary of statistics
        """
        if len(self.klines) == 0:
            return {
                'total_klines': 0,
                'trend': 'unknown',
                'price_change': 0,
                'price_change_pct': 0
            }
        
        first_kline = self.klines[0]
        last_kline = self.klines[-1]
        
        price_change = last_kline['close'] - first_kline['open']
        price_change_pct = (price_change / first_kline['open']) * 100 if first_kline['open'] > 0 else 0
        
        # Determine trend
        if price_change_pct > 0.5:
            trend = 'uptrend'
        elif price_change_pct < -0.5:
            trend = 'downtrend'
        else:
            trend = 'sideways'
        
        # Calculate highest and lowest
        all_highs = [k['high'] for k in self.klines]
        all_lows = [k['low'] for k in self.klines]
        period_high = max(all_highs)
        period_low = min(all_lows)
        
        return {
            'total_klines': len(self.klines),
            'trend': trend,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'period_high': period_high,
            'period_low': period_low,
            'first_price': first_kline['open'],
            'last_price': last_kline['close']
        }
    
    def calculate_support_resistance(self) -> Dict:
        """
        Calculate support and resistance levels
        
        Returns:
            Dictionary of support and resistance levels
        """
        if len(self.klines) < 3:
            return {'support': None, 'resistance': None}
        
        # Simple method: use recent local lows as support, local highs as resistance
        lows = [k['low'] for k in self.klines]
        highs = [k['high'] for k in self.klines]
        
        # Recent support level (lowest point of recent klines)
        support = min(lows[-5:]) if len(lows) >= 5 else min(lows)
        
        # Recent resistance level (highest point of recent klines)
        resistance = max(highs[-5:]) if len(highs) >= 5 else max(highs)
        
        return {
            'support': support,
            'resistance': resistance
        }
    
    def format_for_prompt(self, max_rows: int = 16) -> str:
        """
        Format kline data for AI prompt
        
        Args:
            max_rows: Maximum number of rows to display
            
        Returns:
            Formatted string
        """
        klines = self.get_klines(max_rows)
        
        if len(klines) == 0:
            return "No historical kline data available"
        
        lines = []
        lines.append("Time    Open     High     Low      Close    Change")
        lines.append("─" * 50)
        
        for kline in klines:
            time_str = kline['time'].strftime('%H:%M')
            open_price = kline['open']
            high_price = kline['high']
            low_price = kline['low']
            close_price = kline['close']
            change_pct = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
            
            change_symbol = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
            
            lines.append(f"{time_str}  {open_price:>7.0f}  {high_price:>7.0f}  "
                        f"{low_price:>7.0f}  {close_price:>7.0f}  {change_symbol}{change_pct:>+6.2f}%")
        
        # Add statistical summary
        summary = self.get_summary()
        sr = self.calculate_support_resistance()
        
        lines.append("─" * 50)
        lines.append(f"Period Stats: {summary['total_klines']} klines ({summary['total_klines']*15} minutes)")
        lines.append(f"Overall Trend: {'Uptrend' if summary['trend'] == 'uptrend' else 'Downtrend' if summary['trend'] == 'downtrend' else 'Sideways'}")
        lines.append(f"Price Change: {summary['price_change']:+.0f} ({summary['price_change_pct']:+.2f}%)")
        lines.append(f"Period High: ${summary['period_high']:,.0f}")
        lines.append(f"Period Low: ${summary['period_low']:,.0f}")
        
        if sr['support'] and sr['resistance']:
            lines.append(f"Support: ${sr['support']:,.0f}")
            lines.append(f"Resistance: ${sr['resistance']:,.0f}")
        
        return "\n".join(lines)

