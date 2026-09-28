import inspect

from interface_automation.models.artifact import Action, ClickAction, ControlTarget, ReadAction
from interface_automation.surface import base as surface_base
from interface_automation.surface.base import (
    LiveSession,
    Observation,
    Surface,
    SurfaceActionResult,
    SurfaceFailure,
    TargetValue,
    TargetVisibility,
)


def _button() -> ControlTarget:
    return ControlTarget(semantic_name="search_button", target_kind="CONTROL")


class FakeSurface:
    def act(self, action: Action) -> SurfaceActionResult:
        if isinstance(action, ReadAction):
            return SurfaceActionResult(
                operation_succeeded=True,
                extracted_value="CONF-1",
            )
        return SurfaceActionResult(operation_succeeded=True)

    def observe(self) -> Observation:
        return Observation(
            target_visibilities=[
                TargetVisibility(semantic_name="search_button", visible=True)
            ],
            visible_text="Search",
            target_values=[],
            semantic_states=["MEMBER_SEARCH"],
        )

    def get_session(self) -> LiveSession:
        return LiveSession(session_id="session-001", available=True)


def test_surface_action_result_success() -> None:
    result = SurfaceActionResult(operation_succeeded=True)
    assert result.operation_succeeded is True
    assert result.extracted_value is None
    assert result.failure is None


def test_read_result_carries_extracted_value() -> None:
    result = SurfaceActionResult(
        operation_succeeded=True,
        extracted_value="CONF-1",
    )
    assert result.extracted_value == "CONF-1"


def test_failed_action_carries_surface_failure() -> None:
    failure = SurfaceFailure(
        category="TARGET_RESOLUTION",
        message="Could not resolve search_button",
    )
    result = SurfaceActionResult(operation_succeeded=False, failure=failure)
    assert result.operation_succeeded is False
    assert result.failure == failure
    assert result.extracted_value is None


def test_observation_construction() -> None:
    observation = Observation(
        target_visibilities=[
            TargetVisibility(semantic_name="search_button", visible=True)
        ],
        visible_text="Member not found",
        target_values=[TargetValue(semantic_name="member_id_display", value="12345")],
        semantic_states=["LOADING"],
    )
    names = {item.semantic_name for item in observation.target_visibilities}
    assert "member_detail_panel" not in names
    assert observation.visible_text == "Member not found"


def test_live_session_construction() -> None:
    session = LiveSession(session_id="session-001", available=True)
    assert session.session_id == "session-001"
    assert session.available is True


def test_fake_surface_implements_interface() -> None:
    surface: Surface = FakeSurface()
    click = ClickAction(target=_button())
    result = surface.act(click)
    assert result.operation_succeeded is True
    observation = surface.observe()
    assert isinstance(observation, Observation)
    session = surface.get_session()
    assert session.available is True
    assert isinstance(surface, Surface)


def test_surface_base_does_not_depend_on_playwright() -> None:
    source = inspect.getsource(surface_base)
    assert "import playwright" not in source
    assert "from playwright" not in source
