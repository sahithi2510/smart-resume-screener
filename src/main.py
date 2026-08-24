from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import resume, match

app = FastAPI(
    title="Smart Resume Screener API",
    description="Backend API for the Smart Resume Screener application",
    version="0.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only. Narrow this down in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(match.router)

@app.get("/")
def read_root():
    """
    Root API endpoint returning basic system health status.
    """
    return {
        "status": "ok",
        "app": "Smart Resume Screener API",
        "version": "0.1.0"
    }
