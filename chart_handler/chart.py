import time
import queue
import pandas as pd
from shared.queue_manager import data_queue  # Import shared queue
from ibapi.contract import Contract
from ibapi.order import Order 
from ibapi.client import ScannerSubscription
from ibapi.tag_value import TagValue
from lightweight_charts import Chart  # Assuming lightweight_charts is used

# Import default configuration
import config
from logger import logger


###############################################################################
class ChartHandler:
    """Handles chart creation and updates using lightweight_charts.

    This class manages the charting of historical data received from Interactive Brokers.
    """

    ###########################################################################
    def __init__(self):
        """Initializes the ChartHandler with a configured chart.

        Sets up the chart with a toolbox, legend, and top bar for symbol and
        timeframe selection.
        """
        self.chart = Chart(toolbox=True, width=1000, inner_width=0.7, inner_height=1)
        # Adds a legend to the chart
        self.chart.legend(True)
        self.chart.topbar.textbox('symbol', config.INITIAL_SYMBOL)
        # Add a switcher to select graph timeframe
        self.chart.topbar.switcher('timeframe',
                                   options=config.DEFAULT_TIMEFRAME_OPTIONS,
                                   default=config.DEFAULT_TIMEFRAME,
                                   func=self.on_timeframe_selection)
        # Adds a button to take a screenshot of the chart
        self.chart.topbar.button('screenshot', 'Screenshot', func=self.take_screenshot)
        # Set up a function to call when searching for symbol
        self.chart.events.search += self.on_search
        # Adds a hotkey to place a buy order
        self.chart.hotkey('shift', 'B', self.place_order)
        # Adds a hotkey to place a sell order
        self.chart.hotkey('shift', 'S', self.place_order)
        # Placeholder for IBClient instance
        self.client = None
        # Placeholder for short SMA lines
        self.sma_short_line = None
        self.sma_long_line = None
        # Create a table to display portfolio data
        self.table = self.chart.create_table( 
            name='portfolio',
            width=0.3, height=0.2,
            headings=('symbol', 'position', 'avg cost', 'market price', 'unrealized pnl'),
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
        logger.info(f"Selected timeframe: {timeframe} for {symbol}")
        # Request new data for the selected symbol and timeframe
        self.request_data(symbol, timeframe)

    ###########################################################################
    def on_search(self, chart, searched_string):
        """Callback function for when a new symbol is searched.

        Args:
            chart (Chart): The chart instance where the search is performed.
            searched_string (str): The symbol string that was searched.
        """
        logger.info(f"Searching for symbol: {searched_string}")
        # Request new data for the searched symbol and current timeframe
        self.request_data(searched_string, chart.topbar['timeframe'].value)
        chart.topbar['symbol'].set(searched_string)

    ##########################################################################
    def on_row_click(self, row):
        self.chart.topbar['symbol'].set(row['symbol'])
        self.get_bar_data(row['symbol'], config.DEFAULT_TIMEFRAME)

    ##########################################################################
    def calculate_sma(self, df, period: int = 20):
        """Calculates the Simple Moving Average (SMA) for a given DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing 'close' prices.
            period (int): The period over which to calculate the SMA.

        Returns:
            pd.Series: Series containing the calculated SMA values.
        """
        logger.debug(f"Calculating SMA for period: {period}")
        if 'close' not in df.columns:
            logger.error("DataFrame must contain 'close' column for SMA calculation.")
            return pd.Series(dtype=float) # Return an empty Series
        if period <= 0:
            logger.error("Period must be a positive integer for SMA calculation.")
            return pd.Series(dtype=float) # Return an empty Series
        # Calculate the rolling mean of the 'close' prices over the specified period
        # dropna is cleaning the DataFrame to make sure we're only working with rows
        # where both SMA values are valid (not NaN).
        # The first  rows will be NaN since not enough data to calculeate the mean.
        return pd.DataFrame({'time': df['date'],
                             f'SMA {period}': df['close'].rolling(window=period).mean()}).dropna()

    ###########################################################################
    def update_chart(self):
        """Updates the chart with new data from the queue.

        Retrieves available data from the queue, converts it to a pandas DataFrame,
        and updates the chart.
        """
        bars = []
        try:
            logger.info("Updating chart with new data from the queue.")
            while True:
                data = data_queue.get_nowait()
                bars.append(data)
                logger.debug(f"Received data from the queue: {bars[-1]}")
        except queue.Empty:
            logger.info("No new data in queue.")
        finally:
            # set the data on the chart
            df = pd.DataFrame(bars)
            if not df.empty:
                self.chart.set(df)

                # Compute SMA_SHORT_PERIOD
                sma_short_line_df = self.calculate_sma(df, config.SMA_SHORT_PERIOD)
                if not sma_short_line_df.empty:
                    if self.sma_short_line:
                        self.sma_short_line.set(sma_short_line_df)
                    else:
                        self.sma_short_line = self.chart.create_line(
                            name=f"SMA {config.SMA_SHORT_PERIOD}",
                            color='blue',
                            width=1
                        )
                        self.sma_short_line.set(sma_short_line_df)

                # Compute SMA_LONG_PERIOD
                sma_long_line_df = self.calculate_sma(df, config.SMA_LONG_PERIOD)
                if not sma_long_line_df.empty:
                    if self.sma_long_line:
                        self.sma_long_line.set(sma_long_line_df)
                    else:
                        self.sma_long_line = self.chart.create_line(
                            name=f"SMA {config.SMA_LONG_PERIOD}",
                            color='red',
                            width=1
                        )
                        self.sma_long_line.set(sma_long_line_df)
            else:
                logger.warning("No data to update the chart.")
        self.chart.spinner(False)

    ###########################################################################
    def request_data(self, symbol: str, timeframe: str):
        """Requests historical data from Interactive Brokers.

        Args:
            symbol (str): The stock symbol.
            timeframe (str): The timeframe for historical data (e.g., '1 mins', '5 mins').
        """
        logger.info(f"Requesting bar data for {symbol} {timeframe}")
        self.chart.spinner(True)
        # Create a contract object for the stock symbol
        contract = Contract()
        contract.symbol = symbol # Stock ticker symbol
        contract.secType = 'STK' # Security type 'STK' = stock. Other types include 'OPT', 'FUT', 'CASH', etc
        contract.exchange = 'SMART' # Exchange to use for the contract
        contract.currency = config.DEFAULT_CURRENCY # Currency for the contract, e.g., 'USD'
        what_to_show = 'TRADES' # Data type to request, 'TRADES' for trade data
                                # 'MIDPOINT' for midpoint data, 'BID', 'ASK' for bid and ask data, etc

        # Request historical data from IB API
        # The request will return data in the format specified by the 'barSizeSetting'
        self.client.reqHistoricalData(
            2,                  # requestId: any unique integer ID for tracking
            contract,           # The contract object (symbol, type, etc.)
            endDateTime = '',     # Empty = current time
            durationStr = config.DEFAULT_HISTORICAL_DURATION,  # e.g., '1 D', '1 W', '1 M'
            barSizeSetting = timeframe,  # e.g., '1 min', '5 mins', '1 day'
            whatToShow = what_to_show,   # Type of data ('TRADES')
            useRTH = True,        # Only show data from regular trading hours (RTH)
            formatDate = 2,       # Format: 1=string (YYYYMMDD), 2=UNIX timestamp
            keepUpToDate = False, # Static snapshot; True = streaming update
            chartOptions = []     # Leave empty unless using special features
        )

        time.sleep(1)
        self.chart.watermark(symbol)
        logger.info(f"Requesting data received")

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
            logger.info(f"Placing {order_action} order for {order_quantity} shares of {symbol}")
            order = Order()
            order.orderType = "MKT"
            order.totalQuantity = order_quantity
            order.action = order_action

            self.client.placeOrder(self.client.order_id, contract, order)
        else:
            logger.error("Order ID not received from IB API. Cannot place order.")

