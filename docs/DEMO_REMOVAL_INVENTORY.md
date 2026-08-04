# Demo Removal Inventory

Date: 2026-07-28  
Branch: `feature/production-backend`

## Runtime inventory

| Location | Purpose | Production decision |
| --- | --- | --- |
| `app/main.py:lifespan` | Created demo accounts and schedules on startup | Restricted to `APP_ENV=test` with `ENABLE_TEST_FIXTURES=true`. |
| `app/services/auth_service.py:seed_demo_accounts` | Synthetic clinic, accounts and fallback credentials | Retained as a test fixture helper only; never called in normal startup. |
| `app/services/scheduling_service.py:seed_demo_schedule` | Synthetic clinician availability | Retained as a test fixture helper only. |
| `app/routes.py:staff/pin-login` | Shared PIN authentication | Returns 404 unless test fixtures are explicitly enabled. |
| `app/routes.py:hospital/account-login` | Hard-coded hospital-code authentication | Returns 404 unless test fixtures are explicitly enabled. |
| `app/routes.py:public/testimonials` | Static fictional testimonials | Replaced with an empty response. |
| `app/routes.py:default_tenant_id` usages | Compatibility ownership for legacy signup and test data | Must be replaced by real provisioning in Prompt 2; production startup does not create this tenant. |
| `app/services/demo_cleanup.py` | Legacy demo data classification | Exact-identifier manifest only; dry run never deletes records. |

## Test-only synthetic data

Test modules retain synthetic accounts, facilities, schedules, and credentials. They are
isolated from normal runtime through `tests/conftest.py`, which sets `APP_ENV=test` and
explicitly enables fixture loading. Test fixtures are not production demo content.

## Environment controls

Supported controls include `APP_ENV`, `ENABLE_TEST_FIXTURES`, `ENABLE_DEMO_CONTENT`, and
feature flags for laboratory, pharmacy, payer, government, imaging, and billing modules.
Production startup rejects demo/test flags, SQLite, automatic schema creation, insecure
cookies, weak session secrets, debug mode, default webhook secrets, and local origins.

## Cleanup command

```
python -m app.cli production audit-demo-data
python -m app.cli production remove-demo-data --dry-run
```

The manifest matches only the historical demo tenant UUID and exact legacy identifiers.
It reports related counts and a deletion order. It intentionally performs no deletion.
Any future destructive cleanup must require a verified backup, confirmed manifest ID, and
explicit non-test/non-unknown environment checks.

## Remaining blockers

- Legacy default-tenant signup compatibility must be removed as part of real account
  provisioning.
- Demo marketing request and public content records need an explicit product decision;
  they are not part of the clinical pilot workflow.
- Frontend demo-login pages and demo copy must be removed or feature-gated in a separate
  frontend cutover after backend production login is available.
