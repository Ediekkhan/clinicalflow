import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.rate_limit_config import RATE_LIMITS
from app.services.lexicon import get_redis


async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    identifier: str,
) -> None:
    redis_client = await get_redis()
    if redis_client is None:
        return

    redis_key = f"rate_limit:{key}:{identifier}"
    now = time.time()
    window_start = now - window_seconds

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(redis_key, 0, window_start)
    pipe.zcard(redis_key)
    pipe.zadd(redis_key, {str(now): now})
    pipe.expire(redis_key, window_seconds)
    results = await pipe.execute()
    current_count = int(results[1])

    if current_count >= limit:
        oldest = await redis_client.zrange(redis_key, 0, 0, withscores=True)
        retry_after = window_seconds
        if oldest:
            retry_after = max(1, int(window_seconds - (now - float(oldest[0][1]))) + 1)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after_seconds": retry_after,
                "message": "Too many requests. Please wait before trying again.",
            },
            headers={"Retry-After": str(retry_after)},
        )


async def get_rate_limit_identifier(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.get('sub')}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"

    return f"ip:{request.client.host if request.client else 'unknown'}"


async def track_failed_login(identifier: str) -> int:
    redis_client = await get_redis()
    if redis_client is None:
        return 1

    key = f"failed_login:{identifier}"
    count = await redis_client.incr(key)
    await redis_client.expire(key, 1800)

    lockout_thresholds = {
        1: 0,
        2: 5,
        3: 30,
        4: 300,
        5: 1800,
    }
    wait_seconds = lockout_thresholds.get(int(count), 1800)
    if wait_seconds > 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too many failed attempts",
                "wait_seconds": wait_seconds,
                "attempt_number": int(count),
                "message": f"Account temporarily locked. Try again in {wait_seconds} seconds.",
            },
            headers={"Retry-After": str(wait_seconds)},
        )
    return int(count)


async def clear_failed_login(identifier: str) -> None:
    redis_client = await get_redis()
    if redis_client is not None:
        await redis_client.delete(f"failed_login:{identifier}")


class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or path.endswith("/health") or path.startswith(("/docs", "/openapi")):
            return await call_next(request)

        config = RATE_LIMITS["api:general"]
        identifier = await get_rate_limit_identifier(request)
        await check_rate_limit(
            key="api:general",
            limit=config["requests"],
            window_seconds=config["window_seconds"],
            identifier=identifier,
        )
        return await call_next(request)
