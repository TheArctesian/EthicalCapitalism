"""ETF symbols configuration."""
from ib_insync import Stock

# List of non-US eco ETFs to trade (filtered for scores > 5 on both profitability and world-helping)
ETF_LIST = [
    Stock('INRG', 'LSE', 'GBP'),     # iShares Global Clean Energy UCITS ETF
    Stock('RENW', 'LSE', 'GBP'),     # L&G Clean Energy UCITS ETF
    Stock('LCEU', 'XETRA', 'EUR'),   # Amundi MSCI Europe Climate Action UCITS ETF
    Stock('VEAT', 'BIT', 'EUR'),     # VanEck Sustainable Future of Food UCITS ETF
    Stock('FOOD', 'LSE', 'GBP'),     # Rize Sustainable Future of Food UCITS ETF
    Stock('WATL', 'LSE', 'GBP'),     # L&G Clean Water UCITS ETF
    Stock('CLWD', 'SIX', 'CHF'),     # iShares Global Clean Water UCITS ETF
    Stock('RCIR', 'LSE', 'GBP'),     # BNP Paribas Easy ECPI Circular Economy Leaders UCITS ETF
    Stock('RECY', 'XETRA', 'EUR'),   # Lyxor MSCI Circular Economy ESG Filtered UCITS ETF
    Stock('WNTR', 'LSE', 'GBP'),     # HANetf Circularity Economy UCITS ETF
    Stock('BIOT', 'XETRA', 'EUR'),   # BNP Paribas Easy ECPI Global ESG Biodiversity UCITS ETF
    Stock('KLMT', 'SIX', 'CHF'),     # UBS Climate Action UCITS ETF
    Stock('ESGL', 'LSE', 'GBP'),     # iShares MSCI Global Climate Action UCITS ETF
    Stock('GEND', 'XETRA', 'EUR'),   # Lyxor Gender Equality ETF
    Stock('WELL', 'LSE', 'GBP'),     # L&G Healthcare Breakthrough UCITS ETF
    Stock('HEAL', 'XETRA', 'EUR'),   # iShares Healthcare Innovation UCITS ETF
]

# ETF exchange mapping (simplified market hours reference)
EXCHANGE_TIMEZONES = {
    'LSE': 'Europe/London',
    'XETRA': 'Europe/Berlin',
    'TSX': 'America/Toronto',
    'NASDAQ': 'America/New_York',
    'BIT': 'Europe/Rome',
    'SIX': 'Europe/Zurich'
}