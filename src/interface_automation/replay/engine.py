"""ReplayEngine orchestration skeleton. Full replay semantics are not implemented."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from interface_automation.models.artifact import (
    ClickAction,
    CompositeCondition,
    Condition,
    NavigateAction,
    ReadAction,
    RouteMatchesCondition,
    SelectAction,
    SemanticStateCondition,
    Step,
    TargetNotVisibleCondition,
    TargetVisibleCondition,
    TextPresentCondition,
    TypeAction,
    ValueEqualsCondition,
    WaitAction,
)
from interface_automation.models.replay import (
    CheckpointVerification,
    FailureCategory,
    FailureInfo,
    FailureResult,
    ReplayRequest,
    ReplayResult,
    StepContext,
    SuccessResult,
)
from interface_automation.surface.base import (
    LiveSession,
    Observation,
    Surface,
    SurfaceActionResult,
    SurfaceFailure,
)

_PolicyDecision = Literal["ALLOW"]
_RuntimeSeamResult = Literal["CONTINUE"]

_SURFACE_FAILURE_CATEGORY: dict[str, FailureCategory] = {
    "TARGET_RESOLUTION": "TARGET_RESOLUTION",
    "SESSION": "SESSION_FAILURE",
    "OPERATION": "UNKNOWN",
}


class _SeamNotImplemented(Exception):
    """Fail-closed signal for unimplemented Replay semantics."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.category: FailureCategory = "UNKNOWN"
        self.code = "SEAM_NOT_IMPLEMENTED"
        self.message = message


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ReplayEngine:
    """Deterministic replay orchestrator. Unimplemented seams fail closed."""

    def __init__(self, surface: Surface) -> None:
        self._surface = surface

    def execute(
        self, request: ReplayRequest, session: LiveSession
    ) -> ReplayResult:
        started_at = _utc_now()
        run_id = uuid4().hex
        identity = request.effective_capability.artifact.identity
        last_completed_step_id: str | None = None
        current_step_id: str | None = None
        last_observation: Observation | None = None

        def fail(
            category: FailureCategory,
            code: str,
            message: str,
        ) -> FailureResult:
            return FailureResult(
                run_id=run_id,
                capability_id=identity.capability_id,
                capability_version=identity.capability_version,
                session_id=session.session_id,
                started_at=started_at,
                finished_at=_utc_now(),
                step_context=StepContext(
                    last_completed_step_id=last_completed_step_id,
                    current_step_id=current_step_id,
                ),
                runtime_events=[],
                evidence_refs=[],
                failure=FailureInfo(category=category, code=code, message=message),
            )

        if not session.available:
            return fail(
                "SESSION_FAILURE",
                "SESSION_UNAVAILABLE",
                "LiveSession is not available.",
            )
        if request.execution_context.session_id != session.session_id:
            return fail(
                "SESSION_FAILURE",
                "SESSION_ID_MISMATCH",
                "ReplayRequest.execution_context.session_id does not match LiveSession.",
            )

        try:
            self._check_replay_policy(request)

            for step in request.effective_capability.artifact.steps:
                current_step_id = step.step_id
                self._check_step_policy(step)

                act_result = self._surface.act(step.action)
                if not act_result.operation_succeeded:
                    return fail(*_map_surface_failure(act_result.failure))

                last_observation = self._surface.observe()
                self._evaluate_runtime_conditions(step, last_observation)

                if not self._verify_step_completion(
                    step, last_observation, act_result
                ):
                    return fail(
                        "STEP_VERIFICATION",
                        "STEP_COMPLETION_UNVERIFIED",
                        "Step-completion seam did not succeed.",
                    )
                last_completed_step_id = step.step_id

            if not self._verify_success_checkpoint(request, last_observation):
                return fail(
                    "CHECKPOINT_FAILURE",
                    "SUCCESS_CHECKPOINT_UNVERIFIED",
                    "Success-checkpoint seam did not succeed.",
                )
            if not self._verify_required_outputs(request):
                return fail(
                    "OUTPUT_EXTRACTION",
                    "REQUIRED_OUTPUTS_UNVERIFIED",
                    "Required-output seam did not succeed.",
                )
        except _SeamNotImplemented as exc:
            return fail(exc.category, exc.code, exc.message)

        return SuccessResult(
            run_id=run_id,
            capability_id=identity.capability_id,
            capability_version=identity.capability_version,
            session_id=session.session_id,
            started_at=started_at,
            finished_at=_utc_now(),
            step_context=StepContext(
                last_completed_step_id=last_completed_step_id,
                current_step_id=current_step_id,
            ),
            runtime_events=[],
            evidence_refs=[],
            outputs={},
            checkpoint=CheckpointVerification(verified=True),
        )

    def _check_replay_policy(self, request: ReplayRequest) -> _PolicyDecision:
        raise _SeamNotImplemented("Policy Engine is not implemented.")

    def _check_step_policy(self, step: Step) -> _PolicyDecision:
        raise _SeamNotImplemented("Policy Engine is not implemented.")

    def _evaluate_runtime_conditions(
        self, step: Step, observation: Observation
    ) -> _RuntimeSeamResult:
        raise _SeamNotImplemented("Runtime-condition evaluation is not implemented.")

    def _evaluate_condition(
        self, condition: Condition, observation: Observation
    ) -> bool:
        """Return whether a condition is true on observed facts.

        Missing target facts are unresolved (fail closed), not false.
        """
        if isinstance(condition, RouteMatchesCondition):
            raise _SeamNotImplemented("ROUTE_MATCHES is not implemented.")
        if isinstance(condition, TargetVisibleCondition):
            visible = _observed_visibility(observation, condition.target.semantic_name)
            if visible is None:
                raise _SeamNotImplemented(
                    f"Target {condition.target.semantic_name!r} was not observed."
                )
            return visible is True
        if isinstance(condition, TargetNotVisibleCondition):
            visible = _observed_visibility(observation, condition.target.semantic_name)
            if visible is None:
                raise _SeamNotImplemented(
                    f"Target {condition.target.semantic_name!r} was not observed."
                )
            return visible is False
        if isinstance(condition, TextPresentCondition):
            return condition.text in observation.visible_text
        if isinstance(condition, ValueEqualsCondition):
            value = _observed_value(observation, condition.target.semantic_name)
            if value is None:
                raise _SeamNotImplemented(
                    f"Value for {condition.target.semantic_name!r} was not observed."
                )
            return value == condition.expected_value
        if isinstance(condition, SemanticStateCondition):
            return condition.state in observation.semantic_states
        if isinstance(condition, CompositeCondition):
            if condition.type == "AND":
                return _evaluate_and(self, condition.conditions, observation)
            return _evaluate_or(self, condition.conditions, observation)
        raise _SeamNotImplemented("Unsupported condition type.")

    def _verify_step_completion(
        self,
        step: Step,
        observation: Observation,
        act_result: SurfaceActionResult,
    ) -> bool:
        action = step.action
        if isinstance(action, NavigateAction | WaitAction):
            raise _SeamNotImplemented(
                f"{action.type} step completion is not implemented."
            )
        if isinstance(action, ReadAction):
            if not act_result.operation_succeeded:
                return False
            if act_result.extracted_value is None:
                return False
            if (
                step.result_expectation is not None
                and step.result_expectation.non_empty
                and act_result.extracted_value == ""
            ):
                return False
            return True
        if isinstance(action, ClickAction | TypeAction | SelectAction):
            if step.expected_state is None:
                raise _SeamNotImplemented(
                    f"{action.type} step has no expected_state; completion is unresolved."
                )
            return self._evaluate_condition(
                step.expected_state.condition, observation
            )
        raise _SeamNotImplemented("Unsupported action type for step completion.")

    def _verify_success_checkpoint(
        self, request: ReplayRequest, observation: Observation | None
    ) -> bool:
        raise _SeamNotImplemented("Success-checkpoint evaluation is not implemented.")

    def _verify_required_outputs(self, request: ReplayRequest) -> bool:
        raise _SeamNotImplemented("Required-output extraction is not implemented.")


def _observed_visibility(observation: Observation, semantic_name: str) -> bool | None:
    for item in observation.target_visibilities:
        if item.semantic_name == semantic_name:
            return item.visible
    return None


def _observed_value(observation: Observation, semantic_name: str) -> str | None:
    for item in observation.target_values:
        if item.semantic_name == semantic_name:
            return item.value
    return None


def _evaluate_and(
    engine: ReplayEngine, conditions: list[Condition], observation: Observation
) -> bool:
    unresolved: _SeamNotImplemented | None = None
    for condition in conditions:
        try:
            if not engine._evaluate_condition(condition, observation):
                return False
        except _SeamNotImplemented as exc:
            unresolved = exc
    if unresolved is not None:
        raise unresolved
    return True


def _evaluate_or(
    engine: ReplayEngine, conditions: list[Condition], observation: Observation
) -> bool:
    unresolved: _SeamNotImplemented | None = None
    for condition in conditions:
        try:
            if engine._evaluate_condition(condition, observation):
                return True
        except _SeamNotImplemented as exc:
            unresolved = exc
    if unresolved is not None:
        raise unresolved
    return False


def _map_surface_failure(
    failure: SurfaceFailure | None,
) -> tuple[FailureCategory, str, str]:
    if failure is None:
        return ("UNKNOWN", "SURFACE_OPERATION_FAILED", "Surface.act failed.")
    mapped: FailureCategory = _SURFACE_FAILURE_CATEGORY.get(
        failure.category, "UNKNOWN"
    )
    return (mapped, "SURFACE_OPERATION_FAILED", failure.message)
