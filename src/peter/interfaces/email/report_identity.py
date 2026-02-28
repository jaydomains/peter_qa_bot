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
    m_rn = re.search(r"(?im)^\s*REPORT\s*#\s*:\s*([^\n]+)", norm)
    report_no = _z3(m_rn.group(1)) if m_rn else ""

    # Extract combined reference from Inspection Reference or Name
    m_ref = re.search(r"(?im)^\s*INSPECTION\s*REFERENCE\s*:\s*([^\n]+)", norm)
    if not m_ref:
        m_ref = re.search(r"(?im)^\s*NAME\s*:\s*([^\n]+)", norm)

    site_code = ""
    if m_ref:
        val = m_ref.group(1).strip().upper()
        m_sc = re.search(r"\b([A-Z]{3,10}[A-Z0-9_-]{0,10})\b", val)
        if m_sc:
            site_code = m_sc.group(1)
        if not report_no:
            m_num = re.search(r"\b(\d{1,3})\b", val)
            if m_num:
                report_no = _z3(m_num.group(1))

    if not (site_code and report_no):
        return None

    return ReportIdentity(site_code=site_code, report_no=report_no)
