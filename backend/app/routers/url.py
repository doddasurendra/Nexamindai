"""URL intelligence with SSRF-safe retrieval and optional LLM summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import get_settings
from ..deps import get_current_user
from ..models import User
from ..schemas import UrlAnalyzeRequest, UrlAnalyzeResponse
from ..services import openrouter
from ..services.fetch import fetch_page

settings = get_settings()
router = APIRouter(prefix="/api/url", tags=["url"])


@router.post("/analyze", response_model=UrlAnalyzeResponse)
async def analyze_url(payload: UrlAnalyzeRequest, user: User = Depends(get_current_user)) -> UrlAnalyzeResponse:
    page = await fetch_page(payload.url)
    summary = ""
    answer = None
    if settings.openrouter_configured and page.text:
        if payload.question:
            result = await openrouter.chat(
                [
                    {"role": "system", "content": "Answer using only the page content. If it is insufficient, say so."},
                    {"role": "user", "content": f"Page ({page.final_url}):\n{page.text[:15000]}\n\nQuestion: {payload.question}"},
                ],
                temperature=0.2,
                max_tokens=600,
            )
            answer = result["text"]
        result = await openrouter.chat(
            [
                {"role": "system", "content": "Summarize the page in 5 bullet points. Be faithful to the text."},
                {"role": "user", "content": page.text[:15000]},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        summary = result["text"]
    return UrlAnalyzeResponse(
        url=payload.url,
        title=page.title,
        text=page.text[:10000],
        summary=summary,
        answer=answer,
        links=page.links[:20],
        fetched_bytes=page.bytes_read,
    )
