from __future__ import annotations
 
import logging
import re
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
    DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
    MAX_CONTEXT_TOKENS, MAX_RETRIEVAL_K, SAVE_DEBUG_ARTIFACTS,
)
from app.utils.file_utils import get_stem, write_json
 
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
 
 
    def add_documents(
        self,
        docs: list[Document],
        source: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> int:
        stem = get_stem(source)
 
        # Section-aware chunking 
        # Pages that are headings or short get smaller chunks
        # Pages with tables/figures get larger chunks to preserve context
        chunks = []
        for doc in docs:
            label      = doc.metadata.get("label", "text")
            has_table  = doc.metadata.get("has_table", False)
            has_figure = doc.metadata.get("has_figure", False)
 
            # Adjust chunk size based on content type
            if label in ("section_header", "title"):
                chunks.append(doc)
                continue
            elif has_table or has_figure:
                c_size    = max(chunk_size, 3000)
                c_overlap = 200
            else:
                c_size    = chunk_size
                c_overlap = chunk_overlap
 
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=c_size,
                chunk_overlap=c_overlap,
                separators=["\n\n", "\n", ". ", "! ", "? ", " "],
                length_function=self.tiktoken_len,
            )
            split = splitter.split_documents([doc])
            chunks.extend(split)
 
        # Filter junk chunks 
        chunks = self._filter_chunks(chunks)
 
        texts     = [c.page_content for c in chunks]
        metadatas = [c.metadata     for c in chunks]
        ids       = [str(uuid.uuid4()) for _ in chunks]
 
        log.info("Split into %d chunks (from %d pages)", len(chunks), len(docs))
 
        embeddings = self.embedder.embed_documents(texts)
 
        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        log.info("Upserted %d chunks into ChromaDB", len(chunks))
 
        if SAVE_DEBUG_ARTIFACTS:
            self._save_chunks(ids, texts, metadatas, stem)
            self._save_embeddings(ids, texts, metadatas, embeddings, stem)
            self._save_vectorstore_snapshot(stem)
 
        return len(ids)
 
    def similarity_search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        q_emb   = self.embedder.embed_query(query)
        total   = self.collection.count()
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )
        return self._format_hits(results)

    def retrieve(
        self,
        query: str,
        k: int = 10,
        *,
        broad: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve chunks with optional page-diverse selection for broad questions."""
        total = self.collection.count()
        if total == 0:
            return []

        # Small oversample for page diversity to avoid scanning the whole index
        extra     = 6 if broad else 3
        fetch_k   = min(k + extra, total, MAX_RETRIEVAL_K + extra)
        candidates = self.similarity_search(query, k=fetch_k)

        if broad:
            selected = self._diversify_by_page(candidates, k)
        else:
            selected = candidates[:k]

        return self._fit_context_budget(selected)

    # Helpers
    @staticmethod
    def _format_hits(results: dict) -> list[dict[str, Any]]:
        if not results["documents"] or not results["documents"][0]:
            return []
        return [
            {
                "text":     doc,
                "distance": dist,
                "page":     meta.get("page"),
                "label":    meta.get("label", ""),
                "section":  meta.get("section", ""),
                "source":   meta.get("file_name", meta.get("source", "?")),
                "metadata": meta,
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def _diversify_by_page(
        self, candidates: list[dict[str, Any]], k: int
    ) -> list[dict[str, Any]]:
        """Pick the best chunk per page first, then fill remaining slots."""
        by_page: dict[Any, list[dict[str, Any]]] = {}
        for hit in candidates:
            page = hit.get("page", "?")
            by_page.setdefault(page, []).append(hit)

        selected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        # Round 1: best chunk from each page (sorted by distance)
        for page in sorted(by_page.keys(), key=lambda p: (p is None, p)):
            best = min(by_page[page], key=lambda h: h["distance"])
            key  = f"{best.get('page')}-{best['text'][:80]}"
            if key not in seen_ids:
                selected.append(best)
                seen_ids.add(key)

        # Round 2: fill with remaining high scoring chunks
        for hit in sorted(candidates, key=lambda h: h["distance"]):
            if len(selected) >= k:
                break
            key = f"{hit.get('page')}-{hit['text'][:80]}"
            if key not in seen_ids:
                selected.append(hit)
                seen_ids.add(key)

        return selected[:k]

    def _fit_context_budget(
        self, hits: list[dict[str, Any]], max_tokens: int = MAX_CONTEXT_TOKENS
    ) -> list[dict[str, Any]]:
        """Trim hits to stay within the LLM context budget."""
        selected: list[dict[str, Any]] = []
        used = 0
        for hit in hits:
            tokens = self.tiktoken_len(hit["text"]) + 40  
            if selected and used + tokens > max_tokens:
                break
            selected.append(hit)
            used += tokens
        return selected
 
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
 
    def _filter_chunks(self, chunks: list) -> list:
        filtered = []
        for chunk in chunks:
            # Strip PDF watermark patterns 
            text = re.sub(r"lOMoARcPSD\|\d+", "", chunk.page_content).strip()
            if text != chunk.page_content.strip():
                chunk.page_content = text

            if len(text) < 20:          continue   # too short
            if text.isnumeric():        continue   # pure numbers
            if len(set(text)) <= 3:     continue   # repeated characters
            filtered.append(chunk)
        return filtered
 
    def _save_chunks(self, ids, texts, metadatas, stem):
        out = [
            {
                "chunk_index": i,
                "chunk_id":    ids[i],
                "page":        metadatas[i].get("page", "?"),
                "source":      metadatas[i].get("file_name", metadatas[i].get("source", "?")),
                "section":     metadatas[i].get("section", ""),
                "label":       metadatas[i].get("label", ""),
                "has_table":   metadatas[i].get("has_table", False),
                "has_figure":  metadatas[i].get("has_figure", False),
                "text":        texts[i],
                "char_count":  len(texts[i]),
                "token_count": self.tiktoken_len(texts[i]),
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
                "section":           metadatas[i].get("section", ""),
                "label":             metadatas[i].get("label", ""),
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
                "section":           all_data["metadatas"][i].get("section", ""),
                "label":             all_data["metadatas"][i].get("label", ""),
                "has_table":         all_data["metadatas"][i].get("has_table", False),
                "has_figure":        all_data["metadatas"][i].get("has_figure", False),
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
 