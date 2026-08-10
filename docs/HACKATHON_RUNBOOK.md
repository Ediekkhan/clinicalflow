# Hackathon Runbook

This profile is for a local presentation or judged demo only. It is not a production clinical deployment.

## Start the backend

```powershell
$env:APP_ENV = "hackathon"
$env:DATABASE_URL = "sqlite+aiosqlite:///./hackathon.db"
$env:AUTO_CREATE_SCHEMA = "true"
$env:ENABLE_HACKATHON_PROVIDERS = "true"
python -m uvicorn app.main:app --reload --port 8000
```

## Start the frontend

```powershell
cd frontend
npm run dev
```

The sandbox notification providers acknowledge email, SMS, push, WhatsApp, and storage events locally. They never contact external services and must not be used for real patient care.

## Demo journey

Patient signup -> symptom intake -> location-aware facility routing -> hospital acceptance -> same-hospital doctor assignment -> private notification -> nurse/doctor workflow.

Incomplete modules remain disabled rather than returning fabricated clinical or financial records.
