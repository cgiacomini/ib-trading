import datetime
import time
import queue
from threading import Thread
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ContractDetails
from ibapi.order import Order
from ibapi.scanner import ScannerSubscription
from ibapi.tag_value import TagValue
from shared.queue_manager import data_queue  # Importing shared queue


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
        self.connect(host, port, client_id)
        self.thread = Thread(target=self.run)
        self.thread.start()
        self.chart_handler = None  # Placeholder for ChartHandler instance
        self.order_id = None  # Placeholder for order IDs
        print("Thread started.")

    ###########################################################################    
    def set_chart_handler(self, chart_handler):
        """Assigns ChartHandler instance after creation."""
        self.chart_handler = chart_handler

    ###########################################################################
    def error(self, reqId: int, errorTime: str, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Handles error messages from Interactive Brokers. C

        Args:
            reqId (int): The request ID linked to the error.
            errorCode (int): The error code received from IB.
            errorString (str): Description of the error.
            misc (str, optional): Additional information. Defaults to "".
        """
        if errorCode in [2104, 2106, 2158]:  # Common IB status messages
            print(errorString)
        else:
            print(f"Error. Id: {reqId}, Code: {errorCode}, Msg: {errorString}, Time: {errorTime}")

    ###########################################################################
    def historicalData(self, req_id: int, bar):
        """Processes historical data received from IB.

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

        data_queue.put(data)

    ###########################################################################
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Handles the end of historical data retrieval.

        Calls `update_chart()` to display the retrieved data.

        Args:
            reqId (int): The request ID.
            start (str): Start date of the retrieved data.
            end (str): End date of the retrieved data.
        """
        self.chart_handler.chart.spinner(False)

        print(f"End of data {start} {end}")
        self.chart_handler.update_chart()

    ###########################################################################
    def nextValidId(self, orderId: int):
        """Receives the next valid order ID from IB API."""
        super().nextValidId(orderId)
        self.order_id = orderId
        print(f"Next valid order ID: {self.order_id}")

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
            print(f"Placing {action} order for {quantity} shares of {contract.symbol}")
            self.placeOrder(self.order_id, contract, order)
        else:
            print("Error: Order ID not received from IB API.")
    ###########################################################################
    def orderStaus(self, orderId: int, status: str, filled: float, remaining: float,
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
        print(f"order status {orderId} {status} {filled} {remaining} {avgFillPrice}")

    ###########################################################################
    def scannerData(self, req_id: int, rank: int, details: ContractDetails, 
                    distance:str, benchmark: str, projection: str, legsStr:str):

        """Processes scanner data received from IB. Callback for when a scan finishes.

        Args:
            req_id (int): The request ID for the scanner data.
            rank (int): The rank of the scanned item.
            details: Details of the scanned contract.
            distance (str): Distance from the benchmark.
            benchmark (str): Benchmark used for scanning.
            projection (str): Projection type.
            legsStr (str): String representation of legs in the contract.       
        """
        super().scannerData(req_id, rank, details, distance, benchmark, projection, legsStr)

        data = {
            'secType': details.contract.secType,
            'secId': details.contract.secId,
            'exchange': details.contract.primaryExchange,
            'symbol': details.contract.symbol
        }
        data_queue.put(data)

    ###########################################################################
    def subscribe_marketscan(self, scan_code: str):
        """Subscribes to IB market scan and retrieves results."""
        scannerSubscription = ScannerSubscription()
        scannerSubscription.instrument = "STK"
        scannerSubscription.locationCode = "STK.US.MAJOR"
        scannerSubscription.scanCode = scan_code
        tagValues = [TagValue("optVolumeAbove", "1000"), TagValue("avgVolumeAbove", "10000")]

        self.reqScannerSubscription(7002, scannerSubscription, [], tagValues)
        time.sleep(1)

        self.display_scan()
        self.cancelScannerSubscription(7002)

    ###########################################################################
    def display_scan(self):
        """Displays market scan results retrieved from IB."""
        try:
            while True:
                data = data_queue.get_nowait()
                print(f"Scanned: {data['symbol']}")
        except queue.Empty:
            print("No scan results available.")
        finally:
            print("Market scan completed.")
