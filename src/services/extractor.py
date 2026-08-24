"""
extractor.py — LLM-powered structured extraction for resumes and job descriptions.

Uses Google Gemini in response_schema mode (temperature=0) to convert raw text into
validated Pydantic schemas. Includes a single stateless retry: on validation failure
the error message is appended to the original prompt and generate_content is called
again with a clean context (no multi-turn history required).

Provider: Google GenAI (google-genai >= 1.0.0)
Model:    gemini-3.5-flash  (GA as of mid-2026; optimised for structured extraction)
"""

from __future__ import annotations

import logging
from typing import TypeVar, Type

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

from src.config import get_settings
from src.schemas.candidate import ParsedResume
from src.schemas.job import JobDescription
from src.services.scrubber import scrub_pii

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 1  # one retry = two total LLM calls maximum

# System prompts ─ kept terse; per-field rules live in the Pydantic Field descriptions
# which flow into the JSON Schema supplied as response_schema.

_RESUME_SYSTEM = """\
You are a precise resume data extractor.
Your task is to extract structured information from the resume text provided by the user.
You MUST return a JSON object conforming to the schema and populate every field.
Rules:
- skills: flat list of distinct technical and soft skills; normalise capitalisation
  (e.g. "python" -> "Python").
- experience: one entry per distinct role. duration_months must be an integer; if only
  years are stated multiply by 12; if a role is ongoing use today's date as the end date.
- education: one entry per degree. graduation_year is null if not stated.
- years_experience_total: sum of all duration_months / 12.0, rounded to one decimal.
- Do NOT invent information that is not present in the text."""

_JD_SYSTEM = """\
You are a precise job description data extractor.
Your task is to extract structured information from the job description text provided
by the user. You MUST return a JSON object conforming to the schema and populate every field.
Rules:
- required_skills: skills explicitly marked as required, must-have, or essential.
- preferred_skills: skills marked as preferred, nice-to-have, or a plus. If no
  distinction is made, classify clearly technical/hard skills as required and
  domain/soft skills as preferred.
- min_years_experience: the lower bound of any stated range (e.g. "3-5 years" -> 3.0).
  Use 0.0 if not mentioned.
- education_requirement: minimum degree level as a plain string ("Bachelor's",
  "Master's", "PhD", "None"). Null if not mentioned.
- Do NOT invent information that is not present in the text."""

# ---------------------------------------------------------------------------
# Generic extractor
# ---------------------------------------------------------------------------

S = TypeVar("S", bound=BaseModel)


class ExtractionError(RuntimeError):
    """Raised when the LLM output fails Pydantic validation after all retries."""


async def _extract(
    raw_text: str,
    schema: Type[S],
    system_prompt: str,
) -> S:
    """
    Core extraction loop — provider-agnostic over the schema.

    Gemini response_schema notes:
      - response_mime_type="application/json" + response_schema=<PydanticModel>
        instructs the SDK to parse the response and expose it as response.parsed.
      - If response.parsed is None (e.g. model refused), ExtractionError is raised.
      - Retry is stateless: the validation error is appended to the original user
        prompt and generate_content is called again with a fresh contents list.
        MAX_RETRIES = 1 (two total calls maximum).
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.google_api_key)

    gen_config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0,
        # Disable Automatic Function Calling — we use response_schema mode, not
        # tool/function calling. Without this, the SDK emits a spurious AFC warning.
        automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        logger.debug(
            "extractor: calling generate_content for %s (attempt %d/%d)",
            schema.__name__,
            attempt + 1,
            MAX_RETRIES + 1,
        )

        # Stateless re-call: on retry the error description is appended to the
        # original user text so the model sees why the previous output was wrong.
        if attempt == 0:
            user_content = raw_text
        else:
            user_content = (
                f"{raw_text}\n\n"
                f"---\n"
                f"IMPORTANT: Your previous response failed schema validation with "
                f"the following errors. Fix them and return a valid JSON object:\n"
                f"{last_error}"
            )

        response = await client.aio.models.generate_content(
            model=settings.llm_model,
            contents=user_content,
            config=gen_config,
        )

        # response.parsed is a Pydantic instance when response_schema is set and
        # the model returned valid JSON; None means the model refused or returned
        # something unparseable.
        if response.parsed is None:
            raise ExtractionError(
                f"LLM did not return a parseable JSON object for {schema.__name__}. "
                f"finish_reason={response.candidates[0].finish_reason if response.candidates else 'unknown'}"
            )

        try:
            # response.parsed is already an instance of `schema` when the SDK
            # parses successfully, but we validate explicitly to surface any
            # field-level coercion issues as ValidationError.
            return schema.model_validate(
                response.parsed
                if isinstance(response.parsed, dict)
                else response.parsed.model_dump()
            )
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "extractor: %s attempt %d failed validation: %s",
                schema.__name__,
                attempt + 1,
                exc,
            )

            if attempt == MAX_RETRIES:
                break

    raise ExtractionError(
        f"LLM output for {schema.__name__} failed validation after "
        f"{MAX_RETRIES + 1} attempt(s): {last_error}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_resume(raw_text: str) -> ParsedResume:
    """
    Extract structured resume data from raw text.

    The text is scrubbed of PII (name, photo refs, age, gender, marital status)
    before being sent to the LLM — a deliberate fairness measure.
    Stripped categories and character counts are logged (not the content itself).
    """
    scrubbed_text, strip_log = scrub_pii(raw_text)
    logger.info("extract_resume: scrubber log = %s", strip_log)

    return await _extract(
        raw_text=scrubbed_text,
        schema=ParsedResume,
        system_prompt=_RESUME_SYSTEM,
    )


async def extract_job_description(raw_text: str) -> JobDescription:
    """
    Extract structured job description data from raw text.

    Job descriptions contain no candidate PII, so the scrubber is not applied.
    """
    return await _extract(
        raw_text=raw_text,
        schema=JobDescription,
        system_prompt=_JD_SYSTEM,
    )
