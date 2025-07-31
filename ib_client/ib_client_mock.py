"""Module to mock EClient and EWrapper"""
import os
import datetime
import csv
import time
import pandas as pd
from ibapi.client import EClient
from ibapi.common import BarData, TickerId, TagValueList
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper
from threading import Thread, Event


# Import default configuration
from shared.queue_manager import data_queue  # Importing shared queue
from shared.logger import log

###########################################################################
class MockEWrapper(EWrapper):
    """
    EWrappper Mock Class
    """

    ###########################################################################
    def __init__(self):
        """Initialize the MockEWrapper."""

        self.chart_handler = None

    ###########################################################################
    def historicalData(self, reqId: int, bar: BarData):
        """Handle historical data received from the mock client."""

        # Convert the date from string to datetime object
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
        log('debug',"Received historical data for request ID %d: %s", reqId, data)

    ############################################################################
    def cancelMktData(self, req_id):
        
        """Handle cancellation of market data requests."""

        log('info',"[Mock Wrapper] Tick cancel market data for ReqId: %s", req_id)
        # This is where you would handle the cancellation logic if needed.
        # For now, we just log it.
        self.chart_handler.chart.spinner(False)

    ###########################################################################
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Handle the end of historical data stream."""

        log('info',"[Mock Wrapper] - ReqId: %s, Start: %s, End: %s", reqId, start, end)
        # Update the chart with the new data
        self.chart_handler.update_chart()
        self.chart_handler.chart.spinner(False)

    ###########################################################################
    def tickPrice(self, reqId, tickType, price, attrib):
        """Handle tick price updates from the mock client."""

        # Filter only the tick types you care about (e.g., last price)
        if tickType == 4:  # 4 = Last Price
            tick = pd.Series({
                'time': datetime.datetime.now(datetime.timezone.utc),
                'price': price
            })
            data_queue.put(tick)
            self.chart_handler.chart.update_from_tick(tick)

    ###########################################################################
    def set_chart_handler(self, chart_handler):
        """
        Assigns ChartHandler instance after creation.
        """
        self.chart_handler = chart_handler

###########################################################################
class MockEClient(EClient):
    """Mock EClient Class to simulate IB API client behavior."""

    ###########################################################################
    def __init__(self, wrapper: EWrapper):
        super().__init__(wrapper)
        self.current_req_id = 0
        self.mock_data_path = None

    ###########################################################################
    def connect(self, host: str, port: int, clientId: int) -> bool:
        """ Simulate connection to the IB server"""

        log('info',"[Mock Client] Simulating connect")
        return True

    ###########################################################################
    def connected(self):
        """ Check if the client is connected to the IB server"""
        log('info',"[Mock Client] Simulating connected")
        return True

    ###########################################################################
    def get_next_req_id(self):

        """Return the next calculated request id"""

        self.current_req_id += 1
        return self.current_req_id

    ###########################################################################
    def reqHistoricalData(self, reqId, contract, endDateTime, durationStr,
                          barSizeSetting, whatToShow, useRTH, formatDate,
                          keepUpToDate, chartOptions):

        """Simulate HistoricalData request"""

        log('info',"[Mock Client] Simulating reqHistoricalData for ReqId: %s", reqId)

        data_file = f"{contract.symbol}_{barSizeSetting.replace(' ','_')}.csv"
        self.mock_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "../DataFiles", data_file)
        log('info',"Using data file: %s", self.mock_data_path)
        if not os.path.exists(self.mock_data_path):
            log('error',"[ERROR] Data file does not exist: %s", self.mock_data_path)
            return
        self.simulate_historical_data_from_csv(reqId, self.mock_data_path)

    ###########################################################################
    def simulate_historical_data_from_csv(self, req_id: int, filepath: str):

        """Simulate HistoricalData retrieval."""

        try:
            bars = []
            log('info',"[Mock Client] Reading %s", filepath)
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    bar = BarData()
                    bar.date = row['time']
                    bar.open = float(row['open'])
                    bar.high = float(row['high'])
                    bar.low = float(row['low'])
                    bar.close = float(row['close'])
                    bar.volume = float(row['volume'])
                    bar.barCount = 1
                    bar.average = (bar.open + bar.close) / 2
                    bar.hasGaps = False
                    self.wrapper.historicalData(req_id, bar)
                    bars.append(bar)
                if bars:
                    self.wrapper.historicalDataEnd(req_id, bars[0].date,
                                                   bars[-1].date)

        except FileNotFoundError:
            log('error',"[ERROR] File not found: %s", filepath)
        except Exception as e:
            log('error',"[ERROR] Failed to read mock data: %s", e)

###########################################################################
class MockIBClient(MockEWrapper, MockEClient):
    """
    IBClient Mocker
    """

    ###########################################################################
    def __init__(self):
        MockEWrapper.__init__(self)
        MockEClient.__init__(self, wrapper=self)
        self.market_data_thread = None
        self.stop_event = Event()

    ###########################################################################
    def set_mock_data_path(self, data_file_path: str):
        """
        Set the path of the data file used to simulate incomming bars
        """
        self.mock_data_path = data_file_path

    ###########################################################################
    def stop_market_data(self):
        """
        Stop the market data simulation thread if it's running.
        """
        if self.market_data_thread and self.market_data_thread.is_alive():
            self.stop_event.set()
            self.market_data_thread.join()
            self.stop_event.clear()

    ############################################################################
    def simulate_market_data_from_csv(self, req_id: int, filepath: str):
        """
        Simulate Market Data retrieval from a CSV file."""

        try:
            ticks = []
            log('info',"[Mock Client] Reading %s", filepath)
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if self.stop_event.is_set(): 
                        log('info',"[Mock Client] Market data simulation stopped.")
                        break

                    self.wrapper.tickPrice(req_id,
                                    tickType = 4, # last price
                                    price = float(row['close']),
                                    attrib = None)
                    ticks.append(row)
                    time.sleep(0.1)  # Simulate a delay between ticks
            # If there are ticks and the stop event is not set, cancel market
            #  data subscription
            if ticks and not self.stop_event.is_set():
                self.wrapper.cancelMktData(req_id)

        except FileNotFoundError:
            log('error',"[ERROR] File not found: %s", filepath)
        except Exception as e:
            log('error',"[ERROR] Failed to read mock realtime data: %s", e)

    ###########################################################################
    def reqMktData(self, reqId: TickerId, contract: Contract,
                   genericTickList: str, snapshot: bool,
                   regulatorySnapshot: bool,
                   mktDataOptions: TagValueList = None):
        """
        Simulate Market Data request
        """

        log('info',"[Mock Client] Simulating reqMktData for ReqId: %s", reqId)
        data_file = f"{contract.symbol}_ticks.csv"
        self.mock_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "../DataFiles", data_file)
        log('info',"Using data file: %s", self.mock_data_path)
        if not os.path.exists(self.mock_data_path):
            log('error',"[ERROR] Market data file does not exist: %s", self.mock_data_path)
            return

        # Simulate market data retrieval
        self.stop_market_data()
        self.market_data_thread = Thread(target=self.simulate_market_data_from_csv, 
                                         args=(reqId, self.mock_data_path), daemon=False)
        self.market_data_thread.start()
