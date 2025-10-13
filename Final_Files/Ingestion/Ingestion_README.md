# YouTube Channel RAG Ingestion Pipeline

---



## 1. Overview

This project provides an automated, modular pipeline designed to ingest video content from a specified YouTube channel and prepare it for a Retrieval-Augmented Generation (RAG) application.

The pipeline executes a sequence of steps: it fetches video metadata, downloads the audio, transcribes the speech to text, generates a concise summary, chunks the transcript into manageable segments, creates vector embeddings for each chunk, and finally uploads the structured data into a ChromaDB vector database. The ultimate goal is to make the spoken content of the YouTube videos fully searchable.

## 2. Core Technologies & Services

The pipeline relies on several key external services and Python libraries:

* **Data Source:** YouTube
* **YouTube API:** Google API Client (`google-api-python-client`) for fetching video metadata.
* **Audio Downloading:** `pytubefix` for efficiently downloading audio-only streams.
* **Transcription:** [AssemblyAI](https://www.assemblyai.com/) for fast and accurate audio-to-text transcription, including word-level timestamps.
* **Summarization:** [Google Gemini API](https://ai.google.dev/) (`gemini-1.5-flash`) for generating concise video summaries from transcripts.
* **Embeddings:** [Jina AI](https://jina.ai/) (`jina-embeddings-v2-base-en`) for creating powerful vector embeddings from text chunks.
* **Vector Database:** [ChromaDB Cloud](https://www.trychroma.com/) for storing and indexing the final vector data.

## 3. Ingestion Workflow

The pipeline follows a linear, step-by-step process orchestrated by `main_ingestion.py`. Intermediate data and artifacts are saved at each major stage.

```
[Start]
   |
   V
[ 1. Fetch & Filter YouTube Videos ] --> (Saves video_metadata.json)
   |
   V
[ 1b. Save Last Run Timestamp ] --> (Saves last_run.txt)
   |
   V
[ 2. Download Audio from Videos ] --> (Saves .m4a audio files)
   |
   V
[ 3. Transcribe Audio to Text ]
   |
   V
[ 4. Generate Video Summaries ]
   |
   V
[ 5. Prepare Data for Vector DB ]
   |--> [ 5a. Create Text Chunks ]
   |--> [ 5b. Generate Embeddings ]
   |
   V
[ 6. Upload Data to ChromaDB ] --> (Saves final_vectors.json)
   |
   V
[End]
```

## 4. Project Structure

```
.
├── Final_Files/
│   ├── Ingestion/
│   │   ├── i1_get_youtube_data.py
│   │   ├── i1b_timestamp.py
│   │   ├── i2_download_audio.py
│   │   ├── i3_get_transcription.py
│   │   ├── i4_get_summary.py
│   │   ├── i5a_create_chunks.py
│   │   ├── i5b_get_embeddings.py
│   │   ├── i5_prepare_vector_data.py
│   │   └── i6_upload_to_vector_db.py
│   ├── Saving_Intermediate_Data/  # All output artifacts are saved here
│   │   ├── STEP_1_JSON_YouTube_Videos_Data/
│   │   ├── STEP_2_M4A_Files/
│   │   ├── STEP_8_Transcripts/
│   │   └── STEP_10_Chunks_With_Embeddings/
│   └── Logs/                        # Log files are generated here
├── main_ingestion.py                # The main orchestration script
├── logger_utils.py                  # Logging configuration
├── .env                             # For storing API keys and credentials
└── requirements.txt                 # Project dependencies
```

## 5. Setup and Installation

1. **Clone the Repository**
   
   ```sh
   git clone <your-repository-url>
   cd <your-repository-directory>
   ```

2. **Create and Activate a Virtual Environment**
   
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a file named `.env` in the root of the project directory and populate it with the necessary API keys and credentials.
   **`.env` template:**
   
   ```env
   # Google / YouTube
   YOUTUBE_API_KEY="YOUR_YOUTUBE_DATA_API_KEY"
   
   # AssemblyAI
   ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_API_KEY"
   
   # Google Gemini
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   
   # Jina AI
   JINA_API_KEY="YOUR_JINA_API_KEY"
   
   # ChromaDB Cloud
   CHROMA_API_KEY="YOUR_CHROMA_API_KEY"
   CHROMA_TENANT="YOUR_CHROMA_TENANT_NAME"
   CHROMA_DATABASE="YOUR_CHROMA_DATABASE_NAME"
   ```

## 6. Configuration

Before running the pipeline, you can adjust the following constants in `main_ingestion.py`:

* `CHANNEL_URL`: The URL of the target YouTube channel.
* `MINIMUM_VIDEO_MINUTES`: An integer to filter out videos shorter than this duration.
* `CHROMA_COLLECTION_NAME`: The name of the collection to be used in ChromaDB.

## 7. Execution

To run the entire ingestion pipeline, execute the main script from the root directory:

```sh
python main_ingestion.py
```

All progress, warnings, and errors will be logged to both the console and a timestamped log file in the `Final_Files/Logs/` directory.

## 8. Detailed Step-by-Step Breakdown

This section details the purpose of each script and, crucially, the data structure it takes as **input** and produces as **output**.

---

### **Step 1: Fetch YouTube Data (`i1_get_youtube_data.py`)**

* **Purpose:** Connects to the YouTube Data API v3 to fetch metadata for all videos on a channel and filters them based on a minimum duration.
* **Implementation:** Resolves the channel ID from various URL formats, fetches all video IDs from the channel's "uploads" playlist, retrieves video details in batches of 50, and filters the results.
* **Input:**
  * `channel_url: str` (from `main_ingestion.py` config)
  * `min_duration_minutes: int` (from `main_ingestion.py` config)
* **Output:**
  
  ```python
  # A list of dictionaries, one for each filtered video.
  [
      {
          "channel_id": "UC...",
          "video_id": "...",
          "video_url": "https://www.youtube.com/watch?v=...",
          "video_title": "Video Title",
          "duration": "HH:MM:SS"
      },
      # ... more video dictionaries
  ]
  ```

---

### **Step 2: Download Audio (`i2_download_audio.py`)**

* **Purpose:** Downloads the audio-only stream for each video identified in the previous step.
* **Implementation:** Uses the `pytubefix` library. It sanitizes the video title to create a valid filename and saves the audio as an `.m4a` file.
* **Input:** The `list[dict]` returned from Step 1.
* **Output:**
  
  ```python
  # A list of mappings between the video URL and its local audio file path.
  [
      {
          "video_url": "https://www.youtube.com/watch?v=...",
          "m4a_path": PosixPath('/path/to/project/Final_Files/Saving_Intermediate_Data/STEP_2_M4A_Files/Video_Title.m4a')
      },
      # ... more mapping dictionaries
  ]
  ```
  
  *(Note: This output is merged back into the main `video_data` list in `main_ingestion.py`)*

---

### **Step 3: Transcribe Audio (`i3_get_transcription.py`)**

* **Purpose:** Converts the downloaded audio files into text transcripts.
* **Implementation:** Uses the AssemblyAI API. To improve performance, it processes multiple audio files concurrently using Python's `threading` module. It is configured to enable punctuation and text formatting and retrieves word-level timestamps, which are essential for the chunking logic later.
* **Input:** The main `video_data` list, where each dictionary must contain `video_url` and `m4a_file_path`.
* **Output:**
  
  ```python
  # A list of dictionaries, one for each successfully transcribed video.
  [
      {
          "video_url": "https://www.youtube.com/watch?v=...",
          "transcript_text": "This is the full transcript of the video...",
          "transcript_words": [ # List of AssemblyAI Word objects
              Word(text='This', start=100, end=250),
              Word(text='is', start=260, end=350),
              # ...
          ]
      },
      # ... more transcript dictionaries
  ]
  ```
  
  *(Note: This output is also merged back into the main `video_data` list.)*

---

### **Step 4: Generate Summaries (`i4_get_summary.py`)**

* **Purpose:** Creates a short, concise summary for each video's transcript.
* **Implementation:** Uses the Google Gemini API (`gemini-1.5-flash`). It employs a detailed system prompt and a strict response schema to ensure the model returns a clean JSON object containing only the summary. Calls are made sequentially for each video.
* **Input:** A list of dictionaries, each containing `video_url` and `transcript_text`.
* **Output:**
  
  ```python
  # A list of dictionaries containing the summary for each video.
  [
      {
          "video_url": "https://www.youtube.com/watch?v=...",
          "summary": "This video talks about male hormone optimization and the role of physiotherapy..."
      },
      # ... more summary dictionaries
  ]
  ```
  
  *(Note: This output is the final piece of data merged into the `video_data` list.)*

---

### **Step 5: Prepare Data for Vector DB (`i5_prepare_vector_data.py`)**

This is an orchestrator script that calls two sub-modules:

#### **Step 5a: Create Chunks (`i5a_create_chunks.py`)**

* **Purpose:** To break down the long video transcripts into smaller, semantically meaningful text chunks.
* **Implementation:** This script uses a sentence-aware chunking strategy. It iterates through the word-level timestamps (`transcript_words`), accumulating words until a chunk size of **200-300 words** is reached. It then waits for the next sentence-ending punctuation (`.`, `?`) to finalize the chunk. This is more effective than naive fixed-size chunking as it avoids splitting sentences mid-thought.
* **Input:** The fully enriched `video_data` list from the main script.
* **Output:**
  
  ```python
  # A single dictionary containing lists of chunked data from ALL videos.
  {
    "_id": ["videoID1_0001", "videoID1_0002", ...],
    "content": ["First chunk of text...", "Second chunk of text...", ...],
    "metadata": [
      {
        "timestamp": 12,
        "channel_ID": "UC...",
        "video_ID": "videoID1",
        "video_title": "Video Title 1",
        "video_summary": "Summary of video 1..."
      },
      # ... more metadata objects
    ]
  }
  ```

#### **Step 5b: Generate Embeddings (`i5b_get_embeddings.py`)**

* **Purpose:** To convert the text chunks (`content`) into numerical vector representations.
* **Implementation:** Uses the Jina AI embeddings API (`jina-embeddings-v2-base-en`). For efficiency and to respect API rate limits, it sends the text chunks in batches of 512.
* **Input:** The dictionary containing chunk data produced by `i5a_create_chunks.py`.
* **Output:** The same dictionary as the input, but with a new key, `$vector`, containing the list of embeddings. (This is the final data structure before upload).

---

### **Step 6: Upload to Vector DB (`i6_upload_to_vector_db.py`)**

* **Purpose:** To load the final prepared data into the ChromaDB Cloud instance.
* **Implementation:** Connects to the ChromaDB client using credentials from the `.env` file. It gets or creates the specified collection and uploads the data in batches of 200 for reliability.
* **Input:** The final data dictionary with chunks, metadata, and embeddings from Step 5.
* **Output:** None (uploads data to the external database).

## 9. Final Vector Database Schema

The final data structure prepared and uploaded to ChromaDB is a single dictionary where each key holds a list of corresponding values. Each index across these lists represents a single data point (a chunk).

This structure is optimized for batch uploading to ChromaDB.

```json
{
  "_id": [
    "videoID1_0001",
    "videoID1_0002",
    "videoID2_0001"
  ],
  "content": [
    "This is the first chunk of text from the first video...",
    "This is the second chunk of text from the first video...",
    "This is the first chunk from the second video..."
  ],
  "metadata": [
    {
      "timestamp": 15,
      "channel_ID": "UC...",
      "video_ID": "videoID1",
      "video_title": "First Video Title",
      "video_summary": "A summary of the first video."
    },
    {
      "timestamp": 45,
      "channel_ID": "UC...",
      "video_ID": "videoID1",
      "video_title": "First Video Title",
      "video_summary": "A summary of the first video."
    },
    {
      "timestamp": 8,
      "channel_ID": "UC...",
      "video_ID": "videoID2",
      "video_title": "Second Video Title",
      "video_summary": "A summary of the second video."
    }
  ],
  "$vector": [
    [0.012, -0.045, ..., 0.089],
    [0.034, 0.001, ..., -0.021],
    [-0.076, 0.055, ..., 0.004]
  ]
}
```

* **`_id` -> `ids`:** A unique identifier for each text chunk.
* **`content` -> `documents`:** The actual text of the chunk.
* **`metadata` -> `metadatas`:** A dictionary of associated data for filtering and context.
* **`$vector` -> `embeddings`:** The numerical vector representation of the `content`.
