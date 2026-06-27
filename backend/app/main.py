from fastapi import FastAPI
from contextlib import asynccontextmanager

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}
