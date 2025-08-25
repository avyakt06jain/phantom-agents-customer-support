import os
import uvicorn
import hashlib
import requests
import faiss
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Import your custom pipeline functions
from ingestion_pipeline.ingestionPipeline import run_ingestion_pipeline
from inference_pipeline.inferencePipeline import run_inference_pipeline

# -- Initial Setup --
load_dotenv()
app = FastAPI(title="Phantom Agents API - Single Endpoint")
security = HTTPBearer()

# -- Environment Variables & Constants --
API_KEY = os.getenv("API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not all([API_KEY, GEMINI_API_KEY]):
    raise ValueError("Missing critical API keys in .env file")

CACHE_DIR = "knowledge_base_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# -- RAG State & Model Initialization --
class RAGState:
    """
    Manages the state of the RAG application, including models and the
    currently active document knowledge base.
    """
    def __init__(self, embedding_model_name="all-MiniLM-L6-v2"):
        print("Initializing RAG state...")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        genai.configure(api_key=GEMINI_API_KEY)
        self.generative_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # In-memory cache for loaded knowledge bases (persists across requests)
        self.loaded_indexes: Dict[str, faiss.Index] = {}
        self.loaded_chunks: Dict[str, List[Dict]] = {}
        
        # Tracks the currently active document for the single-endpoint logic
        self.active_doc_hash: Optional[str] = None
        print("RAG state initialized successfully.")

rag_state = RAGState()

# -- Pydantic Models for API Schema --
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender, 'user' or 'model'.")
    content: str = Field(..., description="Content of the message.")

class ProcessRequest(BaseModel):
    query: str = Field(..., description="The user query.")
    history: List[ChatMessage] = Field([], description="The history of the conversation.")
    document_url: Optional[str] = Field(None, description="URL for a document to process. If omitted, uses the last processed document.")

class ProcessResponse(BaseModel):
    answer: str = Field(..., description="The generated answer from the AI agent.")
    document_hash: Optional[str] = Field(None, description="The hash of the document used for the response.")

# -- Helper Functions --
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

def download_file(url: str, local_path: str):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Could not download document from URL: {e}")

def get_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

# -- API Endpoint --
@app.post("/process", response_model=ProcessResponse, dependencies=[Depends(verify_api_key)], tags=["Core"])
async def process_query(request: ProcessRequest):
    """
    A single endpoint to handle both document ingestion and chat.
    - If `document_url` is provided, it processes the document and makes it the active context.
    - If `document_url` is null, it uses the previously processed document as context.
    """
    doc_hash_to_use = rag_state.active_doc_hash
    temp_file_path = None

    try:
        # **Step 1: Handle Document Ingestion if URL is provided**
        if request.document_url:
            print(f"Document URL provided: {request.document_url}")
            file_extension = ".pdf" if ".pdf" in request.document_url.lower() else ".docx"
            temp_file_path = os.path.join(CACHE_DIR, f"temp_document{file_extension}")
            
            download_file(request.document_url, temp_file_path)
            current_doc_hash = get_file_hash(temp_file_path)
            
            # Set this document as the currently active one for this and future queries
            rag_state.active_doc_hash = current_doc_hash
            doc_hash_to_use = current_doc_hash
            
            index_path = os.path.join(CACHE_DIR, f"{doc_hash_to_use}.index")
            if not os.path.exists(index_path):
                print(f"Cache miss for {doc_hash_to_use}. Running ingestion pipeline...")
                run_ingestion_pipeline(
                    doc_path=temp_file_path,
                    doc_hash=doc_hash_to_use,
                    embedding_model=rag_state.embedding_model,
                    cache_dir=CACHE_DIR
                )
            else:
                print(f"Cache hit for {doc_hash_to_use}. Ingestion skipped.")

        # **Step 2: Check if there is an active document to query**
        if not doc_hash_to_use:
            raise HTTPException(status_code=400, detail="No document has been processed yet. Please provide a `document_url` in your first request.")

        # **Step 3: Run Inference**
        print(f"Running inference against document hash: {doc_hash_to_use}")
        history_dicts = [msg.model_dump() for msg in request.history]
        answer = run_inference_pipeline(
            query=request.query,
            history=history_dicts,
            doc_hash=doc_hash_to_use,
            cache_dir=CACHE_DIR,
            embedding_model=rag_state.embedding_model,
            generative_model=rag_state.generative_model,
            loaded_indexes=rag_state.loaded_indexes,
            loaded_chunks=rag_state.loaded_chunks
        )
        
        return ProcessResponse(answer=answer, document_hash=doc_hash_to_use)

    except HTTPException as e:
        raise e  # Re-raise FastAPI exceptions
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        # Clean up the downloaded file after the request is complete
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# -- Main Execution --
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)