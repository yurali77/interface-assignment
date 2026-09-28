import inspect
from pathlib import Path

from interface_automation.models.artifact import Action, CapabilityArtifact, Step
from interface_automation.models.replay import (
    EffectiveCapability,
    ExecutionContext,
    FailureResult,
    ReplayRequest,
    ResolutionMetadata,
    SuccessResult,
)
from interface_automation.replay import engine as replay_engine_module
from interface_automation.replay.engine import ReplayEngine
from interface_automation.surface.base import (
    LiveSession,
    Observation,
    SurfaceActionResult,
    SurfaceFailure,
    TargetVisibility,
)


def _artifact_payload() -> dict:
    from importlib.util import module_from_spec, spec_from_file_location

    path = Path(__file__).with_name("test_capability_artifact.py")
    spec = spec_from_file_location("test_capability_artifact", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._minimal_artifact_payload()


def _request(steps: list[dict] | None = None) -> ReplayRequest:
    payload = _artifact_payload()
    if steps is not None:
        payload["steps"] = steps
    return ReplayRequest(
        effective_capability=EffectiveCapability(
            artifact=CapabilityArtifact.model_validate(payload),
            resolution_metadata=ResolutionMetadata(
                base_capability_version="1",
                tenant_id="credit_union_a",
                app_version="v1",
            ),
        ),
        inputs={"member_id": "12345"},
        execution_context=ExecutionContext(
            tenant_id="credit_union_a",
            session_id="session-001",
            environment="local_demo",
        ),
    )


def _session(*, available: bool = True, session_id: str = "session-001") -> LiveSession:
    return LiveSession(session_id=session_id, available=available)


class RecordingFakeSurface:
    def __init__(self, act_result: SurfaceActionResult | None = None) -> None:
        self.calls: list[str] = []
        self.acted_types: list[str] = []
        self.act_result = act_result or SurfaceActionResult(operation_succeeded=True)

    def act(self, action: Action) -> SurfaceActionResult:
        self.calls.append("act")
        self.acted_types.append(action.type)
        return self.act_result

    def observe(self) -> Observation:
        self.calls.append("observe")
        return Observation(
            target_visibilities=[
                TargetVisibility(semantic_name="member_id_field", visible=True)
            ],
            visible_text="",
            target_values=[],
            semantic_states=[],
        )

    def get_session(self) -> LiveSession:
        return _session()


class AllowPolicyEngine(ReplayEngine):
    """Test-only: policy ALLOW so later seams or Surface.act can run."""

    def _check_replay_policy(self, request):
        return "ALLOW"

    def _check_step_policy(self, step: Step):
        return "ALLOW"


class OpenSeamsEngine(AllowPolicyEngine):
    """Test-only: all skeleton seams succeed so orchestration order can be asserted."""

    def __init__(self, surface: RecordingFakeSurface, log: list[str] | None = None) -> None:
        super().__init__(surface)
        self._log = log if log is not None else []

    def _check_step_policy(self, step: Step):
        self._log.append("policy")
        return "ALLOW"

    def _evaluate_runtime_conditions(self, step, observation):
        return "CONTINUE"

    def _verify_step_completion(self, step, observation, act_result) -> bool:
        return True

    def _verify_success_checkpoint(self, request, observation) -> bool:
        return True

    def _verify_required_outputs(self, request) -> bool:
        return True


class CompletionFailingEngine(AllowPolicyEngine):
    def _evaluate_runtime_conditions(self, step, observation):
        return "CONTINUE"

    def _verify_step_completion(self, step, observation, act_result) -> bool:
        return False


def test_session_unavailable_returns_failure() -> None:
    result = ReplayEngine(RecordingFakeSurface()).execute(
        _request(), _session(available=False)
    )
    assert isinstance(result, FailureResult)
    assert result.failure.category == "SESSION_FAILURE"
    assert result.failure.code == "SESSION_UNAVAILABLE"


def test_session_id_mismatch_returns_failure() -> None:
    result = ReplayEngine(RecordingFakeSurface()).execute(
        _request(), _session(session_id="other-session")
    )
    assert isinstance(result, FailureResult)
    assert result.failure.category == "SESSION_FAILURE"
    assert result.failure.code == "SESSION_ID_MISMATCH"


def test_unimplemented_policy_does_not_call_surface_act() -> None:
    surface = RecordingFakeSurface()
    result = ReplayEngine(surface).execute(_request(), _session())
    assert isinstance(result, FailureResult)
    assert result.failure.code == "SEAM_NOT_IMPLEMENTED"
    assert surface.calls == []


def test_unimplemented_semantics_do_not_return_success() -> None:
    result = ReplayEngine(RecordingFakeSurface()).execute(_request(), _session())
    assert not isinstance(result, SuccessResult)
    assert isinstance(result, FailureResult)


def test_policy_act_observe_order() -> None:
    surface = RecordingFakeSurface()
    log: list[str] = []
    result = OpenSeamsEngine(surface, log).execute(_request(), _session())
    assert isinstance(result, SuccessResult)
    assert log + surface.calls == ["policy", "act", "observe"]


def test_surface_action_failure_stops_replay() -> None:
    surface = RecordingFakeSurface(
        act_result=SurfaceActionResult(
            operation_succeeded=False,
            failure=SurfaceFailure(
                category="TARGET_RESOLUTION",
                message="unresolved",
            ),
        )
    )
    result = AllowPolicyEngine(surface).execute(_request(), _session())
    assert isinstance(result, FailureResult)
    assert result.failure.category == "TARGET_RESOLUTION"
    assert result.step_context.current_step_id == "enter_member_id"
    assert result.step_context.last_completed_step_id is None
    assert surface.calls == ["act"]


def test_last_completed_step_id_updates_only_after_completion_seam() -> None:
    failed = CompletionFailingEngine(RecordingFakeSurface()).execute(
        _request(), _session()
    )
    assert isinstance(failed, FailureResult)
    assert failed.failure.category == "STEP_VERIFICATION"
    assert failed.step_context.last_completed_step_id is None

    succeeded = OpenSeamsEngine(RecordingFakeSurface()).execute(_request(), _session())
    assert isinstance(succeeded, SuccessResult)
    assert succeeded.step_context.last_completed_step_id == "enter_member_id"


def test_replay_uses_artifact_step_order() -> None:
    request = _request(
        steps=[
            {
                "step_id": "enter_member_id",
                "action": {
                    "type": "TYPE",
                    "target": {
                        "semantic_name": "member_id_field",
                        "target_kind": "CONTROL",
                    },
                    "value_binding": "{{member_id}}",
                },
            },
            {
                "step_id": "submit_member_search",
                "action": {
                    "type": "CLICK",
                    "target": {
                        "semantic_name": "search_button",
                        "target_kind": "CONTROL",
                    },
                },
            },
        ]
    )
    surface = RecordingFakeSurface()
    result = OpenSeamsEngine(surface).execute(request, _session())
    assert isinstance(result, SuccessResult)
    assert surface.acted_types == ["TYPE", "CLICK"]
    assert result.step_context.last_completed_step_id == "submit_member_search"


def test_replay_engine_has_no_playwright_or_llm_imports() -> None:
    source = inspect.getsource(replay_engine_module)
    assert "import playwright" not in source
    assert "from playwright" not in source
    lowered = source.lower()
    assert "openai" not in lowered
    assert "anthropic" not in lowered
    assert "llm" not in lowered
