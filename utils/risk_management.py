"""Enhanced risk management functionality."""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger('utils.advanced_risk_management')

class AdvancedRiskManager:
    """Advanced risk management with portfolio-level controls."""
    
    def __init__(self, data_provider, max_portfolio_risk=0.02, max_drawdown=0.15, 
                 max_correlation=0.7, position_sizing_method='volatility'):
        """Initialize the advanced risk manager.
        
        Args:
            data_provider: Data provider object for historical data
            max_portfolio_risk: Maximum risk per trade as fraction of portfolio
            max_drawdown: Maximum allowed drawdown before reducing exposure
            max_correlation: Maximum allowed correlation between positions
            position_sizing_method: Method to use for position sizing
                ('volatility', 'equal', 'kelly')
        """
        self.data_provider = data_provider
        self.max_portfolio_risk = max_portfolio_risk
        self.max_drawdown = max_drawdown
        self.max_correlation = max_correlation
        self.position_sizing_method = position_sizing_method
        self.correlation_matrix = None
        self.current_drawdown = 0
        self.peak_value = 0
        self.trailing_stops = {}  # Symbol -> trailing stop price
    
    def update_portfolio_metrics(self, portfolio):
        """Update portfolio metrics like drawdown and peak value."""
        current_value = portfolio.get_total_value()
        
        # Update peak value
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # Calculate current drawdown
        if self.peak_value > 0:
            self.current_drawdown = (self.peak_value - current_value) / self.peak_value
        
        return {
            'current_value': current_value,
            'peak_value': self.peak_value,
            'current_drawdown': self.current_drawdown
        }
    
    def update_correlation_matrix(self, symbols, lookback_days=60):
        """Update correlation matrix for the given symbols."""
        if not symbols:
            self.correlation_matrix = None
            return None
        
        # Get historical data for all symbols
        price_data = {}
        for symbol in symbols:
            contract = next((c for c in symbols if c.symbol == symbol), None)
            if contract:
                df = self.data_provider.get_historical_data(
                    contract, duration=f'{lookback_days} D')
                if df is not None and len(df) > 10:
                    price_data[symbol] = df['close']
        
        if len(price_data) < 2:
            self.correlation_matrix = None
            return None
        
        # Create a DataFrame with all price series
        df = pd.DataFrame(price_data)
        
        # Calculate returns
        returns = df.pct_change().dropna()
        
        # Calculate correlation matrix
        self.correlation_matrix = returns.corr()
        
        return self.correlation_matrix
    
    def check_correlation(self, symbol, portfolio):
        """Check if adding a new position would exceed correlation limits."""
        if self.correlation_matrix is None or symbol not in self.correlation_matrix:
            return True
        
        # Get current positions
        current_symbols = list(portfolio.positions.keys())
        
        # Check correlation with existing positions
        for existing_symbol in current_symbols:
            if existing_symbol in self.correlation_matrix and symbol in self.correlation_matrix:
                correlation = self.correlation_matrix.loc[symbol, existing_symbol]
                if abs(correlation) > self.max_correlation:
                    logger.warning(f"Correlation between {symbol} and {existing_symbol} " 
                                  f"is too high: {correlation:.2f}")
                    return False
        
        return True
    
    def calculate_optimal_position_size(self, price, volatility, portfolio_value, symbol, portfolio, 
                                       max_positions=3):
        """Calculate position size using the selected method."""
        # Basic checks
        if portfolio_value <= 0:
            return 1
        
        # Apply drawdown-based scaling
        drawdown_factor = 1.0
        if self.current_drawdown > 0:
            # Reduce position size as drawdown increases
            drawdown_factor = max(0.2, 1.0 - (self.current_drawdown / self.max_drawdown))
        
        # Calculate base risk amount
        risk_per_trade = portfolio_value * self.max_portfolio_risk * drawdown_factor / max_positions
        
        if self.position_sizing_method == 'equal':
            # Equal position sizes
            position_value = portfolio_value / max_positions * drawdown_factor
            position_size = int(position_value / price)
            
        elif self.position_sizing_method == 'kelly':
            # Kelly criterion (simplified)
            # Assuming win rate of 50% and reward:risk ratio based on historical data
            win_rate = 0.5  # Default
            
            # Try to get better estimates if we have historical data
            if hasattr(portfolio, 'transactions') and portfolio.transactions:
                trades = [t for t in portfolio.transactions if t['symbol'] == symbol]
                if trades:
                    wins = sum(1 for t in trades if (
                        (t['action'] == 'SELL' and t['price'] > t['entry_price']) or
                        (t['action'] == 'BUY' and t['price'] < t['entry_price'])
                    ))
                    win_rate = wins / len(trades) if len(trades) > 0 else 0.5
            
            # Calculate reward:risk ratio (simplified)
            reward_risk_ratio = 2.0  # Default assumption
            
            # Apply Kelly formula (simplified)
            kelly_fraction = max(0, (win_rate - ((1 - win_rate) / reward_risk_ratio)))
            
            # Kelly is often too aggressive, so we use half Kelly
            kelly_fraction = kelly_fraction * 0.5
            
            position_value = portfolio_value * kelly_fraction * drawdown_factor
            position_size = int(position_value / price)
            
        else:  # Default to volatility-based sizing
            # Convert annualized volatility to daily
            daily_volatility = volatility / np.sqrt(252)
            
            # Calculate stop loss amount
            # Either use fixed percentage or volatility-based
            stop_loss_pct = max(0.02, daily_volatility * 2)  # At least 2%
            stop_loss_amount = price * stop_loss_pct
            
            if stop_loss_amount <= 0:
                # Fallback to volatility-based sizing
                position_size = int(risk_per_trade / (price * daily_volatility * 3))
            else:
                # Risk-based position sizing
                position_size = int(risk_per_trade / stop_loss_amount)
        
        # Ensure minimum and maximum position sizes
        position_size = max(1, min(position_size, int(portfolio_value * 0.2 / price)))
        
        return position_size
    
    def check_portfolio_risk(self, portfolio, new_position_details=None):
        """Check if adding a new position would exceed risk limits."""
        # Update portfolio metrics
        metrics = self.update_portfolio_metrics(portfolio)
        
        # Check drawdown limit
        if metrics['current_drawdown'] >= self.max_drawdown:
            logger.warning(f"Maximum drawdown reached: {metrics['current_drawdown']:.2%}")
            return False
        
        # Check maximum positions
        current_positions = len(portfolio.positions)
        if current_positions >= 3:  # Max positions hardcoded here
            return False
        
        # Check correlation if we have position details
        if new_position_details and 'symbol' in new_position_details:
            if not self.check_correlation(new_position_details['symbol'], portfolio):
                return False
        
        return True
    
    def calculate_trailing_stop(self, symbol, current_price, position):
        """Calculate and update trailing stop price."""
        if symbol not in self.trailing_stops:
            # Initialize trailing stop at fixed percentage below entry
            entry_price = position.get('avg_cost', current_price)
            initial_stop = entry_price * 0.95  # 5% initial stop
            self.trailing_stops[symbol] = initial_stop
        else:
            # Update trailing stop if price has moved in our favor
            new_stop = current_price * 0.95  # 5% below current price
            if new_stop > self.trailing_stops[symbol]:
                self.trailing_stops[symbol] = new_stop
        
        return self.trailing_stops[symbol]
    
    def should_exit_position(self, symbol, current_price, position, days_held):
        """Determine if a position should be exited based on multiple criteria."""
        # Check trailing stop
        trailing_stop = self.calculate_trailing_stop(symbol, current_price, position)
        if current_price < trailing_stop:
            return True, "Trailing stop triggered"
        
        # Time-based exit
        if days_held > 30:  # Exit after 30 days regardless of profit/loss
            return True, "Time-based exit"
        
        # Profit target
        entry_price = position.get('avg_cost', current_price)
        if current_price >= entry_price * 1.2:  # 20% profit target
            return True, "Profit target reached"
        
        # Volatility-based exit (exit if volatility spikes)
        if 'volatility' in position and position['volatility'] > 0:
            current_volatility = position.get('current_volatility', position['volatility'])
            if current_volatility > position['volatility'] * 2:
                return True, "Volatility spike"
        
        return False, None