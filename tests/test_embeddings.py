import pytest
from src.services.embeddings import generate_resume_embedding, generate_job_embedding
from src.schemas.candidate import ParsedResume, Experience, Education
from src.schemas.job import JobDescription

def test_generate_resume_embedding_dimension():
    resume = ParsedResume(
        skills=["Python", "SQL"],
        experience=[
            Experience(
                title="Engineer",
                company="Acme",
                duration_months=24,
                description="Did stuff."
            )
        ],
        education=[
            Education(
                degree="BS",
                field="CS",
                institution="State Univ",
                graduation_year=2020
            )
        ],
        years_experience_total=2.0
    )
    embedding = generate_resume_embedding(resume)
    assert len(embedding) == 384
    assert isinstance(embedding[0], float)

def test_generate_job_embedding_dimension():
    jd = JobDescription(
        required_skills=["Python"],
        preferred_skills=["Docker"],
        min_years_experience=2.0,
        education_requirement="BS"
    )
    embedding = generate_job_embedding(jd)
    assert len(embedding) == 384
    assert isinstance(embedding[0], float)
