from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
