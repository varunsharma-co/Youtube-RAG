import json
import os
import re
from datetime import datetime
from pathlib import Path

import googleapiclient.discovery
import isodate
from dotenv import load_dotenv

# Import the configured logger
from logger_utils import logger

# =======================================================
#               PRIVATE HELPER FUNCTIONS
# =======================================================


def _get_username_for_filename(url):
    """Extracts a clean username/handle from the URL for use in a filename."""
    match = re.search(r"youtube\.com/(?:@|c/|user/)([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return "youtube_channel"


def _get_channel_id_from_url(youtube, url):
    """Extracts the channel ID from various YouTube URL formats."""
    match = re.search(r"youtube\.com/channel/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"youtube\.com/user/([A-Za-z0-9_-]+)", url)
    if match:
        request = youtube.channels().list(part="id", forUsername=match.group(1))
        response = request.execute()
        if "items" in response and response["items"]:
            return response["items"][0]["id"]
        else:
            raise ValueError(
                f"Could not resolve username '{match.group(1)}' to a Channel ID."
            )
    match = re.search(r"youtube\.com/(?:@|c/)([A-Za-z0-9_-]+)", url)
    if match:
        request = youtube.search().list(
            part="id", q=match.group(1), type="channel", maxResults=1
        )
        response = request.execute()
        if "items" in response and response["items"]:
            return response["items"][0]["id"]["channelId"]
        else:
            raise ValueError(
                f"Could not resolve handle '{match.group(1)}' to a Channel ID."
            )
    raise ValueError("Could not find a valid channel identifier in the URL.")


def _get_all_video_ids(youtube, channel_id):
    """Gets all video IDs from a channel, logging a summary upon completion."""
    uploads_playlist_id = channel_id.replace("UC", "UU", 1)
    video_ids = []
    next_page_token = None
    while True:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()
        for item in response.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    logger.info(f"Found a total of {len(video_ids)} videos on the channel.")
    return video_ids


def _get_video_details_in_batches(youtube, video_ids):
    """Fetches details for video IDs in batches, logging a summary upon completion."""
    all_video_details = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        request = youtube.videos().list(
            part="snippet,contentDetails", id=",".join(chunk)
        )
        response = request.execute()
        all_video_details.extend(response.get("items", []))
    logger.info(f"Successfully fetched details for {len(all_video_details)} videos.")
    return all_video_details


# =======================================================
#               PUBLIC FUNCTION
# =======================================================


def fetch_and_filter_youtube_videos(
    channel_url: str, min_duration_minutes: int, save_dir: str
):
    """
    Orchestrates fetching, filtering, and SAVING YouTube video data.
    """
    try:
        logger.info("Starting YouTube Data Ingestion process.")
        load_dotenv()
        YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
        if not YOUTUBE_API_KEY:
            raise ValueError("API key not found in .env file.")
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=YOUTUBE_API_KEY
        )
        min_duration_seconds = min_duration_minutes * 60

        channel_id = _get_channel_id_from_url(youtube, channel_url)
        logger.info(f"Successfully resolved Channel ID: {channel_id}")
        all_ids = _get_all_video_ids(youtube, channel_id)
        video_details_list = _get_video_details_in_batches(youtube, all_ids)

        final_output = []
        logger.info(
            f"Filtering for videos longer than {min_duration_minutes} minutes..."
        )
        for video in video_details_list:
            duration_iso = video["contentDetails"]["duration"]
            duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
            if duration_seconds >= min_duration_seconds:
                final_output.append(
                    {
                        "channel_id": video["snippet"]["channelId"],
                        "video_id": video["id"],
                        "video_url": f"https://www.youtube.com/watch?v={video['id']}",
                        "video_title": video["snippet"]["title"],
                        "duration": str(isodate.parse_duration(duration_iso)),
                    }
                )

        if final_output:
            username = _get_username_for_filename(channel_url)
            timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S")
            json_filename = f"{username}_{timestamp}.json"
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            full_json_filepath = save_path / json_filename
            logger.info(
                f"Saving {len(final_output)} filtered videos to: {full_json_filepath.name}"
            )
            with open(full_json_filepath, "w", encoding="utf-8") as f:
                json.dump(final_output, f, indent=4)
            logger.info("JSON file saved successfully.")
        else:
            logger.warning("No videos met the filter criteria. No JSON file was saved.")

        return final_output

    except googleapiclient.errors.HttpError as e:
        error_details = json.loads(e.content.decode("utf-8"))
        error_message = error_details.get("error", {}).get(
            "message", "Unknown API error"
        )
        logger.error(f"An API error occurred: {error_message}", exc_info=True)
        raise RuntimeError(f"An API error occurred: {error_message}") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise e
