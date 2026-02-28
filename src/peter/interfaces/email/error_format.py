from __future__ import annotations

import time
import traceback
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorEnvelope:
    error_id: str
    stage: str
    message: str
    exc_type: str


def make_error_id() -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    import secrets

    return f"ERR-{ts}-{secrets.token_hex(2)}"


def format_error_email(*, cmd: str, stage: str, error_id: str, exc: BaseException, hint: str | None = None) -> str:
    et = type(exc).__name__
    msg = str(exc)
    lines = [
        "ERROR",
        f"- error_id: {error_id}",
        f"- command: {cmd}",
        f"- stage: {stage}",
        f"- exception: {et}: {msg}",
    ]
    if hint:
        lines.append(f"- next_step: {hint}")
    lines.append("\n(Full traceback is in server logs: journalctl -u peter | grep " + error_id + ")")
    return "\n".join(lines) + "\n"


def format_trace_for_logs(*, error_id: str, exc: BaseException) -> str:
    return f"{error_id}\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
