import json
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum  # <--- REQUIRED IMPORT
from pydantic import BaseModel, Field

# Import the core business logic function
from main_retrieval import main_retrieval_workflow

# ----------------------------------------------------
# 1. FastAPI Setup
# ----------------------------------------------------
# Define allowed origins for CORS.
origins = ["*"]

RAG_TAGS = [
    {
        "name": "RAG Retrieval",
        "description": "Endpoints for the modular Retrieval-Augmented Generation workflow.",
    }
]

app = FastAPI(
    title="Modular RAG API",
    description="A robust and modular RAG pipeline implemented in Python and exposed via FastAPI.",
    version="1.0.0",
    openapi_tags=RAG_TAGS,
)

# --- Add CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------
# 2. Pydantic Schemas (Input/Output)
# ----------------------------------------------------
class QueryRequest(BaseModel):
    """Schema for the incoming request body."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The user's question or search query.",
    )


class FinalResponse(BaseModel):
    """Schema for the final, structured API response."""

    answer: str = Field(..., description="The LLM-generated answer to the query.")
    references: List[str] = Field(
        ...,
        description="A list of up to 3 YouTube URLs (or ['NA'] for no sources/error).",
    )


# ----------------------------------------------------
# 3. API Endpoints
# ----------------------------------------------------
@app.get("/", summary="Health Check and Welcome Message")
async def root():
    """
    Returns a simple JSON object to confirm the API is running and healthy.
    """
    return {
        "message": "Welcome to the Modular RAG API!",
        "status": "Online",
        "version": app.version,
    }


@app.post(
    "/rag/query",
    response_model=FinalResponse,
    summary="Execute the full RAG retrieval pipeline for a query.",
    tags=["RAG Retrieval"],
)
def get_rag_answer(request: QueryRequest):
    """
    Executes the entire 6-step RAG pipeline: Embedding, Vector Search, Reranking,
    Filtering, LLM Generation, and Final Formatting.

    Returns the final structured answer and its source references.
    """
    try:
        final_output_dict = main_retrieval_workflow(request.query)

        if final_output_dict is None:
            raise HTTPException(
                status_code=500,
                detail="Workflow returned a critical failure (None) and could not generate a structured error response.",
            )

        return final_output_dict

    except Exception as e:
        print(f"FATAL UNCAUGHT ERROR in API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unhandled critical error occurred during the RAG process. Error: {str(e)}",
        )


# ----------------------------------------------------
# 4. AWS Lambda Handler (using Mangum) <--- CRITICAL ADDITION
# ----------------------------------------------------
handler = Mangum(app)

# ----------------------------------------------------
# 5. Local Execution / Testing
# ----------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    print("Running FastAPI server locally (uvicorn api_main:app --reload)...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
