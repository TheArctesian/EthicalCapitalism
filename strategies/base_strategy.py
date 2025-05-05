"""Base strategy class for the trading bot."""
import logging

logger = logging.getLogger('strategies.base')

class BaseStrategy:
    """Base class for all trading strategies."""
    
    def __init__(self, data_provider):
        """Initialize the strategy with a data provider."""
        self.data_provider = data_provider
        
    def generate_signals(self, contracts):
        """Generate trading signals for the given contracts.
        
        This method should be implemented by subclasses.
        
        Args:
            contracts: List of IB contract objects to analyze
            
        Returns:
            dict: A dictionary of signals by symbol
        """
        raise NotImplementedError("Subclasses must implement generate_signals")