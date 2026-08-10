# Specialist Workflows

## Completed workflow

- The specialist dashboard derives assigned-patient, being-seen, appointment, and critical-load metrics from persistent records.
- The patient Kanban lists tenant tickets, supports explicit self-assignment, and permits status changes only after assignment.
- Escalation uses the shared audited, idempotent critical escalation path and broadcasts live updates.
- Appointments and schedule views are scoped to providers matching the specialist's configured specialty.
- Consultation notes persist against an assigned ticket and the authenticated specialist.
- Secure messages persist against the authenticated specialist account.
- Earnings are derived from completed appointments using the MVP consultation fee; no financial ledger is implied.
- Notifications derive from current patient activity, while settings expose the persisted specialist identity and specialty.

## Authorization

Every `/api/v1/specialist/*` workflow requires a persistent account whose authoritative role is `specialist`. Assignment prevents one specialist from taking a ticket already owned by another. Status and note mutations require the ticket to be assigned to the current specialist.

Tenant scope comes from the authenticated session and PostgreSQL RLS applies to the new notes and messages tables.

## Persistence

Alembic revision `20260716_0008` adds specialist ticket assignment, consultation notes, and messages. Revision `20260716_0009` repairs the assignment foreign key for SQLite while PostgreSQL receives the foreign key directly in `0008`.

The specialist API includes:

- `GET /api/v1/specialist/{dashboard|queue|patients|appointments|schedule|notes|messages|earnings|notifications|settings}`
- `PATCH /api/v1/specialist/patients/{ticket_id}/assign-self`
- `PATCH /api/v1/specialist/patients/{ticket_id}/status`
- `PATCH /api/v1/specialist/patients/{ticket_id}/escalate`
- `POST /api/v1/specialist/patients/{ticket_id}/notes`
- `POST /api/v1/specialist/messages`
