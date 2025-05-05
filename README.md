# Ethical Capitalism

My left accelerationsism contribution, a IBKR trading bot

## WARNING

READ THE LICENCE OF THIS BEFORE YOU TRY ANY SHIT. IF YOU MAKE THIS INTO A HEDGE FUND WITH A FORK I WILL FIND YOU AND SUE YOU FOR EVERYTHING YOU MADE.

If you want to contribute to this, fork it or pull it and make a pr back to the repo. Failure to do this will also result in a lawsuit.

This software is licenced under the GNU Affero General Public License v3.0 (AGPL-3.0). This is why it's good for the summary (llm wrote the following)

1. Strongest copyleft protection: It requires that all modified versions of your code remain open source, even when running as a network service.

2. Closes the "service loophole": Unlike regular GPL, AGPL specifically addresses network/cloud services. If someone uses your trading bot code to run a service (like a hedge fund's trading infrastructure), they must release their modifications.

3. Prevents commercial exploitation without sharing: Anyone who modifies and uses your code commercially must share their improvements back to the community.

4. Allows for commercial use with constraints: People can still use it commercially, but they cannot keep their modifications private.

5. Preserves attribution: Ensures you're credited as the original creator.

## Method

I did vibe code this, but my conception of vibe coding is not windsurf or cursor, I have had terrible TERRIBLE experience coding with those. I use claude-3.7 to generate the project structure API connections and then edit that code.

For the ETF choice, I used Claude-3.7s reasoning model to do ethical and financial analysis of this data.

I then edit and test the code found in the `/tests` directory.

## Usage

1. Install dependencies:

`pip install -r requirements.txt`

2. Ensure Interactive Brokers TWS or IB Gateway is running

- Enable API connections in TWS/Gateway settings
- Set API port to match the one in `config/settings.py`

3. Configure your ETFs in `config/symbols.py`

4. Adjust strategy parameters in `config/settings.py`

5. Run the bot:

```
# Run with paper trading using the ensemble strategy

python main.py --paper --strategy ensemble

# Run with live trading using the mean reversion strategy

python main.py --strategy mean_reversion

# View stats summary without starting the bot

python main.py --stats
```

## Project Structure

- `config/`: Configuration files
- `core/`: Core bot functionality
- `data/`: Market data retrieval
- `strategies/`: Trading strategies
- `execution/`: Order execution and position management
- `utils/`: Utility functions
- `logs/`: bot logs

## Adding New Strategies

To add a new strategy:

1. Create a new file in the `strategies/` directory
2. Implement a class that inherits from `BaseStrategy`
3. Update `main.py` to use your new strategy

## Disclaimer

USE AT YOUR OWN RISK
