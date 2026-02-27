from __future__ import annotations

import re


_BOILERPLATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^Created with Fieldwire on\s+\d{2}-\d{2}-\d{4}\s*$", re.I),
    re.compile(r"^Paint Reference Panel Report #\d+\s+pg\.\s*\d+\s*$", re.I),
    re.compile(r"^Paint Reference Panel Report #\d+\s*$", re.I),
    re.compile(r"^pg\.\s*\d+\s*$", re.I),
]


def clean_extracted_text(text: str) -> str:
    """De-noise pdftotext output for human summarization.

    - Strips common boilerplate lines
    - Collapses repeated identical lines (keeps first occurrence)
    """

    lines_in = (text or "").splitlines()
    out_lines: list[str] = []
    seen: set[str] = set()

    for raw in lines_in:
        line = raw.strip()
        if not line:
            continue
        if any(pat.match(line) for pat in _BOILERPLATE_PATTERNS):
            continue
        # collapse duplicates (case-insensitive)
        key = re.sub(r"\s+", " ", line).lower()
        if key in seen:
            continue
        seen.add(key)
        out_lines.append(line)

    return "\n".join(out_lines) + "\n"
