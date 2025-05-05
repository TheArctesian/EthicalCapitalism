"""Enhanced moving average strategy with confirmation filters."""
import logging
import numpy as np
from strategies.base_strategy import BaseStrategy
from config.settings import SMA_SHORT, SMA_LONG, LOOKBACK_PERIOD

logger = logging.getLogger('strategies.enhanced_ma')

class EnhancedMovingAverage(BaseStrategy):
    """Enhanced moving average strategy with multiple confirmations."""
    
    def __init__(self, data_provider, short_period=SMA_SHORT, long_period=SMA_LONG,
                 volume_factor=1.5, signal_strength_threshold=0.01, rsi_period=14):
        """Initialize the enhanced MA strategy."""
        super().__init__(data_provider)
        self.short_period = short_period
        self.long_period = long_period
        self.volume_factor = volume_factor  # Volume should be this times average to confirm
        self.signal_strength_threshold = signal_strength_threshold  # Min % difference for crossover
        self.rsi_period = rsi_period
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI technical indicator."""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down if down != 0 else np.inf
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100./(1. + rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0
            else:
                upval = 0
                downval = -delta
                
            up = (up * (period-1) + upval) / period
            down = (down * (period-1) + downval) / period
            rs = up/down if down != 0 else np.inf
            rsi[i] = 100. - 100./(1. + rs)
        return rsi
    
    def detect_market_regime(self, df, lookback=50):
        """Detect if market is trending or range-bound."""
        if len(df) < lookback:
            return "unknown"
            
        # Calculate directional movement
        price_direction = df['close'].iloc[-1] - df['close'].iloc[-lookback]
        price_range = df['high'].iloc[-lookback:].max() - df['low'].iloc[-lookback:].min()
        
        # Calculate ADX-like measure
        directional_strength = abs(price_direction) / price_range if price_range > 0 else 0
        
        if directional_strength > 0.3:  # Threshold can be tuned
            return "trending"
        else:
            return "range_bound"
    
    def generate_signals(self, contracts):
        """Generate trading signals with confirmation filters."""
        signals = {}
        
        for contract in contracts:
            # Get historical data with more data points to calculate indicators
            df = self.data_provider.get_historical_data(
                contract,
                duration=f'{max(LOOKBACK_PERIOD, 50) + 20} D'
            )
            
            if df is None or len(df) < self.long_period + 2:
                logger.warning(f"Insufficient data for {contract.symbol}")
                continue
                
            # Calculate indicators
            df['sma_short'] = df['close'].rolling(self.short_period).mean()
            df['sma_long'] = df['close'].rolling(self.long_period).mean()
            df['ma_diff'] = (df['sma_short'] - df['sma_long']) / df['close'] * 100  # % difference
            df['volume_avg'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_avg']
            
            # Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'].values, self.rsi_period)
            
            # Detect market regime
            market_regime = self.detect_market_regime(df)
            
            # Get last two rows to check for crossover
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Determine base signal
            signal = None
            
            # Buy signal: short MA crosses above long MA
            if (prev_row['sma_short'] <= prev_row['sma_long'] and 
                last_row['sma_short'] > last_row['sma_long']):
                
                # Apply confirmation filters
                if (abs(last_row['ma_diff']) >= self.signal_strength_threshold and
                    last_row['volume_ratio'] >= self.volume_factor):
                    
                    # Additional RSI filter
                    if market_regime == "trending" or (
                        market_regime == "range_bound" and last_row['rsi'] < 70):
                        signal = 'BUY'
                        
            # Sell signal: short MA crosses below long MA
            elif (prev_row['sma_short'] >= prev_row['sma_long'] and 
                  last_row['sma_short'] < last_row['sma_long']):
                
                # Apply confirmation filters
                if (abs(last_row['ma_diff']) >= self.signal_strength_threshold and
                    last_row['volume_ratio'] >= self.volume_factor):
                    
                    # Additional RSI filter
                    if market_regime == "trending" or (
                        market_regime == "range_bound" and last_row['rsi'] > 30):
                        signal = 'SELL'
            
            if signal:
                logger.info(f"Generated {signal} signal for {contract.symbol} (Regime: {market_regime})")
                signals[contract.symbol] = {
                    'action': signal,
                    'price': last_row['close'],
                    'volatility': last_row.get('volatility', df['close'].pct_change().std() * np.sqrt(252)),
                    'signal_strength': abs(last_row['ma_diff']),
                    'market_regime': market_regime
                }
                
        return signals