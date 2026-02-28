from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RoleMismatch:
    key: str
    title: str
    severity: str  # LOW|MED|HIGH|CRITICAL
    evidence_spec: list[str]
    evidence_report: list[str]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _find_lines(text: str, pat: re.Pattern[str], *, max_lines: int = 4) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        l = _norm(line)
        if not l:
            continue
        if pat.search(l):
            out.append(l)
            if len(out) >= max_lines:
                break
    return out


def check_elastoshield_used_as_primer(*, spec_text: str, report_text: str) -> RoleMismatch | None:
    """Detect the warranty-critical mismatch:

    - Spec requires PP700 as primer in repair workflows.
    - Report shows Elastoshield used as "Primer coat".

    This is deterministic and intentionally narrow to avoid false positives.
    """

    st = (spec_text or "")
    rt = (report_text or "")

    # Spec evidence: lines indicating priming with PP700
    spec_ev = _find_lines(
        st,
        re.compile(r"\bprime\b.*\b(pp\s*700|pp700)\b|\bprofessional\s+gypsum\s*&\s*plaster\s+primer\b.*\b(pp\s*700|pp700)\b", re.I),
        max_lines=5,
    )

    # Report evidence: Elastoshield listed as primer coat
    report_ev = _find_lines(
        rt,
        re.compile(r"\belasto\s*shield\b|\bpes\b", re.I),
        max_lines=20,
    )

    # Require explicit "Primer coat" context in the report near Elastoshield
    primer_lines = [l for l in report_ev if re.search(r"\bprimer\s+coat\b", l, flags=re.I)]

    if not primer_lines:
        return None

    # If report explicitly mentions PP700 as primer coat too, do not flag.
    if re.search(r"\b(pp\s*700|pp700)\b", rt, flags=re.I):
        # could still be wrong, but keep the rule strict for now.
        return None

    if not spec_ev:
        # If we can't find spec evidence, don't flag (groundedness).
        return None

    return RoleMismatch(
        key="SPEC_ROLE_MISMATCH_ELASTOSHIELD_PRIMER",
        title="Spec role mismatch: Elastoshield used as primer coat (PP700 required)",
        severity="HIGH",
        evidence_spec=spec_ev[:5],
        evidence_report=primer_lines[:5],
    )
