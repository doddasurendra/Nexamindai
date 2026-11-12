"""Retrieval-augmented generation: chunking, embeddings, hybrid search, grounded answers."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..errors import ProviderError
from ..models import Document, DocumentChunk, KnowledgeBase
from . import openrouter
from .docs import chunk_text

settings = get_settings()

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def local_embedding(text: str, dims: int | None = None) -> list[float]:
    """Deterministic offline embedding (feature hashing). Stable across runs, no network."""
    dim = dims or settings.embedding_dimensions
    vector = [0.0] * dim
    counts = Counter(tokenize(text))
    for token, count in counts.items():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [round(v / norm, 6) for v in vector]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if settings.embedding_provider == "openrouter" and settings.openrouter_configured:
        return await openrouter.embeddings(texts)
    return [local_embedding(text) for text in texts]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    na = math.sqrt(sum(v * v for v in a[:length])) or 1.0
    nb = math.sqrt(sum(v * v for v in b[:length])) or 1.0
    return dot / (na * nb)


def bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    query_terms = tokenize(query)
    tokenized = [tokenize(d) for d in docs]
    if not tokenized:
        return []
    avg_len = sum(len(t) for t in tokenized) / len(tokenized) or 1.0
    df: Counter[str] = Counter()
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1
    n = len(tokenized)
    scores = []
    for tokens in tokenized:
        counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            if counts[term] == 0:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            tf = counts[term]
            score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * len(tokens) / avg_len))
        scores.append(score)
    return scores


async def index_document(db: AsyncSession, document: Document, text: str) -> int:
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    chunks = chunk_text(text)
    if not chunks:
        return 0
    vectors = await embed_texts(chunks)
    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
        db.add(
            DocumentChunk(
                document_id=document.id,
                idx=index,
                content=chunk,
                tokens=max(1, len(chunk) // 4),
                embedding=vector,
            )
        )
    await db.commit()
    return len(chunks)


async def retrieve(
    db: AsyncSession, knowledge_base_id: int, query: str, top_k: int = 5, mode: str = "hybrid"
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(DocumentChunk, Document.filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.knowledge_base_id == knowledge_base_id)
        )
    ).all()
    if not rows:
        return []
    docs = [row[0].content for row in rows]
    query_vector = (await embed_texts([query]))[0]
    semantic = [cosine(query_vector, row[0].embedding) for row in rows]
    lexical = bm25_scores(query, docs)
    max_lex = max(lexical) or 1.0
    results = []
    for index, (chunk, filename) in enumerate(rows):
        lex_score = lexical[index] / max_lex
        score = semantic[index] if mode == "semantic" else 0.65 * semantic[index] + 0.35 * lex_score
        results.append(
            {
                "document_id": chunk.document_id,
                "filename": filename,
                "chunk_id": chunk.id,
                "content": chunk.content,
                "score": round(score, 6),
                "semantic": round(semantic[index], 6),
                "lexical": round(lex_score, 6),
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


async def answer_with_rag(
    db: AsyncSession,
    knowledge_base_id: int,
    query: str,
    *,
    model: str | None = None,
    top_k: int = 5,
    mode: str = "hybrid",
    grounded: bool = True,
) -> dict[str, Any]:
    hits = await retrieve(db, knowledge_base_id, query, top_k=top_k, mode=mode)
    if grounded and not hits:
        return {
            "answer": "I could not find anything relevant in the connected knowledge base, so I will not guess.",
            "citations": [],
            "hits": [],
        }
    context = "\n\n".join(
        f"[{i + 1}] ({hit['filename']}) {hit['content']}" for i, hit in enumerate(hits)
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Answer strictly from the provided context. Cite sources as [n]. "
                "If the context is insufficient, say so instead of guessing."
            ),
        },
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ]
    if not settings.openrouter_configured:
        # Honest degraded mode: return retrieval results only.
        return {
            "answer": None,
            "citations": [
                {"index": i + 1, "document_id": h["document_id"], "filename": h["filename"], "chunk_id": h["chunk_id"]}
                for i, h in enumerate(hits)
            ],
            "hits": hits,
            "notice": "OPENROUTER_API_KEY is not configured; retrieval works but answer synthesis is disabled.",
        }
    try:
        result = await openrouter.chat(messages, model=model, temperature=0.2, max_tokens=900)
    except ProviderError as exc:
        raise ProviderError("OpenRouter", f"RAG answer failed: {exc}") from exc
    citations = [
        {"index": i + 1, "document_id": h["document_id"], "filename": h["filename"], "chunk_id": h["chunk_id"]}
        for i, h in enumerate(hits)
    ]
    return {"answer": result["text"], "citations": citations, "hits": hits, "usage": result}
