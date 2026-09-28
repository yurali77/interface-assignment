import pytest

from interface_automation.models.artifact import (
    ClickAction,
    CompositeCondition,
    ControlTarget,
    ExpectedState,
    NavigateAction,
    ReadAction,
    ResultExpectation,
    RouteMatchesCondition,
    SemanticStateCondition,
    Step,
    TargetNotVisibleCondition,
    TargetVisibleCondition,
    TextPresentCondition,
    ValueEqualsCondition,
    WaitAction,
)
from interface_automation.replay.engine import ReplayEngine, _SeamNotImplemented
from interface_automation.surface.base import (
    LiveSession,
    Observation,
    SurfaceActionResult,
    TargetValue,
    TargetVisibility,
)


class _UnusedSurface:
    def act(self, action):
        raise AssertionError("Surface.act should not run in unit tests")

    def observe(self):
        raise AssertionError("Surface.observe should not run in unit tests")

    def get_session(self) -> LiveSession:
        return LiveSession(session_id="session-001", available=True)


def _engine() -> ReplayEngine:
    return ReplayEngine(_UnusedSurface())


def _target(name: str) -> ControlTarget:
    return ControlTarget(semantic_name=name, target_kind="CONTROL")


def _observation(
    *,
    visibilities: list[TargetVisibility] | None = None,
    visible_text: str = "",
    values: list[TargetValue] | None = None,
    states: list[str] | None = None,
) -> Observation:
    return Observation(
        target_visibilities=visibilities or [],
        visible_text=visible_text,
        target_values=values or [],
        semantic_states=states or [],
    )


def test_target_visible_true() -> None:
    condition = TargetVisibleCondition(target=_target("panel"))
    observation = _observation(
        visibilities=[TargetVisibility(semantic_name="panel", visible=True)]
    )
    assert _engine()._evaluate_condition(condition, observation) is True


def test_target_visible_false_when_explicitly_hidden() -> None:
    condition = TargetVisibleCondition(target=_target("panel"))
    observation = _observation(
        visibilities=[TargetVisibility(semantic_name="panel", visible=False)]
    )
    assert _engine()._evaluate_condition(condition, observation) is False


def test_target_not_visible_only_on_explicit_false() -> None:
    condition = TargetNotVisibleCondition(target=_target("dialog"))
    hidden = _observation(
        visibilities=[TargetVisibility(semantic_name="dialog", visible=False)]
    )
    shown = _observation(
        visibilities=[TargetVisibility(semantic_name="dialog", visible=True)]
    )
    assert _engine()._evaluate_condition(condition, hidden) is True
    assert _engine()._evaluate_condition(condition, shown) is False


def test_missing_target_does_not_satisfy_target_not_visible() -> None:
    condition = TargetNotVisibleCondition(target=_target("dialog"))
    with pytest.raises(_SeamNotImplemented, match="not observed"):
        _engine()._evaluate_condition(condition, _observation())


def test_text_present() -> None:
    condition = TextPresentCondition(text="Member not found")
    assert (
        _engine()._evaluate_condition(
            condition, _observation(visible_text="Error: Member not found")
        )
        is True
    )
    assert (
        _engine()._evaluate_condition(condition, _observation(visible_text="OK"))
        is False
    )


def test_value_equals() -> None:
    condition = ValueEqualsCondition(
        target=_target("member_id_display"),
        expected_value="12345",
    )
    matching = _observation(
        values=[TargetValue(semantic_name="member_id_display", value="12345")]
    )
    mismatch = _observation(
        values=[TargetValue(semantic_name="member_id_display", value="999")]
    )
    assert _engine()._evaluate_condition(condition, matching) is True
    assert _engine()._evaluate_condition(condition, mismatch) is False


def test_semantic_state() -> None:
    condition = SemanticStateCondition(state="CONFIRMATION_SCREEN")
    assert (
        _engine()._evaluate_condition(
            condition, _observation(states=["CONFIRMATION_SCREEN"])
        )
        is True
    )
    assert _engine()._evaluate_condition(condition, _observation(states=["LOADING"])) is False


def test_nested_and_or() -> None:
    condition = CompositeCondition(
        type="AND",
        conditions=[
            SemanticStateCondition(state="CONFIRMATION_SCREEN"),
            CompositeCondition(
                type="OR",
                conditions=[
                    TextPresentCondition(text="Saved"),
                    TextPresentCondition(text="Done"),
                ],
            ),
        ],
    )
    observation = _observation(
        visible_text="Done",
        states=["CONFIRMATION_SCREEN"],
    )
    assert _engine()._evaluate_condition(condition, observation) is True
    observation_fail = _observation(visible_text="Nope", states=["CONFIRMATION_SCREEN"])
    assert _engine()._evaluate_condition(condition, observation_fail) is False


def test_unsupported_route_matches_fails_closed() -> None:
    with pytest.raises(_SeamNotImplemented, match="ROUTE_MATCHES"):
        _engine()._evaluate_condition(RouteMatchesCondition(), _observation())


def test_click_with_satisfied_expected_state_completes() -> None:
    step = Step(
        step_id="submit",
        action=ClickAction(target=_target("search_button")),
        expected_state=ExpectedState(
            condition=TargetVisibleCondition(target=_target("panel"))
        ),
    )
    observation = _observation(
        visibilities=[TargetVisibility(semantic_name="panel", visible=True)]
    )
    act = SurfaceActionResult(operation_succeeded=True)
    assert _engine()._verify_step_completion(step, observation, act) is True


def test_click_with_failed_expected_state_does_not_complete() -> None:
    step = Step(
        step_id="submit",
        action=ClickAction(target=_target("search_button")),
        expected_state=ExpectedState(
            condition=TargetVisibleCondition(target=_target("panel"))
        ),
    )
    observation = _observation(
        visibilities=[TargetVisibility(semantic_name="panel", visible=False)]
    )
    act = SurfaceActionResult(operation_succeeded=True)
    assert _engine()._verify_step_completion(step, observation, act) is False


def test_state_changing_action_without_expected_state_does_not_auto_complete() -> None:
    step = Step(
        step_id="submit",
        action=ClickAction(target=_target("search_button")),
    )
    with pytest.raises(_SeamNotImplemented, match="expected_state"):
        _engine()._verify_step_completion(
            step,
            _observation(),
            SurfaceActionResult(operation_succeeded=True),
        )


def test_read_with_non_empty_extracted_value_completes() -> None:
    step = Step(
        step_id="read_confirmation",
        action=ReadAction(target=_target("confirmation_id"), output_binding="confirmation_id"),
        result_expectation=ResultExpectation(type="string", non_empty=True),
    )
    act = SurfaceActionResult(operation_succeeded=True, extracted_value="ABC123")
    assert _engine()._verify_step_completion(step, _observation(), act) is True


def test_read_empty_value_with_non_empty_expectation_fails() -> None:
    step = Step(
        step_id="read_confirmation",
        action=ReadAction(target=_target("confirmation_id"), output_binding="confirmation_id"),
        result_expectation=ResultExpectation(type="string", non_empty=True),
    )
    act = SurfaceActionResult(operation_succeeded=True, extracted_value="")
    assert _engine()._verify_step_completion(step, _observation(), act) is False


def test_navigate_and_wait_remain_fail_closed() -> None:
    act = SurfaceActionResult(operation_succeeded=True)
    with pytest.raises(_SeamNotImplemented, match="NAVIGATE"):
        _engine()._verify_step_completion(
            Step(step_id="go", action=NavigateAction()),
            _observation(),
            act,
        )
    with pytest.raises(_SeamNotImplemented, match="WAIT"):
        _engine()._verify_step_completion(
            Step(step_id="pause", action=WaitAction()),
            _observation(),
            act,
        )
