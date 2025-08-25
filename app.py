import os
import uvicorn
import hashlib
import json # Added for parsing history string
import faiss
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Updated FastAPI imports for file uploads and form data
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Import your custom pipeline functions (no changes here)
from ingestion_pipeline.ingestionPipeline import run_ingestion_pipeline
from inference_pipeline.inferencePipeline import run_inference_pipeline

# -- Initial Setup --
load_dotenv()
app = FastAPI(title="Phantom Agents API - File Upload")
security = HTTPBearer()

# -- Environment Variables & Constants --
API_KEY = os.getenv("API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not all([API_KEY, GEMINI_API_KEY]):
    raise ValueError("Missing critical API keys in .env file")

CACHE_DIR = "knowledge_base_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# -- RAG State & Model Initialization (Unchanged) --
class RAGState:
    def __init__(self, embedding_model_name="all-MiniLM-L6-v2"):
        print("Initializing RAG state...")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        genai.configure(api_key=GEMINI_API_KEY)
        self.generative_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        self.loaded_indexes: Dict[str, faiss.Index] = {}
        self.loaded_chunks: Dict[str, List[Dict]] = {}
        self.active_doc_hash: Optional[str] = None
        print("RAG state initialized successfully.")

rag_state = RAGState()

# -- Pydantic Models for API Schema --
# ChatMessage is used to validate the structure of the parsed history
class ChatMessage(BaseModel):
    role: str
    content: str

# ProcessRequest model is removed as we are now using Form data.
class ProcessResponse(BaseModel):
    answer: str
    document_hash: Optional[str]

# -- Helper Functions --
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# download_file function is removed as it's no longer needed.

def get_file_hash_from_bytes(file_bytes: bytes) -> str:
    """Generates a SHA256 hash from the file's byte content."""
    sha256 = hashlib.sha256()
    sha256.update(file_bytes)
    return sha256.hexdigest()

# -- API Endpoint (Modified for File Upload) --
@app.post("/process", response_model=ProcessResponse, dependencies=[Depends(verify_api_key)], tags=["Core"])
async def process_query(
    query: str = Form(...),
    history: str = Form("[]"),  # History is now a JSON string
    document: Optional[UploadFile] = File(None) # Document is now an optional file upload
):
    """
    A single endpoint to handle both document ingestion (via file upload) and chat.
    - If a `document` file is provided, it's processed and becomes the active context.
    - If `document` is omitted, the previously processed document is used.
    """
    doc_hash_to_use = rag_state.active_doc_hash
    temp_file_path = None

    try:
        # **Step 1: Handle Document Ingestion if a file is uploaded**
        if document:
            print(f"Document uploaded: {document.filename}")
            
            # Validate file type
            if not (document.filename.lower().endswith('.pdf') or document.filename.lower().endswith('.docx')):
                raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .pdf or .docx file.")
            
            # Read file content into memory
            file_bytes = await document.read()
            
            # Generate hash and define temporary path
            current_doc_hash = get_file_hash_from_bytes(file_bytes)
            temp_file_path = os.path.join(CACHE_DIR, f"temp_{current_doc_hash}_{document.filename}")

            # Save file temporarily for the ingestion pipeline
            with open(temp_file_path, "wb") as f:
                f.write(file_bytes)

            # Set this document as the active one
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

        # **Step 2: Check for active document**
        if not doc_hash_to_use:
            raise HTTPException(status_code=400, detail="No document has been processed. Please upload a document with your first request.")

        # **Step 3: Parse history and run inference**
        try:
            history_list = json.loads(history)
            history_dicts = [ChatMessage(**msg).model_dump() for msg in history_list]
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid 'history' format. It must be a valid JSON string representing a list of objects.")

        print(f"Running inference against document hash: {doc_hash_to_use}")
        answer = run_inference_pipeline(
            query=query,
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
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# -- Main Execution --
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
