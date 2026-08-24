"""
tests/test_scorer.py

Unit tests for src.services.scorer — the LLM-powered resume scoring service.

All Google GenAI calls are mocked. Three critical paths are covered:

1. **Recomputation-overwrite**: LLM returns a wrong overall_score, Python
   recomputes from sub_scores and overwrites it.
2. **High-variance flagging**: Two scoring runs disagree by >1.0 point,
   high_variance=True and both run_scores are surfaced.
3. **Consistent-run averaging**: Two runs agree, sub_scores are averaged,
   overall_score is recomputed from the averaged sub_scores.

Plus: happy-path single call, edge cases for _recompute_overall.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.scoring import MatchResult, SubScores
from src.services.scorer import (
    _recompute_overall,
    _score_once,
    score_resume,
    RUBRIC_WEIGHTS,
    RECOMPUTE_TOLERANCE,
    VARIANCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Settings fixture — prevents import-time .env requirement
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_settings():
    """Patch get_settings() for every test so no real .env is needed."""
    fake = MagicMock()
    fake.google_api_key = "test-key"
    fake.llm_model = "gemini-3.5-flash"
    with patch("src.services.scorer.get_settings", return_value=fake):
        yield


# ---------------------------------------------------------------------------
# Fake SDK response builder (same pattern as test_extractor.py)
# ---------------------------------------------------------------------------

def _make_response(parsed_obj):
    """Build a minimal fake GenerateContentResponse."""
    response = MagicMock()
    response.parsed = parsed_obj
    candidate = MagicMock()
    candidate.finish_reason = "STOP"
    response.candidates = [candidate]
    return response


# ---------------------------------------------------------------------------
# Valid fixture data
# ---------------------------------------------------------------------------

def _make_match_result(
    skills_match: float = 8.0,
    experience_relevance: float = 7.0,
    education_fit: float = 6.0,
    domain_keyword_overlap: float = 5.0,
    overall_score: float | None = None,
    matched_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
    justification: str = "Candidate is a strong fit. Minor gaps in education.",
    confidence: float = 0.85,
) -> MatchResult:
    """Build a MatchResult, optionally with a custom (potentially wrong) overall_score."""
    sub_scores = SubScores(
        skills_match=skills_match,
        experience_relevance=experience_relevance,
        education_fit=education_fit,
        domain_keyword_overlap=domain_keyword_overlap,
    )
    if overall_score is None:
        overall_score = _recompute_overall(sub_scores)

    return MatchResult(
        overall_score=overall_score,
        sub_scores=sub_scores,
        matched_skills=matched_skills or ["Python", "FastAPI"],
        missing_skills=missing_skills or ["Kubernetes"],
        justification=justification,
        confidence=confidence,
    )


_SAMPLE_RESUME_DATA = {
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "experience": [
        {
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "duration_months": 24,
            "description": "Built REST APIs with Python and FastAPI.",
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

_SAMPLE_JOB_DATA = {
    "required_skills": ["Python", "FastAPI", "Kubernetes"],
    "preferred_skills": ["Docker", "Redis"],
    "min_years_experience": 3.0,
    "education_requirement": "Bachelor's",
}


# ===========================================================================
# _recompute_overall — pure unit tests
# ===========================================================================


class TestRecomputeOverall:
    """Tests for the server-side weighted-sum recomputation."""

    def test_canonical_weights_sum_to_one(self):
        """Rubric weights must sum to exactly 1.0."""
        assert sum(RUBRIC_WEIGHTS.values()) == pytest.approx(1.0)

    def test_basic_recomputation(self):
        """Hand-checked: (8×0.40)+(7×0.30)+(6×0.15)+(5×0.15) = 6.95."""
        sub_scores = {
            "skills_match": 8.0,
            "experience_relevance": 7.0,
            "education_fit": 6.0,
            "domain_keyword_overlap": 5.0,
        }
        assert _recompute_overall(sub_scores) == 6.95

    def test_all_tens(self):
        """All 10s → overall = 10.0."""
        sub_scores = {k: 10.0 for k in RUBRIC_WEIGHTS}
        assert _recompute_overall(sub_scores) == 10.0

    def test_all_zeros(self):
        """All 0s → overall = 0.0."""
        sub_scores = {k: 0.0 for k in RUBRIC_WEIGHTS}
        assert _recompute_overall(sub_scores) == 0.0

    def test_missing_key_defaults_to_zero(self):
        """A missing sub_score key should contribute 0.0 (via dict.get default)."""
        sub_scores = {
            "skills_match": 10.0,
            # everything else missing
        }
        assert _recompute_overall(sub_scores) == 4.0  # 10.0 × 0.40

    def test_rounding_to_two_decimals(self):
        """Result should be rounded to exactly 2 decimal places."""
        sub_scores = {
            "skills_match": 7.33,
            "experience_relevance": 6.67,
            "education_fit": 8.11,
            "domain_keyword_overlap": 5.89,
        }
        # (7.33×0.40) + (6.67×0.30) + (8.11×0.15) + (5.89×0.15)
        # = 2.932 + 2.001 + 1.2165 + 0.8835 = 7.033
        assert _recompute_overall(sub_scores) == 7.03


# ===========================================================================
# _score_once — recomputation-overwrite path
# ===========================================================================


class TestScoreOnceRecomputation:
    """Tests that _score_once overwrites LLM overall_score when arithmetic is wrong."""

    @pytest.mark.asyncio
    async def test_correct_overall_score_not_overwritten(self):
        """When LLM overall_score matches recomputed value, it stays unchanged."""
        result = _make_match_result()  # overall_score auto-computed = 6.95
        response = _make_response(result)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(return_value=response)

            scored = await _score_once("test content", instance, "gemini-3.5-flash")

        assert scored.overall_score == 6.95

    @pytest.mark.asyncio
    async def test_wrong_overall_score_overwritten(self):
        """When LLM returns a wrong overall_score (off by >0.05), it is overwritten."""
        # LLM says 7.50 but sub_scores compute to 6.95 — delta = 0.55
        result = _make_match_result(overall_score=7.50)
        response = _make_response(result)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(return_value=response)

            scored = await _score_once("test content", instance, "gemini-3.5-flash")

        # Must be overwritten to the recomputed value
        assert scored.overall_score == 6.95

    @pytest.mark.asyncio
    async def test_wrong_overall_score_logs_warning(self, caplog):
        """Overwriting should produce a WARNING log with both values and delta."""
        result = _make_match_result(overall_score=8.00)  # recomputed = 6.95
        response = _make_response(result)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(return_value=response)

            import logging
            with caplog.at_level(logging.WARNING, logger="src.services.scorer"):
                scored = await _score_once("test content", instance, "gemini-3.5-flash")

        assert scored.overall_score == 6.95
        assert "LLM overall_score=8.00" in caplog.text
        assert "recomputed=6.95" in caplog.text
        assert "overwriting" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_small_delta_within_tolerance_not_overwritten(self):
        """When delta <= 0.05, the LLM's value should be kept."""
        # recomputed = 6.95, LLM says 6.99 → delta = 0.04, within tolerance
        result = _make_match_result(overall_score=6.99)
        response = _make_response(result)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(return_value=response)

            scored = await _score_once("test content", instance, "gemini-3.5-flash")

        # Should keep the LLM's value since delta (0.04) <= tolerance (0.05)
        assert scored.overall_score == 6.99

    @pytest.mark.asyncio
    async def test_boundary_delta_exactly_at_tolerance_not_overwritten(self):
        """When delta == RECOMPUTE_TOLERANCE exactly, should NOT overwrite (> not >=)."""
        recomputed = 6.95
        llm_value = recomputed + RECOMPUTE_TOLERANCE  # exactly at boundary
        result = _make_match_result(overall_score=llm_value)
        response = _make_response(result)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(return_value=response)

            scored = await _score_once("test content", instance, "gemini-3.5-flash")

        assert scored.overall_score == llm_value


# ===========================================================================
# score_resume — high-variance flagging path
# ===========================================================================


class TestHighVarianceFlagging:
    """Tests that scoring runs disagreeing by >1.0 are flagged, not averaged."""

    @pytest.mark.asyncio
    async def test_high_variance_flagged(self):
        """Two runs with >1.0 delta → high_variance=True, run_scores populated."""
        # Run 1: overall = 6.95, Run 2: overall = 4.90
        run1 = _make_match_result(
            skills_match=8.0, experience_relevance=7.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
            confidence=0.85,
        )  # overall = 6.95
        run2 = _make_match_result(
            skills_match=5.0, experience_relevance=4.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
            confidence=0.60,
        )  # overall = (5×.4)+(4×.3)+(6×.15)+(5×.15) = 2.0+1.2+0.9+0.75 = 4.85

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, high_variance, run_scores = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert high_variance is True
        assert run_scores is not None
        assert len(run_scores) == 2
        assert 6.95 in run_scores
        assert 4.85 in run_scores

    @pytest.mark.asyncio
    async def test_high_variance_uses_min_confidence(self):
        """When flagged, confidence = min(run1, run2), not average."""
        run1 = _make_match_result(
            skills_match=8.0, experience_relevance=7.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
            confidence=0.90,
        )
        run2 = _make_match_result(
            skills_match=5.0, experience_relevance=4.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
            confidence=0.40,
        )

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, high_variance, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert high_variance is True
        assert result.confidence == 0.40  # min, not average (0.65)

    @pytest.mark.asyncio
    async def test_high_variance_returns_first_run_result(self):
        """When flagged, the returned result is the first run's data (not averaged)."""
        run1 = _make_match_result(
            skills_match=8.0, experience_relevance=7.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
            matched_skills=["Python", "FastAPI"],
            missing_skills=["Kubernetes"],
            justification="Run 1 justification.",
        )
        run2 = _make_match_result(
            skills_match=5.0, experience_relevance=4.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
            matched_skills=["Python"],
            missing_skills=["Kubernetes", "FastAPI"],
            justification="Run 2 justification.",
        )

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, high_variance, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert high_variance is True
        assert result.overall_score == 6.95  # run1's recomputed value
        assert result.justification == "Run 1 justification."

    @pytest.mark.asyncio
    async def test_exactly_at_variance_threshold_not_flagged(self):
        """Delta == VARIANCE_THRESHOLD exactly → NOT flagged (> not >=)."""
        # Run 1 overall = 6.95
        run1 = _make_match_result(
            skills_match=8.0, experience_relevance=7.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
        )
        # Run 2 overall = 5.95 → delta = 1.0 exactly
        run2 = _make_match_result(
            skills_match=6.5, experience_relevance=6.0,
            education_fit=5.0, domain_keyword_overlap=5.0,
        )
        # Verify: (6.5×.4)+(6×.3)+(5×.15)+(5×.15) = 2.6+1.8+0.75+0.75 = 5.9
        # delta = |6.95 - 5.9| = 1.05 ... let me recalculate
        # Actually let me pick values that give exactly 5.95
        # (x×.4)+(y×.3)+(z×.15)+(w×.15) = 5.95
        # Let's use 7.0, 5.5, 5.0, 5.0:
        # (7×.4)+(5.5×.3)+(5×.15)+(5×.15) = 2.8+1.65+0.75+0.75 = 5.95 ✓
        run2 = _make_match_result(
            skills_match=7.0, experience_relevance=5.5,
            education_fit=5.0, domain_keyword_overlap=5.0,
        )

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, high_variance, run_scores = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert high_variance is False  # delta = 1.0, threshold is > not >=
        assert run_scores is None


# ===========================================================================
# score_resume — consistent-run averaging path
# ===========================================================================


class TestConsistentRunAveraging:
    """Tests that two consistent runs are properly averaged."""

    @pytest.mark.asyncio
    async def test_sub_scores_averaged(self):
        """Sub-scores from two runs should be averaged per category."""
        run1 = _make_match_result(
            skills_match=8.0, experience_relevance=7.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
        )  # overall = 6.95
        run2 = _make_match_result(
            skills_match=8.4, experience_relevance=7.2,
            education_fit=6.4, domain_keyword_overlap=5.4,
        )  # overall = (8.4×.4)+(7.2×.3)+(6.4×.15)+(5.4×.15) = 3.36+2.16+0.96+0.81 = 7.29

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, high_variance, run_scores = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert high_variance is False
        assert run_scores is None

        # Averaged sub_scores
        assert result.sub_scores.skills_match == pytest.approx(8.2, abs=0.01)
        assert result.sub_scores.experience_relevance == pytest.approx(7.1, abs=0.01)
        assert result.sub_scores.education_fit == pytest.approx(6.2, abs=0.01)
        assert result.sub_scores.domain_keyword_overlap == pytest.approx(5.2, abs=0.01)

    @pytest.mark.asyncio
    async def test_overall_recomputed_from_averaged_subs(self):
        """overall_score must be recomputed from averaged sub_scores, not averaged directly."""
        run1 = _make_match_result(
            skills_match=8.0, experience_relevance=7.0,
            education_fit=6.0, domain_keyword_overlap=5.0,
        )  # recomputed = 6.95
        run2 = _make_match_result(
            skills_match=8.4, experience_relevance=7.2,
            education_fit=6.4, domain_keyword_overlap=5.4,
        )  # recomputed = 7.29

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, _, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        # Averaged subs: skills=8.2, exp=7.1, edu=6.2, kw=5.2
        # Recomputed: (8.2×.4)+(7.1×.3)+(6.2×.15)+(5.2×.15)
        #           = 3.28 + 2.13 + 0.93 + 0.78 = 7.12
        expected = _recompute_overall(result.sub_scores)
        assert result.overall_score == expected

    @pytest.mark.asyncio
    async def test_matched_skills_unioned(self):
        """matched_skills = union of both runs (generous)."""
        run1 = _make_match_result(
            matched_skills=["Python", "FastAPI"],
        )
        run2 = _make_match_result(
            matched_skills=["Python", "Docker"],
        )

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, _, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        # Union: Python, FastAPI, Docker
        assert set(result.matched_skills) == {"Python", "FastAPI", "Docker"}

    @pytest.mark.asyncio
    async def test_missing_skills_intersected(self):
        """missing_skills = intersection of both runs (conservative)."""
        run1 = _make_match_result(
            missing_skills=["Kubernetes", "Terraform"],
        )
        run2 = _make_match_result(
            missing_skills=["Kubernetes", "Helm"],
        )

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, _, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        # Intersection: only Kubernetes (both agree it's missing)
        assert set(result.missing_skills) == {"Kubernetes"}

    @pytest.mark.asyncio
    async def test_confidence_averaged(self):
        """confidence = average of both runs when consistent."""
        run1 = _make_match_result(confidence=0.90)
        run2 = _make_match_result(confidence=0.80)

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, _, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert result.confidence == pytest.approx(0.85, abs=0.01)

    @pytest.mark.asyncio
    async def test_justification_from_first_run(self):
        """justification is taken from the first run."""
        run1 = _make_match_result(justification="First run analysis.")
        run2 = _make_match_result(justification="Second run analysis.")

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, _, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert result.justification == "First run analysis."

    @pytest.mark.asyncio
    async def test_identical_runs_produce_same_values(self):
        """Two identical runs → averaged result equals either run."""
        run1 = _make_match_result()
        run2 = _make_match_result()  # identical

        resp1 = _make_response(run1)
        resp2 = _make_response(run2)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(
                side_effect=[resp1, resp2]
            )

            result, high_variance, _ = await score_resume(
                _SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA
            )

        assert high_variance is False
        assert result.overall_score == run1.overall_score
        assert result.sub_scores == run1.sub_scores


# ===========================================================================
# score_resume — dual call verification
# ===========================================================================


class TestDualCallMechanics:
    """Tests that score_resume always makes exactly two LLM calls."""

    @pytest.mark.asyncio
    async def test_always_two_calls(self):
        """score_resume must call generate_content exactly twice."""
        result = _make_match_result()
        response = _make_response(result)

        with patch("src.services.scorer.genai.Client") as MockClient:
            instance = MockClient.return_value
            instance.aio.models.generate_content = AsyncMock(return_value=response)

            await score_resume(_SAMPLE_RESUME_DATA, _SAMPLE_JOB_DATA)

        assert instance.aio.models.generate_content.call_count == 2
