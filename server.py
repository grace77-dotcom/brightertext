# server.py
from dotenv import load_dotenv
from typing import List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os

from rag_backend import (
    build_knowledge_base_from_paths,
    feedback_on_student_answer,
)

# ----------- env + OpenAI client ----------------
load_dotenv()
client = OpenAI()

print("DEBUG OPENAI key prefix:", os.getenv("OPENAI_API_KEY", "")[:7])

# ----------- FastAPI app ------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # OK for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------- build RAG knowledge base ------------

KB: List[Dict] = []


@app.on_event("startup")
def load_kb():
    """Build the RAG knowledge base once, from your PDFs."""
    global KB

    pdf_paths = [
        # TODO: put your actual PDF paths here:
        "dyslexia_research.pdf",
        # "easy_phonics.pdf",
        # "syntax_article.pdf",
    ]

    existing = [p for p in pdf_paths if os.path.exists(p)]
    if not existing:
        print("WARNING: no PDFs found for KB")
        KB = []
        return

    KB = build_knowledge_base_from_paths(existing)
    print(f"Loaded KB with {len(KB)} chunks from {existing}")


# ----------- feedback endpoint -------------------

class FeedbackRequest(BaseModel):
    question: str
    student_answer: str
    level: int | None = None
    correct: bool | None = None


class FeedbackResponse(BaseModel):
    feedback: str


@app.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(req: FeedbackRequest):
    """
    Return dyslexia-friendly feedback on a student's answer,
    using your RAG model + PDFs.
    """
    fb = feedback_on_student_answer(
        question=req.question,
        student_answer=req.student_answer,
        kb=KB,
    )
    return {"feedback": fb}
