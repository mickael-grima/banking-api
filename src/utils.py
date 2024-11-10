import datetime
import logging
import os
from datetime import timezone
from http.client import responses

from fastapi import Request


def get_utc_timestamp() -> int:
    # Getting the current date and time
    dt = datetime.datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    return int(utc_time.timestamp())


def server_log_message(req: Request, status_code: int):
    """
    Create a nice looking log for server responses
    """
    status_str = f"{status_code} {responses[status_code]}"
    return f'"{req.method} {req.url}" {status_str}'


def get_logger(name: str) -> logging.Logger:
    """
    Create a custom logger:
    - set its logging level
    - make sure logs are streamed to the console
    """
    # parse debug from environment
    debug_env = os.getenv("DEBUG", "0")
    try:
        debug = bool(int(debug_env))
    except ValueError:
        logging.exception(f"DEBUG environment has the wrong format: {debug_env}")
        debug = False

    # create handler and formatter
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # set-up the logger
    logger = logging.getLogger(name)
    logger.propagate = False
    if debug:
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
