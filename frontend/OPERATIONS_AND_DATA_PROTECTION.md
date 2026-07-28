# Operations and Data Protection Runbook

## Scope and compliance posture

The controls here support an NDPA-aligned engineering posture but do not themselves certify compliance. A real clinical deployment still requires a documented lawful basis, privacy notices/consent where applicable, processor agreements, DPIA, incident response ownership, and legal/security review. Do not use pitch infrastructure for real patient data.

## Environment and secrets

Set `APP_ENVIRONMENT=production` only with PostgreSQL, `AUTO_CREATE_SCHEMA=false`, secure cookies, and a replaced webhook secret. Startup rejects unsafe production combinations. Store database, webhook, Neo4j, and Redis credentials in the hosting secret manager; never in Git or frontend `NEXT_PUBLIC_*` variables. Rotate provider secrets after staff changes or suspected exposure.

## Retention

Defaults are configurable through `AUDIT_RETENTION_DAYS`, `SESSION_RETENTION_DAYS`, and `LEAD_RETENTION_DAYS`. An administrator can run `POST /api/v1/admin/maintenance/retention`; the action is itself audited. Schedule it daily in production. Clinical ticket retention requires an approved medical/legal policy and is intentionally not automatically deleted by this generic job.

## Logs, metrics, and alerts

Requests emit JSON logs containing request ID, method, route template, status, and duration—no body, phone number, or raw URL identifiers. `X-Request-ID` is accepted/returned for tracing. `/metrics` exposes request/error counters. Configure alerts for repeated 5xx responses, database failures, backup failures, elevated 401/429 rates, and Redis/Neo4j degraded health.

## PostgreSQL backup and restore

Use the provider's point-in-time recovery where available and take encrypted logical backups before releases/migrations:

```bash
pg_dump --format=custom --no-owner --file=synaptiverse.dump "$DATABASE_URL"
pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_DATABASE_URL" synaptiverse.dump
```

Never restore first into production. Restore into an isolated database, run `alembic current`, integrity checks, and critical-path tests, then document the recovery time and recovery point. Keep backups encrypted with restricted access and a retention period matching the approved policy.

## Deployment and rollback

Render runs `alembic upgrade head` before Uvicorn. CI independently applies migrations to a clean SQLite database, checks drift, runs backend tests, typechecks, and builds the frontend. Before a risky migration: capture a verified backup, review downgrade feasibility, deploy during a change window, and monitor health/error metrics. Prefer forward-fix migrations; restore only under the incident plan.

## Hosted topology decision

For the pitch: Render Free backend plus Neon Free PostgreSQL, with Redis and Neo4j optional/degraded. For any real pilot, move to paid services with contractual support, private/TLS connectivity, automated backups/PITR, separate migration-owner and restricted runtime database roles, monitoring, and an approved data-processing location.
