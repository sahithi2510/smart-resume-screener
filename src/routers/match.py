import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.resume import Resume
from src.schemas.job import JobDescription
from src.schemas.scoring import ScoreRequest, ScoreResponse, ScoredCandidate
from src.services.embeddings import generate_job_embedding
from src.services.extractor import extract_job_description
from src.services.scorer import score_resume

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match", tags=["Match"])


@router.post("/prefilter")
def prefilter_resumes(
    job_desc: JobDescription,
    top_n: int = Query(5, description="Number of top matches to return"),
    db: Session = Depends(get_db),
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate job embedding: {str(e)}",
        )

    try:
        # Query top_n closest resumes by cosine distance
        closest_resumes = (
            db.query(Resume)
            .order_by(Resume.embedding.cosine_distance(job_embedding))
            .limit(top_n)
            .all()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database query failed: {str(e)}"
        )

    results = []
    for r in closest_resumes:
        results.append(
            {
                "id": r.id,
                "source_filename": r.source_filename,
                "extracted_data": r.extracted_data,
                # We omit embedding and scrubbed_text from the response to save bandwidth
            }
        )

    return {"matches": results}


@router.post("/score", response_model=ScoreResponse)
async def score_resumes(
    request: ScoreRequest,
    db: Session = Depends(get_db),
):
    """
    End-to-end scoring pipeline:

    1. **Extract** — parse raw JD text into a structured ``JobDescription`` (LLM).
    2. **Pre-filter** — find the top-N candidates via embedding similarity (pgvector).
    3. **Score** — evaluate each candidate against the JD with a dual-run,
       rubric-based LLM scorer; flag high-variance results.

    Results are sorted by ``overall_score`` descending.
    """
    # Step 1: Extract structured JD from raw text
    try:
        job_desc = await extract_job_description(request.job_description_text)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract job description: {e}",
        )

    job_data = job_desc.model_dump()

    # Step 2: Pre-filter via embedding similarity
    try:
        job_embedding = generate_job_embedding(job_desc)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate job embedding: {e}",
        )

    try:
        closest_resumes = (
            db.query(Resume)
            .order_by(Resume.embedding.cosine_distance(job_embedding))
            .limit(request.top_n)
            .all()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database query failed: {e}"
        )

    if not closest_resumes:
        return ScoreResponse(scored_candidates=[], job_description=job_data)

    # Step 3: Score each pre-filtered candidate
    scored_candidates: list[ScoredCandidate] = []

    for resume in closest_resumes:
        try:
            result, high_variance, run_scores = await score_resume(
                resume_data=resume.extracted_data,
                job_data=job_data,
            )
            scored_candidates.append(
                ScoredCandidate(
                    resume_id=resume.id,
                    source_filename=resume.source_filename,
                    overall_score=result.overall_score,
                    sub_scores=result.sub_scores.to_dict(),
                    matched_skills=result.matched_skills,
                    missing_skills=result.missing_skills,
                    justification=result.justification,
                    confidence=result.confidence,
                    high_variance=high_variance,
                    run_scores=run_scores,
                )
            )
        except Exception as e:
            # Log but don't fail the entire batch for one candidate
            logger.error(
                "scorer: failed to score resume %d: %s", resume.id, e
            )

    # Sort by overall_score descending
    scored_candidates.sort(key=lambda c: c.overall_score, reverse=True)

    return ScoreResponse(
        scored_candidates=scored_candidates,
        job_description=job_data,
    )
