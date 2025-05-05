"""Main entry point for the Eco ETF Trading Bot."""
import sys
import time
import argparse
import os
import json
from datetime import datetime, timedelta
import pandas as pd

from utils.logging_config import setup_logging
from core.connection import IBConnection
from core.bot import EcoETFBot
from core.portfolio import Portfolio
from data.historical import HistoricalDataProvider
from data.market_data import MarketDataProvider
from strategies.moving_average import MovingAverageCrossover
from strategies.enhanced_ma import EnhancedMovingAverage
from strategies.volatility import VolatilityBreakout
from strategies.mean_reversion import MeanReversionStrategy
from strategies.ensemble import EnsembleStrategy
from execution.order import OrderExecutor
from execution.position import PositionManager
from utils.market_hours import MarketHoursChecker
from utils.risk_management import RiskManager
from utils.advanced_risk_management import AdvancedRiskManager
from config.settings import EXECUTION_INTERVAL
from config.symbols import ETF_LIST
from tests.backtest import run_all_backtests

# Create stats directory if it doesn't exist
STATS_DIR = 'stats'
if not os.path.exists(STATS_DIR):
    os.makedirs(STATS_DIR)

# Set up trade log file
TRADE_LOG_FILE = os.path.join(STATS_DIR, 'trade_log.json')

def log_trade(trade_data):
    """Log trade details to a JSON file for stats tracking."""
    trade_data['timestamp'] = datetime.now().isoformat()
    
    # Load existing trades
    trades = []
    if os.path.exists(TRADE_LOG_FILE):
        try:
            with open(TRADE_LOG_FILE, 'r') as f:
                trades = json.load(f)
        except json.JSONDecodeError:
            # File exists but is empty or corrupted
            trades = []
    
    # Append new trade
    trades.append(trade_data)
    
    # Save updated trades
    with open(TRADE_LOG_FILE, 'w') as f:
        json.dump(trades, f, indent=2)

def generate_stats_summary():
    """Generate statistics summary from trade log."""
    if not os.path.exists(TRADE_LOG_FILE):
        return "No trade data available."
    
    try:
        with open(TRADE_LOG_FILE, 'r') as f:
            trades = json.load(f)
        
        if not trades:
            return "No trades recorded yet."
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(trades)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate basic stats
        total_trades = len(df)
        winning_trades = sum(df['profit'] > 0) if 'profit' in df.columns else 0
        losing_trades = sum(df['profit'] < 0) if 'profit' in df.columns else 0
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L stats
        total_profit = df['profit'].sum() if 'profit' in df.columns else 0
        average_profit = df['profit'].mean() if 'profit' in df.columns and len(df) > 0 else 0
        max_profit = df['profit'].max() if 'profit' in df.columns and len(df) > 0 else 0
        max_loss = df['profit'].min() if 'profit' in df.columns and len(df) > 0 else 0
        
        # Strategy performance
        strategy_performance = {}
        if 'strategy' in df.columns:
            for strategy in df['strategy'].unique():
                strategy_df = df[df['strategy'] == strategy]
                strategy_profit = strategy_df['profit'].sum() if 'profit' in strategy_df.columns else 0
                strategy_count = len(strategy_df)
                strategy_performance[strategy] = {
                    'total_trades': strategy_count,
                    'total_profit': strategy_profit,
                    'avg_profit': strategy_profit / strategy_count if strategy_count > 0 else 0
                }
        
        # Symbol performance
        symbol_performance = {}
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol]
            symbol_profit = symbol_df['profit'].sum() if 'profit' in symbol_df.columns else 0
            symbol_count = len(symbol_df)
            symbol_performance[symbol] = {
                'total_trades': symbol_count,
                'total_profit': symbol_profit,
                'avg_profit': symbol_profit / symbol_count if symbol_count > 0 else 0
            }
        
        # Format the summary
        summary = f"""
        TRADING BOT PERFORMANCE SUMMARY
        ==============================
        Period: {df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}
        Total Trades: {total_trades}
        Win Rate: {win_rate:.2%}
        
        P&L STATISTICS
        --------------
        Total P&L: ${total_profit:.2f}
        Average P&L per Trade: ${average_profit:.2f}
        Maximum Profit: ${max_profit:.2f}
        Maximum Loss: ${max_loss:.2f}
        
        STRATEGY PERFORMANCE
        -------------------
        """
        
        for strategy, stats in strategy_performance.items():
            summary += f"{strategy}: {stats['total_trades']} trades, ${stats['total_profit']:.2f} total P&L, ${stats['avg_profit']:.2f} avg\n        "
        
        summary += """
        SYMBOL PERFORMANCE
        -----------------
        """
        
        for symbol, stats in symbol_performance.items():
            summary += f"{symbol}: {stats['total_trades']} trades, ${stats['total_profit']:.2f} total P&L, ${stats['avg_profit']:.2f} avg\n        "
        
        return summary
        
    except Exception as e:
        return f"Error generating stats summary: {e}"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Eco ETF Trading Bot')
    
    parser.add_argument('--paper', action='store_true', 
                       help='Use paper trading mode (default: live trading)')
    
    parser.add_argument('--strategy', type=str, default='ensemble',
                       choices=['moving_average', 'enhanced_ma', 'volatility', 
                               'mean_reversion', 'ensemble'],
                       help='Trading strategy to use')
    
    parser.add_argument('--risk', type=str, default='advanced',
                       choices=['basic', 'advanced'],
                       help='Risk management approach')
    
    parser.add_argument('--stats', action='store_true',
                       help='Print stats summary and exit')
    
    # Add backtest-related arguments
    parser.add_argument('--backtest', action='store_true',
                       help='Run backtesting instead of live trading')
    
    parser.add_argument('--days', type=int, default=252,
                       help='Number of trading days to backtest (default: 252)')
    
    parser.add_argument('--capital', type=int, default=100000,
                       help='Initial capital for backtesting (default: $100,000)')
    
    parser.add_argument('--symbols', nargs='+', 
                       help='Symbols to backtest (space-separated)')
    
    parser.add_argument('--no-plots', action='store_true',
                       help='Disable plotting in backtest mode')
    
    return parser.parse_args()

def main():
    """Main function to start the bot or run backtests."""
    args = parse_arguments()
    
    # Set up logging
    logger = setup_logging()
    
    # If stats flag is set, just print stats and exit
    if args.stats:
        print(generate_stats_summary())
        return 0
    
    # If backtest flag is set, run backtests and exit
    if args.backtest:
        logger.info("Starting backtest mode")
        
        # Get symbols for backtesting
        symbols = args.symbols if args.symbols else [etf.symbol for etf in ETF_LIST]
        
        # Run backtests
        results, results_file, summary_file = run_all_backtests(
            symbols=symbols,
            days=args.days,
            initial_capital=args.capital,
            show_plots=not args.no_plots
        )
        
        logger.info(f"Backtest completed. Results saved to {results_file}")
        logger.info(f"Summary saved to {summary_file}")
        
        return 0
    
    # Normal trading mode
    logger.info("Starting Eco ETF Trading Bot")
    
    # Log trading mode
    trading_mode = "Paper Trading" if args.paper else "Live Trading"
    logger.info(f"Trading Mode: {trading_mode}")
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        # Create IB connection with appropriate client ID for paper/live
        client_id = 1 if args.paper else 2
        connection = IBConnection(is_paper=args.paper, client_id=client_id)
        
        # Create market hours checker
        market_hours_checker = MarketHoursChecker(connection)
        
        # Create data providers
        historical_data = HistoricalDataProvider(connection)
        market_data = MarketDataProvider(connection)
        
        # Create portfolio manager
        portfolio = Portfolio(connection)
        portfolio.initialize()
        
        # Create risk manager based on args
        if args.risk == 'advanced':
            risk_manager = AdvancedRiskManager(historical_data)
            logger.info("Using Advanced Risk Management")
        else:
            risk_manager = RiskManager()
            logger.info("Using Basic Risk Management")
        
        # Create order executor
        order_executor = OrderExecutor(connection, market_hours_checker, is_paper=args.paper)
        
        # Create position manager
        position_manager = PositionManager(connection, order_executor)
        
        # Create strategy based on args
        if args.strategy == 'moving_average':
            strategy = MovingAverageCrossover(historical_data)
            logger.info("Using Moving Average Crossover Strategy")
        elif args.strategy == 'enhanced_ma':
            strategy = EnhancedMovingAverage(historical_data)
            logger.info("Using Enhanced Moving Average Strategy")
        elif args.strategy == 'volatility':
            strategy = VolatilityBreakout(historical_data)
            logger.info("Using Volatility Breakout Strategy")
        elif args.strategy == 'mean_reversion':
            strategy = MeanReversionStrategy(historical_data)
            logger.info("Using Mean Reversion Strategy")
        elif args.strategy == 'ensemble':
            # Create multiple strategies and combine them
            ma_strategy = MovingAverageCrossover(historical_data)
            enhanced_ma = EnhancedMovingAverage(historical_data)
            vol_strategy = VolatilityBreakout(historical_data)
            mr_strategy = MeanReversionStrategy(historical_data)
            
            # Create ensemble with weighted strategies
            strategy = EnsembleStrategy(
                historical_data,
                strategies=[ma_strategy, enhanced_ma, vol_strategy, mr_strategy],
                weights=[0.1, 0.3, 0.3, 0.3]  # Enhanced MA, Volatility and Mean Reversion get more weight
            )
            logger.info("Using Ensemble Strategy")
        
        # Create and run the bot with trade logging capability
        bot = EcoETFBot(
            connection=connection,
            data_provider=historical_data,
            market_data=market_data,
            strategy=strategy,
            position_manager=position_manager,
            order_executor=order_executor,
            portfolio=portfolio,
            risk_manager=risk_manager,
            trade_logger=log_trade,
            is_paper=args.paper
        )
        
        logger.info("Bot initialized successfully")
        
        # Print current portfolio status
        logger.info(f"Starting Portfolio Value: ${portfolio.get_total_value():.2f}")
        
        # Run the bot
        logger.info("Starting trading cycles...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        
        # Print stats summary when the bot is stopped
        logger.info("Performance Summary:")
        logger.info(generate_stats_summary())
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())