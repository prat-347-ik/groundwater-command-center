import logging
import sys
import os
from pathlib import Path

def setup_logger(name: str = "orchestrator", log_dir: str = "logs"):
    """
    Configures a centralized logger that writes to both console and file.
    """
    # --- WINDOWS FIX START ---
    # Force standard output to handle emojis (UTF-8) on Windows
    if sys.platform.startswith("win") and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # --- WINDOWS FIX END ---

    # Ensure logs directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding duplicate handlers if setup is called multiple times
    if logger.hasHandlers():
        return logger

    # Format: Timestamp - Component - Level - Message
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (logs/orchestrator.log)
    file_handler = logging.FileHandler(log_path / "orchestrator.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger