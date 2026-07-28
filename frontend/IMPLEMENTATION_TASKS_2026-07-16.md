# Implementation Task List — 2026-07-16

The sequence below is ordered by dependency and production risk. Complete and verify one task before moving to the next.

## Phase 0 — Establish the baseline

- [x] **T01 — Audit frontend routes against implemented backend endpoints.** Deliverable: `PORTAL_API_AUDIT_2026-07-16.md`.
- [x] **T02 — Stabilize the current baseline.** Backend tests, frontend typecheck, and production build pass. See `BASELINE_VALIDATION_2026-07-16.md`.

## Phase 1 — Security and tenancy foundation

- [x] **T03 — Replace demo auth with persistent staff/patient sessions.** Database-backed accounts now use PBKDF2 password hashes, short-lived opaque access sessions, rotating refresh sessions, HttpOnly cookies, and logout revocation. PIN staff login is completed separately in T06.
- [x] **T04 — Enforce trusted tenant context.** Tenant scope now comes from persistent sessions, PostgreSQL transactions receive `app.current_tenant_id`, forged headers are ignored, and WebSockets require authentication. Patient record-level scoping remains in T07.
- [x] **T05 — Add PostgreSQL migrations and RLS.** Alembic owns the initial schema, tenant tables have read/write RLS policies and indexes, schema drift is clean, and isolation/migration generation are tested. Live hosted-PostgreSQL validation remains in T20.
- [x] **T06 — Wire all login surfaces and route protection.** Hospital and PIN gateways use persisted accounts, frontend portals enforce role hints, backend staff mutations enforce authoritative roles, refresh/logout remain active, and role redirects are wired.

## Phase 2 — Core operational engine

- [x] **T07 — Make ticket intake clinically useful.** Complaints and conservative symptom terms persist, ticket IDs are collision-safe, Nigerian phones normalize/validate, patient reads are phone-scoped, the live patient queue is real, and record access is audited.
- [x] **T08 — Implement duplicate-phone intake guardrail.** WhatsApp/SMS intake APIs now intercept active visits, return channel-specific intent menus, continue existing tickets, and create isolated family tickets linked by `account_group_phone`; the WhatsApp canvas includes a live simulator.
- [x] **T09 — Implement persistent provider scheduling.** Provider/slot/appointment models, RLS, live availability, row-locked booking/cancel/reschedule, emergency blocks, channel confirmation/cancellation, WebSocket updates, and persistent patient/staff UIs are complete. See `SCHEDULING_ENGINE_2026-07-16.md`.
- [x] **T10 — Finish real-time/offline consistency.** Authenticated tenant broadcasts, persistent idempotency receipts, optimistic versions/409 conflicts, pending-action deduplication, and authoritative reconnect reconciliation are complete. See `OFFLINE_SYNC_2026-07-16.md`.

## Phase 3 — Clinical rules and infrastructure

- [x] **T11 — Implement the Neo4j deterministic knowledge graph.** Neo4j is an optional auxiliary ontology with constraints/seed fixtures, parameterized read-only weighted traversal, persistent ticket decisions, conservative degraded-mode routing, and no PHI in the graph. See `KNOWLEDGE_GRAPH_2026-07-16.md`.
- [x] **T12 — Add Redis infrastructure.** Optional Redis now provides a shared clinical lexicon/config cache, fixed-window authentication/intake limits, source-deduplicated tenant WebSocket fan-out, health visibility, and tested process-local degradation. See `REDIS_INFRASTRUCTURE_2026-07-16.md`.

## Phase 4 — Complete product surfaces

- [x] **T13 — Complete patient workflows.** Dedicated `/my-visit`, shared-phone selection, authenticated dashboard/queue, persistent appointments/history/profile/card, and detailed booking confirmations are complete. See `PATIENT_WORKFLOWS_2026-07-16.md`.
- [x] **T14 — Complete nurse/clinic/hospital workflows.** Tenant-scoped dashboards, queues, providers/departments, scheduler, waiting-room data/TTS, settings, notifications, patient context, forced overtake, and degraded real-time behavior are complete. See `OPERATIONAL_PORTALS_2026-07-16.md`.
- [x] **T15 — Complete specialist workflow.** Authenticated patient assignment/status/escalation, specialty-scoped schedule and appointments, persistent notes/messages, derived earnings, notifications, settings, and interactive Kanban are complete. See `SPECIALIST_WORKFLOWS_2026-07-16.md`.
- [x] **T16 — Complete pharmacy, lab, HMO, MOH, and admin APIs/UI.** Every current sector/admin `EntityDashboard` resource now has an authorized persistent projection, admin-managed create/update records, proxy protection, health/audit views, and RLS. See `SECTOR_AND_ADMIN_PORTALS_2026-07-16.md`.
- [x] **T17 — Complete WhatsApp/SMS channel engines.** Signed Meta/normalized-SMS webhooks, provider verification/normalization, shared intake, interactive menus, live booking/cancellation, API-backed templates, and persistent delivery receipts are complete. See `CHANNEL_ENGINES_2026-07-16.md`.
- [x] **T18 — Complete public content and admin controls.** API-backed content, persisted lead capture, enforced/audited intake pause, channel controls, dependency health, audit browser, staff roster, and tenant views are complete. See `PUBLIC_AND_ADMIN_CONTROLS_2026-07-16.md`.

## Phase 5 — Production readiness

- [x] **T19 — Test the critical paths.** 55 backend tests plus four real-browser Playwright flows now cover login roles, booking, queue/escalation, scheduling, WebSockets, offline conflicts/replay, signed channels, and tenant/role isolation. See `CRITICAL_PATH_TEST_MATRIX_2026-07-16.md`.
- [x] **T20 — Add operational readiness.** Production config validation, NDPA-aligned retention/access guidance, structured request logs/IDs/metrics, auditable retention, backup/restore, migration-aware CI/deploy, and the Render+Neon pitch decision are complete. See `docs/deployment/OPERATIONS_AND_DATA_PROTECTION.md`.

## Phase 6 — Frontend/API convergence and experience

- [x] **T21 — Audit and wire frontend API consumption.** After backend completion, compare every backend endpoint against all frontend routes/components, wire endpoints into existing UI, and publish a precise list of endpoints that have no UI. Stop for approval before creating missing screens.
- [x] **T22 — Complete approved UI and UX consistency.** Shared public and portal shells now provide consistent navigation, loading/error/empty states, feedback, accessibility, and responsive behavior. See `UI_UX_CONSISTENCY_2026-07-16.md`.

## Definition of done for each task

- Behaviour is backed by persistent or explicitly documented stub data.
- Tenant and role authorization are tested for both allowed and denied access.
- Relevant backend tests and frontend typecheck/build pass.
- API contracts and local setup documentation are updated.
- No new placeholder action is presented as functional UI.
