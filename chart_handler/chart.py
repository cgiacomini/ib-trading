import time
import queue
import pandas as pd
from shared.queue_manager import data_queue  # Import shared queue
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.scanner import ScannerSubscription
from ibapi.tag_value import TagValue
from lightweight_charts import Chart  # Assuming lightweight_charts is used

# Import default configuration
from config import INITIAL_SYMBOL    # Import default configuration
from config import DEFAULT_TIMEFRAME, DEFAULT_HISTORICAL_DURATION, DEFAULT_CURRENCY


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
        self.chart = Chart(toolbox=True, width=1000, inner_width=0.6, inner_height=1)
        # Adds a legend to the chart
        self.chart.legend(True) 
        self.chart.topbar.textbox('symbol', INITIAL_SYMBOL)
        self.chart.topbar.switcher('timeframe', 
                                   ('5 mins', '15 mins', '1 hour'), 
                                   default=DEFAULT_TIMEFRAME, 
                                   func=self.on_timeframe_selection)
        
        # Adds a button to take a screenshot of the chart
        self.chart.topbar.button('screenshot', 'Screenshot', func=self.take_screenshot)
        
        # Set up a function to call when searching for symbol
        self.chart.events.search += self.on_search
        # Adds a hotkey to place a buy order
        self.chart.hotkey('shift', 'B', self.place_order)
        # Adds a hotkey to place a sell order
        self.chart.hotkey('shift', 'S', self.place_order)
        # Tracks indicator lines on the chart
        self.current_lines = []
        # Placeholder for IBClient instance
        self.client = None  

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

        Args:
            chart (Chart): The chart instance where the timeframe is selected.
        """ 
        symbol = chart.topbar['symbol'].value
        timeframe = chart.topbar['timeframe'].value
        print(f"Selected timeframe: {timeframe} for {symbol}")
        self.request_data(symbol, timeframe)

    ###########################################################################
    def on_search(self, chart, searched_string):
        """Callback function for when a new symbol is searched.

        Args:
            chart (Chart): The chart instance where the search is performed.
            searched_string (str): The symbol string that was searched.
        """
        self.request_data(searched_string, chart.topbar['timeframe'].value)
        chart.topbar['symbol'].set(searched_string)

    ###########################################################################
    def on_horizontal_line_move(self, chart, line):
        """Callback for when the user moves the horizontal line.

        Args:
            chart (Chart): The chart instance.
            line (Line): The moved horizontal line.
        """
        print(f'Horizontal line moved to: {line.price}')

    ###########################################################################
    def update_chart(self):
        """Updates the chart with new data from the queue.

        Retrieves available data, converts it to a pandas DataFrame, and updates the chart.
        """
        bars = []
        try:
            while True:
                data = data_queue.get_nowait()
                bars.append(data)
        except queue.Empty:
            print("No new data in queue.")
        finally:
            df = pd.DataFrame(bars)
            self.chart.set(df)

            if not df.empty:
                self.chart.horizontal_line(df['high'].max(), func=self.on_horizontal_line_move)
                self.chart.spinner(False)

    ###########################################################################   
    def request_data(self, symbol: str, timeframe: str):
        """Requests historical data from Interactive Brokers.

        Args:
            symbol (str): The stock symbol.
            timeframe (str): The timeframe for historical data (e.g., '5 mins').
        """
        print(f"Requesting bar data for {symbol} {timeframe}")
        self.chart.spinner(True)

        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = DEFAULT_CURRENCY
        what_to_show = 'TRADES'

        # endDateTime
        self.client.reqHistoricalData(
            2, contract, #
            endDateTime='', # Empty string for current time
            durationStr=DEFAULT_HISTORICAL_DURATION, # Default for 30 days back
            barSizeSetting=timeframe, 
            whatToShow=what_to_show,  # 'TRADES' for trade data
            useRTH=True,  # Regular Trading Hours
            formatDate=2, # 1: date as string, 2: date as timestamp
            keepUpToDate=False, # 
            chartOptions=[]
        )

        time.sleep(1)
        self.chart.watermark(symbol)

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
            print(f"Placing {order_action} order for {order_quantity} shares of {symbol}")
            order = Order()
            order.orderType = "MKT"
            order.totalQuantity = order_quantity
            order.action = order_action

            self.client.placeOrder(self.client.order_id, contract, order)

    ###########################################################################
    def subscribe_marketscan(self, scan_code: str):
        """Subscribes to IB market scan and retrieves results."""
        scannerSubscription = ScannerSubscription()
        scannerSubscription.instrument = "STK"
        scannerSubscription.locationCode = "STK.US.MAJOR"
        scannerSubscription.scanCode = scan_code

        # Create tag values for the scanner subscription
        # Example tag values to filter results
        # You can adjust these values based on your requirements
        # For example, filter stocks with volume above 1000 and average volume above 10000
        tagValues = []
        tagValues.append(TagValue("optVolumeAbove", "1000"))
        tagValues.append(TagValue("avgVolumeAbove", "10000"))

        # Request the scanner subscription
        self.client.reqScannerSubscription(7002, scannerSubscription, [], tagValues)
        time.sleep(1)

        self.display_scan()

        # After displaying the scan, cancel the subscription
        self.client.cancelScannerSubscription(7002)

    ###########################################################################
    def display_scan(self):
        """Displays market scan results retrieved from IB."""
        def on_row_click(row):
            """Function called when one of the scan results is clicked."""
            self.chart.topbar['symbol'].set(row['symbol'])
            self.request_data(row['symbol'], DEFAULT_TIMEFRAME)

        table = self.chart.create_table(
            width=0.4,
            height=0.5,
            headings=('symbol', 'value'),
            widths=(0.7, 0.3),
            alignments=('left', 'center'),
            position='left', func=on_row_click
        )

        try:
            while True:
                data = data_queue.get_nowait()
                table.new_row(data['symbol'], '')
        except queue.Empty:
            print("No scan results available.")
        finally:
            print("Market scan completed.")
