from __future__ import annotations

import re


def parse_tds_subject(subject: str) -> tuple[str | None, str | None, str | None]:
    """Parse: TDS | <VENDOR> | <CODE> | <URL>"""

    s = (subject or "").strip()
    parts = [p.strip() for p in s.split("|")]
    if len(parts) < 4:
        return None, None, None
    if parts[0].upper() != "TDS":
        return None, None, None
    vendor = parts[1].strip().upper()
    code = re.sub(r"\s+", "", parts[2].strip().upper())
    url = parts[3].strip()
    return vendor or None, code or None, url or None
