# position_manager.py
from typing import Dict
from ibapi.contract import Contract
from logger import logger

###############################################################################
# PortfolioManager class to manage trading positions.
# This class keeps track of positions in various contracts, allowing updates,
# checks for existing positions, and retrieval of position details.
# It also provides a method to clear all positions.
class PortfolioManager:
    ###########################################################################
    def __init__(self):
        """
        Initializes the PortfolioManager with an empty positions dictionary.
        This dictionary will hold positions keyed by contract symbol, with each
        position containing details such as contract, quantity, and average cost.
        """
        logger.info("Initializing PortfolioManager...")
        self.client = None  # Placeholder for IBClient instance

    ###########################################################################
    def update_position(self, contract: Contract, quantity_change: int):
        """
        Updates the position for a given contract.
        """
        logger.info(f"Updating position for {contract.symbol} with quantity change: {quantity_change}")
        
    ###########################################################################
    def has_position(self, symbol: str) -> bool:
        logger.info(f"Checking position for {symbol}")
        return True

    ###########################################################################
    def get_position(self, symbol: str):
        logger.info(f"Retrieving position for {symbol}")

    ###########################################################################
    def clear(self):
        logger.info("Clearing all positions...")

    ###########################################################################
    def set_client(self, client):
        """Assigns IBClient instance after creation.

        Args:
            client (IBClient): The IBClient instance managing the connection.
        """
        self.client = client