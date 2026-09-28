"""ReplayEngine orchestration skeleton. Full replay semantics are not implemented."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from interface_automation.models.artifact import Step
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

    def _verify_step_completion(
        self,
        step: Step,
        observation: Observation,
        act_result: SurfaceActionResult,
    ) -> bool:
        raise _SeamNotImplemented("Step-completion verification is not implemented.")

    def _verify_success_checkpoint(
        self, request: ReplayRequest, observation: Observation | None
    ) -> bool:
        raise _SeamNotImplemented("Success-checkpoint evaluation is not implemented.")

    def _verify_required_outputs(self, request: ReplayRequest) -> bool:
        raise _SeamNotImplemented("Required-output extraction is not implemented.")


def _map_surface_failure(
    failure: SurfaceFailure | None,
) -> tuple[FailureCategory, str, str]:
    if failure is None:
        return ("UNKNOWN", "SURFACE_OPERATION_FAILED", "Surface.act failed.")
    mapped: FailureCategory = _SURFACE_FAILURE_CATEGORY.get(
        failure.category, "UNKNOWN"
    )
    return (mapped, "SURFACE_OPERATION_FAILED", failure.message)
