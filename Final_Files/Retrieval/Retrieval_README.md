# Modular RAG Workflow for YouTube Content Q&A

## 1. Overview

This project implements a complete Retrieval-Augmented Generation (RAG) pipeline designed to answer user questions based on the content of Rian Doris's YouTube videos. The entire workflow is orchestrated by `main_retrieval.py`, which calls a series of modular, single-purpose functions in a specific sequence.

This modular approach ensures separation of concerns, making the system easier to debug, maintain, and upgrade.

**Core Technologies:**

- **API Server:** FastAPI, deployed via AWS Lambda Containers
- **Embeddings & Reranking:** Jina AI (`jina-embeddings-v3/v4`, `jina-reranker-v2-base-multilingual`)
- **Vector Storage:** ChromaDB Cloud
- **Answer Generation:** Google Gemini (`gemini-2.5-flash-lite`)

---

## 2. Workflow Architecture

The process begins with a user query and ends with a formatted JSON object containing the answer and source references. Each step is handled by a dedicated script.

1.  **`main_retrieval.py` (Orchestrator):** Manages the entire flow, calling each function in order and handling critical errors.

2.  **`r1_get_query_embedding.py`:** The user's text query is converted into a numerical vector (embedding) using the Jina Embeddings API.

3.  **`r2_call_vectorDB.py`:** The query embedding is used to search a ChromaDB vector database and retrieve the top 6 most similar document chunks.

4.  **`r3_reranker.py`:** The 6 retrieved documents are re-evaluated for relevance against the original query using the Jina Reranker API, which assigns a `relevance_score` to each.

5.  **`r4_filter_top_results.py`:** The reranked documents are sorted, filtered by a relevance score threshold, and capped at a maximum of 3 documents.

6.  **`r5_call_llm.py`:** The final, filtered documents are provided as context to the Google Gemini LLM, which synthesizes a single, coherent answer.

7.  **`r6_format_final_output.py`:** The LLM's answer and the source video references are formatted into a clean, final JSON output with clickable YouTube URLs.

---

## 3. Setup and Configuration

### Dependencies (`requirements.txt`)

The following packages are required for the application and its deployment via the Serverless Framework:

```txt
# Core application
fastapi
pydantic
uvicorn
python-dotenv

# AWS Lambda Handler
mangum

# RAG dependencies (from Final_Files/Retrieval)
requests           # For Jina APIs (r1, r3)
chromadb           # For Vector Search (r2)
google-genai       # For Gemini LLM (r5)
```

### Environment Variables

This project requires API keys and configuration details to be stored in a `.env` file in the root directory. These variables must also be explicitly passed to the Lambda environment during deployment (e.g., via `serverless.yml`).

```ini
# .env file

# For Jina Embeddings & Reranker API
JINA_API_KEY="your_jina_api_key_here"

# Set the Jina embedding model version to 'v3' or 'v4'
JINA_EMBEDDING_MODEL_VERSION="v4"
RELEVANCE_SCORE_THRESHOLD="0.4"

# For ChromaDB Cloud connection
CHROMA_API_KEY="your_chroma_api_key_here"
CHROMA_TENANT="your_chroma_tenant_name"
CHROMA_DATABASE="your_chroma_database_name"

# For Google Gemini LLM
GEMINI_API_KEY="your_google_gemini_api_key_here"
```

---

## 4. Deployment to AWS Lambda (Container Image)

The API is deployed as a Docker container image to AWS Lambda using the FastAPI `api_main.py` entry point and the `mangum` adapter.

### The Dockerfile

The `Dockerfile` is based on the official AWS Lambda Python base image, explicitly targeting the `amd64` (x86_64) architecture to prevent multi-architecture builds, which saves storage costs on ECR.

```dockerfile
# Dockerfile

# Use the official AWS Lambda Python 3.11 base image
# NOTE: We MUST use the generic tag here, and rely on the --platform flag in the build command.
FROM public.ecr.aws/lambda/python:3.11

# Set the working directory inside the container
WORKDIR /var/task

# Copy requirements file
COPY requirements.txt .

# Install dependencies from the requirements file
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the command to run the application (Mangum handler)
CMD ["api_main.handler"]

```

### ECR Build and Push Workflow

The following terminal commands are the **most reliable** way to build a single-architecture image and push it to AWS ECR, resolving common authentication and multi-arch issues.

**ACTION: Replace placeholders with your actual AWS account details.**

### I. Setup & Configuration (Set Variables)

```bash
# 1. Define AWS variables (UPDATE THESE)
export AWS_REGION="REGION_NAME"
export IMAGE_NAME="IMAGE-NAME"
```

### Full Sequence of Terminal Commands

Here's the complete, sequential list of commands you ran (or needed to run) based on our troubleshooting. I've grouped them by step for clarity, using your AWS variables (`$AWS_ACCOUNT_ID` and `$REGION`). Copy-paste this into Notion as a code block or checklist. Note: The `docker buildx create` was attempted but skipped due to the existing builder—feel free to run `docker buildx rm mybuilder` later if you want a fresh one.

### Step 1: Create the New ECR Repository

```bash
aws ecr create-repository --repository-name $IMAGE_NAME --region $AWS_REGION

```

### Step 2: Build the Single-Platform Image (with Load)

```bash
# Optional: If you want to reset the builder later
docker buildx rm mybuilder
docker buildx create --use --name mybuilder

# Build and load locally (key fix for single-platform)
docker buildx build --platform linux/amd64 \
  --load \
  -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest \
  -f Dockerfile \
  .

```

### Step 3: Authenticate with ECR

```bash
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

```

### Step 4: Push the Image to ECR

```bash
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest

```

### Verification Commands (Optional, Run After Push)

```bash
# Check repo contents
aws ecr describe-images --repository-name $IMAGE_NAME --region $AWS_REGION

# List local images
docker images | grep $IMAGE_NAME

# Inspect platform (should show "amd64")
docker inspect $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest | grep Architecture

```

### Updating the Docker Image on ECR

### Updated Commands using `$AWS_REGION`

### 1. Use the Existing Builder (If necessary)

```jsx
docker buildx use mybuilder
```

### 2. Build the Updated Image and Tag as `:v2`

```jsx
docker buildx build --platform linux/amd64 \
  --load \
  -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:v3 \
  -f Dockerfile \
  .
```

### 3. Re-Authenticate with ECR

```jsx
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

### 4. Push the Updated Image to ECR

```jsx
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:v3
```

### Deployment Challenges and Resolutions

| Challenge                                               | Cause                                                                                                                                                                                                                                                   | Resolution                                                                                                                                                                                                                                   |
| :------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Authentication Failed (`no basic auth credentials`)** | The `docker login` command failed to successfully store or use the ECR token. Often caused by providing the full repository path (e.g., `.../repo-name`) instead of just the **Registry URI** (e.g., `...amazonaws.com`) to the `docker login` command. | Explicitly define the **Registry URI** and use it ONLY for the `docker login` command (Step 2).                                                                                                                                              |
| **Multiple Images Pushed (High Storage Cost)**          | Building on a modern Linux setup, Docker pushed a **multi-architecture image** (an Image Index, plus separate AMD64 and ARM64 layers) because the base image tag (`:3.11`) is multi-arch.                                                               | **Prevention:** Forced the build to a single architecture using `docker build --platform linux/amd64 ...` (Step 3). **Cleanup:** Manually delete the `latest` tag (Image Index) in the ECR console first, then delete the underlying images. |
| **Repository Not Found Error on Push**                  | The final push failed because the ECR repository name in the `ECR_FULL_IMAGE_URI` did not match an existing repository in the account.                                                                                                                  | Verified and corrected the repository name in the `IMAGE_NAME` variable.                                                                                                                                                                     |

---

## 5. Detailed File Breakdown & Data Flow

This section details the purpose, logic, and data contract (input/output) for each file in the workflow.

### `main_retrieval.py` - The Orchestrator

- **Purpose:** To manage and execute the entire RAG pipeline from start to finish.
- **Key Logic:**
  - Calls each `rX` function in the correct order.
  - Implements **critical failure checks** after API-dependent steps (r1, r2, r3). If any of these fail, the workflow aborts and returns a formatted error.
  - Dynamically constructs the ChromaDB `COLLECTION_NAME` based on the `JINA_EMBEDDING_MODEL_VERSION`.
- **Input:**
  - `query: str` - The initial user question.
- **Output (Success):**
  - `Dict[str, Union[str, List[str]]]` - The final, formatted JSON object.
- **Output (Failure):**
  - `Dict[str, Union[str, List[str]]]` - A structured error message.

---

### `r1_get_query_embedding.py` - Jina Query Embedder

- **Purpose:** To convert the user's text query into a binary vector representation.
- **Key Logic:** Acts as a dispatcher, calling the correct Jina API endpoint (`_call_v3_api` or `_call_v4_api`) based on the `JINA_EMBEDDING_MODEL_VERSION` environment variable, as their input schemas differ.
- **Input:**
  - `query: str`
- **Output (Success):**

  - `List[int]` - A 512-dimension binary embedding vector.

    ```json
    [0, 1, 0, 1, 1, 0, ... , 1]
    ```

- **Output (Failure):**

  - `Dict[str, str]` - A structured error dictionary.

    ```json
    {
      "error": "ConfigurationError",
      "reason": "JINA_API_KEY not found...",
      "source": "Jina API / R1"
    }
    ```

---

### `r2_call_vectorDB.py` - ChromaDB Retriever

- **Purpose:** To fetch the `n` most relevant document chunks from the vector store based on the query embedding.
- **Key Logic:** Connects to ChromaDB Cloud, queries the specified collection, and formats the raw results into a clean list of dictionaries.
- **Input:**
  - `query_embedding: List[int]`
  - `collection_name: str`
- **Output (Success):**

  - `List[Dict[str, any]]` - A list of document dictionaries.

    ```json
    [
    {
        "content": "Allostatic load is the wear and tear on the body...",
        "videoID": "abcdef123",
        "timestamp": 125
    },
    { ... }
    ]
    ```

- **Output (Failure):**
  - `Dict[str, str]` - A structured error dictionary.

---

### `r3_reranker.py` - Jina Document Reranker

- **Purpose:** To refine the search results by applying a more advanced relevance model.
- **Key Logic:** Sends the original query and the text content of the retrieved documents to the Jina Reranker API. It then maps the returned scores back to the original documents, adding a new `relevance_score` key to each dictionary.
- **Input:**
  - `query: str`
  - `documents: List[Dict[str, any]]` (The output from `r2`)
- **Output (Success):**

  - `List[Dict[str, any]]` - The same list of dictionaries, now with the added `relevance_score` key.

    ```json
    [
    {
        "content": "Allostatic load is the wear and tear on the body...",
        "videoID": "abcdef123",
        "timestamp": 125,
        "relevance_score": 0.9876
    },
    { ... }
    ]
    ```

- **Output (Failure):**
  - `Dict[str, str]` - A structured error dictionary.

---

### `r4_filter_top_results.py` - Relevance Filter

- **Purpose:** To select only the highest quality documents to pass to the LLM, reducing noise and cost.
- **Key Logic:** This is a pure Python function. It first **sorts** documents by `relevance_score`, then **filters** out any below a threshold, and finally **caps** the result to 3 documents. If no documents pass the filter, it generates a special **fallback document** to signal this to the next step.
- **Input:**
  - `reranked_documents: List[Dict[str, any]]` (The output from `r3`)
  - `relevance_score_threshold: float`
- **Output (Success):**
  - `List[Dict[str, any]]` - A list of 0 to 3 filtered and sorted documents.
- **Output (Fallback):**

  - `List[Dict[str, any]]` - A list containing a single, special-purpose fallback dictionary.

    ```json
    [
      {
        "content": "A relevant answer could not be found from the videos.",
        "timestamp": null,
        "videoID": null,
        "relevance_score": null
      }
    ]
    ```

---

### `r5_call_llm.py` - Gemini Answer Generator

- **Purpose:** To synthesize a final, human-readable answer using the provided context documents.
- **Key Logic:** First, it checks for the fallback signal from `r4`. If detected, it returns a pre-written message without calling the LLM. Otherwise, it constructs a detailed prompt and uses Gemini's `response_schema` feature to guarantee a valid JSON output.
- **Input:**
  - `query: str`
  - `filtered_results: List[Dict[str, any]]` (The output from `r4`)
- **Output (Success):**

  - `Dict[str, any]` - A dictionary containing the LLM-generated answer and the source references (still as dictionaries).

    ```json
    {
      "answer": "Allostatic load refers to the cumulative physiological burden...",
      "references": [
        { "videoID": "abcdef123", "timestamp": 125 },
        { "videoID": "ghijkl456", "timestamp": 450 }
      ]
    }
    ```

- **Output (Failure / Fallback):**
  - `Dict[str, any]` - Either the pre-written fallback response or a structured LLM error.

---

### `r6_format_final_output.py` - Final Formatter

- **Purpose:** To clean up the LLM output into the final, user-facing format.
- **Key Logic:** The primary function is to iterate through the `references` list and transform each dictionary into a fully-formed, clickable YouTube URL string. It also handles the fallback case to ensure the final references are `["NA"]`.
- **Input:**
  - `llm_raw_output: Dict[str, any]` (The output from `r5`)
- **Output (Success / Fallback):**
  - `Dict[str, Union[str, List[str]]]` - The final, clean dictionary ready to be served.

---

## 6. Final Output Structure

The final JSON object returned by the `main_retrieval_workflow` will adhere to one of the following two structures.

#### On a Successful Retrieval:

```json
{
  "answer": "Allostatic load is the cumulative physiological burden or 'wear and tear' that the body experiences when subjected to chronic stress. It represents the long-term cost of adaptation to challenging situations, where systems like the HPA axis and the sympathetic nervous system remain overactivated.",
  "references": [
    "https://youtu.be/videoID_1?t=125",
    "https://youtu.be/videoID_2?t=450",
    "https://youtu.be/videoID_3?t=310"
  ]
}
```

#### When No Relevant Context is Found (Fallback):

```json
{
  "answer": "This topic has not been discussed in any of Rian's YouTube videos. As such, I can't answer this question accurately. Feel free to ask a different question.",
  "references": ["NA"]
}
```
