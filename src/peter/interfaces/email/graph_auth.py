from __future__ import annotations

import json
import urllib.parse
import urllib.request


class GraphAuthError(RuntimeError):
    pass


def client_credentials_token(*, tenant_id: str, client_id: str, client_secret: str) -> str:
    """Obtain an app-only Microsoft Graph token via OAuth2 client credentials."""

    if not (tenant_id and client_id and client_secret):
        raise GraphAuthError("Missing Graph tenant/client/secret")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        }
    ).encode("utf-8")

    req = urllib.request.Request(token_url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        raise GraphAuthError(f"Token request failed: {e}") from e

    payload = json.loads(raw)
    tok = payload.get("access_token")
    if not tok:
        raise GraphAuthError(f"No access_token in response: {payload}")
    return str(tok)
