from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.job import JobDescription
from src.services.embeddings import generate_job_embedding
from src.models.resume import Resume

router = APIRouter(prefix="/match", tags=["Match"])

@router.post("/prefilter")
def prefilter_resumes(
    job_desc: JobDescription,
    top_n: int = Query(5, description="Number of top matches to return"),
    db: Session = Depends(get_db)
):
    """
    Two-stage approach for resume matching:
    1. Embedding Pre-filter (this endpoint): Fast, cheap vector similarity search 
       using SentenceTransformers + pgvector to find the top-N candidates.
    2. LLM Scoring: Only the top-N candidates are sent to the expensive/slower LLM
       for final rigorous evaluation and reasoning.
       
    This maintains high consistency and keeps API costs low.
    """
    try:
        job_embedding = generate_job_embedding(job_desc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate job embedding: {str(e)}")
        
    try:
        # Query top_n closest resumes by cosine distance
        closest_resumes = db.query(Resume).order_by(
            Resume.embedding.cosine_distance(job_embedding)
        ).limit(top_n).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
        
    results = []
    for r in closest_resumes:
        results.append({
            "id": r.id,
            "source_filename": r.source_filename,
            "extracted_data": r.extracted_data,
            # We omit embedding and scrubbed_text from the response to save bandwidth
        })
        
    return {"matches": results}
