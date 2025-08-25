import os
import gc
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import fitz  # PyMuPDF
import docx  # New import for .docx files
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# --- Configuration Constants ---
HEADER_FOOTER_MARGIN = 0.08
REPEATING_CONTENT_THRESHOLD = 0.5
BATCH_SIZE = 32
WORDS_PER_PAGE_HEURISTIC_DOCX = 300 # Heuristic for splitting DOCX content into "pages"

# --- Document Parsing Functions ---

def _process_pdf_page(args: tuple) -> tuple:
    """Worker function for parallel PDF page processing."""
    pdf_path, page_num = args
    # Use a new doc object in each thread for safety
    with fitz.open(pdf_path) as doc:
        page = doc.load_page(page_num)
        page_elements = []
        header_footer_candidates = []
        
        words = page.get_text("words")
        if not words:
            return [], []

        words.sort(key=lambda w: (w[1], w[0]))

        # This logic for paragraph reconstruction is solid. Let's keep it.
        paragraphs = []
        current_para = [words[0]]
        for i in range(1, len(words)):
            prev_word, curr_word = words[i-1], words[i]
            vertical_gap = curr_word[1] - prev_word[3]
            same_line = abs(curr_word[1] - prev_word[1]) < 2
            line_height = max(10, prev_word[3] - prev_word[1])
            
            if not same_line and vertical_gap > (line_height * 0.7):
                para_text = " ".join(w[4] for w in current_para)
                paragraphs.append({"content": para_text, "page_num": page_num})
                current_para = [curr_word]
            else:
                current_para.append(curr_word)
        
        if current_para:
            para_text = " ".join(w[4] for w in current_para)
            paragraphs.append({"content": para_text, "page_num": page_num})

        for para in paragraphs:
            para_text = para["content"].strip()
            if para_text:
                header_footer_candidates.append(para_text)
                page_elements.append(para)
                
        return page_elements, header_footer_candidates

def _parse_pdf(doc_path: str) -> tuple[list, set]:
    """Parses a PDF document and returns elements and a suppression list."""
    with fitz.open(doc_path) as doc:
        num_pages = doc.page_count
    
    if num_pages == 0: return [], set()

    page_args = [(doc_path, i) for i in range(num_pages)]
    all_page_elements_nested = [None] * num_pages
    all_hf_candidates = []

    with ThreadPoolExecutor() as executor:
        results = executor.map(_process_pdf_page, page_args)
        for i, (page_elements, hf_candidates) in enumerate(tqdm(results, total=num_pages, desc="Parsing PDF pages")):
            all_page_elements_nested[i] = page_elements
            all_hf_candidates.extend(hf_candidates)
    
    elements = [item for sublist in all_page_elements_nested for item in sublist]
    
    header_footer_counts = defaultdict(int)
    for text in all_hf_candidates:
        header_footer_counts[text] += 1
    
    suppression_list = {text for text, count in header_footer_counts.items() 
                        if count / num_pages > REPEATING_CONTENT_THRESHOLD}
    
    return elements, suppression_list

def _parse_docx(doc_path: str) -> tuple[list, set]:
    """Parses a DOCX document and returns elements. Suppression list is empty for DOCX."""
    print("Parsing DOCX file...")
    doc = docx.Document(doc_path)
    elements = []
    word_count = 0
    page_num = 1
    
    for para in doc.paragraphs:
        content = para.text.strip()
        if content:
            elements.append({"content": content, "page_num": page_num})
            word_count += len(content.split())
            
            # Use a word count heuristic to simulate "pages"
            if word_count >= WORDS_PER_PAGE_HEURISTIC_DOCX:
                page_num += 1
                word_count = 0
    
    # For DOCX, we don't have a reliable header/footer detection, so we return an empty suppression list.
    return elements, set()


# --- Chunking Function (Unchanged) ---

def _create_intelligent_chunks(elements: list, suppression_list: set, source_filename: str) -> list:
    """
    Applies cleaning, chunking, and metadata enrichment.
    This function remains the same as it operates on the standardized element list.
    """
    # This function is perfect as-is. No changes needed.
    proto_chunks = []
    for element in elements:
        content = element["content"].strip()
        if content and content not in suppression_list:
            proto_chunks.append({
                "content": content,
                "page_num": element.get("page_num")
            })

    if not proto_chunks: return []

    merged_chunks = []
    list_item_pattern = re.compile(r'^\s*(?:[a-z][\.\)]|[ivx]+\.|[•])', re.IGNORECASE)
    # Corrected logic for merging: Always append first, then check for merges.
    if proto_chunks:
        merged_chunks.append(proto_chunks[0])
        for i in range(1, len(proto_chunks)):
            current_content = proto_chunks[i]["content"]
            # Check if the current line starts like a list item or the previous line was a list item.
            # This logic can be refined, but let's assume merging consecutive list items.
            if list_item_pattern.match(current_content) and list_item_pattern.match(merged_chunks[-1]["content"].split('\n')[-1]):
                merged_chunks[-1]["content"] += f"\n{current_content}"
            else:
                merged_chunks.append(proto_chunks[i])

    final_chunks = []
    current_section_header = "Preamble"
    major_header_pattern = re.compile(r'^(?:[IVXLCDM]+\.|[A-Z]\)|\d+\.)\s+([A-Z\s\-&]+:?)$')
    for chunk in merged_chunks:
        content = chunk["content"]
        header_match = major_header_pattern.match(content.split('\n')[0])
        if header_match:
            current_section_header = header_match.group(1).strip().replace(':', '')
        
        final_chunks.append({
            "content": content,
            "metadata": {
                "source_document": source_filename,
                "page_number": chunk["page_num"],
                "section_header": current_section_header,
                "chunk_type": "content"
            }
        })
    return final_chunks


# --- Main Pipeline Function (Refactored) ---

def run_ingestion_pipeline(doc_path: str, doc_hash: str, embedding_model, cache_dir: str):
    """
    The complete, refactored ingestion pipeline that handles PDF and DOCX.
    """
    print(f"--- Starting Ingestion Pipeline for doc hash: {doc_hash} ---")
    
    # 1. Parse document based on file type
    print("Step 1/3: Parsing document...")
    file_extension = os.path.splitext(doc_path)[1].lower()
    
    if file_extension == '.pdf':
        elements, suppression_list = _parse_pdf(doc_path)
    elif file_extension == '.docx':
        elements, suppression_list = _parse_docx(doc_path)
    else:
        print(f"Error: Unsupported file type '{file_extension}'. Skipping.")
        return

    if not elements:
        print("Warning: No content extracted from the document.")
        return
        
    # 2. Create intelligent chunks (This step is now universal)
    print("Step 2/3: Chunking content...")
    intelligent_chunks = _create_intelligent_chunks(elements, suppression_list, os.path.basename(doc_path))
    
    chunks_path = os.path.join(cache_dir, f"{doc_hash}.json")
    with open(chunks_path, 'w', encoding='utf-8') as f:
        json.dump(intelligent_chunks, f, indent=2, ensure_ascii=False)
    
    # 3. Vectorize chunks and create FAISS index (This step is also universal)
    print("Step 3/3: Vectorizing and creating index...")
    texts_to_embed = [chunk['content'] for chunk in intelligent_chunks]

    if not texts_to_embed:
        print("Warning: No content was left after chunking to create a vector index.")
        return

    embeddings = embedding_model.encode(
        texts_to_embed, 
        batch_size=BATCH_SIZE, 
        show_progress_bar=True, 
        convert_to_numpy=True
    )
    
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    
    index_path = os.path.join(cache_dir, f"{doc_hash}.index")
    faiss.write_index(index, index_path)
    
    gc.collect()
    print(f"--- Ingestion Pipeline Finished. Files saved for hash {doc_hash} ---")