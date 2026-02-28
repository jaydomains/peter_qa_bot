from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProductAllowlist:
    codes: set[str]
    names: set[str]
    aliases: set[str]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def load_allowlist(products_json_path: Path) -> ProductAllowlist:
    data: dict[str, Any] = json.loads(Path(products_json_path).read_text(encoding="utf-8"))
    codes: set[str] = set()
    names: set[str] = set()
    aliases: set[str] = set()

    for p in data.get("paint_products") or []:
        code = p.get("code")
        if code:
            codes.add(_norm(str(code)))
        prod = p.get("product")
        if prod:
            names.add(_norm(str(prod)))
        for a in p.get("aliases") or []:
            aliases.add(_norm(str(a)))

    return ProductAllowlist(codes=codes, names=names, aliases=aliases)


def match_observed(*, allow: ProductAllowlist, raw_text: str, code: str | None) -> bool:
    if code:
        c = _norm(code)
        if c in allow.codes:
            return True

    t = _norm(raw_text)
    if not t:
        return False

    # Substring match against names/aliases (strict-ish)
    for n in allow.names | allow.aliases:
        if n and n in t:
            return True

    return False
