import json
from typing import Any, Dict, List

# Define the expected structure of the final output
FinalOutput = Dict[str, Any]

# Base URL for YouTube videos
YOUTUBE_BASE_URL = "https://youtu.be/"


def format_final_output(llm_raw_output: FinalOutput) -> FinalOutput:
    """
    Handles Step 6: Formats the answer and references into the final desired structure.

    This includes:
    1. Generating the full YouTube URL from videoID and timestamp.
    2. Transforming the references list from a list of dicts to a list of URL strings.
    3. Ensuring the fallback scenario returns ["NA"] for references.
    (This function is silent on success.)

    Args:
        llm_raw_output (FinalOutput): The dictionary output from the LLM call (Step 5),
                                         containing 'answer' and 'references' (list of dicts).

    Returns:
        FinalOutput: The final, cleaned dictionary with 'answer' and 'references'
                     where references contain a list of URL strings.
    """

    answer = llm_raw_output.get("answer", "An error occurred during answer retrieval.")
    raw_references = llm_raw_output.get("references", [])

    new_references: List[str] = []

    # Check for the fallback case (which is signaled by "NA" videoID/timestamp)
    is_fallback = raw_references and raw_references[0].get("videoID") == "NA"

    if is_fallback:
        # Fallback scenario
        new_references = ["NA"]

    else:
        for ref in raw_references:
            video_id = ref.get("videoID")
            timestamp = ref.get("timestamp")

            if video_id and timestamp is not None:
                # Generate the full URL
                # Format: https://youtu.be/<videoID>?t=<timestamp_in_seconds>
                url = f"{YOUTUBE_BASE_URL}{video_id}?t={timestamp}"
                new_references.append(url)
            # NOTE: Any reference without necessary data is silently skipped

    # Final cleanup (ensure max 3 references are served)
    final_references = new_references[:3]

    result_dict = {"answer": answer, "references": final_references}

    return result_dict
