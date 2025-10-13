import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# Import the configured logger
from logger_utils import logger

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Define the required JSON schema structure for the model output
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "The concise summary of the video transcript.",
        }
    },
    "required": ["summary"],
}

# ==============================================================================
# PRIVATE HELPER FUNCTION
# ==============================================================================


def _generate_single_summary(
    client: genai.Client, video_url: str, transcript_text: str
) -> Dict:
    """
    Makes a synchronous call to the Gemini API to summarize a single transcript.

    Returns:
        Dict: A dictionary containing {'video_url': ..., 'summary': ...} or an error.
    """

    # 1. User Prompt (The main query or task)
    USER_PROMPT = f"""Summarize the following video transcript.
    Transcript: {transcript_text}
    """

    # 2. System Prompt (The instruction to guide the model's behavior/persona)
    SYSTEM_PROMPT = """
       # TASK
        You are a helpful assistant. Below is the transcript of a video. 
         Summarize this in 50 words. This summary will help users understand what is in the video without actually needing to watch the whole video.
         Things to note:
         - DONT use the word "speaker", "transcript" or "summary".
         - Dont mention any brands or sponsers in the final transcript
         - Avoid using the word "speaker".
         - Start with something like "This video talks about..."

        # OUTPUT GUIDELINES
        Output your response as JSON in following notation
        {"summary": "YOUR OUTPUT"}

        # SAMPLE OUTPUT
        Here's what a sample output would look like
        {"summary": "In this video, Andrew Huberman, Stanford Professor, interviews Doctor Kyle Gillette, a dual board certified physician. They discuss male hormone optimization via natural methods. They also cover physiotherapy's role as an alternative in modern medicine and conclude by sharing their current goals."

        """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=USER_PROMPT,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )

        try:
            # 3. Parse the JSON string from response.text
            json_output = json.loads(response.text)
            return {
                "video_url": video_url,
                "summary": json_output.get("summary", "Summary not generated"),
            }
        except json.JSONDecodeError:
            error_message = f"Gemini API returned unparseable JSON for {video_url}. Raw text: {response.text[:200]}..."
            logger.error(error_message)
            return {"video_url": video_url, "summary": None, "error": error_message}

    except APIError as e:
        error_message = f"Gemini API Error for {video_url}: {e}"
        logger.error(error_message)
        return {"video_url": video_url, "summary": None, "error": error_message}
    except Exception as e:
        error_message = f"Unexpected Error during summary call for {video_url}: {e}"
        logger.error(error_message)
        return {"video_url": video_url, "summary": None, "error": error_message}


# ==============================================================================
# PUBLIC FUNCTION
# ==============================================================================


def generate_summaries_sync(data_to_summarize: List[Dict]) -> List[Dict]:
    """
    Generates summaries for a list of transcripts by making sequential (synchronous)
    calls to the Gemini API.

    Args:
        data_to_summarize (List[Dict]): List of dicts, each with 'video_url' and 'transcript_text'.

    Returns:
        List[Dict]: List of dicts, each with 'video_url' and 'summary'.
    """
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        logger.error(
            "GEMINI_API_KEY environment variable not found. Halting summarization."
        )
        raise ValueError("Gemini API key is missing.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    summary_results = []

    logger.info(
        f"Starting synchronous summary generation for {len(data_to_summarize)} videos."
    )

    for i, item in enumerate(data_to_summarize):
        video_url = item["video_url"]
        transcript_text = item["transcript_text"]

        logger.info(
            f"[{i+1}/{len(data_to_summarize)}] Generating summary for {video_url}"
        )

        # Call the helper function for a single summary
        result = _generate_single_summary(client, video_url, transcript_text)
        summary_results.append(result)

    logger.info("Summary generation complete.")
    return summary_results
