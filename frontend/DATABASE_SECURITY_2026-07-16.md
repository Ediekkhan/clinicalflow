# Database Migration and Tenant Security

## Schema workflow

Alembic is the authoritative schema mechanism for shared and deployed databases.

```bash
cd backend
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m alembic check
```

Local SQLite can retain `AUTO_CREATE_SCHEMA=true` for convenience. Deployed environments must use `AUTO_CREATE_SCHEMA=false` and run `alembic upgrade head` before starting the API.

## PostgreSQL tenant isolation

The initial migration enables RLS on `staff`, `auth_accounts`, `auth_sessions`, `tickets`, and `audit_logs`. Each policy applies the same tenant expression to both `USING` and `WITH CHECK`:

```sql
tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
```

Authenticated HTTP and WebSocket sessions derive the tenant from the opaque session token and execute `SET LOCAL app.current_tenant_id = :tenant_id` inside the database transaction. Tenant-prefixed random tokens allow the application to establish RLS context before looking up the hashed token; the prefix is routing context, not proof of authentication.

## PostgreSQL role requirement

The runtime API must connect with a dedicated non-owner role that does not have `BYPASSRLS`. Migration ownership should use a separate deployment role. PostgreSQL table owners normally bypass RLS, so using the migration owner as the runtime account would defeat the policies.

## Verification

- Clean SQLite upgrade reaches revision `20260716_0001`.
- `alembic check` reports no model/schema drift.
- Offline PostgreSQL generation verifies five `ENABLE ROW LEVEL SECURITY` statements and five policies containing `WITH CHECK`.
- API tests prove anonymous access is denied and a forged `x-tenant-id` cannot override session scope.

A live hosted-PostgreSQL deployment check remains part of production-readiness work because no PostgreSQL service is available in the local test environment.

