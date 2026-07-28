# SynaptiVerse Global Healthcare Implementation Plan

Status: repository audit and implementation plan  
Branch audited: `test_crasy`  
Audit date: 2026-07-28

## Implementation progress

### Prompt 3 completed: capability-based patient routing

Implemented in migration `20260728_0020` and the associated backend/frontend changes:

- Replaced distance-first selection with clinical eligibility gates for facility status, intake state, coordinates, required service/specialty, verified on-duty coverage, capacity, and emergency capability for critical cases.
- Removed wrong-specialty slot fallback from routing.
- Added weighted suitability ranking where clinical readiness has greater influence than distance and patient preference cannot bypass safety gates.
- Added persisted routing decisions and accepted/rejected candidates with scores and reasons.
- Preserved patient ownership separately from the routed destination facility and existing destination queue visibility.
- Added explicit no-suitable-facility tickets and country-configurable emergency-message integration boundary instead of silently choosing a facility.
- Added suitable alternatives, required department, distance, emergency readiness, and selection reasoning to patient triage responses.
- Added hospital queue routing reasons and a detailed routing-decision endpoint.
- Added authorized manual override restricted to eligible candidates, requiring a reason and creating an audit event.
- Added compatibility backfill for existing seeded facility/service records.
- Added tests for wrong-specialty nearest facilities, farther suitable facilities, critical emergency readiness, capacity, inactive/missing-coordinate facilities, invalid/missing patient coordinates, no suitable facility, patient preference safety, manual override, and cross-country distance calculation.

Remaining production limits:

- Travel time, accessibility, patient transport, live bed capacity, payer networks, and patient preference profiles are not yet backed by trusted external feeds.
- Emergency instructions still require versioned country-pack configuration and clinical/legal review.
- Facility acceptance is represented as required in the queue response; a dedicated acceptance workflow belongs to the referral/encounter phase.
- Routing scores require clinical governance, calibration, monitoring, and jurisdiction-specific validation before production use.
### Prompt 2 completed: patient, provider, facility, and payer registries

Implemented in migration `20260728_0019` and the associated backend/frontend changes:

- Added canonical patient identities independent of phone number, duplicate-match metadata, deceased status, language, contact, address, and emergency-contact fields.
- Added multi-facility patient identifiers without duplicating the patient record.
- Added provider identity, professional role, licence jurisdiction/number, specialty, and verification status.
- Added configurable facility types, country/jurisdiction, hours, emergency capability, equipment, age groups, live capacity state, intake state, and searchable service/specialty capabilities.
- Added payer-plan registry types for HMO, insurer, government, employer, national fund, and self-pay configuration.
- Added purpose-aware patient consent directives, revocation, provenance records, and consent enforcement in clinician access.
- Preserved existing audited break-glass behavior when ordinary consent is unavailable.
- Added revocable, expiring health-card QR credentials containing only an opaque lookup token.
- Added authenticated clinician lookup and a QR display to the existing patient health-card UI.
- Added migration backfill for existing facilities, patients, providers, and default care-delivery consent.
- Added tests for identity matching, multiple facility identifiers, capability search, provider verification, consent enforcement, provenance, and secure QR lookup.

Remaining production limits:

- National identifiers are represented as hashes but country-specific issuance and verification adapters are not implemented.
- Facility service catalogues, equipment vocabularies, payer plan definitions, and licence authorities require country-pack configuration.
- QR lookup currently requires the issuer facility workspace; cross-network lookup needs an explicit trust and consent policy.
- PostgreSQL migration backfill, encryption key management, RLS policy design, and duplicate-merge workflows require staging and security review.
### Prompt 1 completed: unified staff memberships

Implemented in migration `20260728_0018` and the associated backend/frontend changes:

- `StaffMembership` is the canonical authorization relationship.
- Added normalized `Specialty` and `ClinicalPrivilege` models.
- Added UUID department/specialty references while retaining legacy text fields.
- Added a reconciliation link to `HospitalDoctorMembership`; the legacy table remains available for compatibility and is not used as the primary authorization source.
- Added deterministic legacy membership backfill where a destination facility has a department.
- Added selected-workspace enforcement for multi-facility staff.
- Added explicit compatibility selection for existing seeded demo staff accounts.
- Made professional account login independent of one facility tenant.
- Moved specialist reads and mutations to the selected verified workspace.
- Restricted specialist self-assignment by destination facility, department, and specialty.
- Added normalized department lookup by UUID, legacy name, or code during onboarding.
- Added visible active, pending approval, licence verification, suspended, inactive, and expired-invitation states.
- Added a responsive shared workspace selector.
- Added tests for multi-facility selection, suspended/unverified rejection, cross-department denial, expired invitations, and existing demo compatibility.

Verification after Prompt 1:

- 86 backend tests passed.
- Frontend TypeScript passed.
- ESLint completed with zero errors and ten pre-existing warnings.
- Production build completed for all 120 routes.

Remaining compatibility limits:

- `HospitalDoctorMembership` cannot be deleted until production reconciliation reports show no unresolved rows.
- Department and specialty text columns remain during dual-read migration.
- Clinical privileges are modeled and reusable checks are available, but role-specific privilege catalogues and admin grant/revoke screens still need policy decisions.
- PostgreSQL concurrency, RLS, and migration backfill behavior require staging validation with production-like data.
## Executive summary

SynaptiVerse is one shared healthcare platform with role-specific workspaces, not ten independent products. The repository already has a working foundation for patient intake, triage, coordinate-based facility routing, hospital queues, same-hospital clinician assignment, appointments, private notifications, multi-facility staff workspaces, and treatment-relationship record access.

The foundation should be preserved. The next work should consolidate membership and department identifiers, make routing capability-aware, introduce durable domain events and registries, and replace generic `OperationalRecord` resources with explicit clinical, laboratory, pharmacy, payer, referral, and public-health models. Production claims must remain limited until external services, country policy, clinical safety, privacy, and regulatory controls are independently reviewed.

## 1. Current architecture

### Runtime and deployment shape

- Backend: FastAPI, SQLAlchemy async sessions, Alembic migrations, SQLite-compatible tests, PostgreSQL-oriented row-level-security migrations, Redis/WebSocket integration boundaries, and structured audit logging.
- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS, role route guards, cookie-backed sessions, refresh-token retry, normalized list responses, and Playwright critical-path tests.
- Shared data model: tenants/facilities, accounts, sessions, tickets, providers, slots, appointments, notifications, staff memberships, onboarding applications, operational records, care-team assignments, and audit records.
- Multi-tenancy: most operational reads and writes are scoped by tenant or selected staff membership. PostgreSQL migrations enable RLS for protected tables, but application-layer and database-layer coverage is not yet uniform for every future resource.

### Existing connected workflow

```text
Patient intake
  -> triage and specialty selection
  -> patient coordinate validation
  -> active accepting facility routing
  -> hospital queue
  -> same-hospital department/specialty clinician matching
  -> slot reservation and appointment
  -> assigned-clinician and patient notifications
  -> consultation note and restricted patient-record access
```

### Authentication and workspace selection

- `AuthAccount` stores a personal identity and primary role.
- `AuthSession` stores hashed access/refresh tokens and an optional selected membership.
- `/staff/workspaces` and `/staff/workspaces/{membership_id}/select` support multi-facility staff.
- The frontend retries a request once after `/auth/refresh` and routes expired sessions to the appropriate login surface.
- `StaffMembership` checks verification, employment state, active dates, duty status, facility, department, role, and specialty.

## 2. Features already working

The following are implemented and covered by automated or browser tests:

- Patient, specialist, hospital, clinic, nurse, pharmacy, laboratory, HMO, government, and platform-admin signup entry points.
- Patient login, specialist login, hospital workspace login, staff PIN login, logout, refresh sessions, and role route guards.
- Staff invitations, registered-facility lookup, department lookup, membership approval, and workspace selection.
- Patient ticket creation from web/channel intake.
- Triage preview and three-level urgency classification.
- Coordinate validation and Haversine distance calculation.
- Filtering out inactive, non-accepting, intake-disabled, or coordinate-less facilities.
- Hospital queue, waiting-room, department, specialist, schedule, and appointment APIs.
- Same-hospital clinician enforcement using department, specialty, verified membership, active employment, on-duty state, capacity, and open slots.
- Atomic slot booking safeguards and appointment cancellation/rescheduling.
- Assigned-doctor-only detailed notification records and account-targeted WebSocket delivery.
- Patient appointment confirmation and notification delivery retry state.
- Treatment-relationship checks for clinician record access.
- Nurse section restrictions, care-team assignments, break-glass grants, and access audit events.
- Public booking, patient dashboard/queue/history/card, specialist queue/notes/messages, offline idempotency, channel webhook verification, and basic operational controls.
- Frontend API-list normalization before `.map()`, `.filter()`, or `.length`.

Current verification baseline:

- 84 backend tests pass.
- 5 Playwright critical-path tests pass.
- TypeScript and production build pass.
- 120 application routes compile.

## 3. Scaffolding and incomplete workflows

### Generic operational records

`OperationalRecord(entity, resource, title, description, status)` currently backs many clinic, nurse, laboratory, pharmacy, HMO, government, admin, settings, channel receipt, and notification-marker surfaces. It is useful scaffolding but cannot safely represent typed clinical or financial state.

It lacks:

- Resource-specific invariants and lifecycle constraints.
- Patient, encounter, order, performer, specimen, medication, coverage, claim, jurisdiction, and provenance foreign keys.
- Clinical terminology and units.
- Minimum-necessary disclosure controls.
- Version history and correction semantics.
- Strong prevention of invalid state transitions.

### Duplicate and weak relationships

- `HospitalDoctorMembership` overlaps `StaffMembership`.
- `Provider`, `Staff`, and `AuthAccount` partially overlap practitioner identity and employment.
- `department_id` and `specialty_id` are frequently free-text strings instead of foreign keys.
- `Tenant` combines organization, facility, and location concerns.
- `Ticket` still carries triage, routing, queue, assignment, and visit concerns that should eventually live in distinct resources.

### Routing limitations

The router correctly validates coordinates and chooses an eligible active facility, but it currently ranks distance before proving all clinical capabilities. `nearest_available_slot` may fall back to a provider with a different specialty. There are no explicit facility services, equipment, age/population restrictions, emergency capability, live capacity, network participation, accessibility, travel-time, or manual-override records.

### Clinical and sector gaps

Dedicated models and workflows are missing for:

- Patient/client registry and duplicate identity resolution.
- Facility, location, service, provider, practitioner, and specialty registries.
- Consent directives tied to purpose, grantee, resource scope, and revocation.
- Referral, transfer, encounter, diagnosis, allergy, observation, procedure, care plan, task, admission, and discharge.
- Laboratory orders, specimens, results, verification, correction, release, and critical-result acknowledgement.
- Prescriptions, inventory, substitution, dispensing, counselling, and controlled-medication logs.
- Coverage, eligibility, prior authorization, invoices, claims, denials, appeals, remittance, and payments.
- Government indicators, jurisdiction policies, de-identification, mandatory reports, and disclosure authority.
- Country packs, terminology bindings, FHIR profiles, and external interoperability adapters.

### Frontend gaps

- Many role pages are wrappers around `EntityDashboard` or `HospitalRecordsPage`, so they expose generic CRUD rather than domain workflows.
- Some public editorial/testimonial copy is still static content. It is not patient data, but should be CMS-backed if it is presented as current evidence.
- Not every screen has pagination, search, retry, unauthorized, low-bandwidth, and accessible keyboard behavior.
- There is no complete frontend for consent, referrals, encounters, laboratory lifecycle, dispensing, payer adjudication, public-health disclosure, or record-access history.
- API contracts are concentrated in broad route modules and generic records rather than versioned resource schemas.

## 4. Target architecture

### Architectural principles

1. Maintain one longitudinal patient record with provenance; do not copy full records between dashboards.
2. Use personal accounts plus explicit organization memberships and selected workspaces.
3. Authorize every clinical action by role, verified membership, facility, department, treatment relationship, consent, purpose, and country policy.
4. Store clinical changes in typed resources and emit durable events after successful transactions.
5. Give each workspace only the minimum data required for its responsibility.
6. Keep clinical, operational, financial, government, and platform-administration privileges separate.
7. Localize behavior through versioned country packs rather than hard-coded Nigerian assumptions.

### Proposed bounded contexts

- Identity and registries: patient, practitioner, organization, facility, location, service, identifier, duplicate resolution.
- Workforce and access: membership, role, department, specialty, licence, privilege, availability, care team, consent, break glass.
- Intake and navigation: triage, routing recommendation, facility acceptance, queue, referral, transfer.
- Scheduling: schedule, slot, appointment, check-in, cancellation, reminder.
- Clinical record: encounter, note, condition, allergy, observation, procedure, care plan, task, admission, discharge.
- Diagnostics: service request, specimen, observation/result, diagnostic report, imaging request/report.
- Medication: medication, prescription, dispense, stock, substitution, interaction, counselling.
- Coverage and finance: payer, plan, coverage, eligibility, authorization, invoice, claim, response, appeal, remittance.
- Public health: reportable event, aggregate, indicator, jurisdiction, disclosure.
- Platform: country packs, terminology, integration, feature flags, outbox, notification delivery, audit, support access.

### Event architecture

Add a transactional `DomainEvent`/`OutboxMessage` table written in the same database transaction as the clinical change. A background worker publishes events and records attempts without rolling back committed care.

Initial event vocabulary:

- `triage.completed`
- `facility.selected`
- `patient.routed`
- `facility.accepted`
- `appointment.requested`
- `appointment.assigned`
- `appointment.accepted`
- `appointment.rescheduled`
- `appointment.cancelled`
- `patient.checked_in`
- `encounter.started`
- `encounter.completed`
- `patient.condition_escalated`
- `lab_order.created`
- `critical_result.released`
- `prescription.signed`
- `medication.dispensed`
- `referral.created`
- `referral.accepted`
- `authorization.decided`
- `claim.adjudicated`
- `public_health_report.submitted`

Every event must contain an event ID, aggregate type/ID, tenant/workspace, actor account and membership, timestamp, schema version, correlation/causation IDs, classification, and a redacted payload. WebSocket, push, email, and SMS messages are projections of events, not the event store itself.

## 5. Database changes

### Phase A: normalize the foundation

- Make `StaffMembership` canonical.
- Add `department_id -> hospital_departments.id` as a new UUID column while retaining legacy text during migration.
- Introduce `Specialty` and `ProfessionalLicence` tables.
- Add clinical privilege and notification-preference tables rather than unvalidated JSON/text.
- Backfill `HospitalDoctorMembership` into `StaffMembership`, validate counts and conflicts, dual-read temporarily, then stop writes to the legacy table.
- Separate `Organization`, `Facility`, `Location`, and `HealthcareService` from `Tenant` through additive tables and compatibility views/adapters.
- Add a provider/practitioner registry linked to `AuthAccount`, identifiers, licences, specialties, and memberships.

### Phase B: identity, consent, and access

- Add `Patient`, `PatientIdentifier`, `PatientContact`, `IdentityMatch`, and merge history.
- Link tickets and appointments to `patient_id`; retain phone fields only for compatibility during backfill.
- Add purpose- and scope-aware `ConsentDirective`, grants, revocations, and policy versions.
- Generalize `CareTeamAssignment` into typed care-team participants.
- Add immutable `Provenance` and normalized `AuditEvent`.
- Add support-access approval and expiry records.

### Phase C: navigation and clinical care

- Add facility capabilities, services, equipment, populations served, intake state, capacity snapshots, payer networks, accessibility, and routing decisions.
- Add `FacilityAcceptance`, `Referral`, `Transfer`, and status histories.
- Add `Encounter`, `ClinicalNote`, `Condition`, `Allergy`, `Observation`, `Procedure`, `CarePlan`, `ClinicalTask`, `Admission`, `DischargeSummary`, and documents.
- Keep `Ticket` as an intake/queue resource; do not use it as the longitudinal record.

### Phase D: diagnostics, medications, payer, and reporting

- Add laboratory order, ordered test, specimen, accession, result, report, review, correction, release, and acknowledgement tables.
- Add medication, prescription, item, pharmacy order, dispense, inventory, movement, substitution, interaction, controlled-drug, delivery, and counselling tables.
- Add payer, plan, coverage, benefit, eligibility, authorization, invoice, claim, response, denial, appeal, remittance, and payment tables.
- Add jurisdiction, public-health indicator, aggregate, report, legal authority, and disclosure audit tables.

### Cross-cutting constraints

- Use UUID foreign keys, unique business constraints, status checks, optimistic versions, UTC timestamps, soft closure where medico-legal retention applies, and indexes matching tenant/workspace/date queries.
- Enforce same-facility membership and appointment invariants in service transactions and PostgreSQL constraints/triggers where practical.
- Apply RLS to every tenant/patient-scoped table.
- Encrypt or tokenize sensitive identifiers where operationally feasible.
- Never put clinical details in URLs, generic logs, analytics, SMS, or email subject lines.

## 6. API changes

Keep `/api/v1` compatibility while adding typed, versioned resources. Deprecate generic `/{entity}/{resource}` endpoints only after each frontend has moved.

Priority APIs:

- `/patients`, `/patients/{id}/summary`, `/patients/{id}/consents`, `/patients/{id}/access-history`
- `/staff/memberships`, `/staff/workspaces`, `/departments`, `/specialties`, `/privileges`
- `/facilities`, `/facilities/{id}/services`, `/capacity`, `/routing/recommendations`, `/facility-acceptances`
- `/referrals`, `/transfers`
- `/appointments`, `/encounters`, `/conditions`, `/observations`, `/care-plans`, `/tasks`
- `/laboratory/orders`, `/specimens`, `/results`, `/diagnostic-reports`
- `/prescriptions`, `/dispenses`, `/inventory`
- `/coverage`, `/eligibility`, `/authorizations`, `/claims`, `/appeals`
- `/public-health/aggregates`, `/reports`, `/indicators`
- `/events`, `/notifications`, `/notification-preferences`

Contract rules:

- Return explicit DTOs and paginated envelopes with stable metadata.
- Continue frontend normalization during the transition.
- Require idempotency keys for assignment, booking, dispensing, result release, authorization, claim submission, and transfers.
- Use conditional updates/version fields for concurrent acceptance.
- Return machine-readable error codes without sensitive details.
- Enforce authorization server-side; frontend role checks are usability controls only.
- Publish events only after transaction commit through the outbox.

## 7. Dashboard changes

- Patient: consent, triage, routing choice, appointments, queue, referrals, results, prescriptions, coverage, bills, discharge, follow-up, and access history.
- Doctor/specialist: assigned schedule and patients, restricted summary, encounters, diagnoses, notes, orders, prescriptions, referrals, alerts, and follow-up.
- Hospital: registration, services, capabilities, departments, verified workforce, intake acceptance, queue, appointments, admissions, transfers, capacity, billing, and analytics.
- Clinic: walk-ins, outpatient encounters, chronic care, procedures, referrals, follow-up, workforce, and analytics.
- Nurse: assignments, department queue, vitals, assessments, reconciliation, medication administration, tasks, handover, deterioration alerts, and visits.
- Pharmacy: signed prescriptions, validation, allergies/interactions, stock, substitutions, dispensing, counselling, delivery, and alerts.
- Laboratory: orders, collections, specimens, worklists, processing, review, results, corrections, critical acknowledgement, equipment/service state, and alerts.
- HMO/payer: members, coverage, eligibility, benefits, authorization, claims, appeals, contracts, payments, and utilization using minimum necessary data.
- Government: facility registry/licensing, service availability, capacity, aggregate surveillance, mandated reports, jurisdiction filtering, and outbreak alerts.
- Platform admin: organization/user verification, country packs, terminology, integrations, audit investigations, feature flags, security, jobs, and system health; no routine clinical-record browser.

Every migrated screen must include loading, empty, malformed-response, error, unauthorized, expired-session, retry, pagination, filtering, search, accessible forms, keyboard behavior, mobile layout, and low-bandwidth handling.

## 8. Permission matrix

| Role | Allowed | Restricted or prohibited |
| --- | --- | --- |
| Patient | Own identity, consent, care record, appointments, results released to patient, prescriptions, coverage, bills, access history | Other patients; unreleased or legally restricted material |
| Doctor/specialist | Assigned/care-team patients; clinically necessary sections; create signed clinical resources within privileges | Unassigned patients; another facility without referral/temporary privilege; payer/admin-only data |
| Nurse | Assigned or authorized department patients; nursing sections and tasks | Independent diagnosis/prescribing unless country privilege permits; unrelated records |
| Hospital/clinic coordinator | Queue, schedules, capacity, workforce, operational summary | Routine consultation-note content unless treatment role and purpose require it |
| Laboratory staff | Valid orders, specimen identity, relevant context, result workflow | Complete longitudinal record; unrelated orders |
| Pharmacy staff | Signed prescription, required demographics, allergies, coverage/stock context | Complete longitudinal record; unsigned orders |
| HMO/payer | Eligibility, authorization, claim evidence, contract/payment data | Unrestricted clinical record; changing clinical facts |
| Government | Aggregated/de-identified indicators and authorized mandatory reports | Ordinary patient browsing; cross-jurisdiction access |
| Platform admin | Technical configuration, verification, audits, system health | Routine patient-record access; support access without approval, purpose, and expiry |
| Break-glass clinician | Time-limited necessary record sections after reason and confirmation | Silent access, export, indefinite access, or access without alerts/audit |

Authorization inputs must include account, active selected membership, facility, department, specialty/privilege, treatment relationship, patient consent, purpose of use, resource sensitivity, jurisdiction, and emergency policy.

## 9. Migration strategy

1. Baseline and freeze schema assumptions with migration, contract, authorization, and rollback tests.
2. Add new normalized tables and nullable foreign keys without removing legacy columns.
3. Backfill in deterministic batches with reconciliation reports and duplicate/conflict queues.
4. Dual-write through one service layer; compare legacy and new projections.
5. Move read paths per dashboard behind feature flags.
6. Verify tenant isolation, row counts, orphan counts, state histories, performance, and rollback.
7. Stop legacy writes, retain read compatibility for a defined period, then remove generic/legacy structures in a later migration.

Required safeguards:

- Backup and restore rehearsal before production migration.
- No destructive migration in the same release as first new reads.
- Country- and tenant-scoped rollout.
- Idempotent backfills and resumable jobs.
- Data-classification review and retention mapping.
- Explicit rollback for code and schema; medico-legal records are archived, not casually deleted.

## 10. Test strategy

### Existing baseline to retain

- Full backend suite, migration-head checks, frontend typecheck/lint/build, and Playwright critical paths.

### Required additions

- Identity: duplicate detection, merge audit, multi-facility staff, workspace switching, invitation expiry, suspended/unverified membership.
- Authorization: cross-hospital/department denial, consent withdrawal, minimum-necessary sections, government aggregate-only, admin clinical denial, support expiry.
- Routing: required service/specialty, emergency capability, capacity, invalid/missing coordinates, no suitable facility, preference, manual override, farther-but-capable choice.
- Concurrency: duplicate identity creation, slot booking, assignment acceptance, result correction, dispensing, authorization, and claim submission.
- Clinical: encounter lifecycle, provenance, lab specimen/result/critical acknowledgement, prescription/dispense/partial fill, referral/transfer, temporary privileges.
- Privacy: redacted logs/events/messages, access audit completeness, break glass alerts/review, de-identification and small-cell suppression.
- Frontend: response normalization, refresh rotation, intended-route restoration, role login, all loading/empty/error states, keyboard/mobile behavior.
- Contract: OpenAPI snapshots, schema version compatibility, pagination, problem responses, idempotency, event schemas.
- Operations: outbox retry/dead-letter handling, Redis/WebSocket degradation, backup/restore, migration rollback, metrics without PHI.

### End-to-end journeys

1. Signup -> identity -> consent -> triage -> capable facility -> acceptance -> queue -> assignment -> private notification.
2. Check-in -> nurse assessment/vitals -> encounter -> diagnosis/care plan -> lab order -> critical result -> acknowledgement -> patient release.
3. Signed prescription -> pharmacy validation -> dispensing -> counselling -> patient medication history.
4. Referral -> destination acceptance -> transfer -> authorized record sharing -> outcome notification.
5. Eligibility -> authorization -> treatment -> claim -> adjudication -> payment/appeal.
6. Verified events -> de-identified aggregate -> jurisdiction-filtered government report -> disclosure audit.

## 11. Implementation phases

### Milestone 1: secure shared foundation

1. Consolidate staff membership reads/writes and normalize departments/specialties.
2. Add patient, provider, organization, facility, location, and service registries.
3. Add consent directives, provenance, expanded audit, and access-policy services.
4. Add capability/capacity-aware routing and explicit facility acceptance.
5. Add transactional outbox, personal notification subscriptions, acknowledgement, retries, and escalation.
6. Harden same-facility clinician assignment and remove wrong-specialty fallback.

Exit criteria: existing workflow preserved; legacy membership is read-only; capable facility selection is tested; only assigned clinician receives details; all access is audited.

### Milestone 2: clinical care and referrals

7. Nurse tasks and assessments.
8. Encounters and longitudinal clinical resources.
9. Referrals, transfers, teleconsultation, and temporary privileges.

### Milestone 3: diagnostic, medication, and payer workflows

10. Laboratory lifecycle.
11. Pharmacy lifecycle.
12. Imaging foundation.
13. Coverage, authorization, billing, claims, and appeals.

### Milestone 4: public health and internationalization

14. Government reporting and privacy controls.
15. Platform administration and approved support access.
16. Versioned country packs, starting with reviewed Nigeria configuration.
17. FHIR mappings, terminology services, OpenHIE/DHIS2 adapters, offline/low-bandwidth, and localization.
18. Production security, reliability, recovery, and pilot-readiness evidence.

Each phase ends with migrations, rollback notes, authorization review, backend tests, frontend tests, production build, updated documentation, and an explicit list of remaining scaffolding.

## 12. Risks and backward compatibility

### Decisions required before coding

- Canonical patient identity keys and duplicate-resolution authority.
- Whether facilities are tenants, organizations, locations, or a hierarchy of all three.
- Department and specialty terminology ownership.
- Consent defaults, minors/guardians, emergency exceptions, and revocation effects by country.
- Clinical capability scoring and emergency routing policy.
- Whether coordinators receive metadata after assignment; detailed patient data should remain assigned-team only.
- Notification retention, acknowledgement deadlines, escalation rules, and approved channels.
- National data residency, retention, lawful disclosure, and mandatory reporting.
- Terminology licences and supported national FHIR profiles.
- Payer minimum-necessary evidence and appeal requirements.
- Controlled-medication and e-signature policy.
- Support-access approval authority and incident review.

### Principal risks

- Migrating duplicate membership/provider identities may assign the wrong workspace if conflicts are not reconciled.
- Replacing free-text departments/specialties can break matching unless aliases are versioned and backfilled.
- Generic operational records may contain ambiguous values that cannot be safely auto-migrated.
- Routing based only on distance may send patients to a facility unable to treat them.
- Event payloads, logs, analytics, SMS, and email can leak PHI if classification/redaction is not centralized.
- Country packs can encode unsafe or unlawful defaults without local clinical, legal, privacy, and regulatory review.
- SQLite test success does not prove PostgreSQL RLS, locking, and concurrent transaction behavior.
- External Redis, email, SMS, push, WhatsApp, identity, terminology, HIE, and payer integrations need contract and failure testing.

Compatibility policy:

- Preserve `/api/v1` and current DTOs while introducing typed endpoints.
- Use adapters and dual-read/write flags instead of big-bang replacement.
- Preserve existing authenticated routes and working dashboards until their typed replacement passes parity tests.
- Never describe generic CRUD scaffolding as a completed clinical workflow.

## 13. Files inspected

Primary backend:

- `backend/app/models.py`
- `backend/app/routes.py`
- `backend/app/main.py`
- `backend/app/services/facility_routing.py`
- `backend/app/services/*`
- `backend/app/schemas/*`
- `backend/app/core/*`
- `backend/app/middleware/*`
- `backend/migrations/versions/20260716_0001` through `20260727_0017`
- All files under `backend/tests`

Primary frontend:

- All routes under `frontend/src/app`
- `frontend/src/components/entity/EntityDashboard.tsx`
- `frontend/src/components/HospitalRecordsPage.tsx`
- Authentication, signup, scheduling, patient, specialist, notification, shell, and landing components under `frontend/src/components`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/auth.ts`
- `frontend/src/lib/signup-config.ts`
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/hooks/*`
- `frontend/src/proxy.ts`
- `frontend/tests/e2e/critical-paths.spec.ts`
- `frontend/playwright.config.ts`

Supporting material:

- Existing repository documentation.
- Deployment/testing Markdown files copied into `frontend`.
- The attached architecture review, phased prompts, and master implementation specification.

## 14. Recommended next task

Proceed with Prompt 1 only: make `StaffMembership` the canonical workforce relationship, add normalized department/specialty references and privileges, migrate legacy memberships safely, preserve workspace selection, add authorization tests, and leave `HospitalDoctorMembership` available only through a compatibility adapter until reconciliation is proven.

Do not begin laboratory, pharmacy, payer, or government clinical workflows before the identity, membership, consent, event, and authorization foundations are stable.
### Prompt 4 completed: reliable doctor assignment and notifications

- Doctor assignment remains constrained to an active, verified, on-duty membership in the routed hospital, matching department and specialty, with an available unlocked slot and remaining capacity.
- Appointment assignment requests are persisted for eligible clinicians and expose only operational routing metadata until one clinician accepts.
- First acceptance locks the appointment and slot, assigns the accepting membership, and closes competing requests in the same transaction.
- Assigned appointment notifications are recipient-specific, durable, and paired with a restricted transactional outbox record that contains identifiers rather than clinical details.
- Assigned, reminder, and check-in notifications support explicit recipient acknowledgement in addition to read state.
- The specialist notification panel keeps acknowledgement-required items visible and routes appointment events to the existing schedule screen.
- Existing retry state for failed real-time delivery is preserved; notification delivery failure does not roll back a confirmed appointment.
- Migration `20260728_0021` adds acknowledgement fields, assignment requests, and transactional outbox storage with tenant security enabled for PostgreSQL.
### Prompt 5 completed: referrals, transfers, encounters, and records

- Added explicit referrals, transfers, encounters, care teams and members, notes, conditions, allergies, medication history, procedures, observations, care plans, tasks, and clinical documents instead of using tickets as a universal clinical container.
- Referral creation requires a registered patient, active destination, required capability and specialty, an active verified origin membership, and recorded patient consent.
- Only the destination facility can accept or reject a referral; rejection reasons, expiry, transfer handoff, encounter creation, provenance, and audit events are persisted.
- Visiting specialist support uses destination-approved, time-limited staff membership, clinical privilege, encounter, and care-team membership records.
- Patient consent withdrawal immediately closes the referral and revokes temporary cross-facility membership, privilege, and care-team access.

### Prompt 6 completed: laboratory workflow

- Added laboratory orders, ordered tests with optional LOINC mapping, specimens, collections, accessions, custody events, observations/results, diagnostic reports, quality reviews, corrections, and critical-result acknowledgements.
- Enforced clinician-only ordering and laboratory-tenant isolation across acceptance, collection, custody, result entry, correction, quality review, and release.
- Critical findings create a restricted doctor-specific notification and cannot be released to the patient until the ordering clinician acknowledges them.
- Final patient release requires an approved final report; released reports appear in the patient health-history timeline.
- Replaced ticket-derived laboratory request/result views with explicit laboratory overview, request, collection, specimen, worklist, critical-result, completed-report, and equipment/service API views.
- Added a functional lab request workspace for acceptance, specimen collection, preliminary result entry, critical flags, quality approval, and controlled patient release, plus a specialist referral creation and status workspace.
- Migration `20260728_0022` creates the clinical and laboratory domain tables and enables PostgreSQL row-level security.

### Prompt 7 completed: pharmacy workflow

- Added explicit medication, signed prescription, item, pharmacy order, inventory, stock movement, dispense, substitution, interaction, controlled-medicine, delivery, and counselling records.
- Prescribing requires an active verified facility membership and active `PRESCRIBE` privilege allowed by the selected country policy.
- Pharmacy responses expose dispensing context rather than a general patient record.
- Validation and dispensing enforce prescription and stock expiry, matching medication batches, remaining quantity, partial fills, transaction locks, and idempotency keys.
- Controlled medicines require witness and register references. Pharmacy endpoints do not permit silent dosage changes.

### Prompt 8 completed: payer workflow

- Added payer organizations, plans, coverage, benefits, provider contracts, eligibility requests/responses, prior authorizations, claims/items/responses, denial reasons, appeals, remittances, and reconciliation.
- Eligibility supports multiple active coverages, contract and benefit checks, self-pay fallback, coverage expiry, and an explicit rule that emergency care is not delayed by routine authorization.
- Claim creation requires a lawful basis and unique payer reference. Decisions and authorization denials require reasons and remain payer-tenant scoped.

### Prompt 9 completed: government and platform controls

- Added jurisdiction-scoped government access, mandatory disease reports, aggregates, national indicators, outbreak alerts, and disclosure logs.
- Government views are aggregate by default and suppress cells below the country-policy threshold.
- Identifiable reports require configured authority, a legal reference, a stated access basis, and a disclosure record.
- Platform support access is time limited, reason bound, facility approved, visible in audit data, and requires two distinct approvals for sensitive access.
- Platform administrators do not receive routine clinical-record access.

### Prompt 10 completed: country policy, interoperability, and offline support

- Added versioned country packs with a Nigeria-first policy and explicit local legal-review requirement.
- Country policy controls prescription validity and role eligibility, public-health suppression, emergency authorization behavior, localization, retention metadata, and result-release defaults.
- Added FHIR R4 mapping metadata for core clinical, facility, medication, payer, consent, and audit resources.
- Added per-user idempotent offline clinical task and observation queues with bounded replay, retry status, and validation.

### Final hardening status

- Migration `20260728_0023` creates pharmacy, payer, government, support-access, country-pack, interoperability, and offline tables and enables PostgreSQL row-level security.
- Typed sector routes are registered before compatibility routes, and generic `OperationalRecord` writes are disabled for pharmacy, laboratory, payer, and government clinical domains.
- API responses include request IDs and security headers; structured logs avoid request bodies.
- All 103 backend tests pass across isolated clean-database groups. Frontend lint and the 124-route production frontend build pass.
- Full production approval remains blocked by the items documented in `docs/PILOT_READINESS_REPORT.md`.