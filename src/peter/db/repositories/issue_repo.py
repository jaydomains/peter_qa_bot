from __future__ import annotations

import sqlite3


class IssueRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def delete_for_report(self, report_id: int) -> None:
        self.conn.execute(
            "DELETE FROM issues WHERE report_id = ?",
            (int(report_id),),
        )

    def insert(
        self,
        *,
        report_id: int,
        issue_type: str,
        category: str,
        description: str,
        severity: str,
        is_blocking: bool,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO issues (report_id, issue_type, category, description, severity, is_blocking)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (report_id, issue_type, category, description, severity, 1 if is_blocking else 0),
        )
        return int(cur.lastrowid)
