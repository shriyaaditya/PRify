import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api import github

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB, clients, etc.
    yield
    # Cleanup

app = FastAPI(
    title="PRify API",
    description="AI-powered GitHub Pull Request Review System",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(github.router, prefix="/api/github", tags=["github"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}

