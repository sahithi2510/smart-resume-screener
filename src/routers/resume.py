from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.parser import parse_document
from src.services.extractor import extract_resume
from src.services.embeddings import generate_resume_embedding
from src.models.resume import Resume

router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a resume document, parse it, extract structured data, generate embeddings,
    and store it in the database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename not provided")

    # 1. Parse document
    try:
        content = await file.read()
        parsed_doc = parse_document(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {str(e)}")
    
    # 2. Extract structured data and scrubbed text
    try:
        parsed_resume, scrubbed_text = await extract_resume(parsed_doc.raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract resume data: {str(e)}")
    
    # 3. Generate embedding
    try:
        embedding = generate_resume_embedding(parsed_resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")
    
    # 4. Insert into database
    try:
        db_resume = Resume(
            source_filename=file.filename,
            scrubbed_text=scrubbed_text,
            extracted_data=parsed_resume.model_dump(),
            embedding=embedding
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {
        "id": db_resume.id,
        "source_filename": db_resume.source_filename,
        "message": "Resume uploaded and processed successfully"
    }
