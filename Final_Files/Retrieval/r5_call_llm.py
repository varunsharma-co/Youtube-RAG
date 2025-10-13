import json
import os
from typing import Any, Dict, List, Union

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# Define the expected structure of the final output and a standard error
FinalOutput = Dict[str, Any]
DocumentDict = Dict[str, Any]
ErrorResponse = Dict[str, Any]

# Define the required JSON schema structure for the model output
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The final, synthesized answer to the user's question based ONLY on the provided context.",
        }
    },
    "required": ["answer"],
}


def call_llm_for_answer(
    query: str, filtered_results: List[DocumentDict]
) -> Union[FinalOutput, ErrorResponse]:
    """
    Handles Step 5: Generates the final answer using the Gemini API.
    Returns the final output on success, or a structured error dictionary on failure.
    (This function is silent on success and logs only on error.)

    Args:
        query (str): The original user query.
        filtered_results (List[DocumentDict]): A list of 0-3 most relevant documents
                                               or a single fallback document.

    Returns:
        Union[FinalOutput, ErrorResponse]: The final output dictionary on success,
                                           or an ErrorResponse dictionary on failure.
    """

    # Check for the fallback document
    is_fallback = (
        len(filtered_results) == 1 and filtered_results[0].get("videoID") is None
    )

    if is_fallback:
        result_dict = {
            "answer": "This topic has not been discussed in any of Rian's YouTube videos. As such, I can't answer this question accurately. Feel free to ask a different question.",
            "references": [{"videoID": "NA", "timestamp": "NA"}],
        }
        return result_dict

    # --- Prepare for LLM Call ---
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return {
            "error": "ConfigurationError",
            "reason": "GEMINI_API_KEY environment variable not found. Halting LLM call.",
            "source": "Gemini API / R5",
        }

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 1. Compile the context text (using only the 'content' field)
    context_list = [
        f"SOURCE {i+1}: {doc['content']}" for i, doc in enumerate(filtered_results)
    ]
    context_text = "\n\n---\n\n".join(context_list)

    # 2. User Prompt
    USER_PROMPT = f"""
    # USER QUESTION: {query}
    ---
    # CONTEXT: 
    {context_text}
    ---
    Please use ONLY the provided context to answer the user's question. 
    Synthesize a single, coherent, and detailed answer.
    DO NOT use any external knowledge. If the context does not contain the answer, 
    respond with: "Based on the provided context, I cannot answer this question."
    """

    # 3. System Prompt
    SYSTEM_PROMPT = """
    You are an expert Q&A assistant for Rian Doris's YouTube content. 
    Your goal is to provide accurate, concise, and helpful answers based strictly on the provided context documents. 
    You MUST output your response as a single JSON object that strictly adheres to the provided schema.

    Things to note:
    - **Formatting:** Format your final answer for clarity and readability. 
    - **Directness:** Do not include any preamble, conversational filler, or introductory phrases (e.g., "Based on the context...", "The information suggests..."). 
    
    """

    # 4. Make the LLM Call with robust error handling
    try:
        # Use gemini-1.5-flash as the standard robust model
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=USER_PROMPT,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )

        json_output = json.loads(response.text)
        llm_answer = json_output.get("answer", "LLM failed to provide a valid answer.")

        references = [
            {"videoID": doc["videoID"], "timestamp": doc["timestamp"]}
            for doc in filtered_results
        ]

        result_dict = {"answer": llm_answer, "references": references}

        return result_dict

    except APIError as e:
        error_reason = f"Gemini API Error: {type(e).__name__} - {str(e)}"
    except json.JSONDecodeError as e:
        error_reason = f"Unparseable LLM Response. Error: {type(e).__name__} - {e}"
    except Exception as e:
        error_reason = f"An unexpected error occurred during LLM call: {type(e).__name__} - {str(e)}"

    # If any exception was caught, return the structured error message
    error_dict = {
        "error": "LLMGenerationError",
        "reason": error_reason,
        "source": "Gemini API / R5",
    }

    return error_dict
