# position_manager.py
from typing import Dict
from ibapi.contract import Contract
from logger import logger

###############################################################################
# PositionManager class to manage trading positions.
# This class keeps track of positions in various contracts, allowing updates,
# checks for existing positions, and retrieval of position details.
# It also provides a method to clear all positions.
class PositionManager:
    ###########################################################################
    def __init__(self):
        """
        Initializes the PositionManager with an empty positions dictionary.
        This dictionary will hold positions keyed by contract symbol, with each 
        position containing details such as contract, quantity, and average cost.
        """
        self.positions: Dict[str, Dict] = {}

    ###########################################################################
    def update_position(self, contract: Contract, position: float, avg_cost: float):
        """ 
        Updates the position for a given contract.
        """
        symbol = contract.symbol
        if position != 0:
            self.positions[symbol] = {
                "contract": contract,
                "quantity": position,
                "avg_cost": avg_cost
            }
        else:
            self.positions.pop(symbol, None)

    ###########################################################################
    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    ###########################################################################
    def get_position(self, symbol: str):
        return self.positions.get(symbol)
    
    ###########################################################################
    def clear(self):
        self.positions.clear()
