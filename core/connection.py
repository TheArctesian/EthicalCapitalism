"""IBKR connection management."""
import logging
from ib_insync import IB
from config.settings import IB_HOST, IB_PORT, CLIENT_ID

logger = logging.getLogger('core.connection')

class IBConnection:
    """Manages the connection to Interactive Brokers."""
    
    def __init__(self):
        """Initialize the IB connection."""
        self.ib = IB()
        self.connected = False
    
    def connect(self):
        """Connect to IB TWS/Gateway."""
        if self.connected:
            logger.info("Already connected to IBKR")
            return self.ib
        
        try:
            self.ib.connect(IB_HOST, IB_PORT, clientId=CLIENT_ID)
            self.connected = True
            logger.info("Successfully connected to IBKR")
            return self.ib
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from IB."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
    
    def ensure_connection(self):
        """Ensure that we have an active connection to IB."""
        if not self.connected or not self.ib.isConnected():
            return self.connect()
        return self.ib