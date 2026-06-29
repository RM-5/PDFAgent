from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.configs.settings import DEFAULT_CHUNK_SIZE
from app.models.schemas import (
    HealthResponse,
    IngestResponse,
    IngestURLRequest,
    QueryRequest,
    QueryResponse,
    StatsResponse,
)
from app.services.qa_chain import RAGSystem

router = APIRouter()



def get_rag() -> RAGSystem:
    raise NotImplementedError("get_rag dependency not configured")



@router.get("/health", response_model=HealthResponse)
def health(rag: RAGSystem = Depends(get_rag)):
    return {"status": "ok", **rag.stats()}


@router.get("/stats", response_model=StatsResponse)
def stats(rag: RAGSystem = Depends(get_rag)):
    return rag.stats()


@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    chunk_size: int = Form(DEFAULT_CHUNK_SIZE),
    rag: RAGSystem = Depends(get_rag),
):
    suffix   = Path(file.filename).suffix
    tmp_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        info = rag.ingest(
            tmp_path,
            chunk_size=chunk_size,
            original_name=file.filename,
        )
        info["original_name"] = file.filename
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


@router.post("/ingest/url")
def ingest_url(req: IngestURLRequest, rag: RAGSystem = Depends(get_rag)):
    try:
        return rag.ingest(req.url, chunk_size=req.chunk_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, rag: RAGSystem = Depends(get_rag)):
    if rag.stats()["total_chunks"] == 0:
        raise HTTPException(status_code=400, detail="No documents indexed. Please /ingest first.")
    try:
        return rag.query(req.question, k=req.k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset")
def reset(rag: RAGSystem = Depends(get_rag)):
    rag.reset()
    return {"status": "cleared"}
