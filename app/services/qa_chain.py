from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    from langchain_community.llms import Ollama

try:
    from langchain_core.prompts import PromptTemplate
except ImportError:
    from langchain.prompts import PromptTemplate

from app.configs.settings import LLM_MODEL
from app.db.VectorStore import VectorStore
from app.services.loader import DoclingLoader

log = logging.getLogger("rag")


RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a precise document assistant. Use ONLY the context below to answer.
If the answer is not in the context, say "I don't have enough information in the provided documents."

Context:
{context}

Question: {question}

Answer (be concise and cite the source page when possible.):""",
)


class QAChain:

    def __init__(self, vector_store: VectorStore, k: int = 5):
        self.vs  = vector_store
        self.k   = k
        self.llm = Ollama(model=LLM_MODEL, temperature=0.2)
        log.info("QAChain ready — model: %s", LLM_MODEL)

    def ask(self, question: str) -> dict[str, Any]:
        log.info("Question: %s", question)

        hits = self.vs.similarity_search(question, k=self.k)
        if not hits:
            return {"question": question, "answer": "No documents indexed yet.", "sources": []}

        context_parts = []
        sources       = []
        for i, h in enumerate(hits, 1):
            meta = h["metadata"]
            src  = meta.get("file_name", meta.get("source", "unknown"))
            pg   = meta.get("page", "?")
            label = meta.get("label", "text")
            section = meta.get("section", "")
            section_text = f", Section: {section}" if section else ""
            context_parts.append(
                f"[{i}] (Source: {src}, Page: {pg}, Type: {label}{section_text})\n{h['text']}"
            )
            sources.append(
                {
                    "source": src,
                    "page": pg,
                    "label": label,
                    "section": section,
                    "relevance_score": round(1 - h["distance"], 4),
                }
            )

        context     = "\n\n---\n\n".join(context_parts)
        prompt_text = RAG_PROMPT.format(context=context, question=question)
        answer      = self.llm.invoke(prompt_text)

        log.info("Answer generated (%d chars)", len(answer))
        return {
            "question":    question,
            "answer":      answer.strip(),
            "sources":     sources,
            "model":       LLM_MODEL,
            "chunks_used": len(hits),
        }


class RAGSystem:
    """Top-level convenience class — combines all three layers."""

    def __init__(self, ocr: bool = True, k: int = 5):
        self.loader = DoclingLoader(ocr=ocr)
        self.vs     = VectorStore()
        self.qa     = QAChain(self.vs, k=k)

    def ingest(self, source: str | Path, chunk_size: int = 1000) -> dict:
        docs = self.loader.load(source)
        n    = self.vs.add_documents(docs, source=str(source), chunk_size=chunk_size)
        return {"source": str(source), "pages_loaded": len(docs), "chunks_stored": n}

    def query(self, question: str) -> dict:
        return self.qa.ask(question)

    def stats(self) -> dict:
        return self.vs.stats()

    def reset(self) -> None:
        self.vs.clear()
        log.info("RAG system reset.")
