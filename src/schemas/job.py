from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    required_skills: list[str] = Field(
        description=(
            "Skills explicitly marked as required, must-have, or essential. "
            "If no distinction is made between required and preferred, classify "
            "clearly technical/hard skills here."
        )
    )
    preferred_skills: list[str] = Field(
        description=(
            "Skills marked as preferred, nice-to-have, a plus, or desirable. "
            "If no distinction is made, classify domain/soft skills here."
        )
    )
    min_years_experience: float = Field(
        description=(
            "Minimum years of experience required. Use the lower bound of any range "
            "(e.g. '3-5 years' -> 3.0). Use 0.0 if not stated."
        )
    )
    education_requirement: Optional[str] = Field(
        default=None,
        description=(
            "Minimum degree level as a plain string: 'Bachelor\\'s', 'Master\\'s', "
            "'PhD', or 'None'. Null if not mentioned in the job description."
        ),
    )
