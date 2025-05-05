"""Mean reversion strategy for range-bound markets."""
import logging
import numpy as np
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger('strategies.mean_reversion')

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy for range-bound ETFs."""
    
    def __init__(self, data_provider, rsi_period=14, rsi_oversold=30, rsi_overbought=70,
                 bollinger_period=20, bollinger_std=2.0, min_mean_reversion_score=0.7):
        """Initialize the mean reversion strategy."""
        super().__init__(data_provider)
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bollinger_period = bollinger_period
        self.bollinger_std = bollinger_std
        self.min_mean_reversion_score = min_mean_reversion_score
    
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
    
    def calculate_mean_reversion_score(self, df, lookback=100):
        """Calculate a score indicating how mean-reverting an asset is."""
        if len(df) < lookback:
            return 0.5  # Not enough data
            
        # Calculate returns
        returns = df['close'].pct_change().dropna()
        
        # Calculate autocorrelation of returns
        # Negative autocorrelation suggests mean reversion
        autocorr = returns[-lookback:].autocorr(1)
        
        # Normalize to a 0-1 score where higher means more mean-reverting
        score = 0.5 - min(max(autocorr, -1), 1) / 2
        
        return score
    
    def generate_signals(self, contracts):
        """Generate mean reversion trading signals."""
        signals = {}
        
        for contract in contracts:
            # Get historical data
            df = self.data_provider.get_historical_data(
                contract,
                duration='100 D'
            )
            
            if df is None or len(df) < self.bollinger_period + 2:
                logger.warning(f"Insufficient data for {contract.symbol}")
                continue
                
            # Calculate mean reversion score
            mr_score = self.calculate_mean_reversion_score(df)
            
            # If asset doesn't exhibit mean reversion, skip it
            if mr_score < self.min_mean_reversion_score:
                logger.info(f"Skipping {contract.symbol} - low mean reversion score: {mr_score:.2f}")
                continue
                
            # Calculate indicators
            df['sma'] = df['close'].rolling(self.bollinger_period).mean()
            df['std'] = df['close'].rolling(self.bollinger_period).std()
            df['upper_band'] = df['sma'] + (df['std'] * self.bollinger_std)
            df['lower_band'] = df['sma'] - (df['std'] * self.bollinger_std)
            df['pct_b'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
            
            # Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'].values, self.rsi_period)
            
            # Get the last row
            last_row = df.iloc[-1]
            
            # Determine signal
            signal = None
            
            # Buy signal: Price near lower band and RSI oversold
            if (last_row['pct_b'] < 0.2 and last_row['rsi'] < self.rsi_oversold):
                signal = 'BUY'
                
            # Sell signal: Price near upper band and RSI overbought
            elif (last_row['pct_b'] > 0.8 and last_row['rsi'] > self.rsi_overbought):
                signal = 'SELL'
            
            if signal:
                logger.info(f"Generated {signal} signal for {contract.symbol} (MR Score: {mr_score:.2f})")
                signals[contract.symbol] = {
                    'action': signal,
                    'price': last_row['close'],
                    'volatility': df['close'].pct_change().std() * np.sqrt(252),
                    'mean_reversion_score': mr_score
                }
                
        return signals