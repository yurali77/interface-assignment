"""Minimal local Member Search page for the first UI slice.

Stdlib only. No Playwright, Replay, or Surface integration.
"""

from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal
from urllib.parse import parse_qs

VALID_MEMBER_ID = "12345"
VALID_MEMBER_NAME = "Demo Member"

SearchOutcome = Literal["idle", "found", "not_found"]


def lookup(member_id: str) -> tuple[str, str] | None:
    if member_id == VALID_MEMBER_ID:
        return VALID_MEMBER_ID, VALID_MEMBER_NAME
    return None


def render_page(
    *,
    submitted_id: str | None = None,
    outcome: SearchOutcome = "idle",
) -> str:
    member_id_value = html.escape(submitted_id or "", quote=True)
    result_html = ""
    if outcome == "found":
        result_html = f"""
<section
  id="member_detail_panel"
  data-semantic-name="member_detail_panel"
  role="region"
  aria-label="Member Detail"
>
  <h2>Member Detail</h2>
  <table border="1" cellpadding="4" cellspacing="0">
    <tr>
      <th>Member ID</th>
      <td>
        <span id="member_id_display" data-semantic-name="member_id_display"
          >{html.escape(VALID_MEMBER_ID)}</span>
      </td>
    </tr>
    <tr>
      <th>Name</th>
      <td>
        <span id="member_name_display" data-semantic-name="member_name_display"
          >{html.escape(VALID_MEMBER_NAME)}</span>
      </td>
    </tr>
  </table>
</section>
"""
    elif outcome == "not_found":
        result_html = """
<p id="member_not_found" data-semantic-name="member_not_found">Member not found</p>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Member Servicing</title>
</head>
<body>
  <h1>Member Search</h1>
  <form
    id="member_search_form"
    data-semantic-name="member_search_form"
    method="post"
    action="/"
  >
    <label for="member_id">Member ID</label>
    <input
      type="text"
      id="member_id"
      name="member_id"
      data-semantic-name="member_id_field"
      value="{member_id_value}"
    >
    <button type="submit" data-semantic-name="search_button">Search</button>
  </form>
  {result_html}
</body>
</html>
"""


def _decode_form(body: bytes, content_type: str) -> dict[str, list[str]]:
    if "application/x-www-form-urlencoded" not in content_type:
        return {}
    return parse_qs(body.decode("utf-8"), keep_blank_values=True)


def _page_for_submitted_id(submitted_id: str | None) -> str:
    if submitted_id is None:
        return render_page(outcome="idle")
    if lookup(submitted_id) is not None:
        return render_page(submitted_id=submitted_id, outcome="found")
    return render_page(submitted_id=submitted_id, outcome="not_found")


class MemberSearchHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._respond(200, render_page(outcome="idle"))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        form = _decode_form(body, self.headers.get("Content-Type", ""))
        submitted = form.get("member_id", [None])[0]
        self._respond(200, _page_for_submitted_id(submitted))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _respond(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), MemberSearchHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Member Search demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(f"Member Search demo: http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
