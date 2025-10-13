import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from logger_utils import logger


def save_last_run_timestamp(save_dir: Path, username: str):
    """
    Creates a .txt file containing a JSON object with two timestamp formats
    to mark the successful completion of the initial data fetch.

    Args:
        save_dir (Path): The absolute path to the directory where the file will be saved
                         (e.g., /path/to/project/Final_Files/).
        username (str): The YouTube channel username for the filename.
    """
    try:
        logger.info("Creating last run timestamp file...")

        # 1. Get the current time
        now = datetime.now()

        # 2. Prepare the data with two key formats
        timestamp_data: Dict[str, str] = {
            "program_readable_timestamp": now.isoformat(),
            # UPDATED: Changed the strftime format string to match "DD Month YYYY; HH:MM:SS"
            "human_readable_timestamp": now.strftime("%d %B %Y; %H:%M:%S"),
        }

        # 3. Construct the filename and path
        filename = f"{username}_YT_RAG_Last_Run.txt"
        full_filepath = save_dir / filename

        # 4. Ensure the directory exists and save the file
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(full_filepath, "w", encoding="utf-8") as f:
            json.dump(timestamp_data, f, indent=4)

        logger.info(f"Successfully saved last run timestamp to: {full_filepath.name}")

    except Exception as e:
        logger.error(f"Failed to save last run timestamp file: {e}")
