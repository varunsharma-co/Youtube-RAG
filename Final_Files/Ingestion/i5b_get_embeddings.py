import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

from logger_utils import logger

# A safe batch size for many embedding APIs
BATCH_SIZE = 512


def generate_embeddings_in_batches(
    chunks_data: Dict[str, List[Any]],
) -> Dict[str, List[Any]]:
    """
    Takes the chunked data, generates embeddings for the 'content' in optimized batches
    using the Jina Embeddings v4 API, and adds a '$vector' key to the dictionary.

    Args:
        chunks_data (Dict[str, List[Any]]): The dictionary containing '_id', 'content', 'metadata'.

    Returns:
        Dict[str, List[Any]]: The same dictionary, but with an added '$vector' list.
    """
    load_dotenv()
    JINA_API_KEY = os.getenv("JINA_API_KEY")
    if not JINA_API_KEY:
        logger.error(
            "JINA_API_KEY not found in .env file. Halting embedding generation."
        )
        raise ValueError("Jina API key is missing.")

    url = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JINA_API_KEY}",
    }

    texts = chunks_data.get("content", [])
    if not texts:
        logger.warning("No content found to create embeddings.")
        chunks_data["$vector"] = []
        return chunks_data

    all_embeddings = []
    logger.info(
        f"Starting embedding generation for {len(texts)} chunks in batches of {BATCH_SIZE}."
    )

    # Process texts in batches to avoid API limits and improve reliability
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]

        v4_input = [{"text": text} for text in batch_texts]
        data = {
            "input": v4_input,
            "model": "jina-embeddings-v4",
            "task": "retrieval.passage",
            "embedding_type": "binary",
            "dimensions": 512,
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            embeddings_response = response.json().get("data", [])
            batch_embeddings = [
                embedding["embedding"] for embedding in embeddings_response
            ]
            all_embeddings.extend(batch_embeddings)

            logger.info(f"Successfully processed batch {i // BATCH_SIZE + 1}...")

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP Error during embedding generation for batch starting at index {i}: {e}"
            )
            logger.error(f"Response body: {e.response.text}")
            all_embeddings.extend([None] * len(batch_texts))
        except Exception as e:
            logger.error(
                f"An unexpected error occurred for batch starting at index {i}: {e}"
            )
            all_embeddings.extend([None] * len(batch_texts))

    # **CRITICAL CHANGE**: Use '$vector' as the key name for the embeddings list.
    chunks_data["$vector"] = all_embeddings

    logger.info(
        f"Embedding generation complete. Processed {len(all_embeddings)} embeddings."
    )

    return chunks_data
