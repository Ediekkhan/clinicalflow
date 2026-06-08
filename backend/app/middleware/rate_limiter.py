from time import time

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.lexicon import get_redis


class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple Redis-backed per-IP limiter for public patient endpoints."""

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health"):
            return await call_next(request)
        redis = await get_redis()
        if redis is None:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        bucket = int(time() // self.window_seconds)
        key = f"rate:{ip}:{bucket}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.window_seconds)
        if count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again shortly.",
            )
        return await call_next(request)

