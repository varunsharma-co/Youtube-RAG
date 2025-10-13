# RAG-Powered Q&A Chatbot for Rian Doris's YouTube Channel

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=for-the-badge&logo=aws-lambda&logoColor=white)![ChromaDB](https://img.shields.io/badge/ChromaDB-5545A4?style=for-the-badge&logo=chroma&logoColor=white)

I'm a big fan of Rian Doris's YouTube channel, but I always found it frustrating trying to remember which video contained a specific piece of advice.

His content is incredibly valuable, but it's locked away in hours of video. I built this project to fix that.

This is a "semantic search" engine for his entire channel. You can ask it a question in plain English, and it will find the relevant moments in his videos and give you a straight answer.

**[➡️ Check out the Live Demo Here!](https://www.varunsharma.co/youtube-rag)**

## How It All Works

I designed this project in two main parts.

First, there's an **Ingestion Pipeline** that does all the heavy lifting of watching, transcribing, and understanding the videos. Second, there's the **Retrieval API**, which is the smart part that actually answers your questions.

This whole pipeline uses ChromaDB vector database on the backend where all the knowledge is stored.

```
+-------------------------------------------+      +-----------------------------------------+
|      PART 1: THE INGESTION PIPELINE       |      |        PART 2: THE RETRIEVAL API        |
| (I run this whenever I want to update it) |      |   (This is live 24/7 on AWS to answer you)  |
+-------------------------------------------+      +-----------------------------------------+
|                                           |      |                                         |
| [ Rian Doris's YouTube Channel ]          |      |  [ Your Question: "What is allostatic load?" ] |
|               |                           |      |                       |                 |
|               v                           |      |                       v                 |
| [ 1. Fetch & Filter Videos ]              |      |         [ The FastAPI Brain on AWS ]     |
|               |                           |      |                       |                 |
|               v                           |      |                       v                 |
| [ 2. Download Audio Files ]               |      |      [ 1. Understand Your Question ]    |
|               |                           |      |                       |                 |
|               v                           |      |                       v                 |
| [ 3. Transcribe the Audio ]               |      |      [ 2. Find 6 Relevant Video Clips ] |
|               |                           |      |                       |                 |
|               v                           |      |                       v                 |
| [ 4. Create Quick Summaries ]             |      |      [ 3. Double-Check for Relevance ]  |
|               |                           |      |                       |                 |
|               v                           |      |                       v                 |
| [ 5. Chunk & Create "Embeddings" ]        |      |      [ 4. Pick the Top 3 Best Clips ]   |
|               |                           |      |                       |                 |
|               v                           |      |                       v                 |
|     [ 6. UPLOAD TO THE BRAIN ]            |      |      [ 5. Write a New Answer ]          |
|               |                           |      |                       |                 |
|               +---------------------------+      +-----------------------+                 |
|                           |                                            |                 |
|                           v                                            v                 |
|               +--------------------------------------------------------+                 |
|               |            ChromaDB Vector Store (The Brain)           |                 |
|               +--------------------------------------------------------+                 |
|                                                                                          |
+------------------------------------------------------------------------------------------+
```

## The Best Features

- **Does All the Hard Work Automatically:** This pipeline that pulls everything from the YouTube channel, transcribes it, and makes sense of it without me having to lift a finger.

- **Understands Context:** Instead of just chopping up transcripts randomly, it's smart enough to find the end of a sentence before creating a chunk. This means the search results are way more accurate.

- **Finds the _Best_ Answer, Not Just Any Answer:** It does a two-step search. First, it finds 6 possible video clips. Then, a second AI model re-ranks them to find the absolute best ones to use for the answer.

- **Gives You the Transcripts:** The best part! It doesn't just give you an answer; it gives you clickable links to the exact moments in the YouTube videos where Rian talks about that topic.

- **Built Like a Real-World App:** This isn't just a script. The part that answers questions is a proper FastAPI application, running in a Docker container on AWS Lambda. It's built to be fast, scalable, and reliable.

## The Tech Stack I Used

| Category           | Technologies & Services                                                                                                               |
| :----------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| **Backend**        | Python, FastAPI, Mangum (for AWS Lambda), Uvicorn                                                                                     |
| **Data & AI**      | **Vector DB:** ChromaDB Cloud <br> **Embeddings & Reranking:** Jina AI <br> **Transcription:** AssemblyAI <br> **LLM:** Google Gemini |
| **Cloud & DevOps** | AWS Lambda, Amazon ECR (Elastic Container Registry), Docker                                                                           |
| **Libraries**      | Pydantic, python-dotenv, google-api-python-client, pytubefix, requests                                                                |

## Want to Run it Yourself?

To run it yourself, first you need to run the Ingestion pipeline, then you can do the Retrieval part.

### First, You'll Need:

- Python 3.8 or newer.
- Docker installed on your machine.
- An AWS account and the AWS CLI set up if you want to deploy it to the cloud.
- A bunch of API keys for the services it uses.

### 1. Set Up Your API Keys

Create a file named `.env` in the main folder and paste this in. You'll need to fill it out with your own keys.

**`.env` Template:**

```env
# --- KEYS FOR BOTH SYSTEMS ---
# Jina AI (Embeddings & Reranker)
JINA_API_KEY="YOUR_JINA_API_KEY"
JINA_EMBEDDING_MODEL_VERSION="v4"
RELEVANCE_SCORE_THRESHOLD="0.4"

# Google Gemini (LLM for Summaries & Answers)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# ChromaDB Cloud
CHROMA_API_KEY="YOUR_CHROMA_API_KEY"
CHROMA_TENANT="YOUR_CHROMA_TENANT_NAME"
CHROMA_DATABASE="YOUR_CHROMA_DATABASE_NAME"

# --- KEYS FOR INGESTION ONLY ---
# Google / YouTube
YOUTUBE_API_KEY="YOUR_YOUTUBE_DATA_API_KEY"

# AssemblyAI (Transcription)
ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_API_KEY"
```

### 2. Part 1: Run the Ingestion Pipeline

This script will go through the YouTube channel and load all the knowledge into your ChromaDB collection.

```bash
# 1. Set up a virtual environment (good practice!)
python3 -m venv venv
source venv/bin/activate

# 2. Install all the Python packages
pip install -r requirements.txt

# 3. Open up main_ingestion.py and double-check the
#    CHANNEL_URL and CHROMA_COLLECTION_NAME variables.

# 4. Let it run!
python main_ingestion.py
```

This might take a while, so grab a coffee! You'll see its progress in the terminal.

### 3. Part 2: Ask it Questions (Run the API Locally)

Once the database is full, you can start the API server.

```bash
# 1. Make sure your virtual environment is still active
source venv/bin/activate

# 2. Start the local server
uvicorn api_main:app --reload
```

Now you can send requests to `http://127.0.0.1:8000`. Here’s a quick `curl` command to test it:

```bash
curl -X POST "http://127.0.0.1:8000/rag/query" \
-H "Content-Type: application/json" \
-d '{"query": "what is allostatic load"}'
```

## Putting It on the Cloud

To make this a real, usable application, I deployed the Retrieval API to **AWS Lambda** using a **Docker container**.

I chose this serverless approach because it's incredibly scalable and I only pay for when it's actually being used. It’s a professional setup that shows how a project like this can go from a local script to a live web service.

All the nitty-gritty details on how I built the Docker image and pushed it to AWS are in the `Retrieval_README.md` file.
