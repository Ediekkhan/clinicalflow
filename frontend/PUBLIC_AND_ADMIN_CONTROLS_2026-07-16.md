# Public Content and Administrative Controls

## Public surfaces

The marketing experience consumes live APIs for platform statistics, pricing, blog summaries, testimonials, and persisted demo/ROI lead capture. Public booking, patient intake, and channel webhooks remain separate operational contracts with rate limiting and validation.

## Tenant controls

`GET/PATCH /api/v1/hospital/settings` now matches the hospital settings UI. It exposes the persisted facility name, staff roster, SMS route, WhatsApp state, and global intake pause.

Only hospital administrators and platform administrators may change controls. Pausing intake is enforced by the public ticket creation path with HTTP 503, and every control change is audited. Read access remains available to authorized hospital staff.

## Administration

The admin portal provides tenant/facility records, account listings, audit history, dependency health, and settings through authenticated, tenant-scoped APIs. PostgreSQL remains the source of truth; Redis and Neo4j degraded states are visible without taking the core API offline.
