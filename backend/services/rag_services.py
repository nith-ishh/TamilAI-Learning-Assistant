"""
TamilAI - RAG (Retrieval-Augmented Generation) Service
Handles: PDF text extraction → chunking → embedding → FAISS index → semantic search → Gemini answer
"""
 
import os
import json
import pickle
import numpy as np
import google.generativeai as genai
 
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
genai.configure(api_key=GEMINI_API_KEY)
 
EMBED_MODEL = 'models/text-embedding-004'
GEN_MODEL   = 'gemini-2.5-flash'
CHUNK_SIZE  = 800    # characters per chunk
CHUNK_OVERLAP = 100
FAISS_DIR   = os.path.join(os.path.dirname(__file__), '..', 'faiss_indexes')
os.makedirs(FAISS_DIR, exist_ok=True)
 
 
# ─── PDF Processing ───────────────────────────────────────────
def process_pdf(file_path: str, user_id: int) -> tuple[int, str]:
    """
    Extract text from PDF → chunk → embed → save FAISS index.
    Returns (page_count, faiss_index_path)
    """
    # Try pypdf first, fallback to pdfminer
    text_pages = _extract_pdf_text(file_path)
    page_count = len(text_pages)
 
    # Chunk the text
    chunks = _chunk_text(text_pages)
 
    # Generate embeddings
    embeddings = _embed_chunks([c['text'] for c in chunks])
 
    # Build and save FAISS-like index (using numpy for portability)
    index_path = _save_index(chunks, embeddings, user_id, file_path)
 
    return page_count, index_path
 
 
def _extract_pdf_text(file_path: str) -> list[str]:
    """Extract text from PDF, one entry per page."""
    pages = []
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text() or ''
            pages.append(text.strip())
        return pages
    except ImportError:
        pass
 
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
        current_page = []
        for page_layout in extract_pages(file_path):
            page_text = ''
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    page_text += element.get_text()
            pages.append(page_text.strip())
        return pages
    except ImportError:
        pass
 
    # Last resort: treat as text
    with open(file_path, 'rb') as f:
        raw = f.read().decode('utf-8', errors='ignore')
    pages = [raw[i:i+2000] for i in range(0, len(raw), 2000)]
    return pages
 
 
def _chunk_text(pages: list[str]) -> list[dict]:
    """Split pages into overlapping chunks with metadata."""
    chunks = []
    for page_num, page_text in enumerate(pages):
        if not page_text.strip():
            continue
        # Split by paragraph first
        paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
        current = ''
        for para in paragraphs:
            if len(current) + len(para) <= CHUNK_SIZE:
                current += (' ' if current else '') + para
            else:
                if current:
                    chunks.append({'text': current, 'page': page_num + 1, 'chunk_id': len(chunks)})
                current = para[-CHUNK_OVERLAP:] + ' ' + para if len(para) > CHUNK_OVERLAP else para
        if current:
            chunks.append({'text': current, 'page': page_num + 1, 'chunk_id': len(chunks)})
    return chunks
 
 
def _embed_chunks(texts: list[str]) -> np.ndarray:
    """Generate embeddings for text chunks using Gemini."""
    if not texts:
        return np.array([])
 
    embeddings = []
    batch_size = 20  # Gemini batch limit
 
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            result = genai.embed_content(
                model=EMBED_MODEL,
                content=batch,
                task_type='retrieval_document'
            )
            embeddings.extend(result['embedding'])
        except Exception as e:
            # Fallback: random embeddings if API fails
            print(f"Embedding batch {i} failed: {e}, using fallback")
            for t in batch:
                # Simple TF-IDF-like fallback using char frequencies
                emb = _simple_embedding(t)
                embeddings.append(emb)
 
    return np.array(embeddings, dtype=np.float32)
 
 
def _simple_embedding(text: str, dim: int = 768) -> list:
    """Fallback embedding using character n-grams (when API unavailable)."""
    import hashlib
    emb = [0.0] * dim
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dim
        emb[idx] += 1.0
    norm = max(sum(x*x for x in emb) ** 0.5, 1e-9)
    return [x / norm for x in emb]
 
 
def _save_index(chunks: list, embeddings: np.ndarray, user_id: int, file_path: str) -> str:
    """Save chunks + embeddings as a pickle file (portable FAISS alternative)."""
    import time
    fname = f"user{user_id}_{int(time.time())}.pkl"
    index_path = os.path.join(FAISS_DIR, fname)
 
    index_data = {
        'chunks':     chunks,
        'embeddings': embeddings,
        'source':     os.path.basename(file_path),
    }
 
    with open(index_path, 'wb') as f:
        pickle.dump(index_data, f)
 
    return index_path
 
 
# ─── RAG Query ────────────────────────────────────────────────
def rag_query(query: str, index_path: str, file_path: str = None) -> tuple[str, list]:
    """
    1. Embed the query
    2. Find top-k similar chunks via cosine similarity
    3. Feed context to Gemini for answer generation
    Returns (answer, source_chunks)
    """
    if not index_path or not os.path.exists(index_path):
        return "புத்தக index கிடைக்கவில்லை. மீண்டும் upload செய்யவும்.", []
 
    # Load index
    with open(index_path, 'rb') as f:
        index_data = pickle.load(f)
 
    chunks     = index_data['chunks']
    embeddings = index_data['embeddings']
 
    if len(embeddings) == 0:
        return "இந்த புத்தகத்தில் உள்ளடக்கம் எடுக்கப்படவில்லை.", []
 
    # Embed query
    try:
        result = genai.embed_content(
            model=EMBED_MODEL,
            content=query,
            task_type='retrieval_query'
        )
        query_emb = np.array(result['embedding'], dtype=np.float32)
    except Exception:
        query_emb = np.array(_simple_embedding(query), dtype=np.float32)
 
    # Cosine similarity
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
 
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    normed = embeddings / norms
 
    q_norm = query_emb / max(np.linalg.norm(query_emb), 1e-9)
    scores = normed @ q_norm
 
    # Top 4 chunks
    top_k  = min(4, len(scores))
    top_idx = np.argsort(scores)[::-1][:top_k]
    top_chunks = [chunks[i] for i in top_idx]
 
    # Build context
    context = '\n\n---\n\n'.join([
        f"[பக்கம் {c['page']}]\n{c['text']}" for c in top_chunks
    ])
 
    # Generate answer with Gemini
    model  = genai.GenerativeModel(GEN_MODEL)
    prompt = f"""You are TamilAI Tutor. A student uploaded their textbook and is asking a question.
Answer ONLY using the provided textbook content. Do not add information from outside.
Answer in Tamil (தமிழ்) with clear, student-friendly explanations.
 
Textbook content:
{context}
 
Student question: {query}
 
Instructions:
- Answer only from the textbook content above
- If the answer is not in the content, say "இந்த தகவல் உங்கள் பாடப்புத்தகத்தில் இல்லை"
- Use Tamil for explanations
- Reference the page number when possible
- Format with headings and bullets for clarity"""
 
    try:
        response = model.generate_content(prompt)
        answer = response.text
    except Exception as e:
        answer = f"பதில் உருவாக்குவதில் பிழை: {str(e)}"
 
    # Return source info
    sources = [{'page': c['page'], 'snippet': c['text'][:150] + '...'} for c in top_chunks]
 
    return answer, sources

def generate_notes_from_book(index_path: str, topic: str):
    """
    Generate notes using the uploaded textbook.
    """

    answer, sources = rag_query(topic, index_path)

    return {
        "title": topic,
        "summary": answer,
        "sources": sources
    }