"""In-memory fixed-window rate limiting middleware."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    windows: dict[str, deque[float]] = defaultdict(deque)

    def __init__(self, app) -> None:
        super().__init__(app)

    def _limit_for(self, path: str) -> int:
        if path.startswith("/api/auth"):
            return settings.auth_rate_limit_per_minute
        if path.startswith(("/api/chat", "/api/search", "/api/research", "/api/agents", "/api/evals")):
            return settings.rate_limit_per_minute
        return 0

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        limit = self._limit_for(request.url.path)
        if limit:
            client = request.client.host if request.client else "unknown"
            key = f"{client}:{request.url.path.split('/')[2] if request.url.path.count('/') > 2 else 'root'}"
            now = time.time()
            window = self.windows[key]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "code": "rate_limited", "retry_after": 60},
                    headers={"Retry-After": "60"},
                )
            window.append(now)
        return await call_next(request)
