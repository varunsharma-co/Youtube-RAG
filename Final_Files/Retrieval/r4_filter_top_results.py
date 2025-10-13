from typing import Any, Dict, List, Optional

# Define the structure for the document dictionary
DocumentDict = Dict[str, Any]


def filter_top_results(
    reranked_documents: List[DocumentDict], relevance_score_threshold: float
) -> List[DocumentDict]:
    """
    Handles Step 4: Sorts, filters, and caps the reranked documents based on a threshold.
    (This function is silent and only performs local computation.)

    Args:
        reranked_documents (List[DocumentDict]): List of documents with an added
                                                 'relevance_score' key.
        relevance_score_threshold (float): The minimum relevance score required
                                           for a document to be included.

    Returns:
        List[DocumentDict]: A new list of 0 to 3 filtered documents, or a single
                            fallback document if none pass the filter.
    """

    # 1. Sort the documents by relevance_score in descending order.
    # Documents with relevance_score=None are treated as -1.0 for sorting purposes.
    def sort_key(doc):
        score: Optional[float] = doc.get("relevance_score")
        return score if score is not None else -1.0

    sorted_documents = sorted(reranked_documents, key=sort_key, reverse=True)

    # 2. Apply filter: only keep documents where score >= threshold
    filtered_documents = []
    for doc in sorted_documents:
        score = doc.get("relevance_score")
        # FIX: Check if score is None. If it is, use 0.0 for comparison to ensure it fails the threshold.
        comparison_score = score if score is not None else 0.0

        if comparison_score >= relevance_score_threshold:
            filtered_documents.append(doc)

    # 3. Cap the results to a maximum of 3 items
    final_results = filtered_documents[:3]

    # 4. Handle the case where no item passes the filter
    if not final_results:
        final_results.append(
            {
                "content": "A relevant answer could not be found from the videos.",
                "timestamp": None,
                "videoID": None,
                "relevance_score": None,  # Keep score key for consistency
            }
        )

    # The 'relevance_score' key is kept in the output as requested.
    return final_results
