from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


# Auth

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# History

class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: list[dict]
    model: str | None = None
    chunks_used: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionWithMessages(SessionResponse):
    messages: list[MessageResponse]


class DocumentResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    chunks_stored: int
    pages_loaded: int
    ingested_at: datetime

    class Config:
        from_attributes = True
