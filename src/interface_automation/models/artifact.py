"""Capability Artifact action and target models (schema v0, first layer)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

_FORBIDDEN_EXTRAS = ConfigDict(extra="forbid")


class ControlTarget(BaseModel):
    """Surface-agnostic semantic identity of a UI object."""

    model_config = _FORBIDDEN_EXTRAS

    semantic_name: str
    target_kind: str
    role: str | None = None
    accessible_name: str | None = None
    label: str | None = None
    context: dict[str, str] | None = None
    fallbacks: list[dict[str, str]] | None = None


class ClickAction(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["CLICK"] = "CLICK"
    target: ControlTarget


class TypeAction(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["TYPE"] = "TYPE"
    target: ControlTarget
    value_binding: str


class SelectAction(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["SELECT"] = "SELECT"
    target: ControlTarget
    value_binding: str


class ReadAction(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["READ"] = "READ"
    target: ControlTarget
    output_binding: str


class NavigateAction(BaseModel):
    """v0 NAVIGATE type. Executable payload fields are not specified in the frozen schema."""

    model_config = _FORBIDDEN_EXTRAS

    type: Literal["NAVIGATE"] = "NAVIGATE"


class WaitAction(BaseModel):
    """v0 WAIT type. Typed Condition and wait/timing ownership are not fully specified."""

    model_config = _FORBIDDEN_EXTRAS

    type: Literal["WAIT"] = "WAIT"


Action = Annotated[
    ClickAction
    | TypeAction
    | SelectAction
    | ReadAction
    | NavigateAction
    | WaitAction,
    Field(discriminator="type"),
]


class TargetVisibleCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["TARGET_VISIBLE"] = "TARGET_VISIBLE"
    target: ControlTarget


class TargetNotVisibleCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["TARGET_NOT_VISIBLE"] = "TARGET_NOT_VISIBLE"
    target: ControlTarget


class TextPresentCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["TEXT_PRESENT"] = "TEXT_PRESENT"
    text: str


class ValueEqualsCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["VALUE_EQUALS"] = "VALUE_EQUALS"
    target: ControlTarget
    expected_value: str


class RouteMatchesCondition(BaseModel):
    """v0 ROUTE_MATCHES type. Comparison/pattern payload is not specified in the frozen schema."""

    model_config = _FORBIDDEN_EXTRAS

    type: Literal["ROUTE_MATCHES"] = "ROUTE_MATCHES"


class SemanticStateCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["SEMANTIC_STATE"] = "SEMANTIC_STATE"
    state: str


class CompositeCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["AND", "OR"]
    conditions: list["Condition"]


Condition = Annotated[
    TargetVisibleCondition
    | TargetNotVisibleCondition
    | TextPresentCondition
    | ValueEqualsCondition
    | RouteMatchesCondition
    | SemanticStateCondition
    | CompositeCondition,
    Field(discriminator="type"),
]

CompositeCondition.model_rebuild()


class ExpectedState(BaseModel):
    """Step-level post-condition wrapper matching `expected_state.condition`."""

    model_config = _FORBIDDEN_EXTRAS

    condition: Condition


class ResultExpectation(BaseModel):
    """READ step completion expectation; lives on Step, not ReadAction."""

    model_config = _FORBIDDEN_EXTRAS

    type: str
    non_empty: bool


class Step(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    step_id: str
    action: Action
    expected_state: ExpectedState | None = None
    result_expectation: ResultExpectation | None = None


class CapabilityIdentity(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    capability_id: str
    name: str
    description: str
    schema_version: str
    capability_version: str


class Provenance(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    created_from_run_id: str


class Compatibility(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    vendor_product: str
    app_family: str
    supported_versions: list[str]
    surface_kind: str


class InputConstraints(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    pattern: str | None = None
    allowed_values: list[str] | None = None


class InputDefinition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    name: str
    type: str
    required: bool
    description: str
    constraints: InputConstraints | None = None


class OutputExtractionSource(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    step_id: str
    target: ControlTarget


class OutputDefinition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    name: str
    type: str
    description: str
    extraction_source: OutputExtractionSource


class RecoveryPolicy(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    type: Literal["RETRY_STEP"]
    max_retries: int = Field(ge=0)


class BusinessOutcome(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    code: str
    description: str
    applies_at: str
    detection_condition: Condition


class RecoverableCondition(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    code: str
    description: str
    applies_at: str
    detection_condition: Condition
    recovery_policy: RecoveryPolicy


class HardFailure(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    code: str
    description: str
    applies_at: str
    detection_condition: Condition
    escalation_policy: Literal["REQUIRE_HUMAN"] | None = None


class OutcomesAndErrors(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    business_outcomes: list[BusinessOutcome]
    recoverable_conditions: list[RecoverableCondition]
    hard_failures: list[HardFailure]


class SuccessCheckpoint(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    description: str
    condition: Condition
    required_outputs: list[str]


class SensitiveDataHandling(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    sensitive_inputs: list[str]
    sensitive_outputs: list[str]
    persist_raw_values: bool


class StepPolicy(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    step_id: str
    risk_class: str
    required_handling: Literal["ALLOW", "REQUIRE_HUMAN", "BLOCK"]


class PolicyMetadata(BaseModel):
    """Declarative policy context. Policy/Safety remains the enforcement authority."""

    model_config = _FORBIDDEN_EXTRAS

    risk_level: str
    allowed_action_types: list[
        Literal["CLICK", "TYPE", "SELECT", "READ", "NAVIGATE", "WAIT"]
    ]
    sensitive_data_handling: SensitiveDataHandling
    step_policies: list[StepPolicy]


class CapabilityArtifact(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    identity: CapabilityIdentity
    provenance: Provenance
    compatibility: Compatibility
    inputs: list[InputDefinition]
    outputs: list[OutputDefinition]
    steps: list[Step]
    outcomes_and_errors: OutcomesAndErrors
    success_checkpoint: SuccessCheckpoint
    policy_metadata: PolicyMetadata
