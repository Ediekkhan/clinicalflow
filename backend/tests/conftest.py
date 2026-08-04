import os
from uuid import uuid4

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENABLE_TEST_FIXTURES", "true")
os.environ.setdefault("ENABLE_DEMO_CONTENT", "true")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:////tmp/clinicalflow-pytest-{uuid4().hex}.db")
