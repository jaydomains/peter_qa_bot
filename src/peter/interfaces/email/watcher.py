from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from peter.config.settings import Settings
from peter.db.connection import get_connection
from peter.db.schema import init_db
from peter.db.repositories.email_repo import EmailEventRepository
from peter.db.repositories.site_repo import SiteRepository
from peter.interfaces.email.classifier import parse_subject
from peter.interfaces.email.graph_auth import client_credentials_token
from peter.interfaces.email.graph_client import GraphClient
from peter.interfaces.email.recipient_policy import (
    assert_internal_only,
    build_sanitized_reply_recipients,
)
from peter.services.site_service import SiteService
from peter.services.spec_service import SpecService
from peter.services.report_service import ReportService


def _extract_addrs(msg: dict[str, Any], field: str) -> list[str]:
    out: list[str] = []
    for x in msg.get(field, []) or []:
        addr = (x.get("emailAddress") or {}).get("address")
        if addr:
            out.append(str(addr).lower())
    return out


def _has_external(addrs: list[str], *, internal_domain: str) -> bool:
    dom = internal_domain.lower()
    for a in addrs or []:
        if not a.lower().endswith("@" + dom):
            return True
    return False


@dataclass
class EmailWatcher:
    settings: Settings

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.settings.POLL_SECONDS)

    def run_once(self) -> None:
        token = client_credentials_token(
            tenant_id=self.settings.GRAPH_TENANT_ID,
            client_id=self.settings.GRAPH_CLIENT_ID,
            client_secret=self.settings.GRAPH_CLIENT_SECRET,
        )
        graph = GraphClient(token=token)

        with get_connection(self.settings.DB_PATH) as conn:
            init_db(conn)
            site_repo = SiteRepository(conn)
            email_repo = EmailEventRepository(conn)
            site_svc = SiteService(conn, self.settings)
            spec_svc = SpecService(conn, self.settings)
            report_svc = ReportService(conn, self.settings)

            msgs = graph.list_unread_messages(mailbox=self.settings.BOT_MAILBOX, top=10)
            for m in msgs:
                mid = m["id"]
                subject = (m.get("subject") or "").strip()
                cmd = parse_subject(subject)

                from_addr = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
                to_addrs = _extract_addrs(m, "toRecipients")
                cc_addrs = _extract_addrs(m, "ccRecipients")

                all_rcpts = [from_addr] + to_addrs + cc_addrs
                has_ext = _has_external(all_rcpts, internal_domain=self.settings.INTERNAL_DOMAIN)

                # Resolve site id if possible
                site_id = None
                if cmd.site_code:
                    site = site_repo.get_by_code(cmd.site_code)
                    site_id = site.id if site else None

                # TODO: archive original message as .eml (Graph supports $value or MIME content endpoints)
                email_repo.insert_event(
                    site_id=site_id,
                    graph_message_id=mid,
                    internet_message_id=m.get("internetMessageId"),
                    conversation_id=m.get("conversationId"),
                    subject=subject,
                    from_address=from_addr,
                    to_addresses=to_addrs,
                    cc_addresses=cc_addrs,
                    has_external_recipients=has_ext,
                    command_type=cmd.kind,
                    archived_eml_path=None,
                )

                # Build internal-only reply content
                reply_text = ""
                try:
                    if cmd.kind == "NEW_SITE" and cmd.site_code and cmd.arg:
                        site_svc.create_site(site_code=cmd.site_code, site_name=cmd.arg)
                        reply_text = f"OK created site {cmd.site_code}"
                    elif cmd.kind == "SPEC_UPDATE":
                        reply_text = "SPEC UPDATE received. (Attachment ingestion not implemented yet.)"
                    elif cmd.kind == "QA_REPORT":
                        reply_text = "QA REPORT received. (Attachment ingestion not implemented yet.)"
                    elif cmd.kind == "QUERY":
                        reply_text = "QUERY received. (Query via email not implemented yet.)"
                    else:
                        reply_text = "Unrecognized subject format. Expected: QA REPORT | <SITE_CODE> | R01"
                except Exception as e:
                    reply_text = f"ERROR: {e}"

                # Create reply draft
                draft = graph.create_reply_draft(mailbox=self.settings.BOT_MAILBOX, message_id=mid)
                draft_id = draft["id"]

                to_list, cc_list = build_sanitized_reply_recipients(
                    internal_domain=self.settings.INTERNAL_DOMAIN,
                    original_from=from_addr,
                    original_to=to_addrs,
                    original_cc=cc_addrs,
                    bot_mailbox=self.settings.BOT_MAILBOX,
                    forced_cc=list(self.settings.REVIEW_DLIST),
                )
                assert_internal_only(to_list, cc_list, internal_domain=self.settings.INTERNAL_DOMAIN)

                payload = {
                    "toRecipients": [{"emailAddress": {"address": a}} for a in to_list],
                    "ccRecipients": [{"emailAddress": {"address": a}} for a in cc_list],
                    "body": {"contentType": "Text", "content": reply_text},
                }

                graph.update_message(mailbox=self.settings.BOT_MAILBOX, message_id=draft_id, payload=payload)
                graph.send_message(mailbox=self.settings.BOT_MAILBOX, message_id=draft_id)
                graph.mark_read(mailbox=self.settings.BOT_MAILBOX, message_id=mid)


def main() -> None:
    settings = Settings.load()
    settings.ensure_paths_exist()
    EmailWatcher(settings).run_forever()


if __name__ == "__main__":
    main()
