# Supabase, Render, and Vercel deployment

This runbook deploys ClinicalFlow as a three-part system:

- Supabase: managed PostgreSQL database
- Render: FastAPI backend and optional background worker
- Vercel: Next.js frontend

The browser must never receive the database URL, Supabase service-role key, session secret, provider secret, or signing key.

## 1. Prepare Supabase

Create or select the Supabase project and copy a PostgreSQL connection string from **Project settings > Database > Connection string**. Use the session pooler or direct connection for migrations. Use the transaction pooler for runtime traffic only when it is compatible with the deployment and migration strategy.

Use a URL-encoded password. For example, `@` becomes `%40`:

```env
DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<URL_ENCODED_PASSWORD>@<pooler-host>:5432/postgres?ssl=require
```

The application normalizes `postgresql://` and `sslmode=require` forms, but using the async driver form explicitly avoids ambiguity.

Run migrations from a trusted machine, never from the browser:

```bash
cd backend
export DATABASE_URL='postgresql+asyncpg://postgres.<project-ref>:<URL_ENCODED_PASSWORD>@<pooler-host>:5432/postgres?ssl=require'
export APP_ENVIRONMENT=staging
export AUTO_CREATE_SCHEMA=false
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m alembic check
```

PowerShell equivalent:

```powershell
cd backend
$env:DATABASE_URL = 'postgresql+asyncpg://postgres.<project-ref>:<URL_ENCODED_PASSWORD>@<pooler-host>:5432/postgres?ssl=require'
$env:APP_ENVIRONMENT = 'staging'
$env:AUTO_CREATE_SCHEMA = 'false'
$env:PYTHONPATH = (Get-Location).Path
python -m alembic upgrade head
python -m alembic check
```

Do not use `AUTO_CREATE_SCHEMA=true` against a shared or production database. The migration directory is the versioned source of truth.

## 2. Configure the Render backend

Create a Render Web Service from the repository and use the backend service in `render.yaml`.

Recommended settings:

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Build command | `pip install -r backend/requirements.txt` |
| Start command | `cd backend && python -m alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Root directory | repository root |

Set these in Render **Environment**. Values marked secret must not be committed:

```env
APP_ENVIRONMENT=production
DATABASE_URL=<Supabase PostgreSQL URL>
AUTO_CREATE_SCHEMA=false
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
SESSION_SECRET=<at least 32 random characters>
CORS_ORIGINS=https://<your-vercel-domain>
CHANNEL_WEBHOOK_SECRET=<random private webhook secret>
WHATSAPP_VERIFY_TOKEN=<private Meta verification token>
SKIP_PHONE_VERIFICATION=false
ENABLE_TEST_FIXTURES=false
ENABLE_DEMO_CONTENT=false
DEFAULT_CREDENTIALS_PRESENT=false
```

Add provider variables only when the provider is configured and verified. Examples include `REDIS_URL`, `REDIS_ENABLED`, email/SMS credentials, storage credentials, and payment webhook secrets. Never expose these as `NEXT_PUBLIC_*` values.

After saving variables, deploy the latest branch and confirm the logs show migrations completing and Uvicorn binding to Render's `$PORT`. Open:

```text
https://<your-render-service>.onrender.com/health
```

The free Render service may sleep after inactivity; the first request can be delayed while it wakes.

## 3. Configure the Vercel frontend

Create or select the Vercel project and set **Root Directory** to `frontend`.

| Setting | Value |
| --- | --- |
| Install command | `npm install` |
| Build command | `npm run build` |
| Output | Next.js default |

Set these public frontend variables in Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com
NEXT_PUBLIC_WS_BASE_URL=wss://<your-render-service>.onrender.com
```

Use `https://` and `wss://` in deployed environments. Do not set either variable to `localhost`, a Supabase dashboard URL, or a database connection string.

Add the final Vercel production origin, without a trailing slash, to the backend `CORS_ORIGINS`. Redeploy the backend after changing CORS and redeploy the frontend after changing Vercel variables.

## 4. Smoke test after deployment

1. Open the backend `/health` URL and confirm HTTP 200.
2. Open the Vercel site and confirm the landing page loads without a failed network request.
3. Register a test patient using a non-production test identity.
4. Confirm the browser request targets the Render API, not `localhost`.
5. Sign in and confirm the secure session cookie is present.
6. Submit triage with location permission granted and verify the API response contains routing information or a controlled no-facility result.
7. Check the Render logs for failed migrations, CORS errors, database errors, and unhandled 5xx responses.
8. Verify that no secret, database URL, OTP, or private patient data appears in the URL or frontend bundle.

## 5. Troubleshooting

### `404` at the Render root URL

The backend is an API service and may not define `/`. Use `/health` or an API route. A root `404` does not mean the service is down if `/health` returns 200.

### `Unable to reach the healthcare service`

Check the Vercel `NEXT_PUBLIC_API_BASE_URL`, Render service status, CORS origin, and browser Network tab. Confirm the URL includes the Render hostname and does not include a trailing `/api` unless the frontend configuration expects it.

### Migration failure

Read the first Alembic error, confirm the database URL points to the intended Supabase project, and run `alembic current` and `alembic heads` from a trusted environment. Do not bypass migrations by enabling automatic schema creation in production.

### Authentication or cookie failure

Use HTTPS, keep `AUTH_COOKIE_SECURE=true`, use an exact production CORS origin, and avoid testing a `__Host-` cookie on an insecure HTTP deployment. Log out and clear old cookies after changing cookie names or domains.

## Security rules

- Store secrets only in Render/Vercel environment settings or a secrets manager.
- Rotate any secret that was pasted into chat, screenshots, commits, or logs.
- Keep test fixtures, demo content, default passwords, and phone-verification bypasses disabled in production.
- Restrict Supabase database access to the backend service.
- Enable and validate PostgreSQL RLS policies in addition to API tenant authorization.
- Configure backups, point-in-time recovery, restore testing, monitoring, alerting, and incident ownership before a clinical pilot.
