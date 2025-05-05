"""Functions for retrieving historical market data."""
import logging
import pandas as pd
from ib_insync import util

logger = logging.getLogger('data.historical')

class HistoricalDataProvider:
    """Provider for historical market data."""
    
    def __init__(self, ib_connection):
        """Initialize with an IB connection."""
        self.ib_connection = ib_connection
    
    def get_historical_data(self, contract, duration='20 D', bar_size='1 day',
                           what_to_show='MIDPOINT', use_rth=True):
        """Get historical data for a contract."""
        ib = self.ib_connection.ensure_connection()
        
        try:
            bars = ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=use_rth
            )
            
            if not bars:
                logger.warning(f"No historical data returned for {contract.symbol}")
                return None
                
            df = util.df(bars)
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {contract.symbol}: {e}")
            return None
    
    def calculate_indicators(self, df, sma_short=5, sma_long=20):
        """Calculate technical indicators on a dataframe."""
        if df is None or len(df) < sma_long:
            return None
            
        # Make a copy to avoid modifying the original
        result = df.copy()
        
        # Calculate simple moving averages
        result[f'SMA{sma_short}'] = result['close'].rolling(sma_short).mean()
        result[f'SMA{sma_long}'] = result['close'].rolling(sma_long).mean()
        
        # Calculate volatility (20-day rolling standard deviation of returns)
        result['returns'] = result['close'].pct_change()
        result['volatility'] = result['returns'].rolling(20).std() * (252 ** 0.5)  # Annualized
        
        return result