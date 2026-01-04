import logging
import sys
import os
from pathlib import Path

def setup_logger(name: str = "service_b", level=logging.INFO):
    """
    Sets up a logger that outputs to Console (stdout).
    Service C captures stdout, so this ensures logs appear in the Orchestrator.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate logs if setup is called multiple times
    if logger.hasHandlers():
        return logger

    # Format: [Service B Internal] timestamp - message
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Handler: Stream to stdout (Captured by Service C)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger