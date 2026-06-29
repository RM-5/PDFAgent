from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

import ollama

try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None  # type: ignore[misc, assignment]

try:
    from langchain_core.prompts import PromptTemplate
except ImportError:
    from langchain.prompts import PromptTemplate

from app.configs.settings import (
    LLM_MODEL,
    LLM_NUM_CTX,
    LLM_NUM_PREDICT,
    LLM_NUM_PREDICT_BROAD,
    LLM_TEMPERATURE,
    DEFAULT_RETRIEVAL_K,
    MAX_RETRIEVAL_K,
)
from app.services.loader import DoclingLoader
from app.db.vectorstore import VectorStore

log = logging.getLogger("rag")

BROAD_QUESTION_PATTERNS = [
    r"\b(summarize|summary|overview|entire|whole|all pages|complete|comprehensive|everything|full document)\b",
    r"\blist all\b",
    r"\bexplain (in detail|thoroughly|everything)\b",
    r"\bwhat are (all|the main|the key)\b",
    r"\bcompare\b.*\band\b",
    r"\bacross (the )?(document|pages|sections)\b",
]


def is_broad_question(question: str) -> bool:
    q = question.lower()
    if any(re.search(p, q) for p in BROAD_QUESTION_PATTERNS):
        return True
    return len(question.split()) >= 22


NARROW_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a document assistant. Answer using ONLY the context below.
Be clear and concise. Cite page numbers where relevant.

Context:
{context}

Question: {question}

Answer:""",
)

BROAD_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a document assistant with access to extracted content from a document.
The context below contains chunks from different pages — synthesize them into one structured answer.

Rules:
- Use ONLY information from the context provided.
- Cover each relevant section; use headings or bullet points for multi-part answers.
- Cite page numbers where information comes from.
- If information is missing from the context, say so briefly.

Context:
{context}

Question: {question}

Answer:""",
)


class QAChain:

    def __init__(self, vector_store: VectorStore, k: int = DEFAULT_RETRIEVAL_K):
        self.vs = vector_store
        self.k  = k
        log.info("QAChain ready — model: %s, default k: %d", LLM_MODEL, k)

    def _effective_k(self, question: str, k: int | None) -> tuple[int, bool]:
        requested = k if k is not None else self.k
        broad     = is_broad_question(question)
        total     = self.vs.stats()["total_chunks"]

        if broad:
            # Modest boost only — avoid pulling half the index
            effective = min(max(requested, 12), MAX_RETRIEVAL_K, total)
        else:
            effective = min(max(requested, 5), MAX_RETRIEVAL_K, total)

        return effective, broad

    def _estimate_tokens(self, text: str) -> int:
        return self.vs.tiktoken_len(text)

    def _invoke_llm(self, prompt_text: str, broad: bool) -> str:
        num_predict   = LLM_NUM_PREDICT_BROAD if broad else LLM_NUM_PREDICT
        prompt_tokens = self._estimate_tokens(prompt_text)
        num_ctx = min(
            LLM_NUM_CTX,
            max(4096, prompt_tokens + num_predict + 256),
        )
        log.info(
            "LLM call — ~%d prompt tokens, num_ctx=%d, num_predict=%d",
            prompt_tokens, num_ctx, num_predict,
        )

        # qwen3.5 is a thinking model — without think=False the response field is empty
        try:
            result = ollama.generate(
                model=LLM_MODEL,
                prompt=prompt_text,
                think=False,
                options={
                    "num_ctx": num_ctx,
                    "num_predict": num_predict,
                    "temperature": LLM_TEMPERATURE,
                },
            )
            answer = (result.get("response") or "").strip()
        except Exception as exc:
            log.warning("ollama.generate failed (%s), trying ChatOllama fallback", exc)
            answer = self._invoke_via_chatollama(prompt_text, num_ctx, num_predict)

        if not answer:
            raise RuntimeError(
                f"Model '{LLM_MODEL}' returned an empty answer. "
                "If using a Qwen3 thinking model, ensure Ollama is up to date."
            )
        return answer

    def _invoke_via_chatollama(self, prompt_text: str, num_ctx: int, num_predict: int) -> str:
        if ChatOllama is None:
            return ""
        llm = ChatOllama(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            num_ctx=num_ctx,
            num_predict=num_predict,
            reasoning=False,
        )
        msg = llm.invoke(prompt_text)
        return (getattr(msg, "content", None) or str(msg)).strip()

    def ask(self, question: str, k: int | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        log.info("Question: %s", question)

        effective_k, broad = self._effective_k(question, k)
        log.info("Retrieval k=%d (broad=%s)", effective_k, broad)

        t_retrieval = time.perf_counter()
        hits = self.vs.retrieve(question, k=effective_k, broad=broad)
        retrieval_ms = (time.perf_counter() - t_retrieval) * 1000

        if not hits:
            return {"question": question, "answer": "No documents indexed yet.", "sources": []}

        context_parts = []
        sources       = []

        for i, h in enumerate(hits, 1):
            meta    = h["metadata"]
            src     = meta.get("file_name", meta.get("source", "unknown"))
            pg      = meta.get("page", "?")
            section = meta.get("section", "")
            label   = meta.get("label", "")

            header = f"[{i}] Source: {src} | Page: {pg}"
            if section:
                header += f" | Section: {section}"
            if label and label not in ("text", ""):
                header += f" | Type: {label}"

            context_parts.append(f"{header}\n{h['text']}")
            sources.append({
                "source":          src,
                "page":            pg,
                "section":         section,
                "relevance_score": round(1 - h["distance"], 4),
            })

        context     = "\n\n---\n\n".join(context_parts)
        template    = BROAD_PROMPT if broad else NARROW_PROMPT
        prompt_text = template.format(context=context, question=question)

        t_llm = time.perf_counter()
        try:
            answer = self._invoke_llm(prompt_text, broad=broad)
        except Exception as exc:
            log.exception("LLM generation failed")
            return {
                "question": question,
                "answer":   f"Could not generate an answer: {exc}",
                "sources":  sources,
                "model":    LLM_MODEL,
                "chunks_used": len(hits),
            }
        llm_ms = (time.perf_counter() - t_llm) * 1000
        total_ms = (time.perf_counter() - t0) * 1000

        log.info(
            "Answer generated — %d chars, %d chunks | retrieval: %.0fms, llm: %.0fms, total: %.0fms",
            len(answer), len(hits), retrieval_ms, llm_ms, total_ms,
        )
        return {
            "question":    question,
            "answer":      answer.strip(),
            "sources":     sources,
            "model":       LLM_MODEL,
            "chunks_used": len(hits),
        }


class RAGSystem:

    def __init__(self, ocr: bool = False, k: int = DEFAULT_RETRIEVAL_K):
        self.loader = DoclingLoader(ocr=ocr)
        self.vs     = VectorStore()
        self.qa     = QAChain(self.vs, k=k)

    def ingest(
        self,
        source: str | Path,
        chunk_size: int | None = None,
        original_name: str | None = None,
    ) -> dict:
        from app.configs.settings import DEFAULT_CHUNK_SIZE

        docs = self.loader.load(source)

        if original_name:
            for doc in docs:
                doc.metadata["file_name"] = original_name

        size = chunk_size if chunk_size is not None else DEFAULT_CHUNK_SIZE
        n    = self.vs.add_documents(docs, source=str(source), chunk_size=size)
        return {"source": str(source), "pages_loaded": len(docs), "chunks_stored": n}

    def query(self, question: str, k: int | None = None) -> dict:
        return self.qa.ask(question, k=k)

    def stats(self) -> dict:
        return self.vs.stats()

    def reset(self) -> None:
        self.vs.clear()
        log.info("RAG system reset.")
