"""Mock MCP tool server. Rejects every call that lacks the Sentinel-minted downstream token (invariant 5).

It also holds the mail sink: what actually reached the "outside world" is measured here, not at the
gateway, so a leak is judged by what was delivered, never by what a verdict said.
"""

from __future__ import annotations

import hmac
import io
from pathlib import Path
import os
import posixpath
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware
from pypdf import PdfReader
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


def build_tools_server(downstream_token: str, uploads_dir: Path | None = None) -> tuple[FastMCP, MailSink]:
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

    # ---- the general-purpose tools (core plan B3). All sandboxed: no real network, no real files, no commands run. ----
    pdfs = {path: fixtures.make_pdf(visible, hidden) for path, (visible, hidden) in fixtures.DOCUMENTS.items()}
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.execute("CREATE TABLE customers (id INTEGER, name TEXT, email TEXT, phone TEXT, city TEXT, owes INTEGER)")
    db.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)", fixtures.CUSTOMERS)
    db.execute("CREATE TABLE salaries (employee_id TEXT, name TEXT, annual_inr INTEGER)")
    db.executemany("INSERT INTO salaries VALUES (?,?,?)", fixtures.SALARIES)
    db.commit()
    db.execute("PRAGMA query_only = ON")

    def read_only(action, *_args):  # SELECT, reading columns and calling functions only: no writes, PRAGMA, ATTACH or DDL
        return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION) \
            else sqlite3.SQLITE_DENY

    db.set_authorizer(read_only)  # query_only alone could be switched off by the agent with "PRAGMA query_only=OFF"
    db_lock = threading.Lock()

    def who() -> dict[str, str]:
        h = get_http_headers(include_all=True)
        return {"session_id": h.get(SESSION_HEADER, "unknown"), "column": h.get(COLUMN_HEADER, "unknown")}

    def sandbox_path(path: str) -> str:
        p = path.replace("\\", "/")
        if ".." in p.split("/") or "\x00" in p:
            raise ToolError("the path must stay inside the sandbox")
        return posixpath.normpath("/" + p.lstrip("/")).lstrip("/")

    def uploaded() -> dict[str, Path]:
        """Documents the officer uploaded into a chat (plan Q10): `uploads/<name>.pdf`, read fresh on every call."""
        if uploads_dir is None or not uploads_dir.is_dir():
            return {}
        return {f"uploads/{p.name}": p for p in sorted(uploads_dir.glob("*.pdf")) if p.is_file()}

    @server.tool
    def list_documents(folder: str = "reports") -> str:
        """List the documents in a folder."""
        f = sandbox_path(folder)
        names = sorted(p for p in [*pdfs, *uploaded()] if p.startswith(f.rstrip("/") + "/") or p == f)
        return "\n".join(names) if names else f"No documents in {folder}."

    @server.tool
    def read_document(path: str) -> str:
        """Read a PDF document and return its text."""
        p = sandbox_path(path)
        files = uploaded()
        if p in files:  # read exactly as a person's PDF reader would extract it, hidden text included
            data = files[p].read_bytes()
        elif p in pdfs:
            data = pdfs[p]
        else:
            return f"No document at {path}."
        return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages).strip()

    @server.tool
    def query_db(sql: str) -> str:
        """Run one read-only SQL query on the company database (tables: customers, salaries)."""
        statement = sql.strip().rstrip(";")
        if not statement or ";" in statement or not sqlite3.complete_statement(statement + ";"):
            raise ToolError("send exactly one complete SQL statement")
        try:
            with db_lock:
                cur = db.execute(statement)
                rows = cur.fetchmany(50)
                header = [d[0] for d in (cur.description or [])]
        except sqlite3.Error as e:
            raise ToolError(f"the database refused that query: {e}") from e
        return "\n".join([" | ".join(header), *(" | ".join(str(v) for v in r) for r in rows)]) if header else "OK"

    @server.tool
    def fetch_url(url: str) -> str:
        """Fetch a web page (a mock web: no real network request is ever made)."""
        page = fixtures.WEB_PAGES.get(url)
        if page is None or "?" in url or "#" in url:
            # A request to somewhere we did not serve, or one carrying a query string, is something that "reached outside".
            sink.record(**who(), to=url, subject="GET", body="")
        return page if page is not None else "404 Not Found (mock web)"

    @server.tool
    def http_post(url: str, body: str) -> str:
        """POST text to a web address (a mock endpoint: it is recorded, never sent anywhere)."""
        sink.record(**who(), to=url, subject="POST", body=body)
        return "200 OK (mock)"

    @server.tool
    def write_file(path: str, content: str) -> str:
        """Write a text file inside the sandbox."""
        sink.record(**who(), to="file:/" + sandbox_path(path), subject="WRITE", body=content)
        return f"Wrote {path}."

    @server.tool
    def run_command(command: str) -> str:
        """Run a shell command. This demo never executes anything: it only proves the officer's approval gate."""
        return "Refused: this demo environment never runs commands."

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
    uploads = os.environ.get("SENTINEL_UPLOADS_DIR")
    server, _ = build_tools_server(token, Path(uploads) if uploads else None)
    uvicorn.run(server.http_app(), host="127.0.0.1", port=int(os.environ.get("SENTINEL_TOOLS_PORT", "8200")),
                log_level="warning")


if __name__ == "__main__":
    main()
