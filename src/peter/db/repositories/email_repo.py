from __future__ import annotations

import json
import sqlite3


class EmailEventRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_event(
        self,
        *,
        site_id: int | None,
        graph_message_id: str | None,
        internet_message_id: str | None,
        conversation_id: str | None,
        subject: str,
        from_address: str,
        to_addresses: list[str],
        cc_addresses: list[str],
        has_external_recipients: bool,
        command_type: str,
        archived_eml_path: str | None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO email_events (
              site_id, graph_message_id, internet_message_id, conversation_id,
              subject, from_address, to_addresses, cc_addresses,
              has_external_recipients, command_type, archived_eml_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site_id,
                graph_message_id,
                internet_message_id,
                conversation_id,
                subject,
                from_address,
                json.dumps([a.lower() for a in (to_addresses or [])]),
                json.dumps([a.lower() for a in (cc_addresses or [])]),
                1 if has_external_recipients else 0,
                command_type,
                archived_eml_path,
            ),
        )
        return int(cur.lastrowid)
