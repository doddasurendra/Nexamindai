"""Measured evaluation: accuracy, relevance, groundedness, hallucination, latency, cost."""
from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..errors import IntegrationNotConfigured
from ..models import EvaluationRun
from . import openrouter
from .rag import cosine, local_embedding

settings = get_settings()
SENTENCE_RE = re.compile(r"[.!?]\s+")


def _normalize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def token_f1(prediction: str, expected: str) -> float:
    pred, exp = _normalize(prediction), _normalize(expected)
    if not pred or not exp:
        return 0.0
    common = set(pred) & set(exp)
    if not common:
        return 0.0
    precision = len(common) / len(pred)
    recall = len(common) / len(exp)
    return 2 * precision * recall / (precision + recall)


async def run_evaluation(
    db: AsyncSession, *, dataset, user_id: int, model: str, max_items: int = 10
) -> EvaluationRun:
    if not settings.openrouter_configured:
        raise IntegrationNotConfigured("OpenRouter", "OPENROUTER_API_KEY")
    run = EvaluationRun(dataset_id=dataset.id, user_id=user_id, model=model, status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    results: list[dict[str, Any]] = []
    for item in dataset.items[:max_items]:
        question = str(item.get("question", ""))
        expected = str(item.get("expected", ""))
        contexts = item.get("contexts") or []
        started = time.perf_counter()
        try:
            answer = await openrouter.chat(
                [
                    {"role": "system", "content": "Answer the question accurately and concisely."},
                    {"role": "user", "content": question},
                ],
                model=model,
                temperature=0,
                max_tokens=400,
            )
            latency = int((time.perf_counter() - started) * 1000)
            text = answer["text"]
            exact = float(text.strip().lower() == expected.strip().lower()) if expected else None
            f1 = token_f1(text, expected) if expected else None
            relevance = cosine(local_embedding(question), local_embedding(text))
            groundedness = None
            if contexts:
                chunks = [str(c) for c in contexts]
                sentences = [s for s in SENTENCE_RE.split(text) if s.strip()] or [text]
                groundedness = max(
                    (cosine(local_embedding(sentence), local_embedding(chunk)) for sentence in sentences for chunk in chunks),
                    default=0.0,
                )
            results.append(
                {
                    "question": question,
                    "expected": expected,
                    "answer": text,
                    "exact_match": exact,
                    "f1": round(f1, 4) if f1 is not None else None,
                    "relevance": round(relevance, 4),
                    "groundedness": round(groundedness, 4) if groundedness is not None else None,
                    "hallucination": round(1 - groundedness, 4) if groundedness is not None else None,
                    "latency_ms": latency,
                    "tokens_in": answer["tokens_in"],
                    "tokens_out": answer["tokens_out"],
                    "cost": answer["cost"],
                    "status": "ok",
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"question": question, "status": "error", "error": str(exc)})

    ok = [r for r in results if r["status"] == "ok"]
    def mean(key: str) -> float | None:
        values = [r[key] for r in ok if r.get(key) is not None]
        return round(sum(values) / len(values), 4) if values else None

    metrics = {
        "items": len(results),
        "succeeded": len(ok),
        "accuracy_exact_match": mean("exact_match"),
        "f1": mean("f1"),
        "relevance": mean("relevance"),
        "groundedness": mean("groundedness"),
        "hallucination_rate": mean("hallucination"),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in ok) / len(ok)) if ok else None,
        "total_tokens": sum(r["tokens_in"] + r["tokens_out"] for r in ok),
        "total_cost": round(sum(r["cost"] for r in ok), 6),
    }
    run.status = "completed" if ok else "failed"
    run.metrics = metrics
    run.results = results
    if not ok:
        run.error = "All evaluation items failed"
    await db.commit()
    await db.refresh(run)
    return run
