from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from interface_automation.models.replay import (
    BusinessOutcomeResult,
    EscalatedResult,
    FailureResult,
    ReplayResult,
    SuccessResult,
)

result_adapter = TypeAdapter(ReplayResult)


def _common(**overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": "run-001",
        "capability_id": "open_subaccount",
        "capability_version": "1",
        "session_id": "session-001",
        "started_at": "2026-09-28T12:00:00Z",
        "step_context": {
            "last_completed_step_id": "enter_member_id",
            "current_step_id": "submit_member_search",
        },
        "runtime_events": [],
        "evidence_refs": ["evidence://run-001/step-1"],
    }
    payload.update(overrides)
    return payload


def test_valid_success_result() -> None:
    result = SuccessResult.model_validate(
        {
            **_common(finished_at="2026-09-28T12:01:00Z"),
            "status": "SUCCESS",
            "outputs": {"confirmation_id": "ABC123"},
            "checkpoint": {"checkpoint_id": "final_success", "verified": True},
        }
    )
    assert result.status == "SUCCESS"
    assert result.outputs["confirmation_id"] == "ABC123"
    assert result.checkpoint.verified is True
    assert result.checkpoint.checkpoint_id == "final_success"


def test_success_checkpoint_id_is_optional() -> None:
    result = SuccessResult.model_validate(
        {
            **_common(finished_at="2026-09-28T12:01:00Z"),
            "status": "SUCCESS",
            "outputs": {"confirmation_id": "ABC123"},
            "checkpoint": {"verified": True},
        }
    )
    assert result.checkpoint.verified is True
    assert result.checkpoint.checkpoint_id is None


def test_valid_business_outcome_result() -> None:
    result = BusinessOutcomeResult.model_validate(
        {
            **_common(finished_at="2026-09-28T12:01:00Z"),
            "status": "BUSINESS_OUTCOME",
            "outcome": {
                "code": "MEMBER_NOT_FOUND",
                "description": "No member exists for the supplied member_id.",
                "payload": {"member_id": "12345"},
            },
        }
    )
    assert result.status == "BUSINESS_OUTCOME"
    assert not hasattr(result, "outputs") or "outputs" not in result.model_fields
    assert result.outcome.code == "MEMBER_NOT_FOUND"
    assert result.outcome.payload == {"member_id": "12345"}


def test_valid_failure_result() -> None:
    result = FailureResult.model_validate(
        {
            **_common(finished_at="2026-09-28T12:01:00Z"),
            "status": "FAILURE",
            "failure": {
                "category": "STEP_VERIFICATION",
                "code": "EXPECTED_STATE_NOT_REACHED",
                "message": "Member detail page did not appear after Search.",
                "expected": {"summary": "Member detail panel is visible."},
                "observed": {"summary": "Search page remained visible."},
            },
        }
    )
    assert result.status == "FAILURE"
    assert result.failure.category == "STEP_VERIFICATION"


def test_valid_escalated_result() -> None:
    result = EscalatedResult.model_validate(
        {
            **_common(),
            "status": "ESCALATED",
            "escalation": {
                "intervention_id": "intervention-001",
                "reason_code": "UNEXPECTED_DIALOG",
                "reason": "Automation cannot safely continue.",
                "control_owner": "HUMAN",
                "resume_allowed": True,
            },
        }
    )
    assert result.status == "ESCALATED"
    assert result.escalation.control_owner == "HUMAN"
    assert result.escalation.resume_allowed is True
    assert result.finished_at is None


def test_escalated_control_owner_must_be_human() -> None:
    with pytest.raises(ValidationError):
        EscalatedResult.model_validate(
            {
                **_common(),
                "status": "ESCALATED",
                "escalation": {
                    "intervention_id": "intervention-001",
                    "reason_code": "UNEXPECTED_DIALOG",
                    "reason": "Automation cannot safely continue.",
                    "control_owner": "AUTOMATION",
                    "resume_allowed": True,
                },
            }
        )


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        (
            {
                **{
                    "run_id": "run-001",
                    "capability_id": "open_subaccount",
                    "capability_version": "1",
                    "session_id": "session-001",
                    "started_at": "2026-09-28T12:00:00Z",
                    "step_context": {},
                    "runtime_events": [],
                    "evidence_refs": [],
                },
                "status": "SUCCESS",
                "outputs": {"confirmation_id": "ABC123"},
                "checkpoint": {"checkpoint_id": "final_success", "verified": True},
            },
            SuccessResult,
        ),
        (
            {
                "run_id": "run-001",
                "capability_id": "open_subaccount",
                "capability_version": "1",
                "session_id": "session-001",
                "started_at": "2026-09-28T12:00:00Z",
                "step_context": {},
                "runtime_events": [],
                "evidence_refs": [],
                "status": "BUSINESS_OUTCOME",
                "outcome": {
                    "code": "MEMBER_NOT_FOUND",
                    "description": "No member exists.",
                },
            },
            BusinessOutcomeResult,
        ),
        (
            {
                "run_id": "run-001",
                "capability_id": "open_subaccount",
                "capability_version": "1",
                "session_id": "session-001",
                "started_at": "2026-09-28T12:00:00Z",
                "step_context": {},
                "runtime_events": [],
                "evidence_refs": [],
                "status": "FAILURE",
                "failure": {
                    "category": "UNKNOWN",
                    "code": "X",
                    "message": "stopped",
                },
            },
            FailureResult,
        ),
        (
            {
                "run_id": "run-001",
                "capability_id": "open_subaccount",
                "capability_version": "1",
                "session_id": "session-001",
                "started_at": "2026-09-28T12:00:00Z",
                "step_context": {},
                "runtime_events": [],
                "evidence_refs": [],
                "status": "ESCALATED",
                "escalation": {
                    "intervention_id": "intervention-001",
                    "reason_code": "UNEXPECTED_DIALOG",
                    "reason": "blocked",
                    "control_owner": "HUMAN",
                    "resume_allowed": True,
                },
            },
            EscalatedResult,
        ),
    ],
)
def test_replay_result_discriminator_parsing(
    payload: dict[str, Any], expected_type: type
) -> None:
    parsed = result_adapter.validate_python(payload)
    assert isinstance(parsed, expected_type)
    assert parsed.status == payload["status"]


def test_success_cannot_accept_failure_payload() -> None:
    with pytest.raises(ValidationError):
        result_adapter.validate_python(
            {
                **_common(),
                "status": "SUCCESS",
                "outputs": {"confirmation_id": "ABC123"},
                "checkpoint": {"checkpoint_id": "final_success", "verified": True},
                "failure": {
                    "category": "UNKNOWN",
                    "code": "X",
                    "message": "nope",
                },
            }
        )


def test_failure_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        FailureResult.model_validate(
            {
                **_common(),
                "status": "FAILURE",
                "failure": {
                    "category": "NOT_A_CATEGORY",
                    "code": "X",
                    "message": "nope",
                },
            }
        )


def test_business_outcome_is_distinct_from_success_outputs() -> None:
    with pytest.raises(ValidationError):
        result_adapter.validate_python(
            {
                **_common(),
                "status": "BUSINESS_OUTCOME",
                "outputs": {"confirmation_id": "ABC123"},
                "outcome": {
                    "code": "MEMBER_NOT_FOUND",
                    "description": "No member exists.",
                },
            }
        )
