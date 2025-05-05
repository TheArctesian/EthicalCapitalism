"""Configuration settings for the bot."""

# Connection settings
IB_HOST = '127.0.0.1'  # Use 'ibkr-gateway' if connecting from another container
IB_PORT = 4002  # Default port for IB Gateway
CLIENT_ID = 1

# Trading parameters
POSITION_SIZE = 100  # Base number of shares to trade
MAX_POSITIONS = 3    # Maximum number of concurrent positions
STOP_LOSS_PCT = 0.05 # 5% stop loss
TAKE_PROFIT_PCT = 0.1 # 10% take profit

# Strategy parameters
LOOKBACK_PERIOD = 20
SMA_SHORT = 5
SMA_LONG = 20

# Volatility strategy parameters
VOLATILITY_FACTOR = 2.0  # Number of standard deviations for bands

# Execution settings
EXECUTION_INTERVAL = 3600  # Run strategy every hour (in seconds)

# Risk management
MAX_PORTFOLIO_RISK = 0.02  # Maximum 2% portfolio risk per trade

# Logging settings
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/log'