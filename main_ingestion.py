import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Import modules for each step
from Final_Files.Ingestion.i1_get_youtube_data import fetch_and_filter_youtube_videos
from Final_Files.Ingestion.i1b_timestamp import (
    save_last_run_timestamp,
)  # <-- NEW IMPORT
from Final_Files.Ingestion.i2_download_audio import download_audio_from_videos
from Final_Files.Ingestion.i3_get_transcription import transcribe_audio_files_async
from Final_Files.Ingestion.i4_get_summary import generate_summaries_sync
from Final_Files.Ingestion.i5_prepare_vector_data import prepare_data_for_vector_db
from Final_Files.Ingestion.i6_upload_to_vector_db import upload_to_chromadb

# Import the logger
from logger_utils import logger, setup_logger

# =======================================================
#               CONFIGURATION
# =======================================================
CHANNEL_URL = "https://www.youtube.com/@riandoris"
MINIMUM_VIDEO_MINUTES = 2

# --- Vector Database Configuration ---
CHROMA_COLLECTION_NAME = "Rian_Doris_YT_RAG_Working"

# --- Directory Paths ---
BASE_FINAL_FILES_DIRECTORY = "Final_Files"
BASE_SAVE_DIRECTORY = f"{BASE_FINAL_FILES_DIRECTORY}/Saving_Intermediate_Data"

STEP1_JSON_SAVE_DIRECTORY = f"{BASE_SAVE_DIRECTORY}/STEP_1_JSON_YouTube_Videos_Data"
STEP2_M4A_SAVE_DIRECTORY = f"{BASE_SAVE_DIRECTORY}/STEP_2_M4A_Files"
STEP8_TRANSCRIPTS_SAVE_DIRECTORY = f"{BASE_SAVE_DIRECTORY}/STEP_8_Transcripts"
STEP10_CHUNKS_SAVE_DIRECTORY = f"{BASE_SAVE_DIRECTORY}/STEP_10_Chunks_With_Embeddings"

LOG_DIRECTORY_RELATIVE = f"{BASE_FINAL_FILES_DIRECTORY}/Logs"

# =======================================================
#               HELPER FUNCTIONS
# =======================================================


def _get_username_from_url(channel_url: str) -> str:
    """Extracts a clean username from the URL for filenames."""
    match = re.search(r"youtube\.com/(?:@|c/|user/)([A-Za-z0-9_-]+)", channel_url)
    return match.group(1) if match else "youtube_channel"


def _save_jsonl(data: List[Dict], filename: str, save_dir: Path):
    """Saves a list of dictionaries to a JSON Lines file."""
    save_dir.mkdir(parents=True, exist_ok=True)
    full_filepath = save_dir / filename
    logger.info(f"Saving data to: {filename}")
    try:
        with open(full_filepath, "w", encoding="utf-8") as f:
            for item in data:
                item_copy = {
                    k: str(v) if isinstance(v, Path) else v for k, v in item.items()
                }
                if "transcript_words" in item_copy and item_copy["transcript_words"]:
                    item_copy["transcript_words"] = [
                        w.__dict__ if hasattr(w, "__dict__") else w
                        for w in item_copy["transcript_words"]
                    ]
                f.write(json.dumps(item_copy) + "\n")
        logger.info(f"Successfully saved {len(data)} records to {filename}.")
    except Exception as e:
        logger.error(f"Failed to save {filename}: {e}")


def _save_json(data: Dict, filename: str, save_dir: Path):
    """Saves a dictionary to a standard, indented JSON file."""
    save_dir.mkdir(parents=True, exist_ok=True)
    full_filepath = save_dir / filename
    logger.info(f"Saving data to: {filename}")
    try:
        with open(full_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Successfully saved data to {filename}.")
    except Exception as e:
        logger.error(f"Failed to save {filename}: {e}")


# =======================================================
#               EXECUTION
# =======================================================

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    # **UPDATED**: Resolve all absolute paths based on the new configurations.
    absolute_base_final_files_dir = script_dir / BASE_FINAL_FILES_DIRECTORY
    absolute_step1_dir = script_dir / STEP1_JSON_SAVE_DIRECTORY
    absolute_step2_dir = script_dir / STEP2_M4A_SAVE_DIRECTORY
    absolute_step8_dir = script_dir / STEP8_TRANSCRIPTS_SAVE_DIRECTORY
    absolute_step10_dir = script_dir / STEP10_CHUNKS_SAVE_DIRECTORY
    absolute_log_dir = script_dir / LOG_DIRECTORY_RELATIVE

    # --- LOGGER SETUP (with username) ---
    username_for_files = _get_username_from_url(CHANNEL_URL)
    setup_logger(log_dir=absolute_log_dir, username=username_for_files)

    logger.info("--- Starting Master Ingestion Script ---")

    video_data: List[Dict] = []

    try:
        # --- STEP 1: Fetch YouTube Data ---
        logger.info("\n--- STEP 1: Starting YouTube Metadata Fetch and Filter ---")
        video_data = fetch_and_filter_youtube_videos(
            channel_url=CHANNEL_URL,
            min_duration_minutes=MINIMUM_VIDEO_MINUTES,
            save_dir=absolute_step1_dir,
        )
        if not video_data:
            logger.warning("Step 1 returned no videos. Halting process.")
            exit()

        # --- STEP 1b: Save Last Run Timestamp ---
        logger.info("\n--- STEP 1b: Saving Last Run Timestamp ---")
        save_last_run_timestamp(
            save_dir=absolute_base_final_files_dir,  # <-- Save to /Final_Files/
            username=username_for_files,
        )

        # --- STEPS 2-7: Download, Transcribe, and Summarize ---
        logger.info("\n--- STEP 2 & 3: Downloading Audio and Merging Paths ---")
        download_results = download_audio_from_videos(
            video_list=video_data, output_path=absolute_step2_dir
        )
        path_lookup = {item["video_url"]: item["m4a_path"] for item in download_results}
        for video in video_data:
            video["m4a_file_path"] = path_lookup.get(video["video_url"])

        videos_to_process = [v for v in video_data if v.get("m4a_file_path")]
        if not videos_to_process:
            exit()

        logger.info("\n--- STEP 4 & 5: Transcribing Audio and Merging Results ---")
        transcription_results = transcribe_audio_files_async(videos_to_process)
        transcript_lookup = {item["video_url"]: item for item in transcription_results}
        for video in video_data:
            transcript_data = transcript_lookup.get(video["video_url"], {})
            video["transcript_text"] = transcript_data.get("transcript_text")
            video["transcript_words"] = transcript_data.get("transcript_words")

        videos_to_process = [v for v in video_data if v.get("transcript_text")]
        if not videos_to_process:
            exit()

        logger.info("\n--- STEP 6 & 7: Generating Summaries and Merging Results ---")
        summary_results = generate_summaries_sync(
            [
                {"video_url": v["video_url"], "transcript_text": v["transcript_text"]}
                for v in videos_to_process
            ]
        )
        summary_lookup = {
            item["video_url"]: item["summary"] for item in summary_results
        }
        for video in video_data:
            video["summary"] = summary_lookup.get(video["video_url"])

        # --- STEP 8: SAVE INTERMEDIATE ENRICHED DATA (JSONL) ---
        logger.info("\n--- STEP 8: Saving Enriched Video Data ---")
        timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S")
        jsonl_filename = f"{username_for_files}_TRANSCRIPTS_{timestamp}.jsonl"
        _save_jsonl(video_data, jsonl_filename, absolute_step8_dir)

        # --- STEP 9: PREPARE DATA FOR VECTOR DATABASE (CHUNKING & EMBEDDING) ---
        logger.info("\n--- STEP 9: Preparing Data for Vector Database ---")
        final_vector_data = prepare_data_for_vector_db(video_data)

        # --- STEP 10: SAVE FINAL VECTOR-READY DATA (JSON) ---
        if final_vector_data.get("$vector") and any(final_vector_data["$vector"]):
            logger.info("\n--- STEP 10: Saving Final Vector-Ready Data ---")
            vector_filename = f"{username_for_files}_VECTORS_{timestamp}.json"
            _save_json(final_vector_data, vector_filename, absolute_step10_dir)

            # --- STEP 11: UPLOAD DATA TO VECTOR DATABASE ---
            logger.info("\n--- STEP 11: Uploading Data to ChromaDB ---")
            upload_to_chromadb(
                vector_data=final_vector_data, collection_name=CHROMA_COLLECTION_NAME
            )
        else:
            logger.warning("Steps 10 & 11 skipped: No embeddings were generated.")

        logger.info(
            f"\nSuccessfully completed all steps. Processed {len(video_data)} videos."
        )
        logger.info("--- YouTube Data Ingestion Finished Successfully ---")

    except Exception as e:
        logger.error(
            f"--- A critical error occurred in the main script. Process halted: {e} ---",
            exc_info=True,
        )
