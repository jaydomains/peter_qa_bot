from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Flag:
    key: str
    title: str
    evidence: list[str]


def _evidence_lines(text: str, pattern: re.Pattern[str], *, max_lines: int = 5) -> list[str]:
    ev: list[str] = []
    for line in (text or "").splitlines():
        if pattern.search(line):
            ev.append(line.strip())
            if len(ev) >= max_lines:
                break
    return ev


def build_flags(clean_text: str) -> list[Flag]:
    t = clean_text or ""

    flags: list[Flag] = []

    rules: list[tuple[str, str, re.Pattern[str]]] = [
        ("CRACKING", "Cracking mentioned", re.compile(r"\bcrack(?:ing|s)?\b", re.I)),
        ("DELAMINATION", "Delamination mentioned", re.compile(r"\bdelaminat(?:ion|ing)\b", re.I)),
        ("MOISTURE_HIGH", "High moisture mentioned", re.compile(r"\bHIGH\s+moisture\b|\bmoisture\s+content\b", re.I)),
        ("MOISTURE_FAIL", "Moisture FAIL / not acceptable indicated", re.compile(r"\bFAIL\b", re.I)),
        ("BLISTERING", "Blistering/bubbling mentioned", re.compile(r"\bblister(?:ing)?\b|\bbubbl(?:e|ing)\b", re.I)),
        ("PEELING_FLAKING", "Peeling/flaking mentioned", re.compile(r"\bpeel(?:ing)?\b|\bflak(?:ing|es)?\b", re.I)),
    ]

    for key, title, pat in rules:
        ev = _evidence_lines(t, pat)
        if ev:
            flags.append(Flag(key=key, title=title, evidence=ev))

    return flags


def extract_section_excerpt(text: str, heading: str, *, window: int = 600) -> str | None:
    """Return a short excerpt around a heading (best-effort)."""
    t = text or ""
    i = t.lower().find(heading.lower())
    if i == -1:
        return None
    start = max(0, i)
    return t[start : min(len(t), i + window)].strip()
