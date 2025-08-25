import os
import json
import faiss
import numpy as np
import google.generativeai as genai
from typing import List, Dict

# --- Step 1: Triage and Intent Analysis ---

def _triage_query(query: str, history: List[Dict], generative_model) -> Dict:
    """
    Analyzes the user's query and history to determine sentiment and intent.
    """
    print("Step 1/4: Triaging user query...")
    
    # Default response in case of parsing errors
    default_classification = {"sentiment": "Neutral", "intent": "Question"}
    
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    prompt = f"""
    **INSTRUCTION:**
    You are a classification model for a customer support AI. Analyze the "LATEST USER QUERY" in the context of the "CONVERSATION HISTORY".
    Classify the query into one intent and one sentiment.
    Your response MUST be a valid JSON object with two keys: "intent" and "sentiment".

    **INTENT CATEGORIES:**
    - "Question": The user is asking for information, help, or clarification.
    - "Complaint": The user is expressing frustration, anger, or dissatisfaction with a product or service.
    - "Escalate": The user explicitly asks to speak to a human, manager, or agent.

    **SENTIMENT CATEGORIES:**
    - "Positive": The user seems happy or satisfied.
    - "Neutral": The user is expressing no strong emotion.
    - "Negative": The user seems upset, angry, or frustrated.

    **EXAMPLE:**
    CONVERSATION HISTORY:
    user: My order is late.
    model: I see your order #123 is scheduled for today.
    LATEST USER QUERY: This is unacceptable, where is it?!
    YOUR RESPONSE:
    {{
      "intent": "Complaint",
      "sentiment": "Negative"
    }}

    **TASK:**
    CONVERSATION HISTORY:
    {formatted_history}
    LATEST USER QUERY: {query}
    YOUR RESPONSE:
    """
    
    try:
        response = generative_model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        json_response_str = response.text.strip().replace("```json", "").replace("```", "")
        classification = json.loads(json_response_str)
        
        # Validate keys
        if "intent" not in classification or "sentiment" not in classification:
            return default_classification
            
        print(f"Triage Result -> Intent: {classification['intent']}, Sentiment: {classification['sentiment']}")
        return classification
    except (Exception, json.JSONDecodeError) as e:
        print(f"Error during triage: {e}. Defaulting to standard Q&A.")
        return default_classification

# --- Step 2: Semantic Search (Unchanged) ---

def _semantic_search(query: str, embedding_model, faiss_index, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
    """
    Performs semantic search to find the most relevant chunks. (Unchanged from your original code)
    """
    print(f"Step 2/4: Performing semantic search...")
    query_vector = embedding_model.encode([query], convert_to_numpy=True)
    distances, indices = faiss_index.search(query_vector, k=top_k)
    return [chunks[i] for i in indices[0]]

# --- Step 3: Dynamic Answer Generation ---

def _generate_standard_answer(query: str, context_chunks: List[Dict], generative_model) -> str:
    """
    Generates a direct answer for a standard question.
    """
    print("Step 3/4: Generating standard answer...")
    if not context_chunks:
        return "I do not have enough information to answer this question."

    context = "\n\n---\n\n".join([chunk['content'] for chunk in context_chunks])
    prompt = f"""
    **INSTRUCTION:** You are an expert Q&A assistant. Answer the user's question based ONLY on the provided context. Be direct and concise. If the answer is not in the context, say so.
    
    **CONTEXT:**
    {context}
    
    **QUESTION:**
    {query}
    
    **ANSWER:**
    """
    response = generative_model.generate_content(prompt)
    return response.text.strip()

def _generate_empathetic_answer(query: str, context_chunks: List[Dict], generative_model) -> str:
    """
    Generates an empathetic answer for a complaint or negative query.
    """
    print("Step 3/4: Generating empathetic answer...")
    if not context_chunks:
        return "I understand your frustration, but I couldn't find specific information about your issue in the knowledge base. I recommend reaching out to our support team directly for more help."

    context = "\n\n---\n\n".join([chunk['content'] for chunk in context_chunks])
    prompt = f"""
    **INSTRUCTION:** You are a caring and empathetic customer support assistant. A user is upset or has a complaint.
    1. Start by acknowledging their frustration and showing empathy based on their question.
    2. Then, answer their question using ONLY the provided context.
    3. Maintain a supportive and helpful tone throughout.

    **CONTEXT:**
    {context}
    
    **QUESTION:**
    {query}
    
    **EMPATHETIC ANSWER:**
    """
    response = generative_model.generate_content(prompt)
    return response.text.strip()

# --- Main Pipeline Function (Refactored) ---

def run_inference_pipeline(
    query: str,
    history: List[Dict], # Expects [{"role": "user", "content": "..."}, {"role": "model", "content": "..."}]
    doc_hash: str,
    cache_dir: str,
    embedding_model,
    generative_model,
    loaded_indexes: Dict,
    loaded_chunks: Dict
) -> str:
    """
    The complete inference pipeline that triages, routes, and responds to a user query.
    """
    # --- Step 1: Triage Query ---
    triage_result = _triage_query(query, history, generative_model)
    
    # --- Step 2: Dynamic Routing ---
    intent = triage_result.get("intent", "Question")
    sentiment = triage_result.get("sentiment", "Neutral")

    # Path C: Immediate Escalation
    if intent == "Escalate":
        print("Step 2/4: Routing to ESCALATION path.")
        return "I understand. I'm connecting you to a human agent now. Please wait a moment."
    
    # --- Load Knowledge Base (Only if not escalating) ---
    index_path = os.path.join(cache_dir, f"{doc_hash}.index")
    chunks_path = os.path.join(cache_dir, f"{doc_hash}.json")
    if doc_hash not in loaded_indexes:
        try:
            loaded_indexes[doc_hash] = faiss.read_index(index_path)
            with open(chunks_path, 'r', encoding='utf-8') as f:
                loaded_chunks[doc_hash] = json.load(f)
        except FileNotFoundError:
            return f"Error: Knowledge base for document hash {doc_hash} not found."

    faiss_index = loaded_indexes[doc_hash]
    chunks_data = loaded_chunks[doc_hash]
    
    # --- Perform Search (Paths A & B) ---
    retrieved_chunks = _semantic_search(query, embedding_model, faiss_index, chunks_data)
    
    # --- Generate Final Answer (Paths A & B) ---
    # Path B: Empathetic Resolution
    if intent == "Complaint" or sentiment == "Negative":
        print("Step 2/4: Routing to EMPATHETIC path.")
        answer = _generate_empathetic_answer(query, retrieved_chunks, generative_model)
    # Path A: Standard Q&A
    else:
        print("Step 2/4: Routing to STANDARD Q&A path.")
        answer = _generate_standard_answer(query, retrieved_chunks, generative_model)
        
    print("Step 4/4: Final answer generated.")
    return answer