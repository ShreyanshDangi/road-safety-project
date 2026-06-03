"""
main.py — Module 2: Duplicate / Fraud Checker
===============================================
Run with:
    uvicorn main:app --port 8000

API Docs:  http://localhost:8000/docs

Environment variables required:
    DATABASE_URL=postgresql://user:password@host:5432/dbname

Changes vs original:
  • Local SQLite + StaticFiles UI removed; all storage is PostgreSQL via shared.database
  • /ui static mount removed (no local HTML dashboard needed in integrated system)
  • python-multipart dependency no longer needed for file uploads (URLs are plain strings)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from shared.database import init_db

app = FastAPI(
    title="Module 2 — Duplicate & Fraud Checker",
    description=(
        "Detects duplicate road-damage reports using pHash + GPS proximity. "
        "Receives a Cloudinary image URL and damage_class from Module 1."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def startup():
    init_db()
    print("")
    print("✅  Module 2 is running!")
    print("📡  API  →  http://localhost:8000")
    print("📖  Docs →  http://localhost:8000/docs")
    print("")


@app.get("/")
def root():
    return {
        "module": "Module 2 — Duplicate & Fraud Checker",
        "status": "running",
        "docs":   "http://localhost:8000/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
