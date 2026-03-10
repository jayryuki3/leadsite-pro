"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from routes.leads import router as leads_router
from routes.audit import router as audit_router
from routes.mockups import router as mockups_router
from routes.emails import router as emails_router
from routes.settings import router as settings_router
from routes.ai import router as ai_router
from routes.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    os.makedirs(os.path.join(os.path.dirname(__file__), "mockups"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "screenshots"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "exports"), exist_ok=True)
    yield


app = FastAPI(
    title="LeadSite Pro API",
    description="Local business lead generation & AI website builder",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "mockups")
if os.path.exists(static_dir):
    app.mount("/static/mockups", StaticFiles(directory=static_dir), name="mockups")

app.include_router(leads_router)
app.include_router(audit_router, prefix="/audit", tags=["audit"])
app.include_router(mockups_router, prefix="/mockups", tags=["mockups"])
app.include_router(emails_router, prefix="/emails", tags=["emails"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])
app.include_router(ai_router, prefix="/ai", tags=["ai"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "LeadSite Pro", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
