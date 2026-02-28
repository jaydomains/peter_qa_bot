from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from peter.config.settings import Settings
from peter.domain.errors import ValidationError
from peter.interfaces.qa.openai_ask import ask_openai_responses


@dataclass(frozen=True)
class EvidencePack:
    metadata: str
    exec_excerpt: str
    issues: str
    vision: str


def _build_evidence_pack(
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    site_code: str,
    report_code: str,
    vision_text: str,
) -> EvidencePack:
    sc = (site_code or "").strip().upper()
    rc = (report_code or "").strip().upper().replace(" ", "")

    row = conn.execute(
        """
        SELECT r.id, r.sha256, r.stored_path, r.received_at, r.result
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

    meta = (
        f"site={sc}\n"
        f"report_code={rc}\n"
        f"received_at={row['received_at']}\n"
        f"result={row['result']}\n"
        f"sha256={row['sha256']}\n"
        f"stored_path={row['stored_path']}\n"
    )

    # Executive summary excerpt (reuse existing summary generator)
    exec_excerpt = "(not available)"
    try:
        from peter.services.report_service import ReportService

        svc = ReportService(conn, settings)
        summary = svc.summarize_report_text(site_code=sc, report_code=rc)
        marker = "EXECUTIVE SUMMARY (excerpt)"
        if marker in summary:
            exec_excerpt = summary.split(marker, 1)[1].strip()
            # Keep bounded
            exec_excerpt = exec_excerpt[:3500].strip()
    except Exception:
        exec_excerpt = "(not available)"

    # Issues
    issues_rows = conn.execute(
        """
        SELECT issue_type, category, severity, is_blocking, description
        FROM issues
        WHERE report_id = ?
        ORDER BY is_blocking DESC,
                 CASE severity WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3 WHEN 'MED' THEN 2 ELSE 1 END DESC,
                 created_at DESC
        """,
        (report_id,),
    ).fetchall()

    if not issues_rows:
        issues_text = "(none)"
    else:
        lines = []
        for r in issues_rows[:30]:
            block = "blocking" if int(r["is_blocking"] or 0) else "non-blocking"
            desc = str(r["description"] or "")
            desc = desc.replace("\r", " ").strip()
            lines.append(f"- [{r['severity']}] [{block}] {r['category']} ({r['issue_type']}): {desc[:260]}")
        issues_text = "\n".join(lines)

    vision_text = (vision_text or "").strip() or "(not available)"

    return EvidencePack(metadata=meta, exec_excerpt=exec_excerpt, issues=issues_text, vision=vision_text)


def draft_email_reply_llm(
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    site_code: str,
    report_code: str,
    vision_text: str,
) -> str:
    """Draft a human-like QA email reply using OpenAI, grounded in evidence."""

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValidationError("OPENAI_API_KEY not set")

    pack = _build_evidence_pack(
        conn=conn,
        settings=settings,
        site_code=site_code,
        report_code=report_code,
        vision_text=vision_text,
    )

    # Conditional depth
    has_blocking = "[blocking]" in pack.issues
    depth = "deep" if has_blocking or ("Blocking" in pack.vision) else "executive"

    model = os.getenv("PETER_EMAIL_DRAFT_MODEL", "gpt-4.1")

    system = (
        "You are PETER, the QA lead for decorative architectural coatings, replacing a human reviewer. "
        "You MUST be grounded: only use the EVIDENCE provided. "
        "If something is not explicitly supported by evidence, say you cannot confirm it. "
        "Write like a competent human QA reviewer: specific, decisive, and practical. "
        "Scope: paint only (ignore repair materials unless directly relevant to paint performance). "
        "Always include a short EVIDENCE section at the end listing which sources you relied on."
    )

    user = (
        f"DEPTH: {depth}\n"
        "Write an email reply suitable for internal QA stakeholders.\n"
        "Tone: professional, direct, human.\n\n"
        "EVIDENCE (only source of truth):\n"
        "--- METADATA ---\n"
        f"{pack.metadata}\n"
        "--- EXEC_SUMMARY ---\n"
        f"{pack.exec_excerpt}\n\n"
        "--- ISSUES (DB) ---\n"
        f"{pack.issues}\n\n"
        "--- VISION ---\n"
        f"{pack.vision}\n\n"
        "OUTPUT REQUIREMENTS:\n"
        "- Start with: OVERALL STATUS: PASS/WARN/FAIL (choose based on evidence; if result in metadata is set, respect it)\n"
        "- Then: Key findings (bullets). For each key finding, cite source inline: (Source: EXEC_SUMMARY) or (Source: ISSUES) or (Source: VISION pX).\n"
        "- Then: Required actions (bullets). Tie each action to a finding and cite source.\n"
        "- If DEPTH is deep: include a short 'What to verify next visit' section.\n"
        "- End with: EVIDENCE (short list of what you used).\n"
    )

    return ask_openai_responses(api_key=api_key, model=model, system=system, user=user).strip() + "\n"
