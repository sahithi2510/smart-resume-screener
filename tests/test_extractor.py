"""
tests/test_extractor.py

Mocked unit tests for extractor.extract_resume() and extract_job_description().

The Google GenAI client is patched via unittest.mock so no real API key or
network call is needed. Each test constructs a fake GenerateContentResponse
where `.parsed` holds a Pydantic model instance or dict matching the shape
the real SDK returns when response_schema is set.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.extractor import extract_resume, extract_job_description, ExtractionError
from src.schemas.candidate import ParsedResume, Experience, Education
from src.schemas.job import JobDescription


# ---------------------------------------------------------------------------
# Settings fixture — prevents import-time .env requirement
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_settings():
    """
    Patch get_settings() for every test so no real .env is needed.
    The extractor calls get_settings() lazily, so patching it here is sufficient.
    """
    fake = MagicMock()
    fake.google_api_key = "test-key"
    fake.llm_model = "gemini-3.5-flash"
    with patch("src.services.extractor.get_settings", return_value=fake):
        yield


# ---------------------------------------------------------------------------
# Fake SDK response builder
# ---------------------------------------------------------------------------

def _make_response(parsed_obj):
    """
    Build a minimal fake GenerateContentResponse where `.parsed` is the
    supplied object (a dict or Pydantic model instance).
    """
    response = MagicMock()
    response.parsed = parsed_obj
    candidate = MagicMock()
    candidate.finish_reason = "STOP"
    response.candidates = [candidate]
    return response


def _make_parsed_resume(data: dict):
    """Validate a dict into a ParsedResume for use as the fake .parsed value."""
    return ParsedResume.model_validate(data)


def _make_parsed_jd(data: dict):
    """Validate a dict into a JobDescription for use as the fake .parsed value."""
    return JobDescription.model_validate(data)


# ---------------------------------------------------------------------------
# Valid fixture data
# ---------------------------------------------------------------------------

_VALID_RESUME_INPUT = {
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "experience": [
        {
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "duration_months": 24,
            "description": "Built REST APIs.",
        }
    ],
    "education": [
        {
            "degree": "Bachelor of Science",
            "field": "Computer Science",
            "institution": "State University",
            "graduation_year": 2020,
        }
    ],
    "years_experience_total": 2.0,
}

_VALID_JD_INPUT = {
    "required_skills": ["Python", "SQL"],
    "preferred_skills": ["Docker", "Kubernetes"],
    "min_years_experience": 3.0,
    "education_requirement": "Bachelor's",
}


# ---------------------------------------------------------------------------
# extract_resume — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_resume_happy_path():
    """Mock returns a valid parsed object → ParsedResume validates successfully."""
    parsed = _make_parsed_resume(_VALID_RESUME_INPUT)
    response = _make_response(parsed)

    with patch("src.services.extractor.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=response)

        result = await extract_resume("Jane Doe\nSkills: Python\nExperience: 2 years at Acme.")

    assert isinstance(result, ParsedResume)
    assert "Python" in result.skills
    assert result.experience[0].company == "Acme Corp"
    assert result.years_experience_total == 2.0


# ---------------------------------------------------------------------------
# extract_resume — retry path (bad first → valid second)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_resume_retry_success():
    """
    First call returns an invalid parsed object (duration_months is a string).
    Second call returns a valid one.
    Asserts the function succeeds after one stateless retry.
    """
    # Construct a MagicMock that mimics a ParsedResume but has bad data so
    # model_validate raises ValidationError when we call model_dump() on it.
    bad_parsed = MagicMock()
    bad_parsed.model_dump.return_value = {
        **_VALID_RESUME_INPUT,
        "experience": [
            {
                "title": "Engineer",
                "company": "Corp",
                "duration_months": "twenty-four",  # invalid — should be int
                "description": "Did stuff.",
            }
        ],
    }

    good_parsed = _make_parsed_resume(_VALID_RESUME_INPUT)

    bad_response = _make_response(bad_parsed)
    good_response = _make_response(good_parsed)

    with patch("src.services.extractor.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(
            side_effect=[bad_response, good_response]
        )

        result = await extract_resume("Backend engineer resume text.")

    assert isinstance(result, ParsedResume)
    assert result.experience[0].duration_months == 24
    assert instance.aio.models.generate_content.call_count == 2


# ---------------------------------------------------------------------------
# extract_resume — exhausted retries → ExtractionError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_resume_exhausted_retries_raises():
    """Both calls return invalid output → ExtractionError is raised."""
    bad_parsed = MagicMock()
    bad_parsed.model_dump.return_value = {
        **_VALID_RESUME_INPUT,
        "years_experience_total": "not-a-float",
    }
    bad_response = _make_response(bad_parsed)

    with patch("src.services.extractor.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=bad_response)

        with pytest.raises(ExtractionError):
            await extract_resume("Some resume text.")

    # Should have tried exactly MAX_RETRIES + 1 = 2 times
    assert instance.aio.models.generate_content.call_count == 2


# ---------------------------------------------------------------------------
# extract_resume — response.parsed is None → ExtractionError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_resume_no_parsed_raises():
    """If response.parsed is None (model refused), ExtractionError is raised immediately."""
    response = _make_response(None)

    with patch("src.services.extractor.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=response)

        with pytest.raises(ExtractionError, match="did not return a parseable JSON object"):
            await extract_resume("Resume text.")


# ---------------------------------------------------------------------------
# extract_job_description — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_job_description_happy_path():
    """Mock returns a valid parsed object → JobDescription validates successfully."""
    parsed = _make_parsed_jd(_VALID_JD_INPUT)
    response = _make_response(parsed)

    with patch("src.services.extractor.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=response)

        result = await extract_job_description(
            "We are looking for a Python/SQL engineer with 3+ years experience."
        )

    assert isinstance(result, JobDescription)
    assert "Python" in result.required_skills
    assert result.min_years_experience == 3.0
    assert result.education_requirement == "Bachelor's"


# ---------------------------------------------------------------------------
# extract_job_description — retry path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_job_description_retry_success():
    """First JD call invalid (min_years_experience wrong type), second valid."""
    bad_parsed = MagicMock()
    bad_parsed.model_dump.return_value = {
        **_VALID_JD_INPUT,
        "min_years_experience": "three",  # invalid — should be float
    }
    good_parsed = _make_parsed_jd(_VALID_JD_INPUT)

    bad_response = _make_response(bad_parsed)
    good_response = _make_response(good_parsed)

    with patch("src.services.extractor.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(
            side_effect=[bad_response, good_response]
        )

        result = await extract_job_description("Job posting text.")

    assert isinstance(result, JobDescription)
    assert instance.aio.models.generate_content.call_count == 2


# ---------------------------------------------------------------------------
# Scrubber integration: scrubber is called (and not called) correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_resume_calls_scrubber():
    """scrub_pii should be invoked for resume extraction."""
    parsed = _make_parsed_resume(_VALID_RESUME_INPUT)
    response = _make_response(parsed)

    with patch("src.services.extractor.genai.Client") as MockClient, \
         patch("src.services.extractor.scrub_pii", return_value=("scrubbed text", {"name_first_line": 8})) as mock_scrub:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=response)

        await extract_resume("Alice Smith\nEngineer")

    mock_scrub.assert_called_once_with("Alice Smith\nEngineer")


@pytest.mark.asyncio
async def test_extract_job_description_does_not_call_scrubber():
    """scrub_pii must NOT be called for job description extraction."""
    parsed = _make_parsed_jd(_VALID_JD_INPUT)
    response = _make_response(parsed)

    with patch("src.services.extractor.genai.Client") as MockClient, \
         patch("src.services.extractor.scrub_pii") as mock_scrub:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=response)

        await extract_job_description("Looking for a Python developer.")

    mock_scrub.assert_not_called()
