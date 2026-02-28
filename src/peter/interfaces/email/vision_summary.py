from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VisionSummary:
    blocking: list[str]
    notable: list[str]


def summarize_vision_json(
    *,
    vision_json_path: str | Path,
    max_notable: int = 5,
    notable_min_conf: float = 0.85,
) -> VisionSummary:
    """Create short, email-friendly bullet lines from vision JSON.

    The JSON schema is produced by ReportService.analyze_report_visuals().
    We keep it conservative:
    - "blocking" = findings that look severe/high-confidence and are PHOTO-based
    - "notable" = PHOTO-based, confidence >= threshold, not obviously severe

    Output lines include page number and confidence.
    """

    p = Path(vision_json_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    pages = data.get("pages") or []

    blocking: list[tuple[float, str]] = []
    notable: list[tuple[float, str]] = []

    sev_rank = {"CRITICAL": 4, "HIGH": 3, "MED": 2, "LOW": 1}

    for page in pages:
        page_num = int(page.get("page") or page.get("page_number") or 0) or 0
        findings = page.get("findings") or []
        for f in findings:
            try:
                basis = str(f.get("evidence_basis") or "").upper()
                if basis != "PHOTO":
                    continue
                conf = float(f.get("confidence") or 0.0)
                sev = str(f.get("severity") or "LOW").upper()
                defect = str(f.get("defect") or "").strip()
                notes = str(f.get("notes") or "").strip()
                canon = f.get("canonical_defects") or []
                canon_s = ",".join(str(x) for x in canon) if canon else ""

                line = f"- Page {page_num}: {defect} (sev={sev} conf={conf:.2f}{' canon='+canon_s if canon_s else ''})"
                if notes:
                    line += f" — {notes[:140]}"

                # Blocking heuristic: HIGH/CRITICAL and reasonably confident.
                if sev_rank.get(sev, 1) >= 3 and conf >= 0.80:
                    blocking.append((conf + 0.1 * sev_rank.get(sev, 1), line))
                elif conf >= notable_min_conf:
                    notable.append((conf + 0.05 * sev_rank.get(sev, 1), line))
            except Exception:
                continue

    # Sort by score desc
    blocking_lines = [l for _, l in sorted(blocking, key=lambda x: x[0], reverse=True)]
    notable_lines = [l for _, l in sorted(notable, key=lambda x: x[0], reverse=True)][: max_notable]

    return VisionSummary(blocking=blocking_lines, notable=notable_lines)
