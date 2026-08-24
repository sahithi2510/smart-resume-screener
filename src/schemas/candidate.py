from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Education(BaseModel):
    degree: str = Field(description="Degree level, e.g. 'Bachelor of Science', 'MBA'")
    field: str = Field(description="Field of study, e.g. 'Computer Science'")
    institution: str = Field(description="Name of the university or college")
    graduation_year: Optional[int] = Field(
        default=None,
        description="Four-digit graduation year, or null if not stated",
    )


class Experience(BaseModel):
    title: str = Field(description="Job title / role name")
    company: str = Field(description="Employer / organisation name")
    duration_months: int = Field(
        description=(
            "Duration of this role in whole months. "
            "If only years are given, multiply by 12. "
            "If the role is current/ongoing, calculate from start date to today."
        )
    )
    description: str = Field(
        description="Brief summary of responsibilities and achievements in this role"
    )


class ParsedResume(BaseModel):
    skills: list[str] = Field(
        description=(
            "Flat list of distinct technical and soft skills found anywhere in the resume. "
            "Normalise capitalisation (e.g. 'python' -> 'Python', 'AWS' stays 'AWS')."
        )
    )
    experience: list[Experience] = Field(
        description="One entry per distinct role, in reverse-chronological order"
    )
    education: list[Education] = Field(
        description="One entry per degree or qualification"
    )
    years_experience_total: float = Field(
        description=(
            "Sum of all experience.duration_months divided by 12.0, "
            "rounded to one decimal place."
        )
    )
