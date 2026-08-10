# Redis Infrastructure

## Architecture

Redis is an optional shared infrastructure layer, not a system of record. PostgreSQL continues to own all transactional state. The backend uses Redis for:

- shared JSON cache entries, initially the versionable clinical symptom lexicon;
- fixed-window rate limits for authentication and public ticket intake;
- tenant-scoped WebSocket event fan-out between multiple backend processes.

Every key is namespaced as `REDIS_KEY_PREFIX:category:key`. WebSocket envelopes contain a source process ID so the publishing process ignores its own pub/sub copy and clients receive each local event once.

## Configuration

```dotenv
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=synaptiverse
AUTH_RATE_LIMIT=10
PUBLIC_INTAKE_RATE_LIMIT=30
```

For a pitch deployment with one backend process, leave `REDIS_ENABLED=false`. For horizontally scaled deployments, use a managed Redis-compatible service, set its TLS URL as `REDIS_URL`, and enable the integration.

## Degraded mode

If Redis is disabled or becomes unreachable:

- cache reads/writes use process-local memory;
- rate limiting remains active per process;
- WebSocket broadcasts continue for clients connected to the same process;
- database writes, authentication, triage, scheduling, and ticket workflows remain available.

The `/health` response reports Redis as `connected` or `degraded-local`. A degraded state is safe for a single-instance MVP but does not provide cross-process rate limits or WebSocket fan-out.

## Operational notes

- Redis contains derived configuration and short-lived counters/events only; do not cache patient narratives or PHI.
- Configure eviction and persistence according to the hosting provider, but application correctness must never rely on Redis persistence.
- Use a private/TLS connection and rotate credentials in production.
- Rate-limit thresholds are requests per 60 seconds and can be adjusted through environment variables.
