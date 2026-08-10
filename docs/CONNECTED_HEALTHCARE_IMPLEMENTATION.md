# Connected Healthcare Implementation

Status: active implementation  
Source branch: `test_crasy`  
Feature branch: `feature/connected-healthcare`  
Reviewed: 2026-07-28

## Safety position

ClinicalFlow is an engineering implementation under validation. It is not medically
certified, legally approved, or ready for unsupervised production care. Clinical
terminology, routing weights, country policies, prescribing rules, laboratory
workflows, payer rules, and public-health disclosures require qualified professional
review before real patient use.

## Current architecture

- FastAPI and async SQLAlchemy provide the API and transactional service layer.
- Alembic supplies additive migrations with SQLite-compatible automated tests and
  PostgreSQL-oriented row-level security.
- Next.js App Router provides ten role-specific workspaces over shared APIs.
- Cookie-backed access and refresh sessions support personal accounts and selected
  staff workspaces.
- `StaffMembership` is the canonical facility authorization relationship.
- Typed registries cover patients, providers, facilities, services, payers, consent,
  provenance, and health-card credentials.
- Typed domain records cover appointments, encounters, referrals, laboratory,
  pharmacy, payer, public-health, country-policy, support-access, and outbox events.
- Redis/WebSocket integrations project account-specific events; durable notification
  and outbox rows remain the source for retries.

## Existing connected flow

```text
patient intake
  -> triage and terminology release
  -> severity, department, specialty and service
  -> capability-aware facility ranking
  -> destination queue
  -> same-facility eligible clinician and slot
  -> appointment transaction
  -> assigned-clinician private notification
  -> patient confirmation
```

Patient ownership is retained separately from the destination facility. An assigned
doctor must have an active, verified membership in the destination facility and
match the required department, specialty, privilege, duty, capacity, and slot.

## Target architecture

The platform is organized into shared bounded contexts:

1. Identity and registries.
2. Workforce, workspace selection, consent, and access.
3. Intake, terminology, triage, routing, acceptance, and queues.
4. Scheduling, check-in, and clinician assignment.
5. Encounters and longitudinal clinical records.
6. Diagnostics and imaging.
7. Medication and pharmacy.
8. Coverage, billing, and claims.
9. Public-health reporting.
10. Country policy, interoperability, audit, notifications, and platform operations.

Dashboards are projections of these shared resources. They must not create private,
role-specific copies of a patient record.

## Data model status

| Area | Status | Notes |
| --- | --- | --- |
| Staff memberships | Implemented foundation | Legacy `HospitalDoctorMembership` retained for reconciliation only. |
| Patient/provider/facility registries | Implemented foundation | External identity verification still needs production adapters. |
| Consent, break glass, provenance | Implemented foundation | Country-specific legal review remains required. |
| Capability routing | Implemented foundation | Live travel, bed, payer-network and accessibility feeds remain integrations. |
| Appointment assignment/outbox | Implemented foundation | Production concurrency must be verified on PostgreSQL. |
| Encounters/referrals/laboratory | Typed foundation | Clinical validation and fuller UI workflows remain. |
| Pharmacy/payer/public health | Typed foundation | External formularies, payer rails and national reporting remain. |
| Country packs/FHIR metadata | Typed foundation | Nigeria pack is configuration, not a compliance claim. |
| Clinical terminology | Versioned foundation | Import adapters and clinical publication operations remain next. |

Migrations are additive through `20260728_0024`. Existing tables are not dropped.
Legacy columns remain during compatibility and reconciliation periods.

## API boundaries

- Public APIs expose only published, public-safe terminology and facility data.
- Patient APIs require patient ownership or explicit consent.
- Facility APIs derive scope from the selected active membership.
- Clinician APIs require treatment relationship, department scope, privilege, and
  consent or audited emergency access.
- Payer APIs receive minimum-necessary financial and authorization data.
- Government APIs default to aggregated or de-identified jurisdiction-scoped data.
- Platform administrators have no routine patient-record access.
- Critical writes use transactions, idempotency or conditional locking, and outbox
  records where implemented.

## Permission matrix

| Actor | Permitted scope | Explicitly denied |
| --- | --- | --- |
| Patient | Own record, consent, card, appointments, results and bills | Other patients and staff operations |
| Doctor/specialist | Assigned/care-team patients in selected verified workspace | Unassigned and cross-facility records |
| Nurse | Assigned or department-authorized care tasks | Diagnosis/prescribing outside configured scope |
| Facility staff | Operational records in selected facility and department | Other facilities |
| Laboratory | Order, specimen and result minimum necessary data | Unrelated longitudinal record |
| Pharmacy | Prescription, allergy and interaction minimum necessary data | Complete patient record |
| Payer | Coverage, authorization and claim minimum necessary data | Unrestricted clinical notes |
| Government | Aggregates and legally authorized reports | Routine identifiable record browsing |
| Platform admin | Verification, policy, audit and technical health | Routine clinical-record access |

## Events and notifications

Clinical changes and their events should commit together. Durable outbox delivery
supports retry without reversing a completed clinical transaction. Account-specific
WebSocket delivery must never broadcast private appointment details to a department.

Core events include `triage.completed`, `facility.selected`, `patient.routed`,
`facility.accepted`, `appointment.requested`, `appointment.assigned`,
`appointment.accepted`, `appointment.rescheduled`, `appointment.cancelled`,
`patient.checked_in`, `patient.condition_escalated`, `critical_result.released`,
`prescription.signed`, `medication.dispensed`, `referral.accepted`,
`authorization.decided`, and `claim.adjudicated`.

## Dashboard responsibilities

- Patient: identity, triage, card, consent, appointments, queue, records, coverage.
- Doctor: assigned patients, encounters, notes, orders, prescriptions, referrals.
- Hospital/clinic: acceptance, queues, staffing, scheduling, capacity, transfers.
- Nurse: assigned queue, assessments, vitals, care tasks, handover, escalation.
- Laboratory: orders, specimens, worklist, results, review, critical acknowledgement.
- Pharmacy: validation, inventory, dispensing, counselling, delivery.
- Payer: members, eligibility, authorization, claims, appeals, payments.
- Government: registry, capacity, surveillance, reporting and jurisdiction controls.
- Platform admin: verification, terminology, country packs, security and system health.

## Migration plan

1. Keep migrations additive and preserve legacy compatibility fields.
2. Backfill and reconcile before disabling legacy writes.
3. Validate clean upgrades and downgrades in CI.
4. Rehearse PostgreSQL migrations against a restored production-like snapshot.
5. Back up before deployment and prefer application rollback over destructive schema
   downgrade when clinical records exist.

## Test plan

- Identity: duplicate matching, multi-facility workspaces and membership states.
- Authorization: facility, department, treatment, consent, break glass and audit.
- Routing: clinical suitability, emergencies, capacity, coordinates and overrides.
- Assignment: same-facility specialty matching, locks and private notification.
- Clinical services: referral, encounter, laboratory, pharmacy and payer lifecycles.
- Privacy: minimum necessary access, aggregate government access and admin denial.
- Frontend: normalized API responses, session refresh, role redirects and build.
- Infrastructure: PostgreSQL concurrency/RLS, Redis delivery, retries and recovery.

## Backward-compatibility risks

- Legacy membership and free-text department/specialty fields require reconciliation.
- SQLite tests do not prove PostgreSQL lock and RLS behavior.
- Generic operational endpoints remain compatibility surfaces and must not regain
  authority over typed clinical workflows.
- External terminology, messaging, payer, government and registry adapters are not
  production integrations.
- Frontend pages may compile before every typed workflow has complete interaction
  coverage.

## Phase checklist

- [x] Phase 1 architecture audit and this implementation document.
- [x] Phase 2 canonical membership and registry foundations.
- [x] Phase 3 patient identity, health card, consent and provenance foundations.
- [x] Phase 4 capability-aware routing foundation.
- [x] Phase 5 backend facility acceptance, rejection/redirection reasons, transition history, and validated queue-state machine.
- [ ] Phase 5 frontend acceptance, redirection, arrival, and check-in controls.
- [x] Phase 6 same-facility assignment and private notification foundation.
- [ ] Phase 7 complete nurse workflow and country-configured scope.
- [ ] Phase 8 complete encounter and longitudinal-record interfaces.
- [ ] Phase 9 complete referral/transfer and borrowed-specialist lifecycle.
- [ ] Phase 10 complete laboratory lifecycle UI and clinical governance.
- [ ] Phase 11 complete pharmacy lifecycle UI and formulary integration.
- [ ] Phase 12 imaging and radiology workflow.
- [ ] Phase 13 complete payer/billing lifecycle and integrations.
- [ ] Phase 14 complete government reporting integrations.
- [ ] Phase 15 complete platform operations.
- [ ] Phase 16 professionally reviewed country packs and interoperability adapters.
- [ ] Phase 17 complete frontend integration and accessibility coverage.
- [ ] Phase 18 production security and operational evidence.

## Next implementation boundary

The Phase 5 backend now records facility decisions and validates operational transitions. The next work is to connect hospital acceptance, redirection, arrival, and check-in controls to these APIs, then continue the Phase 7 nurse workflow.
