from __future__ import annotations
 
import os
from pathlib import Path
 
PROJECT_DIR = Path(__file__).resolve().parents[2]

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL   = os.getenv("LLM_MODEL", "qwen3.5:9b")

# RAG retrieval & chunking
DEFAULT_CHUNK_SIZE    = int(os.getenv("DEFAULT_CHUNK_SIZE", "1200"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "200"))
DEFAULT_RETRIEVAL_K   = int(os.getenv("DEFAULT_RETRIEVAL_K", "10"))
MAX_RETRIEVAL_K       = int(os.getenv("MAX_RETRIEVAL_K", "18"))
MAX_CONTEXT_TOKENS    = int(os.getenv("MAX_CONTEXT_TOKENS", "8000"))

# Ollama generation to keep context modest. Large num_ctx slows every request on local GPU/CPU
LLM_NUM_CTX           = int(os.getenv("LLM_NUM_CTX", "8192"))
LLM_NUM_PREDICT       = int(os.getenv("LLM_NUM_PREDICT", "1536"))
LLM_NUM_PREDICT_BROAD = int(os.getenv("LLM_NUM_PREDICT_BROAD", "2048"))
LLM_TEMPERATURE       = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# Skip heavy debug JSON dumps during ingest. This makes indexing much faster, but you won't have the debug artifacts to inspect if something goes wrong.
SAVE_DEBUG_ARTIFACTS  = os.getenv("SAVE_DEBUG_ARTIFACTS", "false").lower() in ("1", "true", "yes")
 
CHROMA_DIR  = str(PROJECT_DIR / "chroma_db")
COLLECTION  = "rag_docs"
 
OUTPUTS_DIR     = PROJECT_DIR / "outputs"
CHUNKS_DIR      = OUTPUTS_DIR / "chunks"
EMBEDDINGS_DIR  = OUTPUTS_DIR / "embeddings"
VECTORSTORE_DIR = OUTPUTS_DIR / "vectorstore"
 
for directory in (OUTPUTS_DIR, CHUNKS_DIR, EMBEDDINGS_DIR, VECTORSTORE_DIR):
    directory.mkdir(exist_ok=True)
