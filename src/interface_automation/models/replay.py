"""Replay entry and result models. Replay receives an already resolved EffectiveCapability."""

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from interface_automation.models.artifact import CapabilityArtifact

_FORBIDDEN_EXTRAS = ConfigDict(extra="forbid")

# Invocation / output values are JSON-like scalars. Frozen examples are strings only;
# a closed domain type system is not specified.
InvocationValue: TypeAlias = str | int | float | bool

FailureCategory = Literal[
    "INPUT_VALIDATION",
    "ARTIFACT_VALIDATION",
    "TARGET_RESOLUTION",
    "STEP_VERIFICATION",
    "RUNTIME_CONDITION",
    "OUTPUT_EXTRACTION",
    "CHECKPOINT_FAILURE",
    "POLICY_BLOCK",
    "SESSION_FAILURE",
    "UNKNOWN",
]


class ResolutionMetadata(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    base_capability_version: str
    tenant_id: str
    app_version: str
    applied_override_id: str | None = None


class EffectiveCapability(BaseModel):
    """Thin wrapper around a resolved CapabilityArtifact. Not a Registry."""

    model_config = _FORBIDDEN_EXTRAS

    artifact: CapabilityArtifact
    resolution_metadata: ResolutionMetadata


class ExecutionContext(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    tenant_id: str
    session_id: str
    environment: str


class ReplayRequest(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    effective_capability: EffectiveCapability
    inputs: dict[str, InvocationValue]
    execution_context: ExecutionContext


class StepContext(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    last_completed_step_id: str | None = None
    current_step_id: str | None = None


class RuntimeEvent(BaseModel):
    """Lightweight recoverable-event record. Not a full event taxonomy."""

    model_config = _FORBIDDEN_EXTRAS

    type: str
    code: str
    step_id: str | None = None
    retry_number: int | None = None
    resolved: bool | None = None


class CheckpointVerification(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    checkpoint_id: str | None = None
    verified: bool


class FailureObservation(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    summary: str


class OutcomePayload(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    code: str
    description: str
    payload: dict[str, InvocationValue] | None = None


class FailureInfo(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    category: FailureCategory
    code: str
    message: str
    expected: FailureObservation | None = None
    observed: FailureObservation | None = None


class EscalationInfo(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    intervention_id: str
    reason_code: str
    reason: str
    control_owner: Literal["HUMAN"]
    resume_allowed: bool


class _ReplayResultCommon(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    run_id: str
    capability_id: str
    capability_version: str
    session_id: str
    started_at: str
    finished_at: str | None = None
    step_context: StepContext
    runtime_events: list[RuntimeEvent]
    evidence_refs: list[str]


class SuccessResult(_ReplayResultCommon):
    status: Literal["SUCCESS"] = "SUCCESS"
    outputs: dict[str, InvocationValue]
    checkpoint: CheckpointVerification


class BusinessOutcomeResult(_ReplayResultCommon):
    status: Literal["BUSINESS_OUTCOME"] = "BUSINESS_OUTCOME"
    outcome: OutcomePayload


class FailureResult(_ReplayResultCommon):
    status: Literal["FAILURE"] = "FAILURE"
    failure: FailureInfo


class EscalatedResult(_ReplayResultCommon):
    status: Literal["ESCALATED"] = "ESCALATED"
    escalation: EscalationInfo


ReplayResult = Annotated[
    SuccessResult | BusinessOutcomeResult | FailureResult | EscalatedResult,
    Field(discriminator="status"),
]
