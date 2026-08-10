# Switching Between Local and Cloud Databases

The application uses one setting for both environments: `DATABASE_URL`. No code changes are required when switching.

## Local SQLite

Use this in `backend/.env`:

```env
DATABASE_URL=sqlite+aiosqlite:///./clinicalflow.db
AUTO_CREATE_SCHEMA=true
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
```

Then run:

```bash
cd backend
python -m pip install -r requirements.txt
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

SQLite is appropriate for one developer and a local demo. Do not deploy the SQLite file on a free Render web service: its filesystem is ephemeral and the database will disappear on restart or redeploy.

## Cloud PostgreSQL with Neon

1. Create a Neon Free project and copy its pooled connection string.
2. Set the connection string as `DATABASE_URL`. The backend automatically converts `postgres://` or `postgresql://` to SQLAlchemy's asyncpg scheme and converts `sslmode=require` to `ssl=require`.
3. Disable runtime schema creation and apply migrations:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
AUTO_CREATE_SCHEMA=false
```

```bash
cd backend
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m alembic check
```

To return to local development, restore the SQLite `DATABASE_URL` and set `AUTO_CREATE_SCHEMA=true`.

## Important data behaviour

- Local and cloud databases are separate datasets. Switching the URL does not copy data.
- Never commit a real cloud connection string or password.
- Use Neon for pitch data because its Free plan has no time limit; it currently provides 0.5 GB storage and 100 CU-hours per project.
- For a regulated production deployment, create separate migration-owner and non-owner runtime PostgreSQL roles so RLS cannot be bypassed. The pitch configuration is not authorization to store real patient health information.

## Quick verification after switching

```bash
curl https://YOUR-BACKEND.onrender.com/health
```

Then log in and verify the tenant-scoped API. A forged tenant header must have no effect:

```bash
curl -c /tmp/sv.cookies -X POST https://YOUR-BACKEND.onrender.com/api/v1/auth/patient/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+2348012345678","password":"Password123!"}'

curl -b /tmp/sv.cookies https://YOUR-BACKEND.onrender.com/api/v1/tickets \
  -H 'x-tenant-id: 22222222-2222-2222-2222-222222222222'
```

Sources: [Render free-service limitations](https://render.com/docs/free), [Render web-service deployment](https://render.com/docs/web-services), [Neon pricing](https://neon.com/pricing).
