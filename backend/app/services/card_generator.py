from datetime import UTC, datetime

from redis.asyncio import Redis

STATE_CODES = {
    "Akwa Ibom": "AKS",
    "Lagos": "LGS",
    "Rivers": "RVS",
    "FCT": "FCT",
}


async def generate_card_number(redis: Redis | None, state_location: str, tenant_id: str) -> str:
    year = datetime.now(UTC).year
    state_code = STATE_CODES.get(state_location, "NGN")
    if redis is not None:
        sequence = await redis.incr(f"card-sequence:{tenant_id}:{year}")
    else:
        sequence = 412
    return f"SV-{state_code}-{year}-{int(sequence):05d}"

