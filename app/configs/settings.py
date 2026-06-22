from __future__ import annotations
 
import os
from pathlib import Path
 
PROJECT_DIR = Path(__file__).resolve().parents[2]

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL   = os.getenv("LLM_MODEL", "qwen3.5:9b")
 
CHROMA_DIR  = str(PROJECT_DIR / "chroma_db")
COLLECTION  = "rag_docs"
 
OUTPUTS_DIR     = PROJECT_DIR / "outputs"
CHUNKS_DIR      = OUTPUTS_DIR / "chunks"
EMBEDDINGS_DIR  = OUTPUTS_DIR / "embeddings"
VECTORSTORE_DIR = OUTPUTS_DIR / "vectorstore"
 
for directory in (OUTPUTS_DIR, CHUNKS_DIR, EMBEDDINGS_DIR, VECTORSTORE_DIR):
    directory.mkdir(exist_ok=True)
