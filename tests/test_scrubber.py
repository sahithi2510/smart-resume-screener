"""
tests/test_scrubber.py

Named unit tests for every PII strip category in scrubber.scrub_pii().
Covers both positive (should strip) and negative (must NOT strip) cases,
with particular attention to the first-line name heuristic edge cases.
"""

import pytest
from src.services.scrubber import scrub_pii


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def scrubbed(text: str) -> str:
    """Return only the scrubbed text (ignore the log dict)."""
    result, _ = scrub_pii(text)
    return result


def log(text: str) -> dict:
    """Return only the strip log dict."""
    _, strip_log = scrub_pii(text)
    return strip_log


# ---------------------------------------------------------------------------
# Name — "Name:" label
# ---------------------------------------------------------------------------

def test_name_label_stripped():
    text = "Name: John Smith\nSoftware Engineer with 5 years experience."
    result = scrubbed(text)
    assert "John Smith" not in result
    assert "Software Engineer" in result


def test_name_label_case_insensitive():
    text = "NAME: Jane Doe\nSkills: Python"
    assert "Jane Doe" not in scrubbed(text)


# ---------------------------------------------------------------------------
# Name — first-line heuristic (positive cases)
# ---------------------------------------------------------------------------

def test_first_line_name_stripped():
    text = "Jane Doe\nExperience: 3 years in data science."
    result = scrubbed(text)
    assert "Jane Doe" not in result
    assert "data science" in result


def test_first_line_name_with_hyphen_stripped():
    text = "Mary-Anne O'Brien\nEducation: BSc Computer Science"
    assert "Mary-Anne" not in scrubbed(text)


# ---------------------------------------------------------------------------
# Name — first-line heuristic (negative / do-NOT-strip cases)
# ---------------------------------------------------------------------------

def test_first_line_not_a_name_section_header():
    """All-caps lines are section headers, not names — must be preserved."""
    text = "WORK EXPERIENCE\nSoftware Engineer at Acme Corp"
    result = scrubbed(text)
    assert "WORK EXPERIENCE" in result


def test_first_line_not_a_name_job_title():
    """'Senior Software Engineer' contains a known non-name keyword — must be preserved."""
    text = "Senior Software Engineer\nPython, AWS, Docker"
    result = scrubbed(text)
    assert "Senior Software Engineer" in result


def test_first_line_not_a_name_url():
    """Lines starting with a URL must not be treated as names."""
    text = "https://linkedin.com/in/jdoe\nSkills: Java"
    result = scrubbed(text)
    assert "linkedin.com" in result


def test_first_line_not_a_name_single_word():
    """A single word (even Title Case) is not a full name — must be preserved."""
    text = "Engineer\n5 years of experience."
    result = scrubbed(text)
    assert "Engineer" in result


def test_first_line_not_a_name_blank_leading_line():
    """
    Blank leading lines (common with pdfplumber layout=True) must be skipped;
    the scrubber must still find and strip the actual name on the next line.
    """
    text = "\nAlice Johnson\nSoftware Developer"
    result = scrubbed(text)
    assert "Alice Johnson" not in result
    assert "Software Developer" in result


# ---------------------------------------------------------------------------
# Photo / image references
# ---------------------------------------------------------------------------

def test_photo_label_stripped():
    text = "Photo: headshot.jpg\nExperience: 2 years"
    assert "headshot.jpg" not in scrubbed(text)
    assert "Experience" in scrubbed(text)


def test_image_path_stripped():
    text = "profile_pic.png\nSkills: React"
    assert "profile_pic.png" not in scrubbed(text)


def test_image_path_jpeg_stripped():
    text = "avatar.jpeg uploaded as part of CV"
    assert "avatar.jpeg" not in scrubbed(text)


# ---------------------------------------------------------------------------
# Age / DOB
# ---------------------------------------------------------------------------

def test_age_label_stripped():
    text = "Age: 29\nLocation: London"
    assert "Age: 29" not in scrubbed(text)
    assert "London" in scrubbed(text)


def test_dob_label_stripped():
    text = "Date of Birth: 12/04/1995\nNationality: British"
    result = scrubbed(text)
    assert "1995" not in result
    assert "British" in result


def test_dob_abbreviation_stripped():
    text = "DOB: 1990-05-22\nSkills: SQL"
    assert "1990" not in scrubbed(text)


def test_bare_age_not_over_stripped():
    """'3 years of experience' must NOT be stripped — no age keyword adjacent."""
    text = "3 years of experience in machine learning."
    assert "3 years" in scrubbed(text)


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------

def test_gender_label_stripped():
    text = "Gender: Male\nSkills: Python"
    result = scrubbed(text)
    assert "Gender: Male" not in result
    assert "Python" in result


def test_sex_label_stripped():
    text = "Sex: Female\nExperience: 4 years"
    assert "Sex: Female" not in scrubbed(text)


def test_gender_mid_text_not_stripped():
    """
    'gender' appearing as part of normal prose (not as a PII label) must be preserved.
    """
    text = "Developed gender-neutral UI components for a Fortune 500 client."
    assert "gender-neutral" in scrubbed(text)


# ---------------------------------------------------------------------------
# Marital status
# ---------------------------------------------------------------------------

def test_marital_label_stripped():
    text = "Marital Status: Single\nCity: New York"
    result = scrubbed(text)
    assert "Marital Status" not in result
    assert "New York" in result


def test_married_keyword_stripped():
    text = "married, two children\nProgramming Languages: Go"
    assert "married" not in scrubbed(text)


# ---------------------------------------------------------------------------
# Log output — safety check
# ---------------------------------------------------------------------------

def test_strip_log_contains_category_not_content():
    """
    The strip log must record the category key and a character count,
    but must NEVER contain the actual stripped value.
    """
    text = "Name: Robert Johnson\nAge: 45\nSkills: Java"
    _, strip_log = scrub_pii(text)

    # At least name and age categories must appear
    assert "name_label" in strip_log or "name_first_line" in strip_log
    assert "age_dob" in strip_log

    # All values must be integers (character counts), not strings
    for key, value in strip_log.items():
        assert isinstance(value, int), f"log[{key!r}] should be int, got {type(value)}"
        # The actual PII text must not leak into keys or values
        assert "Robert" not in key
        assert "Johnson" not in key


def test_strip_log_empty_when_nothing_stripped():
    """A resume with no PII fields produces an empty log."""
    text = "Skills: Python, SQL\nExperience: 3 years at Acme Corp"
    _, strip_log = scrub_pii(text)
    assert strip_log == {}
