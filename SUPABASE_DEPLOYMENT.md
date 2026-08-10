# Supabase deployment

ClinicalFlow can use a Supabase project as its PostgreSQL database. The FastAPI service remains the API and authentication layer; the browser should never receive the database connection string.

## Backend environment

In the backend deployment service, set the Supabase **transaction pooler** connection string from `Project settings > Database > Connection string`:

```env
APP_ENV=production
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
AUTO_CREATE_SCHEMA=false
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
SESSION_SECRET=<random-value-at-least-32-characters>
CORS_ORIGINS=https://<your-vercel-domain>,http://localhost:3000,http://127.0.0.1:3000
```

The backend converts the PostgreSQL URL to the async SQLAlchemy driver automatically. Run migrations once from the `backend` directory before starting the API:

```bash
alembic upgrade head
```

Do not use the local `synaptiverse.db` or `hackathon.db` files in production. They are intentionally ignored by Git. The tracked source of truth for the database is `backend/migrations/`.

## Vercel environment

Set this public variable in the Vercel project settings and redeploy:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-backend-domain>
NEXT_PUBLIC_WS_BASE_URL=wss://<your-backend-domain>
```

The value must point to the deployed FastAPI service, not the Supabase dashboard URL and not `localhost`.

## Supabase checklist

1. Create the Supabase project and store the database password securely.
2. Run `alembic upgrade head` against the project database.
3. Deploy the backend with the production variables above.
4. Add the Vercel domain to `CORS_ORIGINS` and redeploy the backend.
5. Set `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_BASE_URL` in Vercel.
6. Verify `https://<your-backend-domain>/health` before testing signup.

Supabase Row Level Security is not a substitute for the API's tenant and role authorization. Enable and validate RLS policies before production use, while keeping the backend authorization checks enabled.
