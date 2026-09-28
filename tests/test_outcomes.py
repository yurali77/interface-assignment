import pytest
from pydantic import ValidationError

from interface_automation.models.artifact import (
    BusinessOutcome,
    CompositeCondition,
    HardFailure,
    RecoverableCondition,
    RecoveryPolicy,
    SuccessCheckpoint,
    TextPresentCondition,
)


def test_business_outcome() -> None:
    outcome = BusinessOutcome.model_validate(
        {
            "code": "MEMBER_NOT_FOUND",
            "description": "No member exists for the supplied member_id.",
            "applies_at": "submit_member_search",
            "detection_condition": {
                "type": "TEXT_PRESENT",
                "text": "Member not found",
            },
        }
    )
    assert outcome.code == "MEMBER_NOT_FOUND"
    assert isinstance(outcome.detection_condition, TextPresentCondition)


def test_retry_step_recovery_with_max_retries() -> None:
    recoverable = RecoverableCondition.model_validate(
        {
            "code": "SLOW_LOAD",
            "description": "Expected page remains in a loading state.",
            "applies_at": "submit_member_search",
            "detection_condition": {"type": "SEMANTIC_STATE", "state": "LOADING"},
            "recovery_policy": {"type": "RETRY_STEP", "max_retries": 1},
        }
    )
    assert isinstance(recoverable.recovery_policy, RecoveryPolicy)
    assert recoverable.recovery_policy.type == "RETRY_STEP"
    assert recoverable.recovery_policy.max_retries == 1


def test_hard_failure_without_escalation() -> None:
    failure = HardFailure.model_validate(
        {
            "code": "PERMISSION_DENIED",
            "description": "Current session is not permitted to perform the operation.",
            "applies_at": "open_subaccount",
            "detection_condition": {
                "type": "TEXT_PRESENT",
                "text": "Permission denied",
            },
        }
    )
    assert failure.escalation_policy is None


def test_hard_failure_with_require_human() -> None:
    failure = HardFailure.model_validate(
        {
            "code": "UNEXPECTED_DIALOG",
            "description": "An unexpected dialog blocks deterministic execution.",
            "applies_at": "open_subaccount",
            "detection_condition": {
                "type": "SEMANTIC_STATE",
                "state": "UNEXPECTED_DIALOG",
            },
            "escalation_policy": "REQUIRE_HUMAN",
        }
    )
    assert failure.escalation_policy == "REQUIRE_HUMAN"


def test_success_checkpoint_with_composite_condition() -> None:
    checkpoint = SuccessCheckpoint.model_validate(
        {
            "description": "Confirmation state for the requested member and account type.",
            "condition": {
                "type": "AND",
                "conditions": [
                    {"type": "SEMANTIC_STATE", "state": "CONFIRMATION_SCREEN"},
                    {
                        "type": "VALUE_EQUALS",
                        "target": {
                            "semantic_name": "member_id_display",
                            "target_kind": "TEXT",
                        },
                        "expected_value": "{{member_id}}",
                    },
                ],
            },
            "required_outputs": ["confirmation_id"],
        }
    )
    assert isinstance(checkpoint.condition, CompositeCondition)
    assert checkpoint.condition.type == "AND"
    assert checkpoint.required_outputs == ["confirmation_id"]


def test_invalid_recovery_type_rejected() -> None:
    with pytest.raises(ValidationError):
        RecoveryPolicy.model_validate({"type": "RETRY", "max_attempts": 1})


def test_negative_max_retries_rejected() -> None:
    with pytest.raises(ValidationError):
        RecoveryPolicy.model_validate({"type": "RETRY_STEP", "max_retries": -1})


def test_invalid_escalation_policy_rejected() -> None:
    with pytest.raises(ValidationError):
        HardFailure.model_validate(
            {
                "code": "UNEXPECTED_DIALOG",
                "description": "An unexpected dialog blocks deterministic execution.",
                "applies_at": "open_subaccount",
                "detection_condition": {
                    "type": "SEMANTIC_STATE",
                    "state": "UNEXPECTED_DIALOG",
                },
                "escalation_policy": "RETRY",
            }
        )
