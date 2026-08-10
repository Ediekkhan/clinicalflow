# Pharmacy, Lab, HMO, MOH, and Admin Portals

## Portal coverage

Every current `EntityDashboard` route for pharmacy, laboratory, HMO, Ministry of Health, and platform administration now resolves to an authenticated backend contract.

- Pharmacy: dashboard, prescriptions, inventory, patients, deliveries/dispensed log, analytics, notifications, and settings.
- Laboratory: dashboard, requests, results, collections, equipment, patients, analytics, notifications, and settings.
- HMO: dashboard, authorizations, claims, members/enrollees, facilities, payments, utilization, analytics, notifications, and settings.
- MOH: dashboard, facilities/hospitals, reports, surveillance, and settings.
- Admin: platform overview, users, hospitals, audit log, dependency health, and settings.

The views project existing PostgreSQL tickets, appointments, accounts, tenants, and audit events. Cross-sector records that are not represented by those core tables use the tenant-scoped `operational_records` table introduced by Alembic revision `20260716_0010`.

## Mutations

Administrators can create and update an operational record for any supported sector resource:

- `POST /api/v1/{entity}/{resource}`
- `PATCH /api/v1/{entity}/{resource}/{record_id}`

Records contain a title, description, and explicit status. Stored records are returned ahead of derived records in their relevant portal view.

This generic MVP record layer is appropriate for catalog/configuration workflow data. Domain-specific clinical or financial transaction models should replace it before claims adjudication, dispensing, laboratory result signing, or payment settlement are treated as regulated production workflows.

## Authorization

All five portal families are protected in both the Next.js proxy and backend. The current MVP grants access to the authenticated administrator role. Patient and other unauthorized sessions receive 403. Backend tenant scope comes from the persistent server-side session, and `operational_records` has PostgreSQL RLS.
