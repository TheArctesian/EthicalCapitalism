"""Portfolio management functionality."""
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger('core.portfolio')

class Portfolio:
    """Manages the trading portfolio."""
    
    def __init__(self, ib_connection):
        """Initialize with an IB connection."""
        self.ib_connection = ib_connection
        self.positions = {}  # Current positions
        self.transactions = []  # Transaction history
        self.starting_cash = 0  # Starting cash amount
        self.current_cash = 0  # Current cash amount
    
    def initialize(self):
        """Initialize portfolio with account data."""
        ib = self.ib_connection.ensure_connection()
        
        try:
            # Get account summary
            account_summary = ib.accountSummary()
            
            # Find cash balance
            for summary in account_summary:
                if summary.tag == 'TotalCashValue':
                    self.starting_cash = float(summary.value)
                    self.current_cash = float(summary.value)
                    break
            
            logger.info(f"Portfolio initialized with {self.current_cash} cash")
            
            # Get current positions
            self.update_positions()
            
        except Exception as e:
            logger.error(f"Error initializing portfolio: {e}")
    
    def update_positions(self):
        """Update current positions from IB."""
        ib = self.ib_connection.ensure_connection()
        
        try:
            # Get current positions
            portfolio_items = ib.portfolio()
            
            # Reset positions
            self.positions = {}
            
            # Update with current positions
            for item in portfolio_items:
                symbol = item.contract.symbol
                if item.position != 0:
                    self.positions[symbol] = {
                        'contract': item.contract,
                        'quantity': item.position,
                        'avg_cost': item.avgCost,
                        'market_price': item.marketPrice,
                        'market_value': item.marketValue,
                        'unrealized_pnl': item.unrealizedPNL,
                        'realized_pnl': item.realizedPNL
                    }
            
            # Update cash balance
            self.update_cash()
            
            logger.info(f"Portfolio updated: {len(self.positions)} positions, {self.current_cash} cash")
            return self.positions
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return {}
    
    def update_cash(self):
        """Update current cash balance."""
        ib = self.ib_connection.ensure_connection()
        
        try:
            # Get account summary
            account_summary = ib.accountSummary()
            
            # Find cash balance
            for summary in account_summary:
                if summary.tag == 'TotalCashValue':
                    self.current_cash = float(summary.value)
                    break
                    
        except Exception as e:
            logger.error(f"Error updating cash balance: {e}")
    
    def record_transaction(self, contract, action, quantity, price, commission=0):
        """Record a transaction in the transaction history."""
        transaction = {
            'date': datetime.now(),
            'symbol': contract.symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'value': quantity * price,
            'commission': commission
        }
        
        self.transactions.append(transaction)
        logger.info(f"Recorded transaction: {action} {quantity} {contract.symbol} @ {price}")
    
    def get_position_value(self):
        """Get the current value of all positions."""
        return sum(pos['market_value'] for pos in self.positions.values())
    
    def get_total_value(self):
        """Get the total portfolio value (positions + cash)."""
        return self.get_position_value() + self.current_cash
    
    def get_performance(self):
        """Calculate portfolio performance metrics."""
        total_value = self.get_total_value()
        starting_value = self.starting_cash
        
        if starting_value == 0:
            return {
                'total_return_pct': 0,
                'total_return_value': 0
            }
            
        total_return_pct = (total_value - starting_value) / starting_value * 100
        total_return_value = total_value - starting_value
        
        return {
            'total_return_pct': total_return_pct,
            'total_return_value': total_return_value,
            'current_value': total_value,
            'starting_value': starting_value
        }
    
    def export_transactions(self, filename='transactions.csv'):
        """Export transactions to a CSV file."""
        if not self.transactions:
            logger.warning("No transactions to export")
            return False
            
        try:
            df = pd.DataFrame(self.transactions)
            df.to_csv(filename, index=False)
            logger.info(f"Exported {len(self.transactions)} transactions to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error exporting transactions: {e}")
            return False