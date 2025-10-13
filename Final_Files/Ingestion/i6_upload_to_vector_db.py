import os
from typing import Any, Dict, List

import chromadb
from dotenv import load_dotenv

from logger_utils import logger

# A safe batch size for ChromaDB uploads
BATCH_SIZE = 200


def upload_to_chromadb(vector_data: Dict[str, List[Any]], collection_name: str):
    """
    Connects to ChromaDB and uploads the prepared vector data in batches.

    Args:
        vector_data (Dict[str, List[Any]]): The final data dictionary containing '_id',
                                            'content', 'metadata', and '$vector'.
        collection_name (str): The name of the collection to create or use in ChromaDB.
    """
    load_dotenv()
    CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
    CHROMA_TENANT = os.getenv("CHROMA_TENANT")
    CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")

    if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE]):
        logger.error("ChromaDB credentials not found in .env file. Halting upload.")
        raise ValueError("One or more ChromaDB environment variables are missing.")

    try:
        logger.info("Connecting to ChromaDB Cloud...")
        chroma_client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY, tenant=CHROMA_TENANT, database=CHROMA_DATABASE
        )
        logger.info("Successfully connected to ChromaDB.")

        logger.info(f"Getting or creating collection: '{collection_name}'")
        my_collection = chroma_client.get_or_create_collection(name=collection_name)
        logger.info("Collection is ready.")

        # --- CRITICAL STEP: Map your dictionary keys to ChromaDB's expected names ---
        ids = vector_data.get("_id", [])
        embeddings = vector_data.get("$vector", [])
        documents = vector_data.get("content", [])
        metadatas = vector_data.get("metadata", [])
        # --- End of mapping ---

        if not ids:
            logger.warning("No data (IDs) found in the input. Nothing to upload.")
            return

        logger.info(
            f"Starting upload of {len(ids)} records to ChromaDB in batches of {BATCH_SIZE}..."
        )

        # Upload data in batches for reliability and efficiency
        for i in range(0, len(ids), BATCH_SIZE):
            batch_ids = ids[i : i + BATCH_SIZE]
            batch_embeddings = embeddings[i : i + BATCH_SIZE]
            batch_documents = documents[i : i + BATCH_SIZE]
            batch_metadatas = metadatas[i : i + BATCH_SIZE]

            try:
                my_collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                )
                logger.info(f"Successfully uploaded batch {i // BATCH_SIZE + 1}...")
            except Exception as e:
                logger.error(
                    f"An error occurred while uploading batch {i // BATCH_SIZE + 1}: {e}"
                )
                # Optional: Decide if you want to stop on error or continue
                # continue

        logger.info("All batches have been processed. ChromaDB upload complete!")

    except Exception as e:
        logger.error(f"A critical error occurred while interacting with ChromaDB: {e}")
        # Re-raise the exception to halt the main script if the connection fails
        raise e
