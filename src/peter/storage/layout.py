from __future__ import annotations

import os


def use_report_folders() -> bool:
    """Feature flag for Option B storage layout."""

    return os.getenv("PETER_STORAGE_REPORT_FOLDERS", "").strip().lower() in ("1", "true", "yes")
