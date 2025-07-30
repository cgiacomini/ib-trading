# logger.py
import os, inspect
import logging
import inspect

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    raise ValueError(f"Invalid log level: {LOG_LEVEL}")

# Log to console or file based on environment variable
LOG_FILE = os.getenv("LOG_FILE", "")


log_fmt = '[%(asctime)s] [%(levelname)s] %(message)s'
if LOG_LEVEL == "DEBUG":
    log_fmt='[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d %(funcName)s() → %(message)s'

formatter = logging.Formatter( fmt=log_fmt, datefmt='%Y-%m-%d %H:%M:%S' )

# Create a handler that writes to a file if LOG_FILE is set, otherwise to stdout
if LOG_FILE and not os.path.isabs(LOG_FILE):
    # If LOG_FILE is relative, make it absolute based on the current working directory
    LOG_FILE = os.path.join(os.getcwd(), LOG_FILE)  
handler = logging.StreamHandler() if LOG_FILE == "" else logging.FileHandler(LOG_FILE)
handler.setFormatter(formatter)

logger = logging.getLogger("ib_app")
logger.setLevel(LOG_LEVEL)
logger.addHandler(handler)
logger.propagate = False  # Prevents double logging if root logger is used

# Suppress ibapi logging
# This is to avoid cluttering the logs with ibapi's own messages
# You can adjust the level to DEBUG if you want to see ibapi log
# This filter out most of ibapi messages, only showing important warnings or errors.
logging.getLogger("ibapi").setLevel(logging.WARNING)


def log(level, message, *args):
    method_name = inspect.stack()[1][3]
    full_message = f"[{method_name}] {message}"
    
    if level == 'debug':
        logger.debug(full_message, *args)
    elif level == 'info':
        logger.info(full_message, *args)
    elif level == 'warning':
        logger.warning(full_message, *args)
    elif level == 'error':
        logger.error(full_message, *args)
    elif level == 'critical':
        logger.critical(full_message, *args)
    else:
        logger.info(f"[{method_name}] Unknown log level '{level}': {message}", *args)

