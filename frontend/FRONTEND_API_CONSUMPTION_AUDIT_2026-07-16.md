# Frontend/API Consumption Audit

## Summary

The backend exposes 50 route patterns (including health, metrics, and WebSockets). Most product reads and core mutations are consumed by existing frontend surfaces through direct API calls, shared API helpers, `EntityDashboard` dynamic routes, or provider webhook integrations.

During this audit, the existing notification UI was found calling four missing contracts. These are now wired:

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/read-all`
- `PATCH /api/v1/notifications/{id}/read`
- `WS /api/v1/ws/notifications`

Notification reads are persistent per account and patient results are phone-scoped.

## Consumed by existing UI

| Backend area | Existing frontend consumers |
| --- | --- |
| Auth login/profile/logout | Patient, specialist, hospital, PIN login pages; shells; auth context |
| Tickets/escalation/status | Booking workspace, patient visit, clinic queues, nurse Kanban/offline queue |
| Scheduling | Booking workspace, appointment scheduler, patient appointments, WhatsApp/SMS intake |
| Patient APIs | Dashboard, triage chat, queue tracker, appointments, history, settings, health card |
| Specialist reads/assignment/status/escalation | Specialist dashboards and interactive patient Kanban |
| Hospital/clinic/nurse projections | Existing operational portal pages and waiting-room screen |
| Sector/admin projections | Existing pharmacy, lab, HMO, MOH, and admin `EntityDashboard` pages |
| Public content/leads | Landing page, blog, ROI calculator, and demo form |
| Channel intake/templates | WhatsApp simulator and SMS template screen |
| Notifications | Specialist/hospital notification bells and notification view |

## Existing UI mutation wiring completed

The existing screens now consume their corresponding write contracts:

1. Specialist notes page → `POST /api/v1/specialist/patients/{ticket_id}/notes`, with assigned-patient selection.
2. Specialist messages page → `POST /api/v1/specialist/messages`.
3. Sector/admin record pages → `POST /api/v1/{entity}/{resource}` and `PATCH /api/v1/{entity}/{resource}/{record_id}`. Only records persisted through these contracts expose editing controls; projected clinical records remain read-only.
4. Admin settings → `POST /api/v1/admin/maintenance/retention`, with deletion counts shown after execution.

## Validation

- Backend: `58 passed`.
- Frontend: TypeScript check passed.
- Production build: all `109` routes generated successfully.

## Backend endpoints that intentionally have no product UI

These are machine/operations contracts and do not need a normal product screen:

- `GET /health` and `GET /metrics` — hosting probes and monitoring collectors.
- `GET /api/v1/webhooks/whatsapp` — Meta provider verification.
- `POST /api/v1/webhooks/{channel}` — provider-to-server callbacks.
- `POST /api/v1/auth/refresh` — invoked internally by the shared API client.

## No-UI candidates requiring user approval

No new standalone screen is strictly required for backend coverage after the existing mutation surfaces above are wired. A dedicated operations console for raw metrics, retention history, webhook deliveries, and provider diagnostics would be optional. Per the project instruction, it should not be created without explicit approval.
