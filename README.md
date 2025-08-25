# Phantom Agents: AI Customer Support Assistant

## Overview

**Phantom Agents** is a project for the NSUToblivion'25 hackathon. Inspired by the theme of spectral creativity, this project brings to life a "Phantom Agent"—an intelligent, 24/7 AI customer support assistant that works tirelessly in the background to solve real-world problems for Small and Medium-sized Enterprises (SMEs).

This agent "haunts" a company's knowledge base (PDFs or DOCX files) to provide instant, accurate answers. It's designed to understand user emotions, handle complaints with empathy, and intelligently escalate complex issues to human agents, ensuring a seamless and efficient customer experience.

## Tech Stack

* **Backend**: FastAPI, Uvicorn
* **AI/ML Frameworks**:
    * **Language Models**: Google Gemini (`gemini-1.5-flash-latest`)
    * **Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`)
    * **Vector Database**: FAISS (Facebook AI Similarity Search)
* **Core Libraries**: PyMuPDF (for PDFs), python-docx (for DOCX), NumPy
* **Deployment**: Docker, Hugging Face Spaces

## Setup and Running Locally

Follow these steps to set up and run the application on your local machine.

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    Install all required packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create `.env` File**
    Create a file named `.env` in the root directory and add your API keys:
    ```env
    API_KEY="your-secret-bearer-token"
    GEMINI_API_KEY="your-google-gemini-api-key"
    ```

5.  **Run the Application**
    Start the FastAPI server using Uvicorn.
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    ```
    The API will now be accessible at `http://127.0.0.1:8000`.

## Features

* **Multi-Format Knowledge Base**: Ingests and processes both `.pdf` and `.docx` files to build a comprehensive knowledge base.
* **Conversational Q&A**: Engages in natural, multi-turn conversations with users.
* **Intelligent Triage System**: Automatically analyzes user queries to detect intent (`Question`, `Complaint`, `Escalate`) and sentiment (`Positive`, `Negative`, `Neutral`).
* **Empathetic Responses**: Dynamically adjusts its tone to handle user complaints with empathy and care.
* **Smart Escalation**: Recognizes when a user needs human intervention and provides a clear path for escalation, bypassing the AI for critical issues.
* **Stateful Memory**: Remembers the context of the current conversation and the active knowledge base.
* **Single Unified API Endpoint**: A simple `/process` endpoint handles both initial document processing and subsequent chat messages.

## Technical Workflow

The application is built on a sophisticated Retrieval-Augmented Generation (RAG) pipeline, divided into two main stages.

### 1. Ingestion Pipeline

When a `document_url` is provided to the `/process` endpoint for the first time:

1.  **Download & Hash**: The document is downloaded, and a unique SHA256 hash is generated from its content. This hash acts as its ID.
2.  **Cache Check**: The system checks if a knowledge base for this hash already exists. If so, ingestion is skipped.
3.  **Parse Content**: Based on the file type (`.pdf` or `.docx`), a specific parser extracts text and structural elements. For PDFs, it intelligently identifies and removes repeating headers/footers.
4.  **Chunking**: The extracted text is broken down into smaller, semantically meaningful chunks.
5.  **Vectorize & Store**: Each chunk is converted into a vector embedding using the Sentence-Transformer model. These embeddings are stored in a FAISS index file (`.index`), and the corresponding text chunks are saved in a JSON file (`.json`).

### 2. Inference Pipeline

For every query sent to the `/process` endpoint:

1.  **Triage & Routing**: The user's query and conversation history are first sent to the Gemini model for a quick classification of **intent** and **sentiment**.
2.  **Decision Making**: Based on the triage result, the pipeline routes the query:
    * **Escalate**: If the intent is to escalate, the system immediately returns a pre-defined message to connect the user to a human agent.
    * **Complaint/Negative**: If the intent is a complaint or the sentiment is negative, it proceeds down the "Empathetic Path."
    * **Question/Neutral**: Otherwise, it proceeds down the "Standard Q&A Path."
3.  **Semantic Search**: The user's query is converted into a vector embedding. This vector is used to search the FAISS index for the most relevant context chunks from the knowledge base.
4.  **Answer Generation**: The original query, conversation history, and the retrieved context chunks are passed to the Gemini model with a dynamically selected prompt (either a standard Q&A prompt or an empathetic prompt).
5.  **Response**: The generated answer is returned to the user.