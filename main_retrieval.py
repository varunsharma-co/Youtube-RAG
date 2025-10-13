import json
import os
from typing import Any, Dict, List, Union

from dotenv import load_dotenv

from Final_Files.Retrieval.r1_get_query_embedding import get_query_embedding
from Final_Files.Retrieval.r2_call_vectorDB import call_vector_db
from Final_Files.Retrieval.r3_reranker import rerank_documents
from Final_Files.Retrieval.r4_filter_top_results import filter_top_results
from Final_Files.Retrieval.r5_call_llm import call_llm_for_answer
from Final_Files.Retrieval.r6_format_final_output import format_final_output

# --- Configuration Section ---
USER_QUERY = "what is allostatic load"
BASE_COLLECTION_NAME = "Rian_Doris_YT_RAG_Working"
DEFAULT_THRESHOLD = 0.4
# -----------------------------

# Load environment variables once for the orchestrator to determine config
load_dotenv()

# --- Dynamic Configuration Loading ---
JINA_MODEL_VERSION = os.environ.get("JINA_EMBEDDING_MODEL_VERSION", "v4").lower()
COLLECTION_NAME = f"{BASE_COLLECTION_NAME}_{JINA_MODEL_VERSION}"

# Load and convert the threshold score from .env, defaulting to 0.4
try:
    RELEVANCE_SCORE_THRESHOLD = float(
        os.environ.get("RELEVANCE_SCORE_THRESHOLD", DEFAULT_THRESHOLD)
    )
except ValueError:
    print(
        f"Warning: RELEVANCE_SCORE_THRESHOLD in .env is not a valid number. Defaulting to {DEFAULT_THRESHOLD}."
    )
    RELEVANCE_SCORE_THRESHOLD = DEFAULT_THRESHOLD
# -------------------------------------


def _is_error_dict(result: Any) -> bool:
    """Helper to check if a function result is a structured error dictionary."""
    return isinstance(result, dict) and "error" in result


def _format_critical_error_response(
    error_details: Dict[str, Any],
) -> Dict[str, Union[str, List[str]]]:
    """
    Creates the final structured error response for critical early failures.
    """
    answer_message = (
        f"There was an error completing your request due to an external service failure "
        f"while performing **{error_details.get('source', 'Unknown')}**. "
        f"Please try again in a few minutes.\n\n"
        f"Error Details: {error_details.get('reason', 'N/A')}"
    )
    return {"answer": answer_message, "references": ["NA"]}


def main_retrieval_workflow(query: str):
    """
    Orchestrates the entire RAG workflow by calling modular functions in sequence.
    (Logs status prints to the console/Lambda logs.)

    Args:
        query (str): The user's input query.

    Returns:
        dict: The final formatted output with an answer and references.
              Returns None if any step fails critically and unrecoverably.
    """
    try:
        # Step 1: Generate embeddings for the query
        print("--- Starting Step 1: Generate Query Embedding ---")
        query_embedding_or_error = get_query_embedding(query)

        # CRITICAL CHECK 1: Check if Step 1 failed
        if _is_error_dict(query_embedding_or_error):
            print(
                f"--- FAILED Step 1: Critical error in Jina API call. Aborting workflow. ---"
            )
            return _format_critical_error_response(query_embedding_or_error)

        query_embedding = query_embedding_or_error
        print("--- Finished Step 1: Successfully generated query embedding. ---\n")

        # Step 2: Retrieve documents from a vector store
        print(
            f"--- Starting Step 2: Vector Search and Retrieval from COLLECTION: {COLLECTION_NAME} ---"
        )
        top_results_or_error = call_vector_db(query_embedding, COLLECTION_NAME)

        # CRITICAL CHECK 2: Check if Step 2 failed
        if _is_error_dict(top_results_or_error):
            print(
                f"--- FAILED Step 2: Critical error in Chroma DB call. Aborting workflow. ---"
            )
            return _format_critical_error_response(top_results_or_error)

        top_results = top_results_or_error
        print(
            f"--- Finished Step 2: Retrieved and formatted {len(top_results)} documents. ---\n"
        )

        # Step 3: Rerank the retrieved documents
        print("--- Starting Step 3: Reranking Documents ---")
        reranked_results_or_error = rerank_documents(query, top_results)

        # CRITICAL CHECK 3: Check if Step 3 failed
        if _is_error_dict(reranked_results_or_error):
            print(
                f"--- FAILED Step 3: Critical error in Jina Reranker call. Aborting workflow. ---"
            )
            return _format_critical_error_response(reranked_results_or_error)

        reranked_results = reranked_results_or_error
        print(
            f"--- Finished Step 3: Successfully reranked {len(reranked_results)} documents. ---\n"
        )

        # Step 4: Filter the results (Local Function - assumes no API-level failure)
        print(
            f"--- Starting Step 4: Filtering Results with Threshold {RELEVANCE_SCORE_THRESHOLD} ---"
        )
        filtered_results = filter_top_results(
            reranked_results, RELEVANCE_SCORE_THRESHOLD
        )

        if len(filtered_results) == 1 and filtered_results[0].get("videoID") is None:
            print(
                "--- Finished Step 4: Final filtered document count: 1 (Fallback used). ---\n"
            )
        else:
            print(
                f"--- Finished Step 4: Final filtered document count: {len(filtered_results)}. ---\n"
            )

        # Step 5: Generate a final answer
        print("--- Starting Step 5: Generating Answer with LLM ---")
        llm_raw_output = call_llm_for_answer(query, filtered_results)

        # Step 6: Structure the final output
        print("--- Starting Step 6: Final Output Formatting ---")
        final_output = format_final_output(llm_raw_output)
        print("--- Finished Step 6: Final Output Formatted. ---\n")

        return final_output

    except Exception as e:
        # Final safety net for truly unhandled system errors
        print(f"\nWorkflow stopped due to a critical, unhandled error: {e}")
        unhandled_error_details = {
            "error": "UnhandledSystemError",
            "reason": f"System error caught in orchestrator: {type(e).__name__} - {str(e)}",
            "source": "Orchestrator / main_retrieval.py",
        }
        return _format_critical_error_response(unhandled_error_details)


if __name__ == "__main__":
    # Run the main workflow
    print(f"--- CLI: Starting retrieval workflow for query: '{USER_QUERY}' ---")

    result = main_retrieval_workflow(USER_QUERY)

    if result:
        print("\n--- CLI: FINAL OUTPUT ---")
        print(json.dumps(result, indent=4))
        print("------------------------")
    else:
        # This branch should rarely be hit due to the robust error handling
        print("\n--- CLI: Workflow failed (returned None). ---")
