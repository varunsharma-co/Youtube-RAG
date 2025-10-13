from typing import Any, Dict, List

from Final_Files.Ingestion.i5a_create_chunks import create_chunks_from_videos
from Final_Files.Ingestion.i5b_get_embeddings import generate_embeddings_in_batches
from logger_utils import logger


def prepare_data_for_vector_db(video_data_list: List[Dict]) -> Dict[str, List[Any]]:
    """
    Orchestrates the entire data preparation process for vector database upload.
    This involves creating text chunks and then generating their embeddings.

    Args:
        video_data_list (List[Dict]): The list of fully processed video dictionaries.

    Returns:
        Dict[str, List[Any]]: The final data structure ready for database upload,
                              containing '_id', 'content', 'metadata', and '$vector'.
    """
    logger.info("--- Starting Data Preparation for Vector Database ---")

    # --- Step 5a: Create Chunks ---
    logger.info("Step 5a: Creating text chunks from transcripts...")
    chunks_without_embeddings = create_chunks_from_videos(video_data_list)

    if not chunks_without_embeddings.get("_id"):
        logger.warning("No chunks were created. Skipping embedding generation.")
        chunks_without_embeddings["$vector"] = []  # Ensure the key exists even if empty
        return chunks_without_embeddings

    # --- Step 5b: Generate Embeddings and add them to the structure ---
    logger.info("Step 5b: Generating embeddings for text chunks...")
    final_data_with_embeddings = generate_embeddings_in_batches(
        chunks_without_embeddings
    )

    logger.info("--- Data Preparation for Vector Database Complete ---")

    return final_data_with_embeddings
