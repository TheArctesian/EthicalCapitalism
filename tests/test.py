"""Backtesting framework for trading strategies."""
import os
import sys
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from tqdm import tqdm
import logging

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base_strategy import BaseStrategy
from strategies.moving_average import MovingAverageCrossover
from strategies.enhanced_ma import EnhancedMovingAverage
from strategies.volatility import VolatilityBreakout
from strategies.mean_reversion import MeanReversionStrategy
from strategies.ensemble import EnsembleStrategy
from data.historical import HistoricalDataProvider
from utils.logging_config import setup_logging

# Configure logging for tests
logger = logging.getLogger('eco_etf_bot.tests.backtest')

class MockHistoricalData:
    """Mock data provider for backtesting."""
    
    def __init__(self, data_dict):
        """Initialize with preloaded historical data."""
        self.data = data_dict
    
    def get_historical_data(self, contract, duration=None, bar_size='1 day',
                           what_to_show='MIDPOINT', use_rth=True):
        """Get historical data from preloaded data."""
        symbol = contract.symbol
        if symbol in self.data:
            return self.data[symbol].copy()
        return None
    
    def calculate_indicators(self, df, sma_short=5, sma_long=20):
        """Calculate indicators on a dataframe."""
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

class Backtest:
    """Backtest trading strategies on historical data."""
    
    def __init__(self, data_folder='backtest_data', output_folder='test_results'):
        """Initialize the backtest engine."""
        self.data_folder = data_folder
        self.output_folder = output_folder
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Create data folder if it doesn't exist
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
            
        self.strategies = {}
        self.results = {}
    
    def load_data(self, symbols, days=252):
        """Load or download historical data for symbols.
        
        Args:
            symbols: List of symbols to test
            days: Number of trading days to test (default 1 year)
            
        Returns:
            dict: Symbol -> DataFrame with historical data
        """
        data = {}
        
        # Check if we have cached data
        for symbol in symbols:
            data_file = os.path.join(self.data_folder, f"{symbol}_data.csv")
            
            if os.path.exists(data_file):
                # Load data from file
                df = pd.read_csv(data_file, parse_dates=['date'])
                
                # Only use the requested number of days
                if len(df) > days:
                    df = df.tail(days)
                
                data[symbol] = df
                logger.info(f"Loaded {len(df)} days of data for {symbol}")
            else:
                # We would download data here in a real implementation
                # For now, we'll just create mock data
                logger.warning(f"No cached data for {symbol}, creating mock data")
                
                # Create mock data for testing
                date_range = pd.date_range(end=datetime.now(), periods=days, freq='B')
                mock_data = pd.DataFrame({
                    'date': date_range,
                    'open': np.random.normal(100, 10, size=days).cumsum(),
                    'high': np.random.normal(100, 10, size=days).cumsum() + 2,
                    'low': np.random.normal(100, 10, size=days).cumsum() - 2,
                    'close': np.random.normal(100, 10, size=days).cumsum(),
                    'volume': np.random.randint(1000, 1000000, size=days)
                })
                
                # Save mock data for reuse
                mock_data.to_csv(data_file, index=False)
                
                data[symbol] = mock_data
        
        return data
    
    def register_strategies(self):
        """Register all available strategies for testing."""
        # Create mock data provider
        mock_data_provider = MockHistoricalData({})  # Will be updated before running tests
        
        # Register all strategies
        self.strategies['MovingAverage'] = MovingAverageCrossover(mock_data_provider)
        self.strategies['EnhancedMA'] = EnhancedMovingAverage(mock_data_provider)
        self.strategies['Volatility'] = VolatilityBreakout(mock_data_provider)
        self.strategies['MeanReversion'] = MeanReversionStrategy(mock_data_provider)
        
        # Create ensemble strategy
        self.strategies['Ensemble'] = EnsembleStrategy(
            mock_data_provider,
            strategies=[
                MovingAverageCrossover(mock_data_provider),
                EnhancedMovingAverage(mock_data_provider),
                VolatilityBreakout(mock_data_provider),
                MeanReversionStrategy(mock_data_provider)
            ],
            weights=[0.1, 0.3, 0.3, 0.3]
        )
        
        return self.strategies
    
    def run_backtest(self, symbols, days=252, initial_capital=100000):
        """Run backtest on historical data for all registered strategies.
        
        Args:
            symbols: List of symbols to test
            days: Number of trading days to test
            initial_capital: Initial capital for portfolio
            
        Returns:
            dict: Strategy name -> backtest results
        """
        # Load historical data
        data = self.load_data(symbols, days)
        
        # Register strategies if not already done
        if not self.strategies:
            self.register_strategies()
        
        # Update mock data provider for each strategy
        for strategy_name, strategy in self.strategies.items():
            strategy.data_provider.data = data
        
        # Run backtest for each strategy
        results = {}
        
        for strategy_name, strategy in self.strategies.items():
            logger.info(f"Running backtest for {strategy_name} strategy")
            
            # Initialize results for this strategy
            strategy_results = {
                'portfolio_value': [],
                'cash': [],
                'positions': [],
                'trades': [],
                'equity_curve': [initial_capital],
                'symbols': symbols,
                'days': days
            }
            
            # Create a portfolio for backtesting
            portfolio = {
                'cash': initial_capital,
                'positions': {},
                'trades': []
            }
            
            # Determine the common date range for all symbols
            common_dates = None
            for symbol in symbols:
                if symbol in data:
                    symbol_dates = data[symbol]['date']
                    if common_dates is None:
                        common_dates = set(symbol_dates)
                    else:
                        common_dates = common_dates.intersection(set(symbol_dates))
            
            if not common_dates:
                logger.error("No common dates found across symbols")
                continue
            
            # Sort common dates
            common_dates = sorted(list(common_dates))
            
            # Only use the requested number of days
            if len(common_dates) > days:
                common_dates = common_dates[-days:]
            
            # Run the backtest day by day
            for day_idx, current_date in enumerate(tqdm(common_dates, desc=f"Testing {strategy_name}")):
                # Skip the first few days to allow for indicator calculation
                if day_idx < 20:  # Need at least 20 days for most indicators
                    continue
                
                # Create a dictionary to hold the data up to this date for each symbol
                historical_data = {}
                for symbol in symbols:
                    if symbol in data:
                        # Get data up to current date
                        symbol_data = data[symbol][data[symbol]['date'] <= current_date]
                        if len(symbol_data) > 0:
                            historical_data[symbol] = symbol_data
                
                # Update mock data provider with data up to this point
                for strat_name, strat in self.strategies.items():
                    strat.data_provider.data = historical_data
                
                # Generate signals for current day
                contracts = [{'symbol': symbol} for symbol in symbols]
                signals = strategy.generate_signals(contracts)
                
                # Process signals and update portfolio
                for symbol, signal_data in signals.items():
                    action = signal_data['action']
                    price = signal_data['price']
                    
                    # Default to 100 shares or position sizing based on volatility
                    if 'volatility' in signal_data:
                        # Simple volatility-based position sizing
                        volatility = signal_data['volatility']
                        target_risk = portfolio['cash'] * 0.01  # 1% risk per trade
                        quantity = max(1, int(target_risk / (price * volatility * 0.1)))
                        quantity = min(quantity, 1000)  # Cap at 1000 shares
                    else:
                        quantity = 100
                    
                    # Implement the signal
                    if action == 'BUY' and symbol not in portfolio['positions']:
                        # Check if we have enough cash
                        cost = price * quantity
                        if cost <= portfolio['cash']:
                            # Buy the stock
                            portfolio['positions'][symbol] = {
                                'quantity': quantity,
                                'entry_price': price,
                                'entry_date': current_date,
                                'current_price': price,
                                'current_value': price * quantity
                            }
                            portfolio['cash'] -= cost
                            
                            # Record the trade
                            portfolio['trades'].append({
                                'date': current_date,
                                'symbol': symbol,
                                'action': 'BUY',
                                'quantity': quantity,
                                'price': price,
                                'cost': cost,
                                'strategy': strategy_name
                            })
                    
                    elif action == 'SELL' and symbol in portfolio['positions']:
                        # Sell the stock
                        position = portfolio['positions'][symbol]
                        proceeds = price * position['quantity']
                        profit = proceeds - (position['entry_price'] * position['quantity'])
                        
                        portfolio['cash'] += proceeds
                        
                        # Record the trade
                        portfolio['trades'].append({
                            'date': current_date,
                            'symbol': symbol,
                            'action': 'SELL',
                            'quantity': position['quantity'],
                            'price': price,
                            'proceeds': proceeds,
                            'profit': profit,
                            'entry_price': position['entry_price'],
                            'entry_date': position['entry_date'],
                            'holding_days': (pd.to_datetime(current_date) - 
                                           pd.to_datetime(position['entry_date'])).days,
                            'strategy': strategy_name
                        })
                        
                        # Remove the position
                        del portfolio['positions'][symbol]
                
                # Update current prices and values for all positions
                for symbol, position in list(portfolio['positions'].items()):
                    if symbol in historical_data:
                        current_price = historical_data[symbol]['close'].iloc[-1]
                        position['current_price'] = current_price
                        position['current_value'] = current_price * position['quantity']
                    else:
                        # If we don't have data for this symbol, assume price unchanged
                        pass
                
                # Calculate total portfolio value
                portfolio_value = portfolio['cash']
                for symbol, position in portfolio['positions'].items():
                    portfolio_value += position['current_value']
                
                # Store the portfolio state for this day
                strategy_results['portfolio_value'].append(portfolio_value)
                strategy_results['cash'].append(portfolio['cash'])
                strategy_results['positions'].append(portfolio['positions'].copy())
                strategy_results['equity_curve'].append(portfolio_value)
            
            # Record all trades
            strategy_results['trades'] = portfolio['trades']
            
            # Calculate performance metrics
            if len(strategy_results['equity_curve']) > 1:
                initial_value = strategy_results['equity_curve'][0]
                final_value = strategy_results['equity_curve'][-1]
                
                # Total return
                total_return = (final_value - initial_value) / initial_value * 100
                
                # Annualized return (assuming 252 trading days in a year)
                days_held = len(strategy_results['equity_curve']) - 1
                annual_return = ((final_value / initial_value) ** (252 / days_held) - 1) * 100 if days_held > 0 else 0
                
                # Convert equity curve to pandas series for calculations
                equity_series = pd.Series(strategy_results['equity_curve'])
                
                # Calculate daily returns
                daily_returns = equity_series.pct_change().dropna()
                
                # Volatility (annualized)
                volatility = daily_returns.std() * np.sqrt(252) * 100
                
                # Sharpe ratio (assuming risk-free rate of 0% for simplicity)
                sharpe = (daily_returns.mean() * 252) / (daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
                
                # Maximum drawdown
                rolling_max = equity_series.cummax()
                drawdown = ((equity_series - rolling_max) / rolling_max) * 100
                max_drawdown = drawdown.min()
                
                # Win rate
                trades = strategy_results['trades']
                winning_trades = [t for t in trades if t.get('profit', 0) > 0]
                win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
                
                # Average profit per trade
                if trades:
                    total_profit = sum(t.get('profit', 0) for t in trades)
                    avg_profit = total_profit / len(trades)
                    avg_win = sum(t.get('profit', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
                    losing_trades = [t for t in trades if t.get('profit', 0) <= 0]
                    avg_loss = sum(t.get('profit', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
                    profit_factor = abs(sum(t.get('profit', 0) for t in winning_trades) / 
                                      sum(t.get('profit', 0) for t in losing_trades)) if losing_trades and sum(t.get('profit', 0) for t in losing_trades) != 0 else float('inf')
                else:
                    total_profit = 0
                    avg_profit = 0
                    avg_win = 0
                    avg_loss = 0
                    profit_factor = 0
                
                # Store metrics
                strategy_results['metrics'] = {
                    'initial_capital': initial_value,
                    'final_value': final_value,
                    'total_return_pct': total_return,
                    'annual_return_pct': annual_return,
                    'volatility_pct': volatility,
                    'sharpe_ratio': sharpe,
                    'max_drawdown_pct': max_drawdown,
                    'win_rate_pct': win_rate,
                    'trade_count': len(trades),
                    'total_profit': total_profit,
                    'avg_profit_per_trade': avg_profit,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor
                }
            
            # Store results for this strategy
            results[strategy_name] = strategy_results
        
        # Store all results
        self.results = results
        
        return results
    
    def plot_results(self, show_plots=True):
        """Plot backtest results."""
        if not self.results:
            logger.error("No backtest results to plot")
            return
        
        # Create plots folder if it doesn't exist
        plots_folder = os.path.join(self.output_folder, 'plots')
        if not os.path.exists(plots_folder):
            os.makedirs(plots_folder)
        
        # Equity curves
        plt.figure(figsize=(12, 8))
        for strategy_name, results in self.results.items():
            if 'equity_curve' in results:
                plt.plot(results['equity_curve'], label=strategy_name)
        
        plt.title('Portfolio Equity Curves')
        plt.xlabel('Trading Days')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True)
        
        # Save the plot
        plt.savefig(os.path.join(plots_folder, 'equity_curves.png'))
        
        if show_plots:
            plt.show()
        
        # Performance comparison chart
        metrics = ['total_return_pct', 'annual_return_pct', 'sharpe_ratio', 'max_drawdown_pct', 'win_rate_pct']
        metric_labels = ['Total Return (%)', 'Annual Return (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Win Rate (%)']
        
        # Extract metrics for each strategy
        strategy_metrics = {}
        for strategy_name, results in self.results.items():
            if 'metrics' in results:
                strategy_metrics[strategy_name] = [results['metrics'].get(m, 0) for m in metrics]
        
        if strategy_metrics:
            # Create bar chart for each metric
            for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
                plt.figure(figsize=(10, 6))
                
                strategies = list(strategy_metrics.keys())
                values = [results['metrics'].get(metric, 0) for strategy, results in self.results.items() 
                         if strategy in strategies and 'metrics' in results]
                
                bars = plt.bar(strategies, values)
                
                # Add value labels on top of bars
                for bar in bars:
                    height = bar.get_height()
                    plt.text(bar.get_x() + bar.get_width()/2., height,
                            f'{height:.2f}',
                            ha='center', va='bottom')
                
                plt.title(f'Strategy Comparison: {label}')
                plt.ylabel(label)
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Save the plot
                plt.savefig(os.path.join(plots_folder, f'comparison_{metric}.png'))
                
                if show_plots:
                    plt.show()
                else:
                    plt.close()
    
    def save_results(self):
        """Save backtest results to files."""
        if not self.results:
            logger.error("No backtest results to save")
            return
        
        # Create a timestamp for the results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save results to JSON
        results_file = os.path.join(self.output_folder, f'backtest_results_{timestamp}.json')
        
        # Prepare results for JSON serialization
        json_results = {}
        for strategy_name, results in self.results.items():
            # Convert positions to serializable format
            serializable_results = results.copy()
            
            # Handle positions (list of dicts)
            if 'positions' in serializable_results:
                serializable_positions = []
                for day_positions in serializable_results['positions']:
                    serializable_day = {}
                    for symbol, pos in day_positions.items():
                        serializable_day[symbol] = {
                            'quantity': pos['quantity'],
                            'entry_price': float(pos['entry_price']),
                            'current_price': float(pos['current_price']),
                            'current_value': float(pos['current_value'])
                        }
                        if 'entry_date' in pos:
                            serializable_day[symbol]['entry_date'] = str(pos['entry_date'])
                    serializable_positions.append(serializable_day)
                serializable_results['positions'] = serializable_positions
            
            # Handle trades (convert dates to strings)
            if 'trades' in serializable_results:
                for trade in serializable_results['trades']:
                    trade['date'] = str(trade['date'])
                    if 'entry_date' in trade:
                        trade['entry_date'] = str(trade['entry_date'])
            
            # Handle metrics (ensure all values are serializable)
            if 'metrics' in serializable_results:
                for key, value in serializable_results['metrics'].items():
                    if isinstance(value, np.float64) or isinstance(value, np.float32):
                        serializable_results['metrics'][key] = float(value)
                    elif isinstance(value, np.int64) or isinstance(value, np.int32):
                        serializable_results['metrics'][key] = int(value)
            
            json_results[strategy_name] = serializable_results
        
        # Save to file
        with open(results_file, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        logger.info(f"Backtest results saved to {results_file}")
        
        # Also generate a summary CSV for easy comparison
        summary_file = os.path.join(self.output_folder, f'backtest_summary_{timestamp}.csv')
        
        summary_data = []
        for strategy_name, results in self.results.items():
            if 'metrics' in results:
                metrics = results['metrics']
                summary_data.append({
                    'Strategy': strategy_name,
                    'Total Return (%)': metrics['total_return_pct'],
                    'Annual Return (%)': metrics['annual_return_pct'],
                    'Volatility (%)': metrics['volatility_pct'],
                    'Sharpe Ratio': metrics['sharpe_ratio'],
                    'Max Drawdown (%)': metrics['max_drawdown_pct'],
                    'Win Rate (%)': metrics['win_rate_pct'],
                    'Trade Count': metrics['trade_count'],
                    'Total Profit ($)': metrics['total_profit'],
                    'Avg Profit/Trade ($)': metrics['avg_profit_per_trade'],
                    'Profit Factor': metrics['profit_factor']
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(summary_file, index=False)
            logger.info(f"Backtest summary saved to {summary_file}")
        
        return results_file, summary_file
    
    def print_summary(self):
        """Print a summary of backtest results to console."""
        if not self.results:
            logger.error("No backtest results to summarize")
            return
        
        print("\n" + "="*80)
        print(f"BACKTEST SUMMARY - {len(self.results)} Strategies")
        print("="*80)
        
        for strategy_name, results in sorted(self.results.items(), 
                                           key=lambda x: x[1].get('metrics', {}).get('total_return_pct', 0),
                                           reverse=True):
            if 'metrics' in results:
                metrics = results['metrics']
                print(f"\nStrategy: {strategy_name}")
                print("-" * 50)
                print(f"Initial Capital: ${metrics['initial_capital']:,.2f}")
                print(f"Final Value:     ${metrics['final_value']:,.2f}")
                print(f"Total Return:    {metrics['total_return_pct']:,.2f}%")
                print(f"Annual Return:   {metrics['annual_return_pct']:,.2f}%")
                print(f"Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}")
                print(f"Max Drawdown:    {metrics['max_drawdown_pct']:,.2f}%")
                print(f"Volatility:      {metrics['volatility_pct']:,.2f}%")
                print(f"Win Rate:        {metrics['win_rate_pct']:,.2f}%")
                print(f"Trade Count:     {metrics['trade_count']}")
                print(f"Profit Factor:   {metrics['profit_factor']:,.2f}")
                
                # Print trade statistics
                if 'trades' in results and results['trades']:
                    trades = results['trades']
                    print(f"\nTrade Statistics:")
                    print(f"  Total Trades:    {len(trades)}")
                    print(f"  Total Profit:    ${sum(t.get('profit', 0) for t in trades):,.2f}")
                    print(f"  Avg Profit/Trade: ${metrics['avg_profit_per_trade']:,.2f}")
                    print(f"  Avg Win:         ${metrics['avg_win']:,.2f}")
                    print(f"  Avg Loss:        ${metrics['avg_loss']:,.2f}")
                    
                    # Calculate average holding period
                    holding_days = [t.get('holding_days', 0) for t in trades if 'holding_days' in t]
                    if holding_days:
                        avg_holding = sum(holding_days) / len(holding_days)
                        print(f"  Avg Holding Days: {avg_holding:.1f}")
        
        print("\n" + "="*80)
        
        # Print overall ranking
        print("\nSTRATEGY RANKING BY TOTAL RETURN")
        print("-" * 50)
        ranking = []
        for strategy_name, results in self.results.items():
            if 'metrics' in results:
                ranking.append((
                    strategy_name,
                    results['metrics'].get('total_return_pct', 0),
                    results['metrics'].get('sharpe_ratio', 0),
                    results['metrics'].get('max_drawdown_pct', 0)
                ))
        
        # Sort by total return
        for i, (strategy, ret, sharpe, dd) in enumerate(sorted(ranking, key=lambda x: x[1], reverse=True)):
            print(f"{i+1}. {strategy:15} - Return: {ret:7.2f}%, Sharpe: {sharpe:5.2f}, Max DD: {dd:7.2f}%")
        
        print("="*80 + "\n")

def run_all_backtests(symbols, days=252, initial_capital=100000, show_plots=True):
    """Run backtests for all strategies and generate reports."""
    # Set up logging
    setup_logging()
    
    logger.info(f"Starting backtest for {len(symbols)} symbols over {days} trading days")
    
    # Create backtest engine
    backtest = Backtest()
    
    # Run the backtest
    results = backtest.run_backtest(symbols, days, initial_capital)
    
    # Plot results
    backtest.plot_results(show_plots)
    
    # Save results
    results_file, summary_file = backtest.save_results()
    
    # Print summary
    backtest.print_summary()
    
    return results, results_file, summary_file

if __name__ == "__main__":
    # Example usage
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    results, _, _ = run_all_backtests(symbols, days=252)