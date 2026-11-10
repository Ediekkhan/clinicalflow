import os
from uuid import uuid4

# Tests must never inherit database or schema-management settings from a
# developer's shell or backend/.env file. Every test run owns a fresh SQLite
# database and creates its schema during application startup.
os.environ["APP_ENV"] = "test"
os.environ["APP_ENVIRONMENT"] = "test"
os.environ["ENABLE_TEST_FIXTURES"] = "true"
os.environ["ENABLE_DEMO_CONTENT"] = "true"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
os.environ["DATABASE_URL"] = (
    f"sqlite+aiosqlite:////tmp/clinicalflow-pytest-{uuid4().hex}.db"
)
