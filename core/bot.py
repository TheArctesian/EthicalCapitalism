"""Main bot class that orchestrates the trading process."""
import logging
import time
from config.settings import EXECUTION_INTERVAL
from config.symbols import ETF_LIST

logger = logging.getLogger('core.bot')

class EcoETFBot:
    """Main trading bot class."""
    
    def __init__(self, connection, data_provider, market_data, strategy, 
                position_manager, order_executor, portfolio, risk_manager):
        """Initialize the bot with its components."""
        self.connection = connection
        self.data_provider = data_provider
        self.market_data = market_data
        self.strategy = strategy
        self.position_manager = position_manager
        self.order_executor = order_executor
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.etfs = ETF_LIST
        self.running = False
    
    def execute_cycle(self):
        """Execute one full trading cycle."""
        logger.info("Starting trading cycle")
        
        try:
            # Update portfolio and positions
            self.portfolio.update_positions()
            self.position_manager.update_positions()
            
            # Manage existing positions (check stop losses, etc.)
            self.position_manager.manage_open_positions()
            
            # Generate new signals
            signals = self.strategy.generate_signals(self.etfs)
            
            # Execute signals if risk allows
            for symbol, signal_data in signals.items():
                # Find the contract for this symbol
                contract = next((etf for etf in self.etfs if etf.symbol == symbol), None)
                if not contract:
                    continue
                
                action = signal_data['action']
                price = signal_data['price']
                volatility = signal_data.get('volatility', 0.2)
                
                # Check if we can take this position based on risk
                portfolio_value = self.portfolio.get_total_value()
                if not self.risk_manager.check_portfolio_risk(self.portfolio):
                    logger.info(f"Skipping {symbol} {action} due to portfolio risk limits")
                    continue
                
                # Implement the signal
                if action == 'BUY' and not self.position_manager.has_position(symbol):
                    # Calculate position size based on risk management
                    quantity = self.risk_manager.calculate_position_size(
                        price, volatility, portfolio_value)
                    
                    # Place the order
                    order_result = self.order_executor.place_market_order(
                        contract, 'BUY', quantity)
                    
                    if order_result and 'fill_price' in order_result:
                        # Record the transaction
                        self.portfolio.record_transaction(
                            contract, 'BUY', quantity, order_result['fill_price'])
                        
                elif action == 'SELL' and self.position_manager.has_position(symbol):
                    position = self.position_manager.positions[symbol]
                    
                    # Place the order
                    order_result = self.order_executor.place_market_order(
                        contract, 'SELL', abs(position['quantity']))
                    
                    if order_result and 'fill_price' in order_result:
                        # Record the transaction
                        self.portfolio.record_transaction(
                            contract, 'SELL', abs(position['quantity']), 
                            order_result['fill_price'])
            
            # Output portfolio summary
            performance = self.portfolio.get_performance()
            logger.info(f"Portfolio value: ${self.portfolio.get_total_value():.2f} "
                       f"(Return: {performance['total_return_pct']:.2f}%)")
            
            logger.info("Trading cycle completed")
            
        except Exception as e:
            logger.error(f"Error during trading cycle: {e}")
    
    def run(self):
        """Run the trading bot."""
        logger.info("Starting Trading Bot")
        self.running = True
        
        try:
            while self.running:
                self.execute_cycle()
                logger.info(f"Waiting {EXECUTION_INTERVAL} seconds until next cycle")
                time.sleep(EXECUTION_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading bot."""
        self.running = False
        
        # Clean up resources
        try:
            # Unsubscribe from market data
            self.market_data.unsubscribe_all()
            
            # Export transaction history
            self.portfolio.export_transactions()
            
            # Disconnect from IB
            self.connection.disconnect()
            
            logger.info("Bot resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        logger.info("Bot stopped")