import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import get_db
from src.config import get_settings
from src.models.base import Base
from src.models.resume import Resume

# We need a real PostgreSQL + pgvector DB for testing cosine_distance.
# We'll use the main database_url but run tests inside a rollback transaction.

engine = create_engine(get_settings().database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_match_prefilter_endpoint(client, db_session):
    # Insert two resumes with distinct embeddings.
    # all-MiniLM-L6-v2 has 384 dimensions.
    
    emb_match = [1.0] + [0.0]*383
    emb_no_match = [0.0] + [1.0] + [0.0]*382
    
    resume1 = Resume(
        source_filename="perfect.pdf",
        scrubbed_text="test",
        extracted_data={"skills": ["Python"]},
        embedding=emb_match
    )
    resume2 = Resume(
        source_filename="bad.pdf",
        scrubbed_text="test",
        extracted_data={"skills": ["Java"]},
        embedding=emb_no_match
    )
    db_session.add_all([resume1, resume2])
    db_session.commit()
    
    # Mock the embedding generator to return our perfect match embedding
    with patch("src.routers.match.generate_job_embedding", return_value=emb_match):
        payload = {
            "required_skills": ["Python"],
            "preferred_skills": [],
            "min_years_experience": 2.0,
            "education_requirement": None
        }
        response = client.post("/match/prefilter?top_n=2", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        matches = data["matches"]
        
        assert len(matches) == 2
        # The closest match should be ranked first
        assert matches[0]["source_filename"] == "perfect.pdf"
        assert matches[1]["source_filename"] == "bad.pdf"
