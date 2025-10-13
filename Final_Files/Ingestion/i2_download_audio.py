import os
import re
from pathlib import Path
from typing import Dict, List, Union

from pytubefix import YouTube

# Import the configured logger
from logger_utils import logger

# =======================================================
#               PUBLIC FUNCTION
# =======================================================


def download_audio_from_videos(video_list: List[Dict], output_path: str) -> List[Dict]:
    """
    Downloads audio for a list of YouTube videos and saves them as .m4a files.

    Crucially, it returns a list of dictionaries mapping the original video URL
    to the new local file path, preserving the data link.

    Args:
        video_list (List[Dict]): A list of dictionaries, where each dict contains
                                 'video_url', 'video_title', etc.
        output_path (str): The directory path where the final .m4a files will be saved.

    Returns:
        List[Dict]: A list of dictionaries, e.g.,
                    [{'video_url': 'some_url', 'm4a_path': Path(...) }, ...],
                    for successfully downloaded files.
    """
    download_mappings = []
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Target directory for M4A files checked/created: {output_dir.name}")
    logger.info(f"Starting audio download for {len(video_list)} filtered videos...")

    for i, video in enumerate(video_list):
        video_url = video.get("video_url")
        video_title = video.get("video_title", f"video_{i}")

        if not video_url:
            logger.warning(f"Video at index {i} is missing a URL. Skipping.")
            continue

        try:
            yt = YouTube(video_url)
            sanitized_title = (
                re.sub(r'[\\/:*?"<>|]', "", yt.title).strip().replace(" ", "_")
            )

            logger.info(
                f"[{i+1}/{len(video_list)}] Downloading audio for: {sanitized_title}"
            )

            video_stream = yt.streams.filter(only_audio=True).first()
            if not video_stream:
                logger.error(
                    f"Could not find an audio stream for {video_url}. Skipping."
                )
                continue

            downloaded_filepath_str = video_stream.download(
                output_path=output_dir, filename=sanitized_title
            )
            downloaded_filepath = Path(downloaded_filepath_str)

            base_name = downloaded_filepath.stem
            final_filepath_m4a = output_dir / f"{base_name}.m4a"

            if downloaded_filepath != final_filepath_m4a:
                if final_filepath_m4a.exists():
                    os.remove(final_filepath_m4a)
                os.rename(downloaded_filepath, final_filepath_m4a)

            # **CRITICAL CHANGE**: Append the dictionary mapping, not just the path
            download_mappings.append(
                {"video_url": video_url, "m4a_path": final_filepath_m4a}
            )
            logger.info(f"Successfully saved M4A file: {final_filepath_m4a.name}")

        except Exception as e:
            logger.error(
                f"An error occurred while processing {video_url}. Skipping. Error: {e}"
            )
            continue

    logger.info(
        f"Audio download process complete. Total files saved: {len(download_mappings)}"
    )
    return download_mappings
