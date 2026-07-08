import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, Response, status
from jose import JWTError, jwt
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


ACCESS_COOKIE = "synapti_access"
REFRESH_COOKIE = "synapti_refresh"
REVOKED_SET = "revoked_tokens"

_redis_client: Redis | None = None
_memory_refresh_tokens: dict[str, tuple[dict[str, str], datetime]] = {}
_memory_revoked: dict[str, datetime] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _get_redis() -> Redis | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        settings = get_settings()
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except RedisError:
        _redis_client = None
        return None


def _cleanup_memory() -> None:
    now = _now()
    for store in (_memory_refresh_tokens, _memory_revoked):
        expired = [key for key, value in store.items() if value[1] <= now]
        for key in expired:
            store.pop(key, None)


def _refresh_delta(user_type: str) -> timedelta:
    if user_type == "SPECIALIST":
        return timedelta(days=7)
    return timedelta(days=30)


def _decode(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _is_revoked(jti: str) -> bool:
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            return bool(redis_client.sismember(REVOKED_SET, jti) or redis_client.exists(f"revoked:{jti}"))
        except RedisError:
            pass
    _cleanup_memory()
    return jti in _memory_revoked


def create_access_token(
    subject: str,
    user_type: str,
    extra_claims: dict,
    expires_delta: timedelta,
) -> str:
    now = _now()
    payload = {
        "sub": subject,
        "type": user_type,
        "iat": _timestamp(now),
        "exp": _timestamp(now + expires_delta),
        "jti": str(uuid4()),
    }
    payload.update(extra_claims or {})
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, user_type: str) -> str:
    now = _now()
    ttl_delta = _refresh_delta(user_type)
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "type": user_type,
        "token_use": "refresh",
        "iat": _timestamp(now),
        "exp": _timestamp(now + ttl_delta),
        "jti": jti,
    }
    settings = get_settings()
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    value = json.dumps({"subject": subject, "user_type": user_type})
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            redis_client.setex(f"refresh:{jti}", int(ttl_delta.total_seconds()), value)
            return token
        except RedisError:
            pass
    _cleanup_memory()
    _memory_refresh_tokens[jti] = ({"subject": subject, "user_type": user_type}, now + ttl_delta)
    return token


def verify_token(token: str) -> dict:
    try:
        payload = _decode(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        ) from exc

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing jti")
    if _is_revoked(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    return payload


def verify_refresh_token(token: str) -> dict:
    payload = verify_token(token)
    if payload.get("token_use") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    jti = payload["jti"]
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            if not redis_client.exists(f"refresh:{jti}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired or rotated",
                )
            return payload
        except RedisError:
            pass
    _cleanup_memory()
    if jti not in _memory_refresh_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or rotated")
    return payload


def delete_refresh_token(jti: str) -> None:
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            redis_client.delete(f"refresh:{jti}")
        except RedisError:
            pass
    _memory_refresh_tokens.pop(jti, None)


def revoke_token(jti: str) -> None:
    ttl_seconds = 30 * 24 * 60 * 60
    expires_at = _now() + timedelta(seconds=ttl_seconds)
    redis_client = _get_redis()
    if redis_client is not None:
        try:
            redis_client.sadd(REVOKED_SET, jti)
            redis_client.setex(f"revoked:{jti}", ttl_seconds, "1")
            return
        except RedisError:
            pass
    _cleanup_memory()
    _memory_revoked[jti] = ({"revoked": "1"}, expires_at)


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,
    access_max_age: int = 8 * 60 * 60,
    refresh_max_age: int | None = None,
) -> None:
    settings = get_settings()
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=access_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=refresh_token,
            max_age=refresh_max_age or 30 * 24 * 60 * 60,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")

