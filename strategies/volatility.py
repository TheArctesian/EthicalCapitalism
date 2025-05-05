"""Volatility-based strategy implementation."""
import logging
import numpy as np
from strategies.base_strategy import BaseStrategy
from config.settings import LOOKBACK_PERIOD

logger = logging.getLogger('strategies.volatility')

class VolatilityBreakout(BaseStrategy):
    """Volatility breakout strategy.
    
    This strategy looks for breakouts from price ranges defined by volatility
    measures. It buys when price breaks above recent volatility bands and sells
    when it breaks below.
    """
    
    def __init__(self, data_provider, volatility_factor=2.0, lookback=LOOKBACK_PERIOD):
        """Initialize the volatility breakout strategy.
        
        Args:
            data_provider: Data provider object
            volatility_factor: Multiplier for volatility bands (e.g., 2.0 = 2 standard deviations)
            lookback: Lookback period for calculating bands
        """
        super().__init__(data_provider)
        self.volatility_factor = volatility_factor
        self.lookback = lookback
    
    def generate_signals(self, contracts):
        """Generate trading signals based on volatility breakouts.
        
        Args:
            contracts: List of contract objects to analyze
            
        Returns:
            dict: Dictionary of signals by symbol
        """
        signals = {}
        
        for contract in contracts:
            # Get historical data
            df = self.data_provider.get_historical_data(
                contract,
                duration=f'{self.lookback+10} D'  # Get a bit more data than needed
            )
            
            if df is None or len(df) < self.lookback + 2:
                logger.warning(f"Insufficient data for {contract.symbol}")
                continue
                
            # Calculate indicators
            df['returns'] = df['close'].pct_change()
            df['volatility'] = df['returns'].rolling(self.lookback).std() * np.sqrt(252)  # Annualized
            
            # Calculate the center of the band (moving average)
            df['sma'] = df['close'].rolling(self.lookback).mean()
            
            # Calculate volatility bands
            band_width = df['close'] * df['volatility'] * self.volatility_factor / np.sqrt(252)
            df['upper_band'] = df['sma'] + band_width
            df['lower_band'] = df['sma'] - band_width
            
            # Get the last two rows
            if len(df) < 2:
                continue
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Determine signal
            signal = None
            
            # Buy signal: price crosses above upper band
            if prev_row['close'] <= prev_row['upper_band'] and last_row['close'] > last_row['upper_band']:
                signal = 'BUY'
                
            # Sell signal: price crosses below lower band
            elif prev_row['close'] >= prev_row['lower_band'] and last_row['close'] < last_row['lower_band']:
                signal = 'SELL'
            
            if signal:
                logger.info(f"Generated {signal} signal for {contract.symbol}")
                signals[contract.symbol] = {
                    'action': signal,
                    'price': last_row['close'],
                    'volatility': last_row['volatility']
                }
                
        return signals