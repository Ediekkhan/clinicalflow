# Nurse, Clinic, and Hospital Operational Portals

## Live workflows

The three operational portals now share authenticated, tenant-scoped data from PostgreSQL:

- dashboards: active queue, critical load, booked appointments, provider roster, and recent ticket activity;
- queues: live tickets with urgency, status, complaint, clinical route, and optimistic/offline actions;
- people and departments: active providers, specialties, rooms, and department load;
- appointments and schedules: persistent providers, slots, bookings, locks, cancellations, and rescheduling;
- notifications: recent tenant queue events routed to the relevant portal screen;
- settings: the persisted tenant name, location, and operational status;
- patient context: raw intake, extracted symptoms, clinical route, and review/resolve actions;
- waiting room: public-safe ticket numbers, current room, next tickets, department counts, and browser TTS.

Nurse forced overtake persists a critical escalation, writes an audit event, increments the optimistic version, broadcasts the tenant event, and remains idempotent during offline replay.

## API design

Specialized queue, appointment, ticket, and waiting-room endpoints remain authoritative for mutations. Read-oriented portal pages use `GET /api/v1/{nurse|clinic|hospital}/{resource}` for operational projections over the same ticket, provider, slot, appointment, account, and tenant tables.

Supported resources are dashboard, queue, people/doctors/specialists, appointments, analytics, notifications, settings, schedule, patients, visits, vitals, care plans, and departments. Unsupported entities/resources return 404 instead of placeholder content.

## Authorization

Operational projections require an authenticated nurse, doctor, hospital administrator, or platform administrator. Tenant scope comes from the server-side session. Patient sessions receive 403 and cannot enumerate facility operations.

## Degraded behavior

PostgreSQL is required for operational state. Redis and Neo4j can degrade independently as documented: local WebSocket delivery and deterministic clinical fallback remain active on a single backend instance.
