from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request

from backend.app.core.config import get_settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        requests = self._requests[key]
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait and try again.",
            )
        requests.append(now)


rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    client_key = _client_key(request)
    rate_limiter.check(
        client_key,
        max(settings.rate_limit_requests_per_minute, 1),
    )


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
