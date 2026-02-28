from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from peter.config.settings import Settings
from peter.domain.errors import ValidationError


@dataclass(frozen=True)
class ReportContext:
    site_code: str
    report_code: str
    sha256: str
    received_at: str
    result: str | None
    stored_path: str
    executive_summary_excerpt: str | None
    issues: list[dict]


def _load_report_context(*, conn: sqlite3.Connection, settings: Settings, site_code: str, report_code: str) -> ReportContext:
    sc = (site_code or "").strip().upper()
    rc = (report_code or "").strip().upper().replace(" ", "")

    row = conn.execute(
        """
        SELECT r.id, r.sha256, r.stored_path, r.received_at, r.result, s.site_code
        FROM reports r
        JOIN sites s ON s.id = r.site_id
        WHERE s.site_code = ? AND r.report_code = ?
        ORDER BY r.received_at DESC
        LIMIT 1
        """,
        (sc, rc),
    ).fetchone()
    if not row:
        raise ValidationError(f"Report not found for site={sc} report_code={rc}")

    report_id = int(row["id"])

    # Load issues (most recent triage/analysis output)
    issues = [
        dict(r)
        for r in conn.execute(
            """
            SELECT issue_type, category, severity, is_blocking, description, created_at
            FROM issues
            WHERE report_id = ?
            ORDER BY is_blocking DESC, severity DESC, created_at DESC
            """,
            (report_id,),
        ).fetchall()
    ]

    # Best-effort: build an executive summary excerpt from cached extracted text if present.
    executive_excerpt = None
    try:
        from peter.services.report_service import ReportService

        svc = ReportService(conn, settings)
        # reuse internal loader by asking for summary; it already extracts excerpts.
        txt = svc.summarize_report_text(site_code=sc, report_code=rc)
        # Extract just the executive excerpt block from the summary output.
        marker = "EXECUTIVE SUMMARY (excerpt)"
        if marker in txt:
            executive_excerpt = txt.split(marker, 1)[1].strip()
            # keep it bounded
            executive_excerpt = executive_excerpt[:2000].strip()
    except Exception:
        executive_excerpt = None

    return ReportContext(
        site_code=sc,
        report_code=rc,
        sha256=str(row["sha256"]),
        received_at=str(row["received_at"]),
        result=(str(row["result"]) if row["result"] is not None else None),
        stored_path=str(row["stored_path"]),
        executive_summary_excerpt=executive_excerpt,
        issues=issues,
    )


def answer_report_question(
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    site_code: str,
    report_code: str,
    question: str,
    mode: str = "grounded",
) -> str:
    """Answer a question about a report.

    mode:
      - grounded: answers only from stored context; avoids speculation
      - recommend: includes a clearly-labeled recommendations section

    NOTE: This is a baseline implementation (no LLM call yet). It produces
    consistent, grounded answers using the triaged issues + executive excerpt.
    """

    ctx = _load_report_context(conn=conn, settings=settings, site_code=site_code, report_code=report_code)
    q = (question or "").strip()
    if not q:
        raise ValidationError("question is required")

    lines: list[str] = []
    lines.append("ANSWER (grounded)")
    lines.append(f"site={ctx.site_code} report={ctx.report_code} result={ctx.result} received_at={ctx.received_at}")
    lines.append(f"stored_path={ctx.stored_path}")

    # Heuristic: if they ask "why warn" or "summary", surface blocking issues first.
    ql = q.lower()
    if ("why" in ql and ("warn" in ql or "warning" in ql)) or "summary" in ql or "issues" in ql:
        if not ctx.issues:
            lines.append("- No issues recorded for this report yet. Run triage-report first.")
        else:
            lines.append("\nKEY ISSUES")
            for it in ctx.issues[:10]:
                block = "BLOCKING" if int(it.get("is_blocking") or 0) else "NON-BLOCKING"
                lines.append(f"- [{it['severity']}] [{block}] {it['category']}")

            lines.append("\nSource: issues table (triage-report)")

        if ctx.executive_summary_excerpt:
            lines.append("\nEXECUTIVE SUMMARY (excerpt)")
            lines.append(ctx.executive_summary_excerpt)
            lines.append("\nSource: report text (Executive Summary excerpt)")

    else:
        # For arbitrary questions, be explicit about limitations.
        lines.append(f"Question: {q}")
        lines.append(
            "I can answer grounded questions from: triaged issues + extracted report text excerpts. "
            "Ask about 'why WARN', 'top issues', 'moisture', 'DFT', or request a draft response in recommend mode."
        )

    if mode == "recommend":
        lines.append("\nRECOMMENDATIONS (explicit; still grounded to findings)")
        if not ctx.issues:
            lines.append("- Run triage-report to generate issues; then I can propose actions tied to each issue.")
        else:
            # Minimal action templates.
            for it in ctx.issues[:10]:
                cat = str(it["category"]).lower()
                if "dft" in cat:
                    lines.append("- Request DFT re-testing and documented compliance with the specified minimum microns before sign-off (warranty-critical).")
                elif "moisture" in cat:
                    lines.append("- Require substrate moisture readings within spec (document locations + instruments) before further coating; investigate cause of elevated moisture.")
                elif "delamination" in cat:
                    lines.append("- Stop-and-fix: investigate adhesion failure root cause (prep/primer/moisture) and implement manufacturer-approved remediation.")
                else:
                    lines.append(f"- Review and address: {it['category']}")
        lines.append("\nNote: Recommendations are not new facts; they are proposed actions based on the grounded issues above.")

    return "\n".join(lines) + "\n"
