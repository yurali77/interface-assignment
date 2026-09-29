from http.client import HTTPConnection
from threading import Thread

from interface_automation.demo.member_search import (
    VALID_MEMBER_ID,
    VALID_MEMBER_NAME,
    make_server,
    render_page,
)


def test_initial_page_has_search_controls() -> None:
    html = render_page(outcome="idle")
    assert 'for="member_id">Member ID</label>' in html
    assert ">Search</button>" in html
    assert 'data-semantic-name="member_id_field"' in html
    assert "Member Detail" not in html
    assert "Member not found" not in html


def test_valid_member_render_shows_detail() -> None:
    html = render_page(submitted_id=VALID_MEMBER_ID, outcome="found")
    assert 'aria-label="Member Detail"' in html
    assert f">{VALID_MEMBER_ID}<" in html
    assert VALID_MEMBER_NAME in html
    assert "Member not found" not in html


def test_invalid_member_render_shows_not_found() -> None:
    html = render_page(submitted_id="99999", outcome="not_found")
    assert "Member not found" in html
    assert 'aria-label="Member Detail"' not in html


def test_http_valid_and_invalid_search() -> None:
    server = make_server("127.0.0.1", 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        conn = HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/")
        idle = conn.getresponse().read().decode("utf-8")
        assert ">Search</button>" in idle
        assert "Member not found" not in idle

        conn.request(
            "POST",
            "/",
            body=f"member_id={VALID_MEMBER_ID}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        found = conn.getresponse().read().decode("utf-8")
        assert "Member Detail" in found
        assert VALID_MEMBER_NAME in found
        assert f">{VALID_MEMBER_ID}<" in found

        conn.request(
            "POST",
            "/",
            body="member_id=99999",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        missing = conn.getresponse().read().decode("utf-8")
        assert "Member not found" in missing
        assert "Member Detail" not in missing
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
