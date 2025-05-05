"""Real-time market data functionality."""
import logging
from ib_insync import util

logger = logging.getLogger('data.market_data')

class MarketDataProvider:
    """Provider for real-time market data."""
    
    def __init__(self, ib_connection):
        """Initialize with an IB connection."""
        self.ib_connection = ib_connection
        self.active_subscriptions = {}  # Symbol -> ticker
    
    def get_market_price(self, contract, timeout=5):
        """Get the current market price for a contract.
        
        Args:
            contract: IB contract object
            timeout: Time to wait for data in seconds
            
        Returns:
            float: Current market price or None if unavailable
        """
        ib = self.ib_connection.ensure_connection()
        
        try:
            if contract.symbol in self.active_subscriptions:
                # We're already subscribed to this ticker
                ticker = self.active_subscriptions[contract.symbol]
            else:
                # Create a new subscription
                ticker = ib.reqMktData(contract)
                self.active_subscriptions[contract.symbol] = ticker
            
            # Wait for data to arrive
            for _ in range(timeout):
                ib.waitOnUpdate(timeout=1)
                last_price = ticker.marketPrice()
                if last_price > 0:
                    return last_price
            
            logger.warning(f"Couldn't get market price for {contract.symbol} within timeout")
            return None
            
        except Exception as e:
            logger.error(f"Error getting market price for {contract.symbol}: {e}")
            return None
    
    def get_bid_ask(self, contract, timeout=5):
        """Get the current bid and ask prices for a contract."""
        ib = self.ib_connection.ensure_connection()
        
        try:
            if contract.symbol in self.active_subscriptions:
                ticker = self.active_subscriptions[contract.symbol]
            else:
                ticker = ib.reqMktData(contract)
                self.active_subscriptions[contract.symbol] = ticker
            
            # Wait for data to arrive
            for _ in range(timeout):
                ib.waitOnUpdate(timeout=1)
                bid = ticker.bid
                ask = ticker.ask
                if bid > 0 and ask > 0:
                    return {'bid': bid, 'ask': ask}
            
            logger.warning(f"Couldn't get bid/ask for {contract.symbol} within timeout")
            return None
            
        except Exception as e:
            logger.error(f"Error getting bid/ask for {contract.symbol}: {e}")
            return None
    
    def unsubscribe(self, contract):
        """Unsubscribe from market data for a contract."""
        ib = self.ib_connection.ensure_connection()
        
        if contract.symbol in self.active_subscriptions:
            ib.cancelMktData(contract)
            del self.active_subscriptions[contract.symbol]
            logger.info(f"Unsubscribed from market data for {contract.symbol}")
    
    def unsubscribe_all(self):
        """Unsubscribe from all market data."""
        ib = self.ib_connection.ensure_connection()
        
        for symbol, ticker in list(self.active_subscriptions.items()):
            ib.cancelMktData(ticker.contract)
            logger.info(f"Unsubscribed from market data for {symbol}")
        
        self.active_subscriptions = {}