import os
from typing import Any, Dict, List, Union

import requests
from dotenv import load_dotenv

# Define the structure for the input/output document dictionary
DocumentDict = Dict[str, Any]
ErrorResponse = Dict[str, Any]


def rerank_documents(
    query: str, documents: List[DocumentDict]
) -> Union[List[DocumentDict], ErrorResponse]:
    """
    Handles Step 3: Reranks a list of retrieved documents using the Jina Reranker API.
    Returns a structured error dictionary on failure.
    (This function is silent on success and logs only on error.)

    Args:
        query (str): The original user query.
        documents (List[DocumentDict]): List of document dictionaries.

    Returns:
        Union[List[DocumentDict], ErrorResponse]: List of reranked documents on success,
                                                  or an ErrorResponse dictionary on failure.
    """

    if not query:
        return {
            "error": "InputError",
            "reason": "Query cannot be empty.",
            "source": "Jina Reranker API / R3",
        }
    if not documents:
        # NOTE: Returning an empty list here is valid and not an error
        return []

    # Load environment variables from .env file
    load_dotenv()
    jina_api_key = os.environ.get("JINA_API_KEY")

    if not jina_api_key:
        return {
            "error": "ConfigurationError",
            "reason": "JINA_API_KEY not found in environment variables or .env file.",
            "source": "Jina Reranker API / R3",
        }

    # 1. Prepare data for the API call
    document_contents = [doc["content"] for doc in documents]
    JINA_TOP_N = "5"

    api_url = "https://api.jina.ai/v1/rerank"
    headers = {"Authorization": f"Bearer {jina_api_key}"}
    payload = {
        "model": "jina-reranker-v2-base-multilingual",
        "query": query,
        "top_n": JINA_TOP_N,
        "documents": document_contents,
        "return_documents": False,
    }

    try:
        # 2. Call the Jina API
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()

        rerank_data = response.json()

        if "results" not in rerank_data:
            return {
                "error": "APIResponseError",
                "reason": "Invalid response format from Jina Reranker API. 'results' key not found.",
                "source": "Jina Reranker API / R3",
            }

    except requests.exceptions.RequestException as e:
        # Print the error for local debugging
        print(f"❌ Error during Jina Reranker API call: {e}")
        return {
            "error": "NetworkRequestError",
            "reason": f"There was a network or timeout error while calling Jina Reranker API. Reason: {type(e).__name__} - {str(e)}",
            "source": "Jina Reranker API / R3",
        }
    except Exception as e:
        # Print the error for local debugging
        print(f"❌ Error processing Jina Reranker API response: {e}")
        return {
            "error": "UnexpectedError",
            "reason": f"An unexpected error occurred: {type(e).__name__} - {str(e)}",
            "source": "Jina Reranker API / R3",
        }

    # 3. Map scores back to the original documents
    reranked_documents = [doc.copy() for doc in documents]
    for doc in reranked_documents:
        doc["relevance_score"] = None

    for result in rerank_data["results"]:
        original_index = result["index"]
        relevance_score = result["relevance_score"]

        if 0 <= original_index < len(reranked_documents):
            reranked_documents[original_index]["relevance_score"] = relevance_score

    return reranked_documents
