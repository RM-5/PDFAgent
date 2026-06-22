from __future__ import annotations

import logging
import uuid
from typing import Any

import numpy as np
import chromadb
from chromadb.config import Settings

try:
    import tiktoken
except ImportError:
    tiktoken = None

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    from langchain_community.embeddings import OllamaEmbeddings

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

from app.configs.settings import (
    EMBED_MODEL, CHROMA_DIR, COLLECTION,
    CHUNKS_DIR, EMBEDDINGS_DIR, VECTORSTORE_DIR,
)
from app.utils.File_utils import get_stem, write_json

log = logging.getLogger("rag")


class VectorStore:

    def __init__(self):
        self.embedder = OllamaEmbeddings(model=EMBED_MODEL)
        self.encoding = tiktoken.get_encoding("cl100k_base") if tiktoken else None
        self.client   = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("ChromaDB collection '%s' ready (%d chunks)", COLLECTION, self.collection.count())


    def add_documents(self, docs: list[Document], source: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> int:
        stem     = get_stem(source)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", " "],
            length_function=self.tiktoken_len,
        )

        chunks = splitter.split_documents(docs)
        chunks = self._filter_chunks(chunks)

        texts     = [c.page_content for c in chunks]
        metadatas = [c.metadata     for c in chunks]
        ids       = [str(uuid.uuid4()) for _ in chunks]

        log.info("Split into %d chunks", len(chunks))

        embeddings = self.embedder.embed_documents(texts)

        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
        log.info("Upserted %d chunks into ChromaDB", len(chunks))

        self._save_chunks(ids, texts, metadatas, stem)
        self._save_embeddings(ids, texts, metadatas, embeddings, stem)
        self._save_vectorstore_snapshot(stem)

        return len(ids)

    def similarity_search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        q_emb   = self.embedder.embed_query(query)
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=min(k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "text":     doc,
                "distance": dist,
                "page":     meta.get("page"),
                "label":    meta.get("label"),
                "section":  meta.get("section"),
                "source":   meta.get("file_name", meta.get("source", "?")),
                "metadata": meta,
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def stats(self) -> dict:
        return {
            "collection":      COLLECTION,
            "total_chunks":    self.collection.count(),
            "embed_model":     EMBED_MODEL,
            "distance_metric": "cosine",
            "database_path":   CHROMA_DIR,
        }

    def clear(self) -> None:
        self.client.delete_collection(COLLECTION)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        log.info("Collection cleared.")

    def tiktoken_len(self, text: str) -> int:
        if self.encoding is None:
            return len(text.split())
        return len(self.encoding.encode(text))

    def _filter_chunks(self, chunks):
        filtered = []
        for chunk in chunks:
            text = chunk.page_content.strip()
            if len(text) < 20:       continue
            if text.isnumeric():     continue
            if len(set(text)) <= 3:  continue
            filtered.append(chunk)
        return filtered

    def _save_chunks(self, ids, texts, metadatas, stem):
        out = [
            {
                "chunk_index": i,
                "chunk_id":    ids[i],
                "page":        metadatas[i].get("page", "?"),
                "source":      metadatas[i].get("file_name", metadatas[i].get("source", "?")),
                "text":        texts[i],
                "char_count":  len(texts[i]),
                "token_count": self.tiktoken_len(texts[i]),
                "label":       metadatas[i].get("label", ""),
                "section":     metadatas[i].get("section", ""),
            }
            for i in range(len(texts))
        ]
        path = CHUNKS_DIR / f"{stem}_chunks.json"
        write_json(out, path)
        log.info("Chunks saved → %s", path)

    def _save_embeddings(self, ids, texts, metadatas, embeddings, stem):
        out = [
            {
                "chunk_index":       i,
                "chunk_id":          ids[i],
                "page":              metadatas[i].get("page", "?"),
                "source":            metadatas[i].get("file_name", metadatas[i].get("source", "?")),
                "label":             metadatas[i].get("label", ""),
                "section":           metadatas[i].get("section", ""),
                "char_count":        len(texts[i]),
                "token_count":       self.tiktoken_len(texts[i]),
                "text_preview":      texts[i][:250] + ("…" if len(texts[i]) > 250 else ""),
                "embedding_dim":     len(embeddings[i]),
                "embedding_norm":    float(np.linalg.norm(embeddings[i])),
                "embedding_preview": embeddings[i][:10],
            }
            for i in range(len(texts))
        ]
        path = EMBEDDINGS_DIR / f"{stem}_embeddings.json"
        write_json(out, path)
        log.info("Embeddings saved → %s", path)

    def _save_vectorstore_snapshot(self, stem):
        all_data = self.collection.get(include=["documents", "metadatas", "embeddings"])
        out = [
            {
                "chunk_index":       i,
                "chunk_id":          all_data["ids"][i],
                "source":            all_data["metadatas"][i].get("file_name", all_data["metadatas"][i].get("source", "?")),
                "page":              all_data["metadatas"][i].get("page", "?"),
                "label":             all_data["metadatas"][i].get("label", ""),
                "section":           all_data["metadatas"][i].get("section", ""),
                "text_preview":      all_data["documents"][i][:250] + ("..." if len(all_data["documents"][i]) > 250 else ""),
                "metadata":          all_data["metadatas"][i],
                "char_count":        len(all_data["documents"][i]),
                "token_count":       self.tiktoken_len(all_data["documents"][i]),
                "embedding_dim":     len(all_data["embeddings"][i]),
                "embedding_norm":    float(np.linalg.norm(all_data["embeddings"][i])),
                "embedding_preview": list(all_data["embeddings"][i][:10]),
            }
            for i in range(len(all_data["ids"]))
        ]
        path = VECTORSTORE_DIR / f"{stem}_vectorstore.json"
        write_json(out, path)
        log.info("VectorStore snapshot saved → %s (%d total chunks)", path, len(out))
