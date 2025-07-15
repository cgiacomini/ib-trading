import time
import config
from config import DEFAULT_HOST, TRADING_PORT, DEFAULT_CLIENT_ID
from chart_handler.chart import ChartHandler
from ib_client.ib_client import IBClient
from logger import logger
from portfolio.portfolio_manager import PortfolioManager
###############################################################################
# Main entry point for the IB Client application
if __name__ == "__main__":
    logger.info("Starting IB Client...")
    logger.info(f"PYWEBVIEW_GUI: {config.PYWEBVIEW_GUI}")

    chart_handler = ChartHandler()
    client = IBClient(config.DEFAULT_HOST, config.TRADING_PORT, config.DEFAULT_CLIENT_ID)
    portfolio_manager = PortfolioManager()
    portfolio_manager.set_client(client)
    
    logger.info("Connected to IB Gateway.")

    client.set_chart_handler(chart_handler)
    logger.info("Market scanner started.")
    chart_handler.set_client(client)
    time.sleep(1)

    # Request initial data for a default symbol and timeframe
    logger.info("Requesting initial data...")

    chart_handler.request_data(config.INITIAL_SYMBOL, config.DEFAULT_TIMEFRAME)
    chart_handler.show_chart()
