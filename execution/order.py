"""Order execution functionality."""
import logging
from ib_insync import MarketOrder, StopOrder, LimitOrder

logger = logging.getLogger('execution.order')

class OrderExecutor:
    """Handles order execution."""
    
    def __init__(self, ib_connection, market_hours_checker, is_paper=False):
        """Initialize with an IB connection."""
        self.ib_connection = ib_connection
        self.market_hours_checker = market_hours_checker
        self.is_paper = is_paper
    
    def place_market_order(self, contract, action, quantity):
        """Place a market order.
        
        Args:
            contract: IB contract object
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            
        Returns:
            dict: Order information if successful, None otherwise
        """
        ib = self.ib_connection.ensure_connection()
        
        # Check if market is open
        if not self.market_hours_checker.is_market_open(contract):
            logger.warning(f"Market closed for {contract.symbol}, skipping order")
            return None
        
        try:
            # Create and place the order
            order = MarketOrder(action, quantity)
            
            # Log paper trading if enabled
            if self.is_paper:
                logger.info(f"[PAPER] Placed {action} market order for {quantity} shares of {contract.symbol}")
                
                # Simulate a fill with current market price
                current_price = None
                ticker = ib.reqMktData(contract)
                for _ in range(5):  # Try for 5 seconds
                    ib.waitOnUpdate(timeout=1)
                    current_price = ticker.marketPrice()
                    if current_price > 0:
                        break
                
                # Cancel market data subscription
                ib.cancelMktData(contract)
                
                if current_price and current_price > 0:
                    # Return simulated fill info
                    return {
                        'status': 'filled',
                        'fill_price': current_price,
                        'quantity': quantity,
                        'action': action,
                        'paper_trade': True
                    }
                else:
                    logger.error("[PAPER] Could not get market price for simulation")
                    return None
            
            # Real trading
            trade = ib.placeOrder(contract, order)
            logger.info(f"Placed {action} market order for {quantity} shares of {contract.symbol}")
            
            # Wait for order to fill
            for i in range(10):  # Try for a limited time
                ib.waitOnUpdate(timeout=5)
                if trade.isDone():
                    break
            
            # Check status
            if trade.orderStatus.status == 'Filled':
                fill_price = trade.orderStatus.avgFillPrice
                logger.info(f"Order filled at {fill_price}")
                
                return {
                    'status': 'filled',
                    'fill_price': fill_price,
                    'quantity': quantity,
                    'action': action,
                    'paper_trade': False,
                    'commission': trade.orderStatus.commission if hasattr(trade.orderStatus, 'commission') else 0
                }
            else:
                logger.error(f"Order not filled: {trade.orderStatus.status}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order for {contract.symbol}: {e}")
            return None
    
    def place_stop_order(self, contract, action, quantity, stop_price):
        """Place a stop order."""
        ib = self.ib_connection.ensure_connection()
        
        # Paper trading simulation
        if self.is_paper:
            logger.info(f"[PAPER] Placed {action} stop order for {quantity} shares of {contract.symbol} at {stop_price}")
            return {
                'status': 'submitted',
                'stop_price': stop_price,
                'quantity': quantity,
                'action': action,
                'paper_trade': True
            }
        
        try:
            order = StopOrder(action, quantity, stop_price)
            trade = ib.placeOrder(contract, order)
            logger.info(f"Placed {action} stop order for {quantity} shares of {contract.symbol} at {stop_price}")
            return trade
        except Exception as e:
            logger.error(f"Error placing stop order for {contract.symbol}: {e}")
            return None