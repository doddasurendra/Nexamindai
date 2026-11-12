"""Typed application errors and consistent integration states."""
from __future__ import annotations


class IntegrationNotConfigured(Exception):
    """Raised when a real external provider lacks credentials. Never faked."""

    def __init__(self, provider: str, env_var: str, message: str | None = None) -> None:
        self.provider = provider
        self.env_var = env_var
        self.message = message or f"{provider} is not configured. Set {env_var} on the backend."
        super().__init__(self.message)


class ProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class SSRFBlocked(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")
