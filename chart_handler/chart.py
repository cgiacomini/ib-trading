from typing import Dict, List
import queue
import time

from ibapi.contract import Contract
from ibapi.order import Order 
from lightweight_charts import Chart  # Assuming lightweight_charts is used
import pandas as pd
from signals_handler import signals_handler
from shared.queue_manager import data_queue  # Import shared queue

# Import default configuration
import config
from logger import logger


###############################################################################
class ChartHandler:
    """Handles chart creation and updates using lightweight_charts.

    This class manages the charting of historical data received from 
    Interactive Brokers.
    """

    ###########################################################################
    def __init__(self):
        """Initializes the ChartHandler with a configured chart.

        Sets up the chart with a toolbox, legend, and top bar for symbol and
        timeframe selection.
        """
        self.chart = Chart(toolbox=True, 
                           width=1000, 
                           inner_width=0.7, 
                           inner_height=1)
        # Adds a legend to the chart
        self.chart.legend(True)
        self.chart.topbar.textbox('symbol', config.INITIAL_SYMBOL)
        # Add a switcher to select graph timeframe
        self.chart.topbar.switcher('timeframe',
                                   options=config.DEFAULT_TIMEFRAME_OPTIONS,
                                   default=config.DEFAULT_TIMEFRAME,
                                   func=self.on_timeframe_selection)
        # Adds a button to take a screenshot of the chart
        self.chart.topbar.button('screenshot', 'Screenshot', 
                                 func=self.take_screenshot)
        # Set up a function to call when searching for symbol
        self.chart.events.search += self.on_search
        # Adds a hotkey to place a buy order
        self.chart.hotkey('shift', 'B', self.place_order)
        # Adds a hotkey to place a sell order
        self.chart.hotkey('shift', 'S', self.place_order)
        # Placeholder for IBClient instance
        self.client = None
        self.portfolio_manager = None
        # Placeholder for short SMA lines
        self.sma_short_line = None
        self.sma_long_line = None
        # Create a table to display portfolio data
        self.table = self.chart.create_table(
            width=0.3, height=0.2,
            headings=('symbol', 'position', 'avg cost', 'market price', 'PL'),
            widths=(0.2, 0.1, 0.2, 0.2, 0.3),
            alignments=('center', 'center', 'right', 'right', 'right'),
            position='left', func=self. on_row_click)

    ###########################################################################
    def set_client(self, client):
        """Assigns IBClient instance after creation.

        Args:
            client (IBClient): The IBClient instance managing the connection.
        """
        self.client = client

    ###########################################################################
    def on_timeframe_selection(self, chart):
        """Callback function for when a new timeframe is selected.
        A timeframe is the period of each bar in the chart (e.g., 1 min, 5 mins).

        Args:
            chart (Chart): The chart instance where the timeframe is selected.
        """
        symbol = chart.topbar['symbol'].value
        timeframe = chart.topbar['timeframe'].value
        logger.info("Selected timeframe: %s for %s", timeframe, symbol)
        # Request new data for the selected symbol and timeframe
        self.request_historical_data(symbol, timeframe)

    ###########################################################################
    def on_search(self, chart, searched_string):
        """Callback function for when a new symbol is searched.

        Args:
            chart (Chart): The chart instance where the search is performed.
            searched_string (str): The symbol string that was searched.
        """
        logger.info("Searching for symbol: %s", searched_string)
        # Request new data for the searched symbol and current timeframe
        self.request_historical_data(searched_string, chart.topbar['timeframe'].value)
        chart.topbar['symbol'].set(searched_string)
        
    ##########################################################################
    def on_row_click(self, row):
        self.chart.topbar['symbol'].set(row['symbol'])
        self.get_bar_data(row['symbol'], config.DEFAULT_TIMEFRAME)
        row['PL'] = round(row['PL']+1, 2)
        row.background_color('PL', 'green' if row['PL'] > 0 else 'red')
        self.table.footer[1] = row['symbol']
    ###########################################################################
    def update_data_with_sma(self, period: int, bars: List[Dict], data: Dict) -> Dict:
        """
        Update received data bas adding a column for the SMA of the  given period

        Args:
            period (int): The period over which to calculate the SMA.
            bars (Lis[Dict]): the current list of received data bars.
            data (Dict): the last received bars still to append.

        Returns:
            data (Dict): the last received bar with the added new SMA column for
                         the given period.
        """

        temp_bars = bars + [data]
        temp_df   = pd.DataFrame(temp_bars)
        if len(temp_df) >= period:
            sma_value = temp_df['close'].rolling(window=period).mean().iloc[-1]
            data[f'SMA_{period}'] = round(sma_value, 2)
        else:
            data[f'SMA_{period}'] = None

        return data

    ###########################################################################
    def show_sma_line(self, period: str, color: str, line_attr_name, df: pd.DataFrame):
        """Displays the Simple Moving Average (SMA) on the chart."""        
        line_attr = getattr(self, line_attr_name, None)
        logger.debug("Showing SMA for period: %s", period)
        sma_column = f'SMA_{period}'

        if sma_column not in df.columns:
            logger.warning("Missing %s column in DataFrame", sma_column)
            return

        sma_df = df[['date', sma_column]].dropna()
        if not sma_df.empty:
            if line_attr:
                line_attr.set(sma_df)
            else:
                logger.info("Creating new SMA line for SMA_%s period", period)
                new_line = self.chart.create_line(
                    name=f"SMA_{period}",
                    color=color,
                    width=1
                )
                new_line.set(sma_df)
                setattr(self, line_attr_name, new_line)
        else:
            logger.warning("No data available to display SMA_%s", period)
            return

    ###########################################################################
    def update_chart(self):
        """Updates the chart with new data from the queue.

        Retrieves available data from the queue, converts it to a pandas DataFrame,
        and updates the chart.
        """
        bars = []

        try:
            logger.info("Updating chart with new data from the queue.")

            # Drain the queue
            while not data_queue.empty():
                data = data_queue.get_nowait()
                self.update_data_with_sma(config.SMA_SHORT_PERIOD, bars, data)
                self.update_data_with_sma(config.SMA_LONG_PERIOD, bars, data)
                bars.append(data)
                logger.debug("Received data from the queue: %s", data)

                # Create markers BUY or SELL bases on some calculations
                signal = signals_handler.buy_or_sell_based_on_signals(bars)
                #print(signal)

            if not bars:
                logger.info("No new data in queue.")
                return

            # Convert to DataFrame
            df = pd.DataFrame(bars)

            # Update chart
            self.chart.set(df) # This uses columns: date/time, open, high, low, close, volume
            self.show_sma_line(config.SMA_SHORT_PERIOD, config.SMA_SHORT_COLOR, "sma_short_line", df)
            self.show_sma_line(config.SMA_LONG_PERIOD, config.SMA_LONG_COLOR, "sma_long_line", df)

        except queue.Empty:
            logger.warning("Queue was unexpectedly empty.")

        finally:
            self.chart.spinner(False)

    ###########################################################################
    def create_contract(self, symbol: str , sec_type: str, exchange: str, currency: str):

        """Create a contract object"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        return contract

    ###########################################################################
    def request_historical_data(self, symbol: str, timeframe: str):
        """Requests historical data from Interactive Brokers.

        Args:
            symbol (str): The stock symbol.
            timeframe (str): The timeframe for historical data
                             (e.g., '1 mins', '5 mins').
        """
        if not self.client.connected:
            logger.error("Not connected to IBKR")
            return None
        try:         
            logger.info("Requesting bar data for %s %s", symbol, timeframe)
            self.chart.spinner(True)

            # Create a contract object for the stock symbol
            contract = self.create_contract(symbol, 
                                            config.SEC_TYPE,
                                            config.CONTRACT_EXCHANGE,
                                            config.DEFAULT_CURRENCY)

            # Request historical data from IB API
            # The request will return data in the format specified by the 'barSizeSetting'
            req_id = self.client.get_next_req_id() # Any unique integer ID for tracking
            self.client.reqHistoricalData(
                reqId = req_id,
                contract = contract,
                endDateTime = '',  # Empty = current time
                durationStr = config.DEFAULT_HISTORICAL_DURATION,
                barSizeSetting = timeframe,
                whatToShow = config.WHAT_TO_SHOW,
                useRTH = config.USE_RTH,
                formatDate = 2,       # Format: 1=string (YYYYMMDD), 2=UNIX timestamp
                keepUpToDate = False, # Static snapshot; True = streaming update
                chartOptions = []     # Leave empty unless using special features
            )
            time.sleep(1)
            self.chart.watermark(symbol)
            logger.info("Requesting data received")

        except Exception as e:
            logger.warning("Error retrieving historical data: %s", e)
            return None

    ###########################################################################
    def show_chart(self):
        """Displays the chart in a blocking manner."""
        self.chart.show(block=True)

    ###########################################################################
    def take_screenshot(self, key):
        """Handles the screenshot button."""
        img = self.chart.screenshot()
        t = time.time()
        with open(f"screenshot-{t}.png", 'wb') as f:
            f.write(img)

    ###########################################################################
    def place_order(self, key):
        """Places a market order based on the key pressed."""
        symbol = self.chart.topbar['symbol'].value

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"

        order_action = "BUY" if key == 'B' else "SELL"
        order_quantity = 1

        self.client.reqIds(-1)
        time.sleep(2)

        if self.client.order_id:
            logger.info("Order %s for %d shares of %s", order_action, order_quantity, symbol)
            order = Order()
            order.orderType = "MKT"
            order.totalQuantity = order_quantity
            order.action = order_action

            self.client.placeOrder(self.client.order_id, contract, order)
        else:
            logger.error("Order ID not received from IB API. Cannot place order.")