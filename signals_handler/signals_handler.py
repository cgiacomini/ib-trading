import pandas as pd
from typing import Dict, List 
from shared.logger import log
from shared import config

###############################################################################
def sma_crossover_signal(bars: List[Dict]) -> str | None:
    """
    Function to generate a trading signal based on Simple Moving Average (SMA) crossover
    This function checks the last two values of the short and long SMAs to determine
    if a buy or sell signal should be generated.
    It returns "BUY" if the short SMA crosses above the long SMA, "SELL" if it crosses below,
    or None if no crossover is detected.
    Args:
        bars: List[Dict]: List of current received historical data with SMA columns.
    Returns:
        str | None: Returns "BUY" if a buy signal is detected, "SELL" if a sell signal is detected,
                    or None if no signal is detected.   
    """

    log('debug', "generating SMA crossover signals")
    df = pd.DataFrame(bars)
    required_columns = [f'SMA_{config.SMA_SHORT_PERIOD}', f'SMA_{config.SMA_LONG_PERIOD}']
    # Check column existence
    missing_columns = [col for col in required_columns if col not in df.columns]
    # Check for all-NaN or None values
    empty_columns = [col for col in required_columns
                    if col in df.columns and df[col].dropna().empty]
    if missing_columns or empty_columns:
        if missing_columns:
            log('debug', f"Missing columns: {missing_columns}")
            return None
        if empty_columns:
            log('debug', f"Columns with only NaN/None: {empty_columns}")
            return None

    # This ensures that only rows where both SMA columns have valid values are kept.
    sma_df = df[['date',
                 f'SMA_{config.SMA_SHORT_PERIOD}',
                 f'SMA_{config.SMA_LONG_PERIOD}']].dropna(
                     subset=[f'SMA_{config.SMA_SHORT_PERIOD}',
                             f'SMA_{config.SMA_LONG_PERIOD}'])

    if len(sma_df) < 2: return # Not enough data

    p_sma_short = sma_df.iloc[-2][f'SMA_{config.SMA_SHORT_PERIOD}']
    c_sma_short = sma_df.iloc[-1][f'SMA_{config.SMA_SHORT_PERIOD}']
    p_sma_long = sma_df.iloc[-2][f'SMA_{config.SMA_LONG_PERIOD}']
    c_sma_long = sma_df.iloc[-1][f'SMA_{config.SMA_LONG_PERIOD}']

    log('debug', "%f %f %f %f", p_sma_short, c_sma_short, p_sma_long, c_sma_long)

    if pd.notna(p_sma_short) and pd.notna(c_sma_short) and pd.notna(p_sma_long) and pd.notna(c_sma_long):
        if c_sma_short > c_sma_long and p_sma_short <= p_sma_long:
            return "buy"
        elif c_sma_short < c_sma_long and p_sma_short >= p_sma_long:
            return "sell"
    return None

###############################################################################
def volumes_signal(df: pd.DataFrame) -> str | None:
    return None

###############################################################################
#signals_functions = [sma_crossover_signal, volumes_signal]
signals_functions = [sma_crossover_signal]

###############################################################################
def buy_or_sell_based_on_signals(df: pd.DataFrame) -> str | None:
    """
    This functions call all signal_functions passing historical data as 
    argument. Each Function perfoms a differen data analisys based on which
    a BUY or a SELL signal signal is produced and added to the list of 
    signals.

    Args:
        df: (pdanda DataFrame): The daframe with historical data.

    Returns:
        Returns, base of the magiority the BUY or SELL signal
    """
    signals = [func(df) for func in signals_functions]
    # For now return the only signal we have
    return signals[len(signals_functions)-1]
    # # Filter out None valuea
    # filtered = [s for s in signals if s is not None]

    # # Count each signal
    # buy_count = filtered.count("Buy")
    # sell_count = filtered.count("Sell")

    # # Decide Buy or Sel base on the majority
    # if buy_count > sell_count:
    #     return "Buy"
    # elif sell_count > buy_count:
    #     return "Sell"
    # else:
    #     return None  # No clear majority   
