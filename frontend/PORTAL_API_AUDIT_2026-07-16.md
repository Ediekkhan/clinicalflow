# Portal-to-API Audit — 2026-07-16

This audit correlates the product brief with the current frontend and backend. A route is **wired** only when the UI calls an implemented backend endpoint. A route is **partial** when some behaviour is live but data is generated, demo-only, or not persisted. A route is **placeholder** when it calls an endpoint that does not exist or only renders a static canvas.

## Implemented backend surface

| Backend route | Current status | Main consumers |
| --- | --- | --- |
| `POST /api/v1/auth/{role}/login` | Partial: in-memory patient and specialist demo accounts only; no token is issued | `/login`, `/specialist/login` |
| `GET /api/v1/auth/{role}/me` | Partial: returns a fixed demo profile without validating a session | Patient and specialist shells |
| `POST /api/v1/auth/refresh` | Placeholder: always succeeds and does not rotate a token | Shared frontend API client |
| `GET/POST /api/v1/tickets` | Wired to SQLite/PostgreSQL-compatible SQLAlchemy models | `/book`, `/clinic/queue`, nurse triage hook |
| `PATCH /api/v1/tickets/{id}` | Wired, including audit and WebSocket broadcast | Nurse triage hook |
| `PATCH /api/v1/tickets/{id}/escalate` | Wired, including audit and high-priority WebSocket broadcast | Nurse triage hook |
| `GET /api/v1/appointments/slots` | Partial: returns generated slots; no slot table | Booking and scheduler components |
| `PATCH /api/v1/appointments/slots/{id}/lock` | Placeholder: acknowledges but does not persist | Scheduler component |
| `GET /api/v1/patient/queue` | Partial: delegates to the tenant-wide ticket list, not the authenticated patient | Patient queue tracker |
| `POST /api/v1/patient/triage` | Placeholder: keyword/demo response; no Neo4j traversal | Patient triage chat |
| `POST /api/v1/channels/{whatsapp|sms}/intake` | Wired: duplicate detection, intent menu, continuation, and shared-phone ticket grouping | Channel simulator and provider webhook adapters |
| `WS /api/v1/ws/triage` | Partial: tenant room broadcast works, but connection authentication is absent | Nurse triage hook |

## Frontend portal matrix

| Portal | Frontend API pattern | Status | Missing backend work |
| --- | --- | --- | --- |
| Patient | `/auth/patient/*`, `/patient/*`, `/tickets` | Partial | Persistent auth; patient-scoped queue, dashboard, appointments, history, profile and card details |
| Specialist | `/auth/specialist/*`, `/specialist/*` | Partial | Dashboard, patients, status/escalation aliases, schedule, appointments, notes, earnings, messages, notifications and settings |
| Hospital | `/hospital/*` with specialist-profile fallback | Placeholder | Hospital login/profile plus dashboard, queue, appointments, specialists, departments, schedule, analytics, notifications, settings and waiting room |
| Clinic | `/clinic/*`; queue directly uses `/tickets` | Partial | Dashboard and all clinic resources except the generic queue ticket list |
| Pharmacy | `/pharmacy/*` | Placeholder | All pharmacy dashboard and resource endpoints |
| Lab | `/lab/*` | Placeholder | All lab dashboard and resource endpoints |
| Nurse | `/nurse/*`; primary triage screen uses `/tickets` | Partial | Nurse profile/dashboard and resource endpoints; generic triage actions themselves work |
| HMO | `/hmo/*` | Placeholder | All HMO dashboard and resource endpoints |
| MOH | `/moh/*` | Placeholder | All MOH dashboard and resource endpoints |
| Admin | `/admin/*` | Placeholder | Dashboard, users, hospitals, audit log, system health, settings and kill-switch controls |
| Public site | `/public/platform-stats`, `/public/pricing`, `/public/blog-posts`, `/public/testimonials` | Placeholder with frontend fallback content | Read-only public content endpoints |
| Notifications | `/notifications`, `/notifications/read-all`, `/notifications/{id}/read` | Placeholder | Notification persistence, listing and read state |

`EntityDashboard` constructs `/api/v1/{entity}/{view}` for most portal pages. None of those generic entity routes currently exist, so the displayed empty states are error fallbacks rather than successfully loaded empty datasets.

## Eleven required viewport status

| Requirement | Current implementation | Status |
| --- | --- | --- |
| `/` marketing and ROI calculator | Landing page and ROI component exist; public APIs are missing | Partial |
| `/book` patient booking | Form creates tickets and displays generated appointment slots | Partial |
| `/my-visit` live ticket | Redirects to `/dashboard/queue`; no dedicated ticket/shared-phone viewport | Placeholder |
| WhatsApp triage canvas | Static `/channels/whatsapp` representation | UI only |
| SMS templates | Static `/channels/sms` representation | UI only |
| `/auth/login` PIN gateway | PIN keypad exists; login button has no backend action | UI only |
| Nurse triage Kanban | Implemented through the nurse queue hook and generic ticket APIs | Wired/partial |
| Patient context drawer | Implemented and invokes ticket status actions | Wired/partial |
| Master scheduler | UI, generated slots, optimistic drag/lock; changes are not persisted | Partial |
| Admin settings | Generic dashboard empty state | Placeholder |
| Waiting room TV | Implemented at `/hospital/waiting-room`; requested path redirects there | Partial pending real hospital API |

## Architecture and security gaps

- Every business table does not yet carry `tenant_id` (only the currently defined tenant-owned tables do), and PostgreSQL RLS migrations/policies do not exist.
- Tenant identity is derived from persistent opaque sessions; public intake is pinned to `DEFAULT_TENANT_ID`. PostgreSQL RLS policies are still pending T05.
- Staff PINs and persistent staff authentication are not implemented.
- Redis is not configured or used for cache, rate limiting, or shared configuration.
- Neo4j settings exist, but schema, seed data, driver/service, and deterministic traversal do not.
- Appointment/provider availability has no relational model or transaction-safe booking workflow.
- WhatsApp and SMS webhook interceptors, duplicate-active-ticket menu flow, and shared-phone family workflow do not exist.
- Audit logging exists for ticket changes, but sensitive reads/auth/admin operations are not comprehensively audited.
