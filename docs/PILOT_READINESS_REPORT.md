# ClinicalFlow Pilot Readiness Report

Date: 2026-07-28  
Scope: Prompts 1-10 and final hardening review  
Decision: **Not approved for unsupervised production clinical use**

## Executive summary

The repository now contains typed foundations and guarded workflows for workforce membership, patient identity and consent, facility routing, doctor assignment, referrals, clinical records, laboratory operations, pharmacy dispensing, payer operations, public-health reporting, country policy, interoperability metadata, and offline mutation replay.

This is suitable for continued engineering validation and a controlled non-production pilot rehearsal. It is not evidence of legal compliance, clinical certification, production security accreditation, or regulatory approval. Nigerian country-pack values explicitly require review by qualified local legal, privacy, clinical, payer, pharmacy, laboratory, and public-health authorities.

## Implemented controls

- Authenticated, tenant-aware API access and selected staff workspaces.
- Active and verified membership, specialty, privilege, schedule, capacity, and slot checks for clinical assignment.
- Haversine facility routing with active facility, coordinate, capability, and acceptance filtering.
- Recipient-specific appointment and critical-result notifications with durable outbox records.
- Explicit referral, encounter, care-team, consent, laboratory, pharmacy, payer, and public-health records.
- Pharmacy partial fills, expiry and stock checks, idempotent dispensing, and controlled-medicine witness/register requirements.
- Payer eligibility, emergency-care continuation messaging, authorization reasons, duplicate claim protection, decisions, and appeals.
- Aggregate public-health access by jurisdiction, small-cell suppression, legal-authority checks, and disclosure records.
- Temporary platform support access with reason, expiry, facility approval, and dual approval for sensitive access.
- Versioned country packs and FHIR R4 resource mapping metadata.
- Offline clinical task and observation queues with per-user idempotency, retry status, and controlled replay.
- Request IDs, structured request logs, security headers, migrations, indexes, pagination limits, and PostgreSQL RLS enablement.
- Generic clinical-domain writes through `OperationalRecord` are disabled; typed APIs are authoritative.

## Verification evidence

- Migration tests: passed, including clean revision `20260728_0023` and PostgreSQL RLS SQL generation.
- Prompt 7-10 focused tests: 4 passed.
- Representative startup and portal authorization tests: 4 passed.
- Frontend production build: passed, 124 routes generated.
- Frontend lint: 0 errors, 10 warnings.
- Complete backend suite: 103 tests passed across four isolated clean-database groups covering all 28 backend test files.

## Blocking work before a live pilot

1. Run the full suite in CI with PostgreSQL, Redis, concurrent booking/dispensing tests, and deterministic per-test database isolation.
2. Complete independent threat modelling, penetration testing, dependency review, secret rotation, and infrastructure hardening.
3. Configure and verify encrypted production storage, backups, point-in-time recovery, restore drills, key management, and retention deletion jobs.
4. Obtain local legal and regulatory review for consent, minors, emergency use, disclosure, retention, controlled medicines, payer adjudication, and mandatory reporting.
5. Validate clinical terminology licences, national profiles, laboratory reference ranges, pharmacy formulary rules, and decision-support content.
6. Integrate and contract-test real email, SMS, push, WhatsApp, FHIR/OpenHIE, DHIS2, payer, identity, and terminology services.
7. Add accessibility testing with assistive technology and field tests for low-bandwidth/offline conflict resolution.
8. Establish incident response, breach handling, support-access review, on-call ownership, escalation paths, and clinical safety monitoring.

## Deployment and recovery gates

- Apply Alembic migrations in staging and take a verified backup before production migration.
- Run smoke tests for login, workspace selection, routing, appointment assignment, lab release, dispensing, eligibility, and notifications.
- Monitor error rate, outbox backlog, notification retries, database locks, queue latency, and audit-log continuity.
- Roll back application code first when possible. Database downgrade must be tested on a restored copy; do not drop clinical-domain tables containing live records.
- Recovery is accepted only after a restore drill proves authentication, tenant isolation, clinical records, audit history, and outbox state are intact.

## Pilot recommendation

Use a supervised staging rehearsal with synthetic data and named clinical, privacy, security, and operational owners. Do not enter real patient data or make real care, dispensing, payment, or public-health decisions until all blocking gates are signed off.
