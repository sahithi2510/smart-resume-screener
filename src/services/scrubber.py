"""
scrubber.py — Fairness pre-processing for resume text.

DELIBERATE FAIRNESS MEASURE: Before any resume text is sent to the LLM, this module
strips attributes that are legally protected or known to introduce demographic bias
into hiring decisions:

  - Candidate name        (encodes ethnicity / gender signals)
  - Photo / image refs    (appearance bias)
  - Age / date of birth   (age discrimination)
  - Gender                (gender discrimination)
  - Marital status        (protected status)

What is logged: the *category* that was stripped and the *character count* of removed
text — never the actual content — so logs are safe for audit and the README's
bias-exclusion documentation.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Name: "Name:" label (case-insensitive) followed by rest of line
_NAME_LABEL = re.compile(r"(?i)^[ \t]*name\s*:\s*.+$", re.MULTILINE)

# First-line name heuristic:
#   - Title Case words (2–4 words, each 2–20 chars, letters/hyphens/apostrophes only)
#   - NOT all-caps (those are section headers like "WORK EXPERIENCE")
#   - NOT containing common non-name keywords
_NON_NAME_KEYWORDS = re.compile(
    r"(?i)\b("
    r"engineer|developer|manager|director|analyst|designer|consultant|architect|"
    r"specialist|lead|senior|junior|associate|intern|officer|coordinator|head|"
    r"experience|education|skills|summary|objective|profile|resume|cv|curriculum|"
    r"http|www|linkedin|github|@"
    r")\b"
)
_TITLE_CASE_NAME = re.compile(
    r"^((?:[A-Z][a-zA-Z'\-]{1,19})(?: [A-Z][a-zA-Z'\-]{1,19}){1,3})$"
)

# Photo / image references — split into two patterns to avoid inline-flag error
_PHOTO_LABEL = re.compile(
    r"(?:photo|image|picture|headshot)\s*:.*$",
    re.IGNORECASE | re.MULTILINE,
)
_PHOTO_PATH = re.compile(
    r"\S+\.(?:jpg|jpeg|png|gif|bmp|webp)",
    re.IGNORECASE,
)

# Age: "Age: 29" or "DOB: ..." or "Date of Birth: ..."
_AGE = re.compile(
    r"(?:age|d\.?o\.?b\.?|date\s+of\s+birth)\s*:?\s*[\d\/\-\.a-zA-Z ,]+$",
    re.IGNORECASE | re.MULTILINE,
)

# Gender: "Gender: Male/Female/..." or "Sex: ..."
_GENDER = re.compile(
    r"(?:gender|sex)\s*:\s*\S+.*$",
    re.IGNORECASE | re.MULTILINE,
)

# Marital status: labelled or bare keyword at start of token
_MARITAL = re.compile(
    r"(?:marital\s+status\s*:\s*\S+.*|(?<!\w)(?:married|single|divorced|widowed|separated)(?!\w).*$)",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrub_pii(text: str) -> tuple[str, dict[str, int]]:
    """
    Strip PII categories from resume text before sending to the LLM.

    Returns:
        (scrubbed_text, stripped_log)

        stripped_log maps each stripped category to the character count removed.
        The log never contains the actual stripped content — only counts.
    """
    stripped_log: dict[str, int] = {}
    scrubbed = text

    # --- 1. Named "Name:" label ---
    scrubbed, n = _apply(scrubbed, _NAME_LABEL, "name_label")
    if n:
        stripped_log["name_label"] = n

    # --- 2. First-line name heuristic ---
    scrubbed, n = _scrub_first_line_name(scrubbed)
    if n:
        stripped_log["name_first_line"] = n

    # --- 3. Photo / image references (two patterns)
    scrubbed, n1 = _apply(scrubbed, _PHOTO_LABEL, "photo_label")
    scrubbed, n2 = _apply(scrubbed, _PHOTO_PATH, "photo_path")
    n = n1 + n2
    if n:
        stripped_log["photo"] = n

    # --- 4. Age / DOB ---
    scrubbed, n = _apply(scrubbed, _AGE, "age_dob")
    if n:
        stripped_log["age_dob"] = n

    # --- 5. Gender ---
    scrubbed, n = _apply(scrubbed, _GENDER, "gender")
    if n:
        stripped_log["gender"] = n

    # --- 6. Marital status ---
    scrubbed, n = _apply(scrubbed, _MARITAL, "marital_status")
    if n:
        stripped_log["marital_status"] = n

    if stripped_log:
        logger.info(
            "scrubber: stripped categories %s (chars removed per category: %s)",
            list(stripped_log.keys()),
            stripped_log,
        )

    return scrubbed.strip(), stripped_log


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply(text: str, pattern: re.Pattern, label: str) -> tuple[str, int]:
    """Replace all matches of pattern with empty string; return (new_text, chars_removed)."""
    matches = pattern.findall(text)
    chars_removed = sum(len(m) for m in matches)
    return pattern.sub("", text), chars_removed


def _scrub_first_line_name(text: str) -> tuple[str, int]:
    """
    Heuristic: if the first non-blank line looks like a personal name (Title Case,
    2-4 words, no common non-name keywords, not all-caps), strip it.

    Guards against false positives:
      - All-caps lines (section headers, e.g. "WORK EXPERIENCE") → kept
      - Lines containing non-name keywords (job titles, URLs, etc.) → kept
      - Blank leading lines → skipped to find the real first content line
    """
    lines = text.splitlines()
    first_content_idx = next(
        (i for i, ln in enumerate(lines) if ln.strip()), None
    )
    if first_content_idx is None:
        return text, 0

    first_line = lines[first_content_idx].strip()

    # Reject all-caps lines (section headers)
    if first_line == first_line.upper() and any(c.isalpha() for c in first_line):
        return text, 0

    # Reject lines containing known non-name tokens
    if _NON_NAME_KEYWORDS.search(first_line):
        return text, 0

    # Must match the Title Case name pattern
    if not _TITLE_CASE_NAME.match(first_line):
        return text, 0

    chars_removed = len(lines[first_content_idx])
    lines[first_content_idx] = ""
    return "\n".join(lines), chars_removed
