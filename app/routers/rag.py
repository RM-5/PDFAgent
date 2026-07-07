from __future__ import annotations
 
import tempfile
import uuid
from pathlib import Path
 
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.db.database import get_db
from app.db.models import User
from app.models.schemas import IngestURLRequest, QueryRequest
from app.services.auth_service import get_current_user
from app.services.qa_chain import RAGSystem
from app.services import history_service
 
router = APIRouter()
 
 
def get_rag() -> RAGSystem:
    raise NotImplementedError("get_rag dependency not configured")
 
 
@router.get("/health")
def health(rag: RAGSystem = Depends(get_rag)):
    return {"status": "ok", **rag.stats()}
 
 
@router.get("/stats")
def stats(rag: RAGSystem = Depends(get_rag)):
    return rag.stats()
 
 
@router.post("/ingest/url")
async def ingest_url(
    req: IngestURLRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rag: RAGSystem = Depends(get_rag),
):
    try:
        info = rag.ingest(req.url, chunk_size=req.chunk_size)
        await history_service.save_document(
            db, current_user.id, req.url, info["chunks_stored"], info["pages_loaded"]
        )
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rag: RAGSystem = Depends(get_rag),
):
    suffix   = Path(file.filename).suffix
    tmp_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
 
    try:
        info = rag.ingest(tmp_path, chunk_size=chunk_size, original_name=file.filename)
        info["original_name"] = file.filename
 
        await history_service.save_document(
            db, current_user.id, file.filename, info["chunks_stored"], info["pages_loaded"]
        )
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)
 
 
@router.post("/query")
async def query(
    req: QueryRequest,
    session_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rag: RAGSystem = Depends(get_rag),
):
    if rag.stats()["total_chunks"] == 0:
        raise HTTPException(status_code=400, detail="No documents indexed. Please /ingest first.")
 
    # Get or create a session for this conversation
    if session_id:
        session = await history_service.get_session(db, session_id, current_user.id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = await history_service.create_session(db, current_user.id)
 
    try:
        result = rag.query(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
    # Save both the question and answer to history
    await history_service.set_session_title_if_new(db, session, req.question)
    await history_service.save_message(db, session.id, "user", req.question)
    await history_service.save_message(
        db, session.id, "assistant", result["answer"],
        sources=result.get("sources", []),
        model=result.get("model"),
        chunks_used=result.get("chunks_used"),
    )
 
    result["session_id"] = str(session.id)
    return result
 
 
@router.delete("/reset")
def reset(rag: RAGSystem = Depends(get_rag)):
    rag.reset()
    return {"status": "cleared"}