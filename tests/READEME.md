This is where I will do retroactive tests to see the efficacy of my trading bot.

# Testing Framework for Eco ETF Trading Bot

This directory contains tools for testing and backtesting the Eco ETF Trading Bot.

## Backtesting Framework

The backtesting system allows you to test all available trading strategies against historical market data and compare their performance.

### Features

- Test all strategies on historical data for specified symbols
- Customizable testing period (number of trading days)
- Detailed performance metrics:
  - Total and annual returns
  - Sharpe ratio
  - Maximum drawdown
  - Win rate
  - Profit factor
  - Trade statistics
- Comparative analysis between strategies
- Visual results (equity curves, performance charts)
- Export results to JSON and CSV files

### Usage

You can run backtests directly from the command line:

```bash
# Run backtest for default ETF symbols with 1 year of data
python main.py --backtest

# Run backtest for specific symbols
python main.py --backtest --symbols AAPL MSFT GOOGL

# Run backtest for 6 months (126 trading days)
python main.py --backtest --days 126

# Run backtest with custom initial capital
python main.py --backtest --capital 50000

# Run backtest without showing plots
python main.py --backtest --no-plots
```

### Output

The backtest will generate:

1. JSON Results File: Detailed results including all trades and daily portfolio values
2. CSV Summary File: Condensed performance metrics for easy comparison
3. Performance Charts: Equity curves and comparative performance metrics
4. Console Output: Summary of results with strategy rankings

## Data

The backtest framework will use cached data when available. For initial runs, it will generate mock data or download real data if available.
Adding New Tests

To add new test types:

1. Create a new Python file in the tests directory
2. Implement your test logic
3. (Optional) Add command-line arguments to main.py to access your test

## Examples
To use the backtesting functionality, you can run commands like:

```bash
# Run backtest for all strategies with 1 year of data
python main.py --backtest

# Run backtest for specific symbols over 3 months
python main.py --backtest --symbols INRG RENW KGRN --days 63

# Run backtest with $50,000 starting capital without showing plots
python main.py --backtest --capital 50000 --no-plots