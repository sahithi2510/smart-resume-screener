"""
scoring.py — Pydantic schemas for LLM-powered resume scoring.

MatchResult is used as the Gemini response_schema (structured output mode).
ScoredCandidate wraps it with per-candidate metadata and variance flags.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SubScores(BaseModel):
    """Explicit sub-score fields for each rubric category.

    Using named fields instead of dict[str, float] because the Gemini
    Developer API does not support ``additionalProperties`` in JSON Schema.
    """

    skills_match: float = Field(
        description="Skills Match sub-score, 0.0 to 10.0 (weight: 40%)."
    )
    experience_relevance: float = Field(
        description="Experience Relevance sub-score, 0.0 to 10.0 (weight: 30%)."
    )
    education_fit: float = Field(
        description="Education Fit sub-score, 0.0 to 10.0 (weight: 15%)."
    )
    domain_keyword_overlap: float = Field(
        description="Domain Keyword Overlap sub-score, 0.0 to 10.0 (weight: 15%)."
    )

    def to_dict(self) -> dict[str, float]:
        """Convert to the dict[str, float] format used by scorer.py weights."""
        return self.model_dump()


class MatchResult(BaseModel):
    """LLM response schema — used as Gemini response_schema for structured scoring."""

    overall_score: float = Field(
        description=(
            "Weighted overall match score from 0.0 to 10.0. Calculated as: "
            "(skills_match × 0.40) + (experience_relevance × 0.30) + "
            "(education_fit × 0.15) + (domain_keyword_overlap × 0.15). "
            "Round to two decimal places."
        )
    )
    sub_scores: SubScores = Field(
        description=(
            "Sub-scores for each rubric category."
        )
    )
    matched_skills: list[str] = Field(
        description=(
            "Every candidate skill that matches a required or preferred skill "
            "in the job description (case-insensitive; treat synonyms as matches)."
        )
    )
    missing_skills: list[str] = Field(
        description=(
            "Every required skill from the job description that the candidate "
            "does NOT possess. Do NOT include preferred-only skills."
        )
    )
    justification: str = Field(
        description=(
            "Exactly 2-3 sentences summarising the match quality — "
            "strengths first, then gaps."
        )
    )
    confidence: float = Field(
        description=(
            "A float between 0.0 and 1.0 reflecting how certain you are of "
            "this assessment. Lower confidence (< 0.7) when the resume is "
            "vague, the JD is ambiguous, or skills are hard to verify."
        )
    )



class ScoredCandidate(BaseModel):
    """Per-candidate scoring result in the API response."""

    resume_id: int
    source_filename: Optional[str] = None
    overall_score: float
    sub_scores: dict[str, float]
    matched_skills: list[str]
    missing_skills: list[str]
    justification: str
    confidence: float
    high_variance: bool = Field(
        description=(
            "True when the two scoring runs disagreed by more than 1.0 point "
            "on overall_score — the frontend should flag this for human review."
        )
    )
    run_scores: Optional[list[float]] = Field(
        default=None,
        description=(
            "Individual overall_score from each scoring run. "
            "Only populated when high_variance is True."
        ),
    )


class ScoreRequest(BaseModel):
    """Request body for POST /match/score."""

    job_description_text: str = Field(
        description="Raw job description text to match candidates against."
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top pre-filtered candidates to score (1-50).",
    )


class ScoreResponse(BaseModel):
    """Response body for POST /match/score."""

    scored_candidates: list[ScoredCandidate]
    job_description: dict = Field(
        description="The structured job description extracted from the raw text."
    )
