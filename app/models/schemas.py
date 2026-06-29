from __future__ import annotations

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    k: int = 10


class IngestURLRequest(BaseModel):
    url: str
    chunk_size: int = 1200


class IngestResponse(BaseModel):
    source: str
    pages_loaded: int
    chunks_stored: int
    original_name: str | None = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]
    model: str
    chunks_used: int


class StatsResponse(BaseModel):
    collection: str
    total_chunks: int
    embed_model: str
    distance_metric: str
    database_path: str


class HealthResponse(BaseModel):
    status: str
    collection: str
    total_chunks: int
    embed_model: str
    distance_metric: str
    database_path: str
