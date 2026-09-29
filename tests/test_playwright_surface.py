from __future__ import annotations

import inspect
from collections.abc import Iterator
from threading import Thread

import pytest
from playwright.sync_api import sync_playwright

from interface_automation.demo.member_search import VALID_MEMBER_ID, VALID_MEMBER_NAME, make_server
from interface_automation.models.artifact import ClickAction, ControlTarget, ReadAction, TypeAction
from interface_automation.surface.base import Observation, Surface, SurfaceActionResult, SurfaceFailure
from interface_automation.surface.playwright import PlaywrightSurface


def _member_id_field() -> ControlTarget:
    return ControlTarget(
        semantic_name="member_id_field",
        target_kind="CONTROL",
        label="Member ID",
    )


def _search_button() -> ControlTarget:
    return ControlTarget(
        semantic_name="search_button",
        target_kind="CONTROL",
        role="button",
        accessible_name="Search",
    )


def _member_id_display() -> ControlTarget:
    return ControlTarget(semantic_name="member_id_display", target_kind="TEXT")


def _missing_field() -> ControlTarget:
    return ControlTarget(
        semantic_name="does_not_exist",
        target_kind="CONTROL",
        label="No Such Field",
    )


def _visibility_names(observation: Observation) -> dict[str, bool]:
    return {item.semantic_name: item.visible for item in observation.target_visibilities}


@pytest.fixture
def demo_url() -> Iterator[str]:
    server = make_server("127.0.0.1", 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def surface(demo_url: str) -> Iterator[PlaywrightSurface]:
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        page = browser.new_page()
        page.goto(demo_url)
        try:
            yield PlaywrightSurface(page=page, session_id="demo-session-1")
        finally:
            browser.close()


def test_playwright_surface_implements_protocol(surface: PlaywrightSurface) -> None:
    assert isinstance(surface, Surface)
    session = surface.get_session()
    assert session.session_id == "demo-session-1"
    assert session.available is True


def test_type_into_member_id_field(surface: PlaywrightSurface) -> None:
    result = surface.act(
        TypeAction(target=_member_id_field(), value_binding=VALID_MEMBER_ID)
    )
    assert result.operation_succeeded is True
    observation = surface.observe()
    values = {item.semantic_name: item.value for item in observation.target_values}
    assert values["member_id_field"] == VALID_MEMBER_ID


def test_click_search_valid_member_reaches_detail(surface: PlaywrightSurface) -> None:
    surface.act(TypeAction(target=_member_id_field(), value_binding=VALID_MEMBER_ID))
    result = surface.act(ClickAction(target=_search_button()))
    assert result.operation_succeeded is True
    observation = surface.observe()
    names = _visibility_names(observation)
    assert names.get("member_detail_panel") is True
    assert VALID_MEMBER_NAME in observation.visible_text
    assert "Member Detail" in observation.visible_text


def test_click_search_invalid_member_shows_not_found(surface: PlaywrightSurface) -> None:
    surface.act(TypeAction(target=_member_id_field(), value_binding="99999"))
    result = surface.act(ClickAction(target=_search_button()))
    assert result.operation_succeeded is True
    observation = surface.observe()
    names = _visibility_names(observation)
    assert "member_detail_panel" not in names
    assert names.get("member_not_found") is True
    assert "Member not found" in observation.visible_text


def test_read_displayed_member_id(surface: PlaywrightSurface) -> None:
    surface.act(TypeAction(target=_member_id_field(), value_binding=VALID_MEMBER_ID))
    surface.act(ClickAction(target=_search_button()))
    result = surface.act(
        ReadAction(target=_member_id_display(), output_binding="member_id")
    )
    assert result.operation_succeeded is True
    assert result.extracted_value == VALID_MEMBER_ID


def test_observe_reports_search_page_facts(surface: PlaywrightSurface) -> None:
    observation = surface.observe()
    names = _visibility_names(observation)
    assert names.get("member_id_field") is True
    assert names.get("search_button") is True
    assert "member_detail_panel" not in names
    assert "Search" in observation.visible_text
    assert observation.semantic_states == []


def test_unresolved_target_returns_target_resolution(surface: PlaywrightSurface) -> None:
    result = surface.act(ClickAction(target=_missing_field()))
    assert result.operation_succeeded is False
    assert result.failure is not None
    assert result.failure.category == "TARGET_RESOLUTION"


def test_surface_public_models_do_not_use_playwright() -> None:
    from interface_automation.surface import base as surface_base

    source = inspect.getsource(surface_base)
    assert "import playwright" not in source
    assert "from playwright" not in source
    for model in (Observation, SurfaceActionResult, SurfaceFailure):
        assert "playwright" not in inspect.getsource(model)
