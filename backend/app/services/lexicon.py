import json
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import get_settings


DEFAULT_SYMPTOM_ALIASES: dict[str, list[str]] = {
    "chest_pain": ["chest pain", "chest dey pain", "pain for chest", "heavy chest"],
    "short_breath": ["short breath", "breathing fast", "no fit breathe", "breathless"],
    "bleeding": ["bleeding", "blood dey come", "serious blood"],
    "fever": ["fever", "hot body", "temperature", "malaria symptoms"],
    "pregnancy_pain": ["pregnant pain", "pregnancy pain", "belle pain"],
    "headache": ["headache", "head dey pain", "migraine"],
    "cough": ["cough", "dry cough", "coughing"],
    "abdominal_pain": ["stomach pain", "abdominal pain", "belly pain"],
}

DANGER_KEYWORDS = {
    "collapse",
    "unconscious",
    "not breathing",
    "seizure",
    "convulsion",
    "severe bleeding",
    "chest pain",
}


@dataclass
class ExtractedSymptoms:
    symptom_ids: list[str]
    dangerous_keywords: list[str]


_redis: Redis | None = None


async def get_redis() -> Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
            await _redis.ping()
        except Exception:
            _redis = None
    return _redis


async def get_cached_aliases() -> dict[str, list[str]]:
    redis = await get_redis()
    if redis is None:
        return DEFAULT_SYMPTOM_ALIASES

    cache_key = "clinical:lexicon:pidgin:v1"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    await redis.set(cache_key, json.dumps(DEFAULT_SYMPTOM_ALIASES), ex=3600)
    return DEFAULT_SYMPTOM_ALIASES


async def extract_symptoms(text: str) -> ExtractedSymptoms:
    normalized = text.lower()
    aliases = await get_cached_aliases()
    symptom_ids = [
        symptom_id
        for symptom_id, terms in aliases.items()
        if any(term in normalized for term in terms)
    ]
    dangerous = [keyword for keyword in DANGER_KEYWORDS if keyword in normalized]
    return ExtractedSymptoms(symptom_ids=symptom_ids, dangerous_keywords=dangerous)

