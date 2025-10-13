import os
import threading
from pathlib import Path
from typing import Dict, List

import assemblyai as aai
from dotenv import load_dotenv

# Import the configured logger
from logger_utils import logger

# =======================================================
#               PRIVATE HELPER FUNCTION (for threading)
# =======================================================


def _transcribe_worker(
    video_data: Dict,
    results_list: List[Dict],
    config: aai.TranscriptionConfig,
    lock: threading.Lock,
):
    """
    Worker function executed by each thread to transcribe a single audio file.

    Args:
        video_data (Dict): A dictionary containing 'video_url' and 'm4a_file_path'.
        results_list (List[Dict]): A shared list to append the results to.
        config (aai.TranscriptionConfig): The AssemblyAI configuration object.
        lock (threading.Lock): A lock to ensure thread-safe appends to the results_list.
    """
    m4a_path = video_data.get("m4a_file_path")
    video_url = video_data.get("video_url")

    if not m4a_path or not Path(m4a_path).exists():
        logger.warning(
            f"M4A file path for {video_url} is missing or invalid. Skipping transcription."
        )
        return

    try:
        logger.info(f"Starting transcription for: {Path(m4a_path).name}")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(str(m4a_path), config)

        if transcript.status == aai.TranscriptStatus.completed:
            # Prepare the result dictionary
            result = {
                "video_url": video_url,
                "transcript_text": transcript.text,
                "transcript_words": transcript.words,
            }
            # Append to the shared list in a thread-safe way
            with lock:
                results_list.append(result)
            logger.info(f"Successfully transcribed: {Path(m4a_path).name}")

        elif transcript.status == aai.TranscriptStatus.error:
            logger.error(
                f"Transcription failed for {Path(m4a_path).name} with error: {transcript.error}"
            )

    except Exception as e:
        logger.error(
            f"An unexpected error occurred during transcription for {video_url}: {e}"
        )


# =======================================================
#               PUBLIC FUNCTION
# =======================================================


def transcribe_audio_files_async(video_data: List[Dict]) -> List[Dict]:
    """
    Transcribes multiple audio files concurrently using threading.

    Args:
        video_data (List[Dict]): The main list of dictionaries, each must contain 'm4a_file_path' and 'video_url'.

    Returns:
        List[Dict]: A list of dictionaries with 'video_url', 'transcript_text', and 'transcript_words'.
    """
    load_dotenv()
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        logger.error(
            "ASSEMBLYAI_API_KEY not found in .env file. Halting transcription."
        )
        raise ValueError("AssemblyAI API key is missing.")

    aai.settings.api_key = api_key

    # Define transcription configuration once
    config = aai.TranscriptionConfig(
        punctuate=True,
        format_text=True,
        speech_model=aai.SpeechModel.universal,
        language_code="en_us",
    )

    threads = []
    transcription_results = []
    lock = (
        threading.Lock()
    )  # To safely append to the results list from multiple threads

    logger.info(f"Starting concurrent transcription for {len(video_data)} audio files.")

    for video in video_data:
        # We pass the shared list, config, and lock to each worker thread
        thread = threading.Thread(
            target=_transcribe_worker, args=(video, transcription_results, config, lock)
        )
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete their work
    for thread in threads:
        thread.join()

    logger.info("All transcription threads have completed.")
    return transcription_results
