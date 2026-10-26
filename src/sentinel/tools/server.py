"""Mock MCP tool server. Rejects every call that lacks the Sentinel-minted downstream token (invariant 5).

It also holds the mail sink: what actually reached the "outside world" is measured here, not at the
gateway, so a leak is judged by what was delivered, never by what a verdict said.
"""

from __future__ import annotations

import hmac
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .. import fixtures

TOKEN_HEADER = "x-sentinel-token"
SESSION_HEADER = "x-sentinel-session"
COLUMN_HEADER = "x-sentinel-column"


@dataclass
class MailSink:
    """Everything the agent managed to send, with the session and column that sent it."""

    delivered: list[dict] = field(default_factory=list)
    bank_changes: list[dict] = field(default_factory=list)  # what actually changed in the vendor records
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, **fields) -> None:
        with self._lock:
            self.delivered.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **fields})

    def snapshot(self, column: str | None = None) -> list[dict]:
        with self._lock:
            return [m for m in self.delivered if column in (None, m["column"])]

    def clear(self) -> None:
        with self._lock:
            self.delivered.clear()


def build_tools_server(downstream_token: str) -> tuple[FastMCP, MailSink]:
    if not downstream_token:
        raise ValueError("a downstream token is required; the tool server never runs open")
    sink = MailSink()
    server = FastMCP("mock-tools")

    def authorised(headers: dict[str, str]) -> bool:
        return hmac.compare_digest(headers.get(TOKEN_HEADER, ""), downstream_token)

    class RequireDownstreamToken(Middleware):
        async def on_request(self, context, call_next):
            if not authorised(get_http_headers(include_all=True)):
                raise ToolError("401: missing or invalid Sentinel token")
            return await call_next(context)

    server.add_middleware(RequireDownstreamToken())

    @server.tool
    def read_quotation(quote_id: str) -> str:
        """Read an incoming vendor quotation by id."""
        return fixtures.QUOTATIONS.get(quote_id, f"No quotation found with id {quote_id}.")

    @server.tool
    def query_stock(item: str) -> str:
        """Look up current stock for an item in the stock register."""
        return fixtures.STOCK_REGISTER

    @server.tool
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email."""
        headers = get_http_headers(include_all=True)
        sink.record(session_id=headers.get(SESSION_HEADER, "unknown"), column=headers.get(COLUMN_HEADER, "unknown"),
                    to=to, subject=subject, body=body)
        return f"Email sent to {to}."

    @server.tool
    def update_vendor_bank(vendor: str, account_number: str) -> str:
        """Change the bank account the vendor is paid into."""
        headers = get_http_headers(include_all=True)
        with sink._lock:
            sink.bank_changes.append({"session_id": headers.get(SESSION_HEADER, "unknown"),
                                      "column": headers.get(COLUMN_HEADER, "unknown"),
                                      "vendor": vendor, "account_number": account_number})
        return f"Bank details for {vendor} updated."

    @server.tool
    def delete_records(table: str) -> str:
        """Delete all records in a table. Registered in nothing: exists to prove unknown tools are blocked."""
        headers = get_http_headers(include_all=True)
        sink.record(session_id=headers.get(SESSION_HEADER, "unknown"), column=headers.get(COLUMN_HEADER, "unknown"),
                    to="", subject="DELETE", body=table)
        return f"Deleted {table}."

    @server.custom_route("/inbox", methods=["GET"])
    async def inbox(request: Request):
        if not authorised(dict(request.headers)):
            return JSONResponse({"error": "unauthorised"}, status_code=401)
        return JSONResponse({"delivered": sink.snapshot(request.query_params.get("column"))})

    @server.custom_route("/reset", methods=["POST"])
    async def reset(request: Request):
        if not authorised(dict(request.headers)):
            return JSONResponse({"error": "unauthorised"}, status_code=401)
        sink.clear()
        return JSONResponse({"ok": True})

    return server, sink


def main() -> None:  # python -m sentinel.tools.server
    import uvicorn

    token = os.environ.get("SENTINEL_DOWNSTREAM_TOKEN", "")
    if not token:
        raise SystemExit("SENTINEL_DOWNSTREAM_TOKEN is not set; the tool server refuses to start without it")
    server, _ = build_tools_server(token)
    uvicorn.run(server.http_app(), host="127.0.0.1", port=int(os.environ.get("SENTINEL_TOOLS_PORT", "8200")),
                log_level="warning")


if __name__ == "__main__":
    main()
