from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from peter.parsing.pdf_text import extract_pdf_text, has_meaningful_text


@dataclass(frozen=True)
class ReportIdentity:
    site_code: str
    report_no: str  # 3-digit

    @property
    def display_ref(self) -> str:
        return f"{self.site_code} - {self.report_no}"


def _z3(s: str) -> str:
    s2 = re.sub(r"\D+", "", s or "")
    return s2.zfill(3) if s2 else ""


def infer_from_pdf_bytes(pdf_bytes: bytes) -> ReportIdentity | None:
    """Infer site_code + report_no from report PDF.

    Supports legacy format (Inspection Reference: PRSVNQA - 006) and
    new format (Report #: 006 + Inspection Reference: PRSVNQA - 006).
    """

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "report.pdf"
        p.write_bytes(pdf_bytes)
        text = extract_pdf_text(p)

    if not has_meaningful_text(text):
        return None

    norm = re.sub(r"[\t\r]+", " ", text)

    # Prefer explicit report number label
    m_rn = re.search(r"(?im)REPORT\s*#\s*:\s*([^\n]+)", norm)
    report_no = _z3(m_rn.group(1)) if m_rn else ""

    # Try to find an explicit inspection reference line, but don't require start-of-line.
    m_ref = re.search(r"(?im)INSPECTION\s*REFERENCE\s*:\s*([^\n]+)", norm)
    if not m_ref:
        m_ref = re.search(r"(?im)\bNAME\b\s*:?\s*([^\n]+)", norm)

    site_code = ""
    ref_text = m_ref.group(1).strip().upper() if m_ref else ""

    # Robust fallback: find patterns like PRSVNQA - 006 anywhere.
    m_pair = re.search(r"\b([A-Z]{3,12}[A-Z0-9_-]{0,10})\s*-\s*(\d{1,3})\b", norm.upper())
    if m_pair:
        site_code = m_pair.group(1).strip().upper()
        if not report_no:
            report_no = _z3(m_pair.group(2))

    # If we have a reference line, use it to refine.
    if ref_text:
        m_sc = re.search(r"\b([A-Z]{3,12}[A-Z0-9_-]{0,10})\b", ref_text)
        if m_sc:
            site_code = site_code or m_sc.group(1)
        if not report_no:
            m_num = re.search(r"\b(\d{1,3})\b", ref_text)
            if m_num:
                report_no = _z3(m_num.group(1))

    if not (site_code and report_no):
        return None

    return ReportIdentity(site_code=site_code, report_no=report_no)
