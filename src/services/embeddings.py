import logging
from sentence_transformers import SentenceTransformer
from src.schemas.candidate import ParsedResume
from src.schemas.job import JobDescription

logger = logging.getLogger(__name__)

# Initialize model once at module level.
# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_resume_embedding(parsed_resume: ParsedResume) -> list[float]:
    """
    Concatenate skills and experience descriptions into a single text block
    and return its vector embedding.
    """
    # Combine skills
    skills_text = "Skills: " + ", ".join(parsed_resume.skills)
    
    # Combine experience descriptions
    exp_text = "Experience: " + " ".join([exp.description for exp in parsed_resume.experience])
    
    full_text = f"{skills_text}\n{exp_text}"
    logger.debug(f"Generating embedding for resume (text length: {len(full_text)})")
    
    embedding = _get_model().encode(full_text)
    return embedding.tolist()

def generate_job_embedding(job_description: JobDescription) -> list[float]:
    """
    Concatenate job requirements into a single text block and return its vector embedding.
    """
    req_skills = "Required Skills: " + ", ".join(job_description.required_skills)
    pref_skills = "Preferred Skills: " + ", ".join(job_description.preferred_skills)
    
    full_text = f"{req_skills}\n{pref_skills}"
    logger.debug(f"Generating embedding for job (text length: {len(full_text)})")
    
    embedding = _get_model().encode(full_text)
    return embedding.tolist()
