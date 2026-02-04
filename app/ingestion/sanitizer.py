"""Sanitize resume-like documents to reduce office-specific leakage and LLM meta-text.

Goal: remove LLM commentary/preambles like "optimized for role at Office of ...",
"Changes Made", "Workspace Suggestions", etc., and keep only the resume content.
"""

from __future__ import annotations

import re


_CUT_SECTION_HEADERS = [
    r"^\s*\*\*?\s*Changes Made\s*:?\s*\*?\*?\s*$",
    r"^\s*\*\*?\s*Workspace Suggestions\s*:?\s*\*?\*?\s*$",
    r"^\s*Changes Made\s*:?\s*$",
    r"^\s*Workspace Suggestions\s*:?\s*$",
]

_DROP_LINE_PATTERNS = [
    # LLM meta / framing
    r"^\s*Based on the provided resume\b.*$",
    r"^\s*Here is (an?|the)\b.*(resume|cover letter)\b.*$",
    r"^\s*I've made the necessary changes\b.*$",
    r"^\s*Here's the optimized resume\b.*$",
    r"^\s*This (directory|file) contains\b.*$",
    # Application-specific office targeting that causes confusion
    r"^\s*I am excited to apply for\b.*$",
    r"^\s*I am applying for\b.*$",
    r"^\s*optimized it for\b.*\b(Office of|Assemblymember|Senator)\b.*$",
    r"^\s*optimized resume\b.*\b(Office of|Assemblymember|Senator)\b.*$",
]

_SECTION_START_HINTS = [
    r"^\s*\*\*Summary\*\*\s*:\s*$",
    r"^\s*Summary\s*:\s*$",
    r"^\s*\*\*Experience\*\*\s*:\s*$",
    r"^\s*Experience\s*:\s*$",
    r"^\s*\*\*Education\*\*\s*:\s*$",
    r"^\s*Education\s*:\s*$",
    r"^\s*\*\*Skills\*\*\s*:\s*$",
    r"^\s*Skills\s*:\s*$",
]


def sanitize_resume_text(text: str) -> str:
    """Return a cleaned resume text suitable for chunking/retrieval."""
    if not text:
        return ""

    lines = text.splitlines()

    # 1) Cut off everything after known "meta" sections.
    cut_re = re.compile("|".join(_CUT_SECTION_HEADERS), re.IGNORECASE)
    kept: list[str] = []
    for line in lines:
        if cut_re.match(line or ""):
            break
        kept.append(line)

    # 2) Drop known meta/application lines.
    drop_res = [re.compile(p, re.IGNORECASE) for p in _DROP_LINE_PATTERNS]
    filtered: list[str] = []
    for line in kept:
        if any(r.match(line or "") for r in drop_res):
            continue
        filtered.append(line)

    # 3) If there is a long preamble, skip down to first likely resume section.
    start_idx = 0
    sec_res = [re.compile(p, re.IGNORECASE) for p in _SECTION_START_HINTS]
    for i, line in enumerate(filtered[:60]):  # only scan first chunk
        if any(r.match(line or "") for r in sec_res):
            start_idx = max(0, i - 2)
            break
        # Some resumes start with a bold name
        if re.match(r"^\s*\*\*[^*]{3,}\*\*\s*$", line or ""):
            start_idx = i
            break
    filtered = filtered[start_idx:]

    # 4) Normalize whitespace: remove excessive blank lines.
    out: list[str] = []
    blank_run = 0
    for line in filtered:
        if not line.strip():
            blank_run += 1
            if blank_run <= 2:
                out.append("")
            continue
        blank_run = 0
        out.append(line.rstrip())

    return "\n".join(out).strip()

