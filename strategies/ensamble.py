"""Ensemble strategy that combines multiple strategies."""
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger('strategies.ensemble')

class EnsembleStrategy(BaseStrategy):
    """Combines signals from multiple strategies with weighted voting."""
    
    def __init__(self, data_provider, strategies, weights=None):
        """Initialize the ensemble strategy.
        
        Args:
            data_provider: Data provider object
            strategies: List of strategy objects
            weights: Optional list of weights for each strategy (default: equal)
        """
        super().__init__(data_provider)
        self.strategies = strategies
        
        # Set equal weights if not provided
        if weights is None:
            self.weights = [1.0 / len(strategies)] * len(strategies)
        else:
            # Normalize weights to sum to 1
            total = sum(weights)
            self.weights = [w / total for w in weights]
    
    def generate_signals(self, contracts):
        """Generate signals by combining results from all strategies."""
        all_signals = {}
        
        # Collect signals from each strategy
        for i, strategy in enumerate(self.strategies):
            strategy_signals = strategy.generate_signals(contracts)
            weight = self.weights[i]
            
            # Store signals with strategy weight
            for symbol, signal_data in strategy_signals.items():
                if symbol not in all_signals:
                    all_signals[symbol] = {
                        'buy_score': 0.0,
                        'sell_score': 0.0,
                        'price': signal_data['price'],
                        'volatility': signal_data.get('volatility', 0.2),
                        'strategies': []
                    }
                
                # Add this strategy's vote
                if signal_data['action'] == 'BUY':
                    all_signals[symbol]['buy_score'] += weight
                elif signal_data['action'] == 'SELL':
                    all_signals[symbol]['sell_score'] += weight
                
                # Track which strategies generated signals
                all_signals[symbol]['strategies'].append({
                    'name': strategy.__class__.__name__,
                    'action': signal_data['action'],
                    'weight': weight
                })
        
        # Determine final signals based on consensus
        signals = {}
        for symbol, data in all_signals.items():
            action = None
            threshold = 0.6  # Require 60% consensus for a signal
            
            if data['buy_score'] > threshold and data['buy_score'] > data['sell_score']:
                action = 'BUY'
            elif data['sell_score'] > threshold and data['sell_score'] > data['buy_score']:
                action = 'SELL'
            
            if action:
                signals[symbol] = {
                    'action': action,
                    'price': data['price'],
                    'volatility': data['volatility'],
                    'confidence': data['buy_score'] if action == 'BUY' else data['sell_score'],
                    'contributing_strategies': ', '.join([s['name'] for s in data['strategies'] 
                                                        if s['action'] == action])
                }
                
                logger.info(f"Ensemble generated {action} signal for {symbol} with " 
                           f"confidence {signals[symbol]['confidence']:.2f}")
                
        return signals