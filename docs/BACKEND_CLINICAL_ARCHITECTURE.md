# SynaptiVerse Backend Clinical Architecture

Date: 2026-07-28  
Branch audited: `test_crasy` working tree  
Clinical status: engineering implementation, not clinically validated

## Current architecture

The backend is a FastAPI application using SQLAlchemy async sessions, Alembic migrations, cookie-based access and refresh sessions, PostgreSQL tenant context/RLS support, SQLite development compatibility, Redis-backed event distribution with local fallback, and an optional Neo4j knowledge graph.

Routes are split into:

- `routes.py`: authentication, signup, tickets, triage, routing, appointments, notifications, patient and core portal APIs.
- `clinical_routes.py`: referrals, encounters, laboratory lifecycle, clinical notes, and result release.
- `sector_routes.py`: pharmacy, payer, government, country policy, interoperability metadata, support access, and offline replay.

The canonical workforce relationship is `StaffMembership`. Patient, provider, facility, consent, provenance, routing, assignment, outbox, longitudinal record, laboratory, pharmacy, payer, government, and country-policy tables exist through migration `20260728_0023`.

## Current data flow

1. Authenticated or channel intake submits free text and optional coordinates.
2. `KnowledgeGraphService.route()` normalizes text with `SYMPTOM_ALIASES`.
3. Neo4j is queried when configured; otherwise `fallback_route()` selects one of four broad condition groups.
4. The ticket stores extracted symptom keys, a broad matched-condition identifier, urgency, specialty, coordinates, and route.
5. Capability routing filters registered facilities, ranks suitable candidates, stores candidates/reasons, and selects a destination.
6. Scheduling assigns an eligible same-hospital clinician or creates limited assignment requests.
7. Notifications and transactional outbox events update the patient, assigned clinician, and authorized operations staff.
8. Subsequent encounters, laboratory orders, prescriptions, claims, and reports use dedicated domain records.

## Working features

- Access/refresh sessions, workspace selection, active verified memberships, privileges, duty state, and tenant isolation.
- Patient identity, consent directives, secure health-card lookup token, provenance, audit, and break-glass records.
- Coordinate validation and clinically constrained facility routing with stored candidate reasons.
- Atomic same-hospital doctor assignment, slot/capacity checks, private notifications, acknowledgement, and outbox storage.
- Referrals, temporary visiting privileges, encounters, care teams, notes, laboratory lifecycle, critical result acknowledgement, and patient release.
- Pharmacy dispensing controls, payer workflow, aggregate government reporting, support-access approval, country policy, and offline replay.
- WebSocket account targeting and Redis/local event fallback.

## Clinical terminology limitations

The current triage catalogue is intentionally small:

- Ten canonical symptom keys: chest pain, breathing difficulty, severe bleeding, fever, cough, headache, vomiting, dizziness, rash, and weakness.
- Nigerian Pidgin aliases exist for some symptoms.
- Four fallback groups: emergency red flag, acute systemic illness, dermatological complaint, and unclassified presentation.
- `possible_illness_for_route()` converts those broad groups into patient-facing possible-condition text.
- The optional Neo4j path returns specialty, urgency, and a condition identifier but has no repository-managed terminology releases or clinical publication workflow.

This is not a comprehensive medical catalogue or a validated diagnostic engine. Possible conditions are not persisted as confirmed diagnoses, and responses include a clinician-confirmation disclaimer.

## Placeholder and compatibility behavior

- `seed_demo_accounts()` and `seed_demo_schedule()` still support local development compatibility.
- Public pricing, blog, and testimonial APIs contain static product content; they are not clinical records.
- `OperationalRecord` remains for system controls, channel delivery receipts, notification compatibility markers, and platform-admin records. Generic writes for clinical sector domains are blocked.
- Several combined portal endpoints adapt typed data to existing frontend list/card envelopes.
- Some patient-summary sections still return empty arrays until dedicated encounter data is connected.

## Missing clinical models

- Versioned terminology releases, concepts, designations, relationships, and clinical content reviews.
- Structured patient-reported symptoms with onset, duration, severity, body location, negation, confidence, language, and extraction provenance.
- Versioned red-flag rules and triage protocols.
- Persisted triage decisions referencing terminology and protocol versions.
- Governed clinical-content publication, separation of duties, withdrawal, and rollback.
- Terminology import jobs, checksum/licence validation, and import reports.

## Authorization gaps

- Clinical-content editor, reviewer, translator, publisher, and country-administrator roles do not yet exist.
- No separation-of-duties control prevents a technical administrator from self-approving clinical content because clinical publishing does not yet exist.
- Terminology public-safe versus administrative response boundaries are not defined.
- Treatment-relationship checks exist for patient records, but future terminology administration needs separate non-PHI authorization.

## Duplicate and transitional models

- `HospitalDoctorMembership` remains as a compatibility model while `StaffMembership` is canonical.
- `Provider`, `ProviderRegistry`, and staff membership represent different scheduling, professional identity, and employment concerns and still require adapters.
- Ticket matched-condition strings coexist with explicit `ConditionRecord`; ticket values are triage categories, not confirmed diagnoses.
- `ClientMutation` and `OfflineClinicalMutation` serve legacy and typed offline flows respectively.

## Migration risks

- Existing ticket condition and symptom strings lack terminology version references.
- Alias normalization changes can alter matching behavior unless historical releases remain resolvable.
- Published terminology must be immutable; corrections require new releases and explicit activation.
- Licensed terminology content must never be committed without valid distribution rights.
- PostgreSQL search/index and transaction behavior must be tested independently of SQLite.
- Backfilling historical tickets must label their source as legacy and must not manufacture clinical certainty.

## Target modular backend

- `terminology`: releases, concepts, designations, relationships, search, import, and historical resolution.
- `symptom_intake`: language-aware extraction, negation, confirmation, structured observations, and uncertainty handling.
- `triage_protocols`: deterministic red flags, protocol evaluation, human review, and audited override.
- `facility_routing`: consumes required capabilities from a persisted triage decision.
- `clinical_content`: review, approval, publication, withdrawal, rollback, evidence, and safety metrics.
- Existing identity, facility, scheduling, clinical, laboratory, pharmacy, payer, and public-health modules remain authoritative for their domains.

## API boundaries

- Public terminology APIs expose active names, codes, safe definitions, designations, and relationships only.
- Authenticated clinician APIs may request richer terminology context.
- Administrative APIs expose draft/version/review metadata only to authorized content roles.
- Triage APIs preserve original text, return recognized symptoms for confirmation, and never return an automatic confirmed diagnosis.
- Routing APIs consume a triage decision identifier rather than trusting frontend specialty/capability fields.

## Event architecture

New durable events should use the existing outbox:

- `terminology.release_imported`
- `terminology.release_published`
- `terminology.release_retired`
- `clinical_content.review_requested`
- `clinical_content.approved`
- `clinical_content.withdrawn`
- `triage.symptoms_confirmed`
- `triage.decision_created`
- `triage.human_review_requested`
- `triage.override_recorded`

Event payloads contain identifiers and classifications, not unrestricted clinical text.

## Test strategy

- Model constraints, release immutability, historical resolution, language/country filters, and search normalization.
- Idempotent and interrupted imports with checksum and licence metadata.
- Negation, misspellings, local expressions, uncertainty, paediatric and pregnancy context.
- Deterministic red flags, priority ordering, protocol versions, and audited overrides.
- Routing based on persisted required capability and no-suitable-facility behavior.
- Content separation of duties, self-approval denial, publication, retirement, withdrawal, and rollback.
- PostgreSQL migration/RLS and concurrency tests plus frontend build and browser journeys.

## Phased order

1. Add versioned terminology and search while retaining the current fallback adapter.
2. Add safe import commands and migrate the ten existing symptoms into a clearly labelled local draft/reviewed release.
3. Add structured symptom intake and patient confirmation.
4. Add reviewable red-flag rules, triage protocols, persisted decisions, and human override.
5. Make facility routing consume persisted triage requirements.
6. Add governed clinical-content administration with separation of duties.
7. Connect every dashboard to the resulting shared records.
8. Complete clinical safety verification and `docs/CLINICAL_BACKEND_READINESS_REPORT.md`.

No phase may describe the platform as clinically validated, medically certified, or legally compliant without independent qualified review.
