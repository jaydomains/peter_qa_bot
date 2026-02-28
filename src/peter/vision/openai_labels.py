from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error


class LabelsVisionError(RuntimeError):
    pass


@dataclass(frozen=True)
class LabelProduct:
    page_number: int
    raw_text: str
    product_code: str | None
    brand: str | None
    confidence: float
    notes: str


def _post_responses(*, api_key: str, model: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        details = ""
        try:
            details = e.read().decode("utf-8", errors="replace")
        except Exception:
            details = ""
        raise LabelsVisionError(f"OpenAI error HTTP {e.code}: {details}".strip())
    except Exception as e:
        raise LabelsVisionError(str(e))
    return json.loads(raw)


def extract_label_products(*, api_key: str, model: str, page_number: int, image_path: Path) -> list[LabelProduct]:
    """A label-focused vision pass.

    Use on pages that likely contain product containers/labels.
    """

    img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")

    prompt = (
        "You are extracting paint product identifiers from images. "
        "Look ONLY for paint drums/buckets/containers and read visible label text. "
        "Return a JSON array of observed products. "
        "For each item include raw_text, optional product_code (e.g. PP700/PU800) if clearly visible, optional brand, confidence, notes. "
        "Do not invent codes. If nothing is visible, return an empty array."
    )

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["raw_text", "confidence"],
            "properties": {
                "raw_text": {"type": "string"},
                "product_code": {"type": ["string", "null"]},
                "brand": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "notes": {"type": "string"},
            },
        },
    }

    payload: dict[str, Any] = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{img_b64}"},
                ],
            }
        ],
        "temperature": float(os.getenv("PETER_LABELS_TEMPERATURE", "0.0")),
        "response_format": {"type": "json_schema", "json_schema": {"name": "label_products", "schema": schema}},
    }

    data = _post_responses(api_key=api_key, model=model, payload=payload)

    out_text = data.get("output_text")
    if not out_text:
        # fallback scan
        for item in data.get("output", []) or []:
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text" and c.get("text"):
                    out_text = c["text"]
                    break

    if not out_text:
        return []

    try:
        arr = json.loads(out_text)
    except Exception:
        return []

    prods: list[LabelProduct] = []
    for it in arr or []:
        raw = str(it.get("raw_text") or "").strip()
        if not raw:
            continue
        prods.append(
            LabelProduct(
                page_number=page_number,
                raw_text=raw,
                product_code=(str(it.get("product_code")).strip().upper().replace(" ", "") if it.get("product_code") else None),
                brand=(str(it.get("brand")).strip().upper() if it.get("brand") else None),
                confidence=float(it.get("confidence") or 0.0),
                notes=str(it.get("notes") or ""),
            )
        )

    return prods
