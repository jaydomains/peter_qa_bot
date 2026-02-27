from __future__ import annotations

import sqlite3

from peter.config.settings import Settings


import re
import shutil
from pathlib import Path

from peter.db.repositories.site_repo import SiteRepository
from peter.db.repositories.report_repo import ReportRepository
from peter.domain.errors import ValidationError
from peter.parsing.pdf_text import extract_pdf_text, has_meaningful_text
from peter.storage.filestore import ensure_site_folders
from peter.util.hashing import sha256_file


class ReportService:
    """Milestone M3: report ingestion (storage + idempotency + text extraction).

    Vision + analysis is M4.
    """

    def __init__(self, conn: sqlite3.Connection, settings: Settings):
        self.conn = conn
        self.settings = settings
        self.site_repo = SiteRepository(conn)
        self.report_repo = ReportRepository(conn)

    def _validate_report_code(self, report_code: str) -> str:
        rc = (report_code or "").strip().upper().replace(" ", "")
        if not re.fullmatch(r"R\d{2}", rc):
            raise ValidationError("report_code must look like R01 / R12")
        return rc

    def ingest_report(self, *, site_code: str, report_code: str, file_path: Path) -> dict:
        site_code = (site_code or "").strip().upper()
        rc = self._validate_report_code(report_code)
        path = Path(file_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise ValidationError(f"Report file not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValidationError("Report must be a PDF")

        site = self.site_repo.get_by_code(site_code)
        if not site:
            raise ValidationError(f"Unknown site_code: {site_code}")

        sandbox = ensure_site_folders(self.settings, folder_name=site.folder_name)

        sha = sha256_file(path)
        existing = self.report_repo.get_by_site_sha(site.id, sha)
        if existing:
            return {
                "status": "duplicate",
                "report_id": existing.id,
                "overall_result": existing.result,
                "sha256": sha,
            }

        safe_filename = f"{site.site_code}__REPORT__{rc}__{sha[:12]}.pdf"
        stored_pdf = sandbox.build_path("02_reports", safe_filename)
        shutil.copy2(path, stored_pdf)

        # Extract text for later analysis (M4)
        text = extract_pdf_text(stored_pdf)
        meaningful = has_meaningful_text(text)
        extracted_rel = None
        if meaningful:
            txt_name = f"{site.site_code}__REPORT__{rc}__{sha[:12]}.txt"
            txt_path = sandbox.build_path("00_admin", txt_name)
            txt_path.write_text(text, encoding="utf-8")
            extracted_rel = str(txt_path.relative_to(self.settings.QA_ROOT))

        stored_rel = str(stored_pdf.relative_to(self.settings.QA_ROOT))
        report_id = self.report_repo.insert(
            site_id=site.id,
            report_code=rc,
            filename=safe_filename,
            sha256=sha,
            stored_path=stored_rel,
            result=None,
            review_md_path=None,
            review_json_path=None,
        )

        return {
            "status": "ok",
            "report_id": report_id,
            "overall_result": None,
            "sha256": sha,
            "stored_path": stored_rel,
            "extracted_text_path": extracted_rel,
        }
