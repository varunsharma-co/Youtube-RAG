import os
from typing import Any, Dict, List, Union

# --- NEW FIX: Import the binary SQLite module and patch the system library ---
try:
    __import__("pysqlite3")
    import sys

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except:
    pass
# ----------------------------------------------------------------------------

import chromadb
from dotenv import load_dotenv

ErrorResponse = Dict[str, Any]


def call_vector_db(
    query_embedding: List[int], collection_name: str, n_results: int = 6
) -> Union[List[Dict[str, Any]], ErrorResponse]:
    """
    Handles Step 2: Calls the Chroma Cloud vector database with the query embedding
     and formats the top N results. Returns a structured error dictionary on failure.
     (This function is silent on success and logs only on error.)

    Args:
        query_embedding (List[int]): The embedding vector of the user query.
        collection_name (str): The name of the collection to query (already versioned).
        n_results (int): The number of top documents to retrieve.

    Returns:
        Union[List[Dict[str, Any]], ErrorResponse]: List of document dictionaries on success,
                                                     or an ErrorResponse dictionary on failure.
    """
    if not query_embedding:
        return {
            "error": "InputError",
            "reason": "Query embedding cannot be empty.",
            "source": "Chroma DB / R2",
        }
    if not collection_name:
        return {
            "error": "InputError",
            "reason": "Collection name must be provided.",
            "source": "Chroma DB / R2",
        }

    # Load environment variables from .env file
    load_dotenv()
    CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
    CHROMA_TENANT = os.getenv("CHROMA_TENANT")
    CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")

    if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE]):
        return {
            "error": "ConfigurationError",
            "reason": "One or more Chroma environment variables (CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE) are missing from .env file.",
            "source": "Chroma DB / R2",
        }

    try:
        # 1. Connect to Chroma DB
        chroma_client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY, tenant=CHROMA_TENANT, database=CHROMA_DATABASE
        )
        my_collection = chroma_client.get_collection(name=collection_name)

        # 2. Query the collection
        raw_results = my_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas"],
        )

        # 3. Process and format results
        top_results = []
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]

        for content, metadata in zip(documents, metadatas):
            result_item = {
                "content": content,
                "videoID": metadata.get("video_ID"),
                "timestamp": metadata.get("timestamp"),
            }
            top_results.append(result_item)

        return top_results

    except Exception as e:
        # Catch any ChromaDB-related exception and return structured error
        return {
            "error": "ChromaDBError",
            "reason": f"Error during Chroma DB connection or query: {type(e).__name__} - {str(e)}",
            "source": "Chroma DB / R2",
        }
