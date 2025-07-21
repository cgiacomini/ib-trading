"""Module to mock EClient and EWrapper"""
import os
import datetime
import csv
from ibapi.common import BarData
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

# Import default configuration
from shared.queue_manager import data_queue  # Importing shared queue
from shared.logger import logger

###########################################################################
class MockEWrapper(EWrapper):
    """
    EWrappper Mock Class
    """

    ###########################################################################
    def __init__(self):
        self.chart_handler = None

    ###########################################################################
    def historicalData(self, reqId: int, bar: BarData):
        logger.debug("[Mock Wrapper] ReqId: %s, Date: %s, Open: %s, High: %s, \
                      Low: %s, Close: %s, Volume: %s", reqId, bar.date, \
                        bar.open, bar.high, bar.low, bar.close, bar.volume)
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

    ###########################################################################
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        logger.info("[Mock Wrapper] HistoricalDataEnd - ReqId: %s, Start: %s, \
                    End: %s", reqId, start, end)
        self.chart_handler.chart.spinner(False)
        # Update the chart with the new data
        self.chart_handler.update_chart()

    ###########################################################################
    def set_chart_handler(self, chart_handler):
        """
        Assigns ChartHandler instance after creation.
        """
        self.chart_handler = chart_handler

###########################################################################
class MockEClient(EClient):
    """EClient Mock Class
    """
    def __init__(self, wrapper: EWrapper):
        super().__init__(wrapper)
        self.current_req_id = 0
        self.mock_data_path = None

    ###########################################################################
    def connect(self, host: str, port: int, clientId: int) -> bool:
        logger.info("[Mock Client] Simulating connect")
        return True

    ###########################################################################
    def connected(self):
        """ Simulate connection
        """
        logger.info("[Mock Client] Simulating connected")
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
        logger.info("[Mock Client] Simulating reqHistoricalData for ReqId: %s", reqId)

        datafile = f"{contract.symbol}_{barSizeSetting.replace(" ","_")}.csv"
        self.mock_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "../DataFiles", datafile)
        logger.info("Using data file: %s", self.mock_data_path)
        if not os.path.exists(self.mock_data_path):
            logger.error("[ERROR] Data file does not exist: %s", self.mock_data_path)
            return
        self.simulate_historical_data_from_csv(reqId, self.mock_data_path)

    ###########################################################################
    def simulate_historical_data_from_csv(self, req_id: int, filepath: str):
        """Simulate HistoricalData retrieval.
        """
        try:
            bars = []
            logger.info("[Mock Client] Reading %s", filepath)
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
            logger.error("[ERROR] File not found: %s", filepath)
        except Exception as e:
            logger.error("[ERROR] Failed to read mock data: %s", e)

###########################################################################
class MockIBClient(MockEWrapper, MockEClient):
    """
    IBClient Mocker
    """

    ###########################################################################
    def __init__(self):
        MockEWrapper.__init__(self)
        MockEClient.__init__(self, wrapper=self)

    ###########################################################################
    def set_mock_data_path(self, data_file_path: str):
        """
        Set the path of the data file used to simulate incomming bars
        """
        self.mock_data_path = data_file_path
