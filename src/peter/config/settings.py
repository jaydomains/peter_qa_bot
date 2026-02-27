from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings.

    Phase 1 uses local filesystem + SQLite.
    Phase 2 will extend with Microsoft Graph email integration.
    """

    PROJECT_ROOT: Path
    DATA_DIR: Path
    DB_PATH: Path
    QA_ROOT: Path

    INTERNAL_DOMAIN: str = "khuselabc.co.za"  # overridden by env PETER_INTERNAL_DOMAIN
    BOT_MAILBOX: str = ""
    GRAPH_TOKEN: str = ""  # legacy/dev
    POLL_SECONDS: int = 30

    GRAPH_TENANT_ID: str = ""
    GRAPH_CLIENT_ID: str = ""
    GRAPH_CLIENT_SECRET: str = ""

    OPENAI_API_KEY: str = ""

    # Always CC list (Phase 2). Keep as list of strings; enforce internal-only.
    REVIEW_DLIST: tuple[str, ...] = (
        "james@khuselabc.co.za",
        "carel@khuselabc.co.za",
        "nickc@khuselabc.co.za",
        "jarrod@khuselabc.co.za",
        "qa@khuselabc.co.za",
    )

    @staticmethod
    def load(project_root: Path | None = None) -> "Settings":
        # settings.py is at <project>/src/peter/config/settings.py
        # parents[3] => <project>
        root = (project_root or Path(__file__).resolve().parents[3]).resolve()
        data_dir = Path(os.getenv("PETER_DATA_DIR", root / "data")).resolve()
        db_path = Path(os.getenv("PETER_DB_PATH", data_dir / "qa.db")).resolve()
        qa_root = Path(os.getenv("PETER_QA_ROOT", data_dir / "QA_ROOT")).resolve()

        internal_domain = os.getenv("PETER_INTERNAL_DOMAIN", "khuselabc.co.za").strip().lower()
        always_cc_raw = os.getenv("PETER_ALWAYS_CC", "").strip()
        if always_cc_raw:
            always_cc = tuple(a.strip().lower() for a in always_cc_raw.replace(";", ",").split(",") if a.strip())
        else:
            always_cc = (
                "james@khuselabc.co.za",
                "carel@khuselabc.co.za",
                "nickc@khuselabc.co.za",
                "jarrod@khuselabc.co.za",
                "qa@khuselabc.co.za",
            )

        return Settings(
            PROJECT_ROOT=root,
            DATA_DIR=data_dir,
            DB_PATH=db_path,
            QA_ROOT=qa_root,
            INTERNAL_DOMAIN=internal_domain,
            REVIEW_DLIST=always_cc,
            BOT_MAILBOX=os.getenv("PETER_BOT_MAILBOX", ""),
            GRAPH_TOKEN=os.getenv("PETER_GRAPH_TOKEN", ""),
            POLL_SECONDS=int(os.getenv("PETER_POLL_SECONDS", "30")),
            GRAPH_TENANT_ID=os.getenv("PETER_GRAPH_TENANT_ID", ""),
            GRAPH_CLIENT_ID=os.getenv("PETER_GRAPH_CLIENT_ID", ""),
            GRAPH_CLIENT_SECRET=os.getenv("PETER_GRAPH_CLIENT_SECRET", ""),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        )

    def ensure_paths_exist(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.QA_ROOT.mkdir(parents=True, exist_ok=True)
        (self.QA_ROOT / "SITES").mkdir(parents=True, exist_ok=True)
