from __future__ import annotations

import sqlite3


class EmailAttachmentRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(
        self,
        *,
        email_event_id: int,
        filename: str,
        content_type: str | None,
        sha256: str,
        stored_path: str | None,
        quarantined: bool,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO email_attachments (
              email_event_id, filename, content_type, sha256, stored_path, quarantined
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(email_event_id),
                filename,
                content_type,
                sha256,
                stored_path,
                1 if quarantined else 0,
            ),
        )
        return int(cur.lastrowid)
