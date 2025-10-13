"""
WE ARE CURRENTLY *NOT* USING THIS code, but can use for uploading very large files by adding a delay in polling.

---

(from AI Studio - Gemini)

The current transcriber.transcribe() function is a "blocking" call—it handles the uploading and status-checking internally and only returns when the job is done.
To insert a delay, we need to switch to the non-blocking, two-step pattern provided by the AssemblyAI SDK:
transcriber.submit(): This uploads the file and immediately returns a transcript object with an ID, without waiting for the result.
transcript.poll(): This is the function we call to check the status of the submitted job.
By using this pattern, we can create our own polling loop and insert the time.sleep(60) delay exactly where you want it.
Here is the complete, updated code for i3_get_transcription.py with the requested changes.

---

(from AI Studio - Gemini)

Summary of Changes:
1. Imported time and TranscriptStatus: These are necessary for the new logic.
2. Switched to transcriber.submit(): Instead of waiting for the full transcription, we now just submit the job to AssemblyAI's queue and immediately move on.
3. Added a while True Polling Loop: After submitting the job, the script now enters a loop.
4. Added time.sleep(60): This is the key change. The script will now pause for 60 seconds before it checks the API for the transcription status. This pause happens both after the initial submission and between every subsequent check.
5. Used transcript.poll(): Inside the loop, this command refreshes the status of our transcription job.
6. Checked Status and Exited Loop: The loop checks if the status is completed or error and breaks accordingly, ensuring the thread eventually finishes. If the job is still queued or processing, the loop continues for another iteration.

"""

import os
import threading
import time  # <-- NEW: Import the time module for delays
from pathlib import Path
from typing import Dict, List

import assemblyai as aai
from assemblyai import TranscriptStatus  # <-- NEW: Import the status enum
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
    This now uses a non-blocking submission and a polling loop with delays.
    """
    m4a_path = video_data.get("m4a_file_path")
    video_url = video_data.get("video_url")

    if not m4a_path or not Path(m4a_path).exists():
        logger.warning(
            f"M4A file path for {video_url} is missing or invalid. Skipping transcription."
        )
        return

    try:
        logger.info(f"Submitting transcription for: {Path(m4a_path).name}")
        transcriber = aai.Transcriber()

        # --- UPDATED LOGIC: Use non-blocking submission ---
        transcript = transcriber.submit(str(m4a_path), config)
        logger.info(
            f"Submitted {Path(m4a_path).name}, Job ID: {transcript.id}. Now polling for results."
        )

        # --- NEW: Polling loop with a 60-second delay ---
        while True:
            # Wait 60 seconds before checking the status.
            # This happens before the first check and between every subsequent check.
            time.sleep(60)

            logger.info(
                f"Polling status for job {transcript.id} ({Path(m4a_path).name})..."
            )
            # Refresh the transcript object with the latest status from the API
            transcript = transcript.poll()

            if transcript.status == TranscriptStatus.completed:
                logger.info(f"Successfully transcribed: {Path(m4a_path).name}")
                result = {
                    "video_url": video_url,
                    "transcript_text": transcript.text,
                    "transcript_words": transcript.words,
                }
                with lock:
                    results_list.append(result)
                break  # Exit the loop on success

            elif transcript.status == TranscriptStatus.error:
                logger.error(
                    f"Transcription failed for {Path(m4a_path).name} with error: {transcript.error}"
                )
                break  # Exit the loop on failure

            # If status is still 'queued' or 'processing', the loop will continue
            # and wait for another 60 seconds before the next poll.
        # --- END OF NEW POLLING LOGIC ---

    except Exception as e:
        logger.error(
            f"An unexpected error occurred during transcription submission for {video_url}: {e}"
        )


# =======================================================
#               PUBLIC FUNCTION
# =======================================================


def transcribe_audio_files_async(video_data: List[Dict]) -> List[Dict]:
    """
    Transcribes multiple audio files concurrently using threading.
    """
    load_dotenv()
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        logger.error(
            "ASSEMBLYAI_API_KEY not found in .env file. Halting transcription."
        )
        raise ValueError("AssemblyAI API key is missing.")

    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(
        punctuate=True,
        format_text=True,
        speech_model=aai.SpeechModel.universal,
        language_code="en_us",
    )

    threads = []
    transcription_results = []
    lock = threading.Lock()

    logger.info(f"Starting concurrent transcription for {len(video_data)} audio files.")

    for video in video_data:
        thread = threading.Thread(
            target=_transcribe_worker, args=(video, transcription_results, config, lock)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logger.info("All transcription threads have completed.")
    return transcription_results
