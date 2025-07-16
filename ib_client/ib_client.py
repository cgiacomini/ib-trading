import datetime, os
import time, csv
import queue
from threading import Thread
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.scanner import ScannerSubscription
from ibapi.common import BarData
from ibapi.tag_value import TagValue
from shared.queue_manager import data_queue  # Importing shared queue
from logger import logger
from portfolio.portfolio_manager import PortfolioManager

###############################################################################
class IBClient(EWrapper, EClient):
    """Interactive Brokers Client to manage connection and data retrieval.

    This class establishes a connection with Interactive Brokers, handles 
    requests for historical data, and processes received data.

    Attributes:
        chart_handler (ChartHandler): An instance of the chart handler.
    """

    ###########################################################################
    def __init__(self, host: str, port: int, client_id: int):
        """Initializes IBClient and starts the connection thread.

        Args:
            host (str): The host address for Interactive Brokers.
            port (int): The port number for connection.
            client_id (int): Unique ID for the client session.
        """
        EClient.__init__(self, self)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.current_req_id = 0
        self.connected = False
        self.chart_handler = None  # Placeholder for ChartHandler instance
        self.order_id = None  # Placeholder for order IDs
    
    ###########################################################################
    def connect(self):
        try:
            super().connect(self.host, self.port, self.client_id)

            # Start the socket in a thread
            api_thread = Thread(target=self.run, daemon=False)
            api_thread.start()

            # Wait for connection
            time.sleep(1)

            if self.isConnected():
                logger.info(f"Connected to IB Gateway at {self.host}:{self.port} with client ID {self.client_id}")
                self.connected = True
                return True
            else:
                logger.error(f"Failed to connect to IB Gateway at {self.host}:{self.port} with client ID {self.client_id}")
                self.connected = False
                return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
        
    ###########################################################################    
    def get_next_req_id(self):
        req_id = self.current_req_id
        self.current_req_id += 1
        return self.current_req_id
    
    ###########################################################################    
    def set_chart_handler(self, chart_handler):
        """Assigns ChartHandler instance after creation."""
        self.chart_handler = chart_handler

    ###########################################################################
    def set_portfolio_manager(self, portfolio_data_file: str):
        """Assigns PositionManager instance for managing trading positions."""
        self.portfolio_manager = PortfolioManager(portfolio_data_file)
        logger.info("Portfolio Manager set in IBClient.")

    ###########################################################################
    def error(self, reqId: int, errorTime: str, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Handles error messages from Interactive Brokers. C

        Args:
            reqId (int): The request ID linked to the error.
            errorCode (int): The error code received from IB.
            errorTime (str): The time the error occured.
            errorString (str): Description of the error.
            misc (str, optional): Additional information. Defaults to "".
        """
        if errorCode in [2104, 2106, 2158]:  # Common IB status messages
            logger.warning(f"IB Status Message: {errorString}")
        else:
            logger.error(f"Error. Id: {reqId}, Code: {errorCode}, Msg: {errorString}, Time: {errorTime}")

    ###########################################################################
    def historicalData(self, req_id: int, bar: BarData):
        """Processes historical data received from IB. 
        This method is called for each bar of historical data.

        Converts IB bar data into a dictionary and adds it to the data queue.

        Args:
            req_id (int): The request ID for historical data.
            bar: A single bar of historical data.
        """

        t = datetime.datetime.fromtimestamp(int(bar.date))
        data = {
            'date': t,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': int(bar.volume)
        }
        # Add the data to the shared queue for processing)
        data_queue.put(data)
        logger.debug(f"Received historical data for request ID {req_id}: {data}")


    ###########################################################################
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Handles the end of historical data retrieval.
        This method is called when all requested historical data has been received.

        Calls `update_chart()` to display the retrieved data.

        Args:
            reqId (int): The request ID.
            start (str): Start date of the retrieved data.
            end (str): End date of the retrieved data.
        """
        self.chart_handler.chart.spinner(False)

        logger.debug(f"Historical data retrieval completed for request ID {reqId} from {start} to {end}")
        # Update the chart with the new data
        self.chart_handler.update_chart()

    ###########################################################################
    def realtimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        return super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        """Processes real-time bar data received from IB.
        This method is called for each real-time bar of data. 
        Converts IB bar data into a dictionary and adds it to the data queue.
        Args:
            reqId (int): The request ID for real-time data.
            time (int): The timestamp of the bar.
            open_ (float): Opening price of the bar.
            high (float): Highest price of the bar.
            low (float): Lowest price of the bar.
            close (float): Closing price of the bar.
            volume (int): Volume of the bar.
            wap (float): Weighted average price of the bar.
            count (int): Number of trades in the bar.
        """
        t = datetime.datetime.fromtimestamp(int(time))
        data = {
            'date': t,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': int(volume)
        }
        # Add the data to the shared queue for processing
        data_queue.put(data)
        logger.debug(f"Received real-time bar data for request ID {reqId}: {data}")
        
    # ###########################################################################
    # JUST FOR TESTING PURPOSES
    # def simulate_live_data(self, symbol, delay=1):
    #     """Simulates live data feed from a CSV file instead of from IBRK.
    #     Reads data from a CSV file and calls the provided callback function
    #     for each row, simulating a live data feed with a specified delay.
    #     Args:
    #         file_path (str): Path to the CSV file containing historical data.
    #         callback (function): Function to call with each data point.
    #         delay (int, optional): Delay in seconds between data points. Defaults to 1.
    #     """
    #     file_path = f"data/{symbol}.csv"  # Assuming data files are stored in a 'data' directory
    #     if not os.path.exists(file_path):
    #         logger.error(f"Data file {file_path} does not exist.")
    #         return
    
    #     with open(file_path, newline='') as csvfile:
    #         reader = csv.DictReader(csvfile)
    #         for row in reader:
    #             # Convert row fields appropriately
    #             data_point = {
    #                 'date': datetime.datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S'),
    #                 'open': float(row['open']),
    #                 'high': float(row['high']),
    #                 'low': float(row['low']),
    #                 'close': float(row['close']),
    #                 'volume': int(row['volume'])
    #             }
    #             self.historicalData(data_point)  # Handle data as if it's coming from IB
    #             time.sleep(delay) # Simulate delay between incoming ticks


    ###########################################################################
    def nextValidId(self, orderId: int):
        """Receives the next valid order ID from IB API."""
        super().nextValidId(orderId)
        self.order_id = orderId
        logger.debug(f"Next valid order ID: {self.order_id}")

    ###########################################################################
    def place_order(self, contract: Contract, action: str, quantity: int):
        """Places an order with IB.

        Args:
            contract (Contract): The contract object.
            action (str): Either 'BUY' or 'SELL'.
            quantity (int): Number of shares to trade.
        """
        if not self.order_id:
            self.reqIds(-1)
            time.sleep(2)  # Small delay to ensure order ID retrieval

        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity

        if self.order_id:
            logger.info(f"Placing {action} order for {quantity} shares of {contract.symbol} with order ID {self.order_id}")
            self.placeOrder(self.order_id, contract, order)
        else:
            logger.info(f"Placed {action} order for {quantity} shares of {contract.symbol} with order ID {self.order_id}")
            # Update portfolio
            quantity_change = quantity if action == "BUY" else -quantity
            self.portfolio_manager.update_position(contract, quantity_change)
# ...
    ###########################################################################
    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float,
                    avgFillPrice: float, permId: int, parentId: int,
                    lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        """Handles order status updates from IB. callback to log order status
        Args:
            orderId (int): The ID of the order.
            status (str): Current status of the order.
            filled (float): Number of shares filled.
            remaining (float): Number of shares remaining.
            avgFillPrice (float): Average fill price of the order.
            permId (int): Permanent ID of the order.
            parentId (int): Parent ID if this is a child order.
            lastFillPrice (float): Last fill price of the order.
            clientId (int): Client ID associated with the order.
            whyHeld (str): Reason why the order is held, if applicable.
        """
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, 
                            permId, parentId, lastFillPrice, clientId, whyHeld, 
                            mktCapPrice)
        logger.info(f"Order Status: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, "
                    f"Avg Fill Price: {avgFillPrice}, Last Fill Price: {lastFillPrice}")
