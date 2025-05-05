"""Position management functionality."""
import logging
from config.settings import STOP_LOSS_PCT, TAKE_PROFIT_PCT

logger = logging.getLogger('execution.position')

class PositionManager:
    """Manages trading positions."""
    
    def __init__(self, ib_connection, order_executor):
        """Initialize with IB connection and order executor."""
        self.ib_connection = ib_connection
        self.order_executor = order_executor
        self.positions = {}  # Symbol -> position data
    
    def update_positions(self):
        """Update the current positions from IB."""
        ib = self.ib_connection.ensure_connection()
        
        # Get current positions from IB
        portfolio = ib.portfolio()
        
        # Update our position tracking
        for item in portfolio:
            symbol = item.contract.symbol
            if item.position != 0:
                if symbol not in self.positions:
                    # New position we're tracking
                    self.positions[symbol] = {
                        'contract': item.contract,
                        'quantity': item.position,
                        'avg_cost': item.avgCost,
                        'market_price': item.marketPrice,
                        'market_value': item.marketValue,
                        'stop_loss_price': item.avgCost * (1 - STOP_LOSS_PCT) if item.position > 0 else item.avgCost * (1 + STOP_LOSS_PCT),
                        'take_profit_price': item.avgCost * (1 + TAKE_PROFIT_PCT) if item.position > 0 else item.avgCost * (1 - TAKE_PROFIT_PCT)
                    }
                else:
                    # Update existing position
                    self.positions[symbol].update({
                        'quantity': item.position,
                        'market_price': item.marketPrice,
                        'market_value': item.marketValue
                    })
            elif symbol in self.positions:
                # Position closed
                del self.positions[symbol]
        
        logger.info(f"Updated positions: {len(self.positions)} active positions")
        return self.positions
    
    def manage_open_positions(self):
        """Check and manage existing positions (stop loss, etc)."""
        self.update_positions()
        
        for symbol, position in list(self.positions.items()):
            contract = position['contract']
            quantity = position['quantity']
            market_price = position['market_price']
            
            # Check stop loss
            if quantity > 0 and market_price <= position['stop_loss_price']:
                logger.info(f"Stop loss triggered for {symbol} at {market_price}")
                self.order_executor.place_market_order(contract, 'SELL', abs(quantity))
            
            # Check take profit
            elif quantity > 0 and market_price >= position['take_profit_price']:
                logger.info(f"Take profit triggered for {symbol} at {market_price}")
                self.order_executor.place_market_order(contract, 'SELL', abs(quantity))
            
            # Short position stop loss
            elif quantity < 0 and market_price >= position['stop_loss_price']:
                logger.info(f"Stop loss triggered for short position {symbol} at {market_price}")
                self.order_executor.place_market_order(contract, 'BUY', abs(quantity))
    
    def get_position_count(self):
        """Get the current number of positions."""
        return len(self.positions)
    
    def has_position(self, symbol):
        """Check if we have a position for the given symbol."""
        return symbol in self.positions