import os
from typing import Any, Dict, List, Union

import requests
from dotenv import load_dotenv

# Define a specific type hint for a structured error response
ErrorResponse = Dict[str, Any]


# --- Helper Function for V4 API (Input is a list of dicts) ---
def _call_v4_api(api_key: str, query: str) -> Union[List[int], ErrorResponse]:
    model_name = "jina-embeddings-v4"

    api_url = "https://api.jina.ai/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model_name,
        "task": "retrieval.query",
        "dimensions": 512,
        "embedding_type": "binary",
        # V4 requires a list of dictionaries with a 'text' key
        "input": [{"text": query}],
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        response_data = response.json()

        if (
            "data" in response_data
            and response_data["data"]
            and "embedding" in response_data["data"][0]
        ):
            return response_data["data"][0]["embedding"]
        else:
            return {
                "error": "APIResponseError",
                "reason": f"Invalid response format from Jina {model_name}. Embedding not found. Raw response: {response.text[:100]}",
                "source": f"Jina API {model_name} / R1",
            }

    except requests.exceptions.RequestException as e:
        print(f"❌ Error during Jina {model_name} API call: {e}")
        return {
            "error": "NetworkRequestError",
            "reason": f"There was a network or timeout error while calling Jina {model_name}. Reason: {type(e).__name__} - {str(e)}",
            "source": f"Jina API {model_name} / R1",
        }


# --- Helper Function for V3 API (Input is a list of strings) ---
def _call_v3_api(api_key: str, query: str) -> Union[List[int], ErrorResponse]:
    model_name = "jina-embeddings-v3"

    api_url = "https://api.jina.ai/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model_name,
        "task": "retrieval.query",
        "dimensions": 512,
        "embedding_type": "binary",
        # V3 requires a list of strings
        "input": [query],
    }

    try:
        # V3 should be more stable, keeping timeout at 60s for consistency
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        response_data = response.json()

        if (
            "data" in response_data
            and response_data["data"]
            and "embedding" in response_data["data"][0]
        ):
            return response_data["data"][0]["embedding"]
        else:
            return {
                "error": "APIResponseError",
                "reason": f"Invalid response format from Jina {model_name}. Embedding not found. Raw response: {response.text[:100]}",
                "source": f"Jina API {model_name} / R1",
            }

    except requests.exceptions.RequestException as e:
        print(f"❌ Error during Jina {model_name} API call: {e}")
        return {
            "error": "NetworkRequestError",
            "reason": f"There was a network or timeout error while calling Jina {model_name}. Reason: {type(e).__name__} - {str(e)}",
            "source": f"Jina API {model_name} / R1",
        }


# --- Main Dispatcher Function ---
def get_query_embedding(query: str) -> Union[List[int], ErrorResponse]:
    """
    Generates a binary embedding for a query using the Jina API, dispatching
    to V3 or V4 based on the JINA_EMBEDDING_MODEL_VERSION environment variable.
    (This function is silent on success and logs only on error.)

    Returns:
        Union[List[int], ErrorResponse]: The embedding vector on success, or a
                                         structured dictionary with error details on failure.
    """

    if not query:
        return {
            "error": "QueryInputError",
            "reason": "Input query cannot be empty.",
            "source": "Jina API / R1",
        }

    # Load environment variables
    load_dotenv()
    jina_api_key = os.environ.get("JINA_API_KEY")
    jina_model_version = os.environ.get(
        "JINA_EMBEDDING_MODEL_VERSION", "v4"
    ).lower()  # Default to v4

    if not jina_api_key:
        return {
            "error": "ConfigurationError",
            "reason": "JINA_API_KEY not found in environment variables or .env file.",
            "source": "Jina API / R1",
        }

    # Dispatch logic
    if jina_model_version == "v3":
        result = _call_v3_api(jina_api_key, query)
    elif jina_model_version == "v4":
        result = _call_v4_api(jina_api_key, query)
    else:
        # Fallback for an invalid configuration
        print(
            "❌ Invalid JINA_EMBEDDING_MODEL_VERSION. Defaulting to V4..."
        )  # KEEP: Important configuration warning
        result = _call_v4_api(jina_api_key, query)

    return result
