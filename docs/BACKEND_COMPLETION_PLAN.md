# SynaptiVerse Backend Completion Plan

Date: 2026-07-28  
Working branch: `feature/backend-completion`  
Baseline commit: `40855a07141c7618bdbbae2c6da182b235576328`

## Branch comparison

Remote `test_crasy` and `feature/connected-healthcare` were fetched again and both
resolved to the baseline commit above. Their trees were identical. The completion
branch was created from `origin/test_crasy` without overwriting local work.

## Reproduced baseline

- Complete backend suite: 109 passed.
- Clean SQLite Alembic upgrade through revision `20260728_0025`: passed.
- Alembic downgrade from head to base: passed.
- Re-upgrade from base to head: passed.
- FastAPI startup and `/health`: passed.
- Redis: not configured; application reported `degraded-local`.
- Neo4j: not configured; application reported `degraded-fallback`.
- PostgreSQL RLS and concurrency: not executed because no PostgreSQL test service is
  configured in this environment.

## Current foundations

The backend already contains canonical staff memberships, patient/provider/facility
registries, consent and health-card credentials, capability-aware routing, facility
acceptance history, same-facility appointment assignment, private notifications and
outbox events, referrals, encounters, clinical records, laboratory, pharmacy, payer,
government, country packs, and versioned terminology/import foundations.

The API is split across `routes.py`, `clinical_routes.py`, `sector_routes.py`, and
`terminology_routes.py`. Migrations are additive through revision 25. The existing
models must be extended rather than recreated.

## Missing workflows

1. Complete account verification, recovery, MFA, lockout, and session/device lifecycle.
2. Provision approved organizations and their authorized administrators.
3. Replace caller-supplied document storage keys with private signed storage.
4. Persist structured reported symptoms, governed red flags, protocols, and decisions.
5. Complete facility acceptance UI, check-in, nursing assessment, and queue transitions.
6. Complete admission, bed, discharge, transfer, and visiting-specialist lifecycles.
7. Complete imaging and diagnostic lifecycle details.
8. Complete prescription signing, formulary, stock, and controlled-drug workflows.
9. Add typed billing/payment/refund infrastructure and provider adapters.
10. Add a durable worker and contract-tested notification/integration adapters.
11. Complete international government, country-policy, and FHIR boundaries.
12. Produce PostgreSQL, Redis, worker, security, load, backup, and recovery evidence.

## Authentication gaps

- Demo PIN and hospital-code login are not explicitly development-gated.
- Account records lack verification, lockout, MFA, and lifecycle timestamps.
- Refresh rotation revokes the old row but does not record token-family reuse attacks.
- No password reset/change lifecycle or session/device management API exists.
- OTP generation is coupled to signup and no provider abstraction delivers it.
- Production responses must never return verification secrets.
- Patient accounts still use the default tenant compatibility field; registry identity
  must remain canonical.
- Organization approval does not yet provision a complete usable administrator workspace.

## Security gaps

- CSRF protection for cookie-authenticated writes is incomplete.
- PostgreSQL RLS coverage and concurrent assignment/dispensing are not proven here.
- Audit events need complete authentication and privilege-change coverage.
- Secrets, key rotation, private storage, malware scanning, retention, and immutable
  audit operations require production implementations.
- Government, payer, platform support, and external notification minimum-necessary
  boundaries require broader authorization matrix tests.

## External integration gaps

Live OTP, email, SMS, WhatsApp, push, object storage, payment, payer, identity/licence,
WHO ICD, FHIR/OpenHIE, DHIS2, maps/travel-time, monitoring, and backup providers are
not configured. Automated tests must use explicit adapters and mocks; no production
readiness claim may be based on a mock.

## Migration risks

- Legacy membership/provider/free-text department and specialty fields still require
  reconciliation before removal.
- SQLite does not prove PostgreSQL locks, constraints, RLS, or transaction isolation.
- Clinical and financial tables require retention-aware rollback; destructive downgrade
  is unsuitable after real records exist.
- New authentication secrets and token-family fields require additive backfill and
  safe defaults for existing sessions.

## Ordered completion plan

1. Authentication and account lifecycle.
2. Organization, professional onboarding, and private documents.
3. Structured terminology-backed symptom intake and governed triage.
4. Facility acceptance, check-in, nursing, and assignment.
5. Encounters, admission, discharge, and referrals.
6. Laboratory, imaging, pharmacy, payer, billing, and payments.
7. Workers, notifications, and external adapters.
8. Government, country policy, and interoperability.
9. Security and production operations.
10. Final end-to-end acceptance and `COMPLETE_BACKEND_READINESS_REPORT.md`.

Each phase must retain a working migration head, pass focused and regression tests,
and document external or professional-review dependencies honestly.
