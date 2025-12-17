import os
from typing import List, Dict

import numpy as np
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from openai import OpenAI

# ── load environment & create OpenAI client ─────────────────────────────

load_dotenv()  # loads .env from the project root

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# DEBUG: show first few chars so we know it's actually being read
print("DEBUG OPENAI KEY in rag_backend:", (OPENAI_API_KEY or "")[:10])

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. "
        "Make sure it's in your .env or exported before running uvicorn."
    )

client = OpenAI(api_key=OPENAI_API_KEY)

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"


# ── helper: read PDF into text ───────────────────────────────────────────

def pdf_to_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n".join(pages)


# ── helper: chunk text into windows (by words) ───────────────────────────

def chunk_text(text: str, words_per_chunk: int = 350) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[i:i + words_per_chunk])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ── embeddings ───────────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
        encoding_format="float",
    )
    return [d.embedding for d in resp.data]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


# ── build KB from PDFs ───────────────────────────────────────────────────

def build_knowledge_base_from_paths(pdf_paths: list[str]) -> List[Dict]:
    kb: List[Dict] = []
    for path in pdf_paths:
        raw_text = pdf_to_text(path)
        chunks = chunk_text(raw_text)
        embeddings = embed_texts(chunks)
        for chunk, emb in zip(chunks, embeddings):
            kb.append(
                {
                    "text": chunk,
                    "source": path,
                    "embedding": np.array(emb, dtype="float32"),
                }
            )
    return kb


# ── retrieval ────────────────────────────────────────────────────────────

def retrieve_relevant_chunks(question: str, kb: List[Dict], k: int = 5) -> List[Dict]:
    if not kb:
        return []
    q_emb = embed_texts([question])[0]
    q_vec = np.array(q_emb, dtype="float32")
    scored = []
    for item in kb:
        score = cosine_similarity(q_vec, item["embedding"])
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:k]]


# ── tutoring feedback API ────────────────────────────────────────────────

def feedback_on_student_answer(question: str, student_answer: str, kb: List[Dict]) -> str:
    if kb:
        top_chunks = retrieve_relevant_chunks(question, kb, k=5)
        context_blocks = []
        for i, item in enumerate(top_chunks):
            context_blocks.append(
                f"[Source {i+1} – {item['source']}]\n{item['text']}"
            )
        context_text = "\n\n".join(context_blocks)
    else:
        context_text = "No PDF knowledge base is loaded."

    system_prompt = (
        "You are BrighterText, a dyslexia-friendly reading tutor. "
        "You give feedback on student answers.\n\n"
        "Rules:\n"
        "- Use short sentences and simple words.\n"
        "- Always be encouraging.\n"
        "- First say what they did well.\n"
        "- Then gently explain what is missing or incorrect.\n"
        "- Show a short model answer.\n"
        "- End with one small practice suggestion."
    )

    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Student's answer:\n{student_answer}\n\n"
        f"Context from teaching PDFs:\n{context_text}\n\n"
        "Give feedback following the rules above."
    )

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    return resp.choices[0].message.content
