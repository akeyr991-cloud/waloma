from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.auth import router as auth_router
from app.api.operations import router as operations_router
from app.core.config import settings
from app.api.system import router as system_router

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title=settings.app_name, version="1.0.0", description="WALOMA Association Management System API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")
app.include_router(system_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "frontend" / "index.html")


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "application": settings.app_name}
