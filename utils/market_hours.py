"""Market hours checking functionality."""
import logging
from datetime import datetime, time
import pytz
from config.symbols import EXCHANGE_TIMEZONES

logger = logging.getLogger('utils.market_hours')

class MarketHoursChecker:
    """Checks if markets are open for trading."""
    
    def __init__(self, ib_connection):
        """Initialize with an IB connection."""
        self.ib_connection = ib_connection
        
        # Standard market hours by exchange (simplified)
        self.market_hours = {
            'LSE': {'open': time(8, 0), 'close': time(16, 30), 'timezone': 'Europe/London'},
            'XETRA': {'open': time(9, 0), 'close': time(17, 30), 'timezone': 'Europe/Berlin'},
            'TSX': {'open': time(9, 30), 'close': time(16, 0), 'timezone': 'America/Toronto'},
            'NASDAQ': {'open': time(9, 30), 'close': time(16, 0), 'timezone': 'America/New_York'}
        }
    
    def is_market_open(self, contract):
        """Check if the market for this contract is open.
        
        Args:
            contract: IB contract object
            
        Returns:
            bool: True if market is open, False otherwise
        """
        ib = self.ib_connection.ensure_connection()
        
        try:
            # Get contract details for exchange info
            details = ib.reqContractDetails(contract)
            if not details:
                logger.warning(f"Could not get contract details for {contract.symbol}")
                return False
            
            exchange = contract.exchange
            
            # Get timezone for the exchange
            if exchange in self.market_hours:
                market_timezone = pytz.timezone(self.market_hours[exchange]['timezone'])
                market_open = self.market_hours[exchange]['open']
                market_close = self.market_hours[exchange]['close']
                
                # Get current time in market timezone
                now = datetime.now(market_timezone).time()
                
                # Check if current time is within market hours
                is_open = market_open <= now <= market_close
                
                # In a real implementation, you'd also check for holidays here
                
                return is_open
            else:
                logger.warning(f"Unknown exchange {exchange} for {contract.symbol}")
                return False
            
        except Exception as e:
            logger.error(f"Error checking market hours for {contract.symbol}: {e}")
            return False