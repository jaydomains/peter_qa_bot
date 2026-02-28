from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfirmCommand:
    kind: str  # CONFIRM|REJECT|NONE
    qid: str | None
    site: str | None
    report: str | None


def parse_confirm_subject(subject: str) -> ConfirmCommand:
    s = (subject or "").strip()
    if not s:
        return ConfirmCommand("NONE", None, None, None)

    m = re.match(r"^(CONFIRM|REJECT)\s+(Q-\d{8}-\d{6}-[0-9a-fA-F]{4})\s*(?:\|\s*(.*))?$", s, flags=re.I)
    if not m:
        return ConfirmCommand("NONE", None, None, None)

    kind = m.group(1).upper()
    qid = m.group(2)
    rest = (m.group(3) or "").strip()

    site = None
    report = None
    if rest:
        # parse tokens like SITE=PRSVNQA | REPORT=006
        parts = [p.strip() for p in rest.split("|") if p.strip()]
        for p in parts:
            if "=" not in p:
                continue
            k, v = [x.strip() for x in p.split("=", 1)]
            k = k.upper()
            v = v.strip().upper().replace(" ", "")
            if k == "SITE":
                site = v
            elif k in ("REPORT", "REF", "REPORTNO"):
                report = v

    return ConfirmCommand(kind, qid, site, report)
