"""
scorer.py — LLM-powered structured resume-to-JD scoring.

Uses the same Gemini response_schema approach as extractor.py.  Each candidate
is scored twice at temperature=0; overall_score is recomputed server-side from
sub_scores (never trusting the LLM's arithmetic), and runs that disagree by
more than 1.0 point are flagged as high_variance rather than silently averaged.

Provider: Google GenAI (google-genai >= 1.0.0)
Model:    gemini-3.5-flash (configurable via settings.llm_model)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types as genai_types
from pydantic import ValidationError

from src.config import get_settings
from src.schemas.scoring import MatchResult, SubScores
from src.services.extractor import ExtractionError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rubric weights — single source of truth for prompt AND server-side check
# ---------------------------------------------------------------------------

RUBRIC_WEIGHTS: dict[str, float] = {
    "skills_match": 0.40,
    "experience_relevance": 0.30,
    "education_fit": 0.15,
    "domain_keyword_overlap": 0.15,
}

VARIANCE_THRESHOLD = 1.0    # flag if two runs disagree by more than this
RECOMPUTE_TOLERANCE = 0.05  # overwrite LLM overall_score if off by more than this
MAX_RETRIES = 1             # one retry on validation failure (same as extractor)

# ---------------------------------------------------------------------------
# System prompt — reviewed and approved rubric
# ---------------------------------------------------------------------------

_SCORING_SYSTEM = """\
You are an expert technical recruiter performing a structured \
resume-to-job-description match evaluation.

You will receive two inputs:
1. RESUME DATA — structured JSON with the candidate's skills, experience, \
and education.
2. JOB DESCRIPTION DATA — structured JSON with the role's required skills, \
preferred skills, minimum experience, and education requirement.

Score the candidate against the job description using the following rubric. \
Each category has a fixed weight; your overall_score MUST equal the weighted \
sum of the sub-scores.

## Scoring Rubric

### 1. Skills Match (weight: 40%)
Evaluate how well the candidate's skills align with the job requirements.
- 9-10: Candidate possesses ≥90% of required skills AND multiple preferred \
skills.
- 7-8:  Candidate possesses ≥75% of required skills AND at least one \
preferred skill.
- 5-6:  Candidate possesses ≥50% of required skills OR has strong \
adjacent/transferable skills.
- 3-4:  Candidate possesses 25-49% of required skills with significant gaps.
- 1-2:  Candidate possesses <25% of required skills; poor alignment.
- 0:    No skill overlap whatsoever.

### 2. Experience Relevance (weight: 30%)
Evaluate the relevance and depth of the candidate's work experience to the \
role.
- 9-10: Experience directly matches the role's domain and seniority; meets \
or exceeds the required years.
- 7-8:  Experience is in a closely related domain with sufficient tenure; \
minor gaps in seniority or scope.
- 5-6:  Some relevant experience but in a different domain or at a different \
level; meets ~50% of requirements.
- 3-4:  Limited relevant experience; mostly tangential roles.
- 1-2:  Minimal professional experience or entirely unrelated fields.
- 0:    No professional experience listed.

### 3. Education Fit (weight: 15%)
Evaluate whether the candidate's educational background meets the job's \
education requirements.
- 9-10: Degree level meets or exceeds the requirement in a directly relevant \
field.
- 7-8:  Degree level meets the requirement but in a related (not exact) \
field, OR exceeds the level in an unrelated field.
- 5-6:  Degree level is one step below the requirement (e.g. Bachelor's when \
Master's required) but in a relevant field.
- 3-4:  Degree level is below the requirement in an unrelated field.
- 1-2:  No formal degree but some coursework or certifications.
- 0:    No education information provided and job requires a specific degree.
If the job description does not specify an education requirement, default \
this sub-score to 7.0.

### 4. Domain Keyword Overlap (weight: 15%)
Evaluate the overlap of domain-specific terminology, tools, frameworks, and \
industry jargon between the resume and job description — beyond the explicit \
skills lists.
- 9-10: Resume language strongly mirrors the JD's domain vocabulary; \
candidate clearly operates in the same technical ecosystem.
- 7-8:  Good keyword overlap; candidate uses most of the same domain terms.
- 5-6:  Moderate overlap; candidate is familiar with the domain but uses \
some different terminology.
- 3-4:  Weak overlap; candidate's language suggests a different technical \
ecosystem.
- 1-2:  Almost no domain keyword alignment.
- 0:    Completely different domain vocabulary.

## Scoring Rules
- Each sub-score MUST be a float between 0.0 and 10.0, inclusive.
- overall_score = (skills_match × 0.40) + (experience_relevance × 0.30) \
+ (education_fit × 0.15) + (domain_keyword_overlap × 0.15). Round to two \
decimal places.
- matched_skills: list every candidate skill that matches a required or \
preferred skill in the JD (case-insensitive comparison; treat synonyms like \
"JS" / "JavaScript" as matches).
- missing_skills: list every required skill from the JD that the candidate \
does NOT possess (do NOT include preferred-only skills here).
- justification: exactly 2-3 sentences summarising the match quality — \
strengths first, then gaps.
- confidence: a float between 0.0 and 1.0 reflecting how certain you are of \
this assessment. Lower confidence (< 0.7) when the resume is vague, the JD \
is ambiguous, or skills are hard to verify from text alone.
- Be strict and calibrated: a score of 7+ should mean the candidate is \
genuinely a strong fit, not just "acceptable".\
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _recompute_overall(sub_scores: SubScores | dict[str, float]) -> float:
    """Recompute overall_score from sub_scores using the canonical rubric weights.

    This is the server-side source of truth — the LLM's own overall_score is
    verified against this and overwritten when it drifts.

    Accepts either a SubScores model instance or a plain dict.
    """
    scores_dict = (
        sub_scores.to_dict() if isinstance(sub_scores, SubScores) else sub_scores
    )
    total = sum(
        scores_dict.get(key, 0.0) * weight
        for key, weight in RUBRIC_WEIGHTS.items()
    )
    return round(total, 2)


def _build_user_content(
    resume_data: dict[str, Any],
    job_data: dict[str, Any],
) -> str:
    """Format resume + JD structured data as the user message for the LLM."""
    return (
        "## RESUME DATA\n"
        f"```json\n{json.dumps(resume_data, indent=2)}\n```\n\n"
        "## JOB DESCRIPTION DATA\n"
        f"```json\n{json.dumps(job_data, indent=2)}\n```"
    )


async def _score_once(
    user_content: str,
    client: genai.Client,
    model: str,
) -> MatchResult:
    """Single scoring LLM call with one stateless retry on validation failure.

    After receiving a valid response, overall_score is recomputed from
    sub_scores using the canonical weights.  If the LLM's value disagrees by
    more than ``RECOMPUTE_TOLERANCE`` (0.05), the server-side value silently
    overwrites it and a warning is logged.
    """
    gen_config = genai_types.GenerateContentConfig(
        system_instruction=_SCORING_SYSTEM,
        response_mime_type="application/json",
        response_schema=MatchResult,
        temperature=0,
        automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        logger.debug(
            "scorer: calling generate_content (attempt %d/%d)",
            attempt + 1,
            MAX_RETRIES + 1,
        )

        if attempt == 0:
            content = user_content
        else:
            content = (
                f"{user_content}\n\n"
                f"---\n"
                f"IMPORTANT: Your previous response failed schema validation "
                f"with the following errors. Fix them and return a valid JSON "
                f"object:\n{last_error}"
            )

        response = await client.aio.models.generate_content(
            model=model,
            contents=content,
            config=gen_config,
        )

        if response.parsed is None:
            raise ExtractionError(
                "LLM did not return a parseable JSON object for MatchResult. "
                f"finish_reason="
                f"{response.candidates[0].finish_reason if response.candidates else 'unknown'}"
            )

        try:
            result = MatchResult.model_validate(
                response.parsed
                if isinstance(response.parsed, dict)
                else response.parsed.model_dump()
            )
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "scorer: MatchResult attempt %d failed validation: %s",
                attempt + 1,
                exc,
            )
            if attempt == MAX_RETRIES:
                break
            continue

        # ----- Server-side arithmetic verification -----
        recomputed = _recompute_overall(result.sub_scores)
        llm_value = result.overall_score
        if abs(llm_value - recomputed) > RECOMPUTE_TOLERANCE:
            logger.warning(
                "scorer: LLM overall_score=%.2f differs from recomputed=%.2f "
                "(delta=%.3f, tolerance=%.2f); overwriting with recomputed value",
                llm_value,
                recomputed,
                abs(llm_value - recomputed),
                RECOMPUTE_TOLERANCE,
            )
            result.overall_score = recomputed

        return result

    raise ExtractionError(
        f"LLM output for MatchResult failed validation after "
        f"{MAX_RETRIES + 1} attempt(s): {last_error}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def score_resume(
    resume_data: dict[str, Any],
    job_data: dict[str, Any],
) -> tuple[MatchResult, bool, list[float] | None]:
    """Score a single resume against a job description with dual-run variance
    detection.

    Each scoring call is made twice at ``temperature=0``.  If the two runs
    disagree on ``overall_score`` by more than ``VARIANCE_THRESHOLD`` (1.0),
    the disagreement is surfaced rather than silently averaged.

    Returns
    -------
    result : MatchResult
        Final scoring result (averaged sub-scores when consistent, first run
        when high-variance).
    high_variance : bool
        ``True`` when the two runs disagreed by > ``VARIANCE_THRESHOLD``.
    run_scores : list[float] | None
        Individual ``overall_score`` from each run when ``high_variance`` is
        ``True``; ``None`` otherwise.
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.google_api_key)
    user_content = _build_user_content(resume_data, job_data)

    # --- Dual run at temperature=0 ---
    run1 = await _score_once(user_content, client, settings.llm_model)
    run2 = await _score_once(user_content, client, settings.llm_model)

    delta = abs(run1.overall_score - run2.overall_score)

    if delta > VARIANCE_THRESHOLD:
        logger.warning(
            "scorer: high variance — run1=%.2f, run2=%.2f, delta=%.2f",
            run1.overall_score,
            run2.overall_score,
            delta,
        )
        # Surface the disagreement: return first run with reduced confidence
        result = run1.model_copy()
        result.confidence = min(run1.confidence, run2.confidence)
        return result, True, [run1.overall_score, run2.overall_score]

    # --- Consistent runs — average sub-scores, recompute overall ---
    run1_subs = run1.sub_scores.to_dict()
    run2_subs = run2.sub_scores.to_dict()
    averaged_sub_dict = {
        key: round(
            (run1_subs.get(key, 0.0) + run2_subs.get(key, 0.0)) / 2,
            2,
        )
        for key in RUBRIC_WEIGHTS
    }
    averaged_sub_scores = SubScores(**averaged_sub_dict)

    result = MatchResult(
        overall_score=_recompute_overall(averaged_sub_scores),
        sub_scores=averaged_sub_scores,
        # Union of matched skills — generous: if either run found it, keep it
        matched_skills=sorted(set(run1.matched_skills) | set(run2.matched_skills)),
        # Intersection of missing skills — conservative: only flag if both agree
        missing_skills=sorted(set(run1.missing_skills) & set(run2.missing_skills)),
        justification=run1.justification,
        confidence=round((run1.confidence + run2.confidence) / 2, 2),
    )

    return result, False, None
