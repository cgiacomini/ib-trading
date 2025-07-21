""" Main application code"""
import time
import sys
import os
import config
from logger import logger
from chart_handler.chart import ChartHandler
from ib_client.ib_client import IBClient
from ib_client.ib_client_mock import MockIBClient

###############################################################################
# Main entry point for the IB Client application
if __name__ == "__main__":
    logger.info("Starting IB Client...")
    logger.info("PYWEBVIEW_GUI: %s", config.PYWEBVIEW_GUI)

    chart_handler = ChartHandler()

    # Choose real or mock client
    if config.MOCK_MODE:
        logger.info("Running in MOCK mode.")
        client = MockIBClient()
    else:
        client = IBClient()
        if not client.connect(config.DEFAULT_HOST, config.TRADING_PORT, config.DEFAULT_CLIENT_ID):
            sys.exit()

    client.set_chart_handler(chart_handler)
    chart_handler.set_client(client)
    time.sleep(1)

    # Request initial data
    chart_handler.request_historical_data(config.INITIAL_SYMBOL,
                                          config.DEFAULT_TIMEFRAME)
    chart_handler.show_chart()
