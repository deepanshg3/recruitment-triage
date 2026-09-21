from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import errors as api_errors
from app.api.routes import candidates as candidates_router
from app.api.routes import health as health_router
from app.api.routes import match as match_router
from app.core.config import settings
from app.db.database import init_db
from app.db.preflight import run_preflight

app = FastAPI(
    title=settings.app_name,
    description=(
        "Candidate triage API: deterministic candidate listing/filtering, "
        "recruiter shortlisting, and JD->retrieval->AI-screening via /match. "
        "AI endpoints require configured Gemini credentials and indexed "
        "embeddings; all other endpoints work without them."
    ),
    version="0.1.0",
)

# Minimal CORS for the future React (Vite) frontend during local development.
# Origins are configurable through settings.cors_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create SQLite database and tables on startup (no-op if they already exist).
init_db()

# Fail fast with a clear message if SQLite + sqlite-vec (vec0) cannot work on
# this runtime - e.g. a Python build whose sqlite3 module has no loadable
# extension support (Render's stock Python 3.13 image) and pysqlite3 is absent.
run_preflight()

api_errors.register_exception_handlers(app)

app.include_router(health_router.router)
app.include_router(candidates_router.router)
app.include_router(match_router.router)