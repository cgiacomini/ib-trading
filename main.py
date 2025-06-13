import os
import time
from config import DEFAULT_HOST, TRADING_PORT, DEFAULT_CLIENT_ID
from chart_handler.chart import ChartHandler
from ib_client.ib_client import IBClient

# Import default configuration
from config import INITIAL_SYMBOL    # Import default configuration
from config import DEFAULT_TIMEFRAME 

if __name__ == "__main__":
    print("Starting IB Client...")
    print("PYWEBVIEW_GUI:", os.getenv("PYWEBVIEW_GUI"))

    chart_handler = ChartHandler()
    client = IBClient(DEFAULT_HOST, TRADING_PORT, DEFAULT_CLIENT_ID)
    print("Connected to IB Gateway.")

    client.set_chart_handler(chart_handler)
    chart_handler.set_client(client)
    time.sleep(1)

    # Request initial data for a default symbol and timeframe
    print("Requesting initial data...")
    chart_handler.request_data(INITIAL_SYMBOL, DEFAULT_TIMEFRAME)
    chart_handler.subscribe_marketscan("HOT_BY_VOLUME")
    chart_handler.show_chart()
