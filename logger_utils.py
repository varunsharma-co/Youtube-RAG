import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Create a logger instance at the module level
logger = logging.getLogger("YouTubeDataIngestion")


def setup_logger(log_dir: str, username: Optional[str] = None):
    """
    Sets up a centralized logger for the application with console output
    and attaches a dynamic file handler using a timestamped filename,
    optionally prepended with a username.

    Args:
        log_dir (str): The base directory for saving the log file.
        username (Optional[str], optional): The username to prepend to the log file name.
                                            Defaults to None.
    """
    if logger.hasHandlers():
        return logger  # Logger already configured

    logger.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console Handler (Always useful)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 2. Dynamic File Handler (with optional username)
    timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S")

    # **UPDATED**: Conditionally create the log filename
    if username:
        log_filename = f"{username}_log_{timestamp}.txt"
    else:
        log_filename = f"log_{timestamp}.txt"

    # Ensure the directory exists
    save_path = Path(log_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    full_log_filepath = save_path / log_filename

    # Add the file handler to the logger
    file_handler = logging.FileHandler(full_log_filepath)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Logger initialized.")
    logger.info(f"All logs for this run will be written to: {full_log_filepath}")

    return logger
