import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Retrieve environment variables
PYWEBVIEW_GUI = os.getenv("PYWEBVIEW_GUI","qt")
DEFAULT_HOST = os.getenv("DEFAULT_HOST", "127.0.0.1")
TRADING_PORT = int(os.getenv("TRADING_PORT", 7497))
LIVE_TRADING_PORT = int(os.getenv("LIVE_TRADING_PORT", 7497))
DEFAULT_CLIENT_ID = int(os.getenv("DEFAULT_CLIENT_ID", 0))
INITIAL_SYMBOL = os.getenv("INITIAL_SYMBOL", "AAPL")
LIVE_TRADING = False
if LIVE_TRADING:
    TRADING_PORT = LIVE_TRADING_PORT

# Other constants
# Default timeframe for chart
DEFAULT_TIMEFRAME = "30 secs" # Default timeframe for chart
DEFAULT_TIMEFRAME_OPTIONS = ('30 secs', '1 min', '5 mins', '15 mins', '1 hour')
# Timeout for queue operations
DATA_QUEUE_TIMEOUT = 5 
# Default duration for historical data requests
DEFAULT_HISTORICAL_DURATION = os.getenv("DEFAULT_HISTORICAL_DURATION", "30 D")
# Exchange to use for the contract (e.g. SMART).
CONTRACT_EXCHANGE = 'SMART'
# Currency for the contract, e.g., 'USD'
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")
# Default Security type 'STK' = stock. Other types include 'OPT', 'FUT', 'CASH', etc
SEC_TYPE = 'STK'
# USE Regular Trading Hours)
USE_RTH = True
# Default Data type to request 'TRADES' for trade data 'MIDPOINT' for midpoint data, 'BID', 'ASK' for bid and ask data, etc
WHAT_TO_SHOW = 'TRADES'
# Default window period for Simple Moving Average (SMA)
SMA_SHORT_PERIOD = 20
# Default window period for Long Simple Moving Average (SMA)
SMA_LONG_PERIOD = 50
# Color for short SMA line
SMA_SHORT_COLOR = "blue"
# Color for long SMA line
# Default market scanner code
SMA_LONG_COLOR = "red"
SCAN_CODE = "Top Percent Gainers"
