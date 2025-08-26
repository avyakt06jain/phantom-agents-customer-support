# Phantom Agents: AI Customer Support Assistant

content: _Phantom Agents_ is a full-stack application built for the NSUToblivion'25 hackathon. Inspired by the theme of spectral creativity, this project brings to life a "Phantom Agent"—an intelligent, 24/7 AI customer support assistant that works tirelessly in the background to solve real-world problems for Small and Medium-sized Enterprises (SMEs). This agent "haunts" a company's knowledge base (PDFs or DOCX files) to provide instant, accurate answers. It's designed to understand user emotions, handle complaints with empathy, and intelligently escalate complex issues to human agents, ensuring a seamless and efficient customer experience.

# Live Demo & Links

content:

- _Frontend (Vercel):_ [https://phantom-agents-customer-support.vercel.app/]
- _Backend API (Hugging Face):_ [https://avyakt06jain-phantom-agents-customer-support.hf.space/process]
- _Video Demo:_ [https://github.com/avyakt06jain/phantom-agents-customer-support/blob/main/REC-20250826100138.mp4]

# Tech Stack

content:
| Area | Technology |
| :--- | :--- |
| _Frontend_ | React, Next.js, Tailwind CSS |
| _Backend_ | FastAPI, Uvicorn |
| _AI/ML_ | Google Gemini (gemini-1.5-flash-latest), Sentence-Transformers (all-MiniLM-L6-v2), FAISS |
| _Deployment_ | Vercel (Frontend), Docker & Hugging Face Spaces (Backend) |

# Features

content:

- _Full-Stack Application:_ A complete solution with a polished React frontend and a powerful FastAPI backend.
- _File Upload Interface:_ Users can directly upload .pdf and .docx files to create a knowledge base.
- _Conversational Q\&A:_ Engages in natural, multi-turn conversations with users.
- _Intelligent Triage System:_ Automatically analyzes user queries to detect intent (Question, Complaint, Escalate) and sentiment.
- _Empathetic Responses:_ Dynamically adjusts its tone to handle user complaints with empathy.
- _Smart Escalation:_ Recognizes when a user needs human intervention and provides a clear path for escalation.

# Setup and Running Locally

content: This project is a monorepo with two main parts: frontend and backend.

## Backend Setup (FastAPI)

content:

1.  _Navigate to the backend directory:_

    cd backend

2.  _Create a Virtual Environment:_

    python -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate

3.  _Install Dependencies:_

    pip install -r requirements.txt

4.  _Create .env File:_ Create a .env file inside the backend folder and add your API keys:

    API_KEY="06864514c746f45fb93a6e0421a052c7875d3d1fd841d870f397c9d50e4146f8"
    GEMINI_API_KEY="your-google-gemini-api-key"

5.  _Run the Backend Server:_

    uvicorn app:app --host 0.0.0.0 --port 8000 --reload

    The backend API will be running at http://127.0.0.1:8000.

## Frontend Setup (React)

content:

1.  _Navigate to the frontend directory (from the root):_

    cd frontend

2.  _Install Dependencies:_

    npm install

3.  _Run the Frontend Development Server:_

    npm run dev

    The frontend application will be accessible at http://localhost:3000.

# Technical Workflow

content: The application is built on a sophisticated Retrieval-Augmented Generation (RAG) pipeline.

## 1\. Ingestion Pipeline

content: When a user _uploads a document_ via the frontend:

1.  _File Upload & Hashing_: The file is sent to the /process endpoint. The backend generates a unique SHA256 hash from the file's content to act as its ID.
2.  _Cache Check_: The system checks if a knowledge base for this hash already exists. If so, ingestion is skipped.
3.  _Parse Content_: Based on the file type (.pdf or .docx), a specific parser extracts text and structural elements.
4.  _Chunking & Vectorization_: The text is broken down into smaller chunks, which are then converted into vector embeddings and stored in a FAISS index.

## 2\. Inference Pipeline

content: For every subsequent query in the chat:

1.  _Triage & Routing: The user's query and conversation history are sent to Gemini for a quick classification of \*\*intent_ and _sentiment_.
2.  _Decision Making_: Based on the triage result, the pipeline routes the query to the appropriate path (Escalation, Empathetic, or Standard Q\&A).
3.  _Semantic Search_: The query is used to search the FAISS index for the most relevant context.
4.  _Answer Generation_: The retrieved context is passed to Gemini with a dynamically selected prompt to generate the final answer.
