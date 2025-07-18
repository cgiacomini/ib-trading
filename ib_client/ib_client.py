"""IBClient Module"""
import datetime
import time
from threading import Thread
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import BarData
from shared.queue_manager import data_queue  # Importing shared queue
from logger import logger

###############################################################################
class IBClient(EWrapper, EClient):
    """Interactive Brokers Client to manage connection and data retrieval.

    This class establishes a connection with Interactive Brokers, handles 
    requests for historical data, and processes received data.

    Attributes:
        chart_handler (ChartHandler): An instance of the chart handler.
    """

    ###########################################################################
    def __init__(self):
        """Initializes IBClient"""
        EClient.__init__(self, self)

        self.current_req_id = 0
        self.connected = False
        self.chart_handler = None  # Placeholder for ChartHandler instance
        self.order_id = None  # Placeholder for order IDs
        self.portfolio_manager = None

    ###########################################################################
    def connect(self, host: str, port: int, clientId: int) -> bool:
        """Starts the connection thread.
            Args:
        host (str): The host address for Interactive Brokers.
        port (int): The port number for connection.
        client_id (int): Unique ID for the client session.
        """
        try:
            super().connect(host, port, clientId)

            # Start the socket in a thread
            api_thread = Thread(target=self.run, daemon=False)
            api_thread.start()

            # Wait for connection
            time.sleep(1)

            if self.isConnected():
                logger.info("Connected to IB Gateway at %s:%d with client ID %d",
                            self.host, self.port, clientId)
                self.connected = True
                return True
            else:
                logger.error("Connection failed. Please check your IB Gateway settings.")
                self.connected = False
                return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    ###########################################################################

    def get_next_req_id(self):
        """Return the next calculated request id"""
        self.current_req_id += 1
        return self.current_req_id

    ###########################################################################
    def set_chart_handler(self, chart_handler):
        """Assigns ChartHandler instance after creation."""
        self.chart_handler = chart_handler

    ###########################################################################
    def error(self, reqId: int, errorTime: int, errorCode: int,
               errorString: str, advancedOrderRejectJson: str = ""):
        """Handles error messages from Interactive Brokers. C

        Args:
            reqId (int): The request ID linked to the error.
            errorCode (int): The error code received from IB.
            errorTime (str): The time the error occured.
            errorString (str): Description of the error.
            misc (str, optional): Additional information. Defaults to "".
        """
        if errorCode in [2104, 2106, 2158]:  # Common IB status messages
            logger.warning("IB Status Message: %s", errorString)
        else:
            logger.error("IB Error %d: %s (Request ID: %d, Time: %s)",
                         errorCode, errorString, reqId, errorTime)

    ###########################################################################
    def historicalData(self, reqId: int, bar: BarData):
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
        logger.debug("Received historical data for request ID %d: %s", reqId, data)

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
        logger.debug("Updating chart with new data after historical data retrieval.")
        # Update the chart with the new data
        self.chart_handler.update_chart()

    ###########################################################################
    def nextValidId(self, orderId: int):
        """Receives the next valid order ID from IB API."""
        super().nextValidId(orderId)
        self.order_id = orderId
        logger.debug("Next valid order ID: %d", self.order_id)

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
        logger.info("Order Status Update: Order ID %d, Status: %s, Filled: %.2f,\
                     Remaining: %.2f, Avg Fill Price: %.2f",
                    orderId, status, filled, remaining, avgFillPrice)
