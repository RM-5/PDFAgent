
from __future__ import annotations
 
import logging
import sys
from pathlib import Path
from threading import Lock
 
sys.path.insert(0, str(Path(__file__).parent.parent))
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.routers import rag as rag_router
from app.routers import auth as auth_router
from app.routers import history as history_router
from app.services.qa_chain import RAGSystem
from app.db.database import engine, Base
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
 
app = FastAPI(
    title="Multi-Format RAG API",
    description="Ingest PDFs, DOCX, PPTX, HTML, and query them with Qwen via Ollama",
    version="1.0.0",
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
_rag: RAGSystem | None = None
_rag_lock = Lock()
 
 
def get_rag() -> RAGSystem:
    global _rag
    if _rag is None:
        with _rag_lock:
            if _rag is None:
                _rag = RAGSystem()
    return _rag
 
 
app.dependency_overrides[rag_router.get_rag] = get_rag
 
app.include_router(auth_router.router,    prefix="/auth",    tags=["auth"])
app.include_router(history_router.router, prefix="/history", tags=["history"])
app.include_router(rag_router.router,     tags=["rag"])
 
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=[str(Path(__file__).parent.parent)],
        reload_excludes=[
            "chroma_db/*",
            "outputs/*",
            "__pycache__/*",
            "venv/*",
            "*.sqlite3",
            "*.bin",
        ],
    )
