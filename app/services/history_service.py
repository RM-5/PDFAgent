from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session, Message, Document


async def create_session(db: AsyncSession, user_id: uuid.UUID, title: str = "New chat") -> Session:
    session = Session(user_id=user_id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    result = await db.execute(
        select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    session = await get_session(db, session_id, user_id)
    if session is None:
        return False
    await db.delete(session)
    await db.commit()
    return True


async def set_session_title_if_new(db: AsyncSession, session: Session, first_question: str) -> None:
    if session.title == "New chat":
        session.title = first_question[:60] + ("..." if len(first_question) > 60 else "")
        await db.commit()


async def save_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    sources: list | None = None,
    model: str | None = None,
    chunks_used: int | None = None,
) -> Message:
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources or [],
        model=model,
        chunks_used=chunks_used,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(db: AsyncSession, session_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def save_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    file_name: str,
    chunks_stored: int,
    pages_loaded: int,
) -> Document:
    document = Document(
        user_id=user_id,
        file_name=file_name,
        chunks_stored=chunks_stored,
        pages_loaded=pages_loaded,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession, user_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.ingested_at.desc())
    )
    return list(result.scalars().all())
