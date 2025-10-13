import math
from typing import Any, Dict, List

from logger_utils import logger

# =======================================================
#               PRIVATE HELPER FUNCTIONS
# =======================================================


def _ms_to_seconds(ms: int) -> float:
    """Converts milliseconds to seconds."""
    return ms / 1000


def _create_chunks_for_single_video(video_data: Dict) -> Dict[str, List[Any]]:
    """
    Processes a single video's data to generate sentence-aware text chunks.
    This is the core chunking logic.
    """
    # Extract data from the main dictionary
    transcript_words = video_data.get("transcript_words", [])
    summary = video_data.get("summary", "")
    video_id = video_data.get("video_id", "unknown_video")
    video_title = video_data.get("video_title", "Unknown Title")
    channel_id = video_data.get("channel_id", "unknown_channel")

    if not transcript_words:
        return {"_id": [], "content": [], "metadata": []}

    # Initialize lists for this video's chunks
    id_list, content_list, metadata_list = [], [], []

    # Initialize variables for the chunking loop
    current_chunk_content = []
    current_start_time = None
    word_count = 0
    chunk_serial = 1

    for word in transcript_words:
        if current_start_time is None:
            # AssemblyAI Word object has .start attribute in ms
            current_start_time = _ms_to_seconds(word.start)

        current_chunk_content.append(word.text)
        word_count += 1

        if word.text.endswith((".", "?")):
            if 200 <= word_count <= 300:
                id_list.append(f"{video_id}_{chunk_serial:04d}")
                content_list.append(" ".join(current_chunk_content))
                metadata_list.append(
                    {
                        "timestamp": math.floor(current_start_time),
                        "channel_ID": channel_id,
                        "video_ID": video_id,
                        "video_title": video_title,
                        "video_summary": summary,
                    }
                )
                current_chunk_content, current_start_time, word_count = [], None, 0
                chunk_serial += 1

            elif word_count > 300:
                id_list.append(f"{video_id}_{chunk_serial:04d}")
                content_list.append(" ".join(current_chunk_content[:300]))
                metadata_list.append(
                    {
                        "timestamp": math.floor(current_start_time),
                        "channel_ID": channel_id,
                        "video_ID": video_id,
                        "video_title": video_title,
                        "video_summary": summary,
                    }
                )
                # Carry over the remainder
                current_chunk_content = current_chunk_content[300:]
                # Note: The start time for the carried-over text is approximated to the current word's start
                current_start_time = _ms_to_seconds(word.start)
                word_count = len(current_chunk_content)
                chunk_serial += 1

    # Handle the final leftover chunk
    if current_chunk_content:
        id_list.append(f"{video_id}_{chunk_serial:04d}")
        content_list.append(" ".join(current_chunk_content))
        metadata_list.append(
            {
                "timestamp": (
                    math.floor(current_start_time)
                    if current_start_time is not None
                    else 0
                ),
                "channel_ID": channel_id,
                "video_ID": video_id,
                "video_title": video_title,
                "video_summary": summary,
            }
        )

    return {"_id": id_list, "content": content_list, "metadata": metadata_list}


# =======================================================
#               PUBLIC FUNCTION
# =======================================================


def create_chunks_from_videos(video_data_list: List[Dict]) -> Dict[str, List[Any]]:
    """
    Takes a list of enriched video data and creates a single, aggregated
    dictionary of chunks ready for embedding and database upload.

    Args:
        video_data_list (List[Dict]): The list of fully processed video dictionaries.

    Returns:
        Dict[str, List[Any]]: A dictionary with keys '_id', 'content', 'metadata',
                              where each value is a list of all chunks from all videos.
    """
    # This is the final structure that will aggregate all chunks
    final_chunks = {"_id": [], "content": [], "metadata": []}

    logger.info(f"Starting chunking process for {len(video_data_list)} videos.")

    for video in video_data_list:
        if not video.get("transcript_words"):
            logger.warning(
                f"Skipping video {video.get('video_id')} due to missing transcript words."
            )
            continue

        # Generate chunks for the current video
        video_chunks = _create_chunks_for_single_video(video)

        # Extend the main lists with the chunks from the current video
        final_chunks["_id"].extend(video_chunks["_id"])
        final_chunks["content"].extend(video_chunks["content"])
        final_chunks["metadata"].extend(video_chunks["metadata"])

    logger.info(
        f"Chunking complete. Generated a total of {len(final_chunks['_id'])} chunks."
    )
    return final_chunks
