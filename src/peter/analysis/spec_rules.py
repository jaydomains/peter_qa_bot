from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SpecRules:
    required_primer_codes: list[str]
    forbidden_primer_codes: list[str]


def default_rules() -> SpecRules:
    return SpecRules(required_primer_codes=["PP700", "PP 700"], forbidden_primer_codes=["ELASTOSHIELD", "PES"])


def load_rules(path: Path) -> SpecRules:
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return SpecRules(
        required_primer_codes=[str(x).upper() for x in (data.get("required_primer_codes") or [])],
        forbidden_primer_codes=[str(x).upper() for x in (data.get("forbidden_primer_codes") or [])],
    )


def write_default(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "required_primer_codes": default_rules().required_primer_codes,
                "forbidden_primer_codes": default_rules().forbidden_primer_codes,
                "notes": "Edit to extend coating system role checks. Codes are matched case-insensitively.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
