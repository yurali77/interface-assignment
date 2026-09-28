import pytest
from pydantic import ValidationError

from interface_automation.models.artifact import (
    CapabilityArtifact,
    ControlTarget,
    InputConstraints,
)


def _minimal_artifact_payload() -> dict:
    return {
        "identity": {
            "capability_id": "open_subaccount",
            "name": "Open Member Sub-account",
            "description": "Looks up a member and opens a sub-account.",
            "schema_version": "1.0",
            "capability_version": "1",
        },
        "provenance": {"created_from_run_id": "discovery-run-001"},
        "compatibility": {
            "vendor_product": "local_legacy_banking_demo",
            "app_family": "member_servicing",
            "supported_versions": ["v1"],
            "surface_kind": "WEB",
        },
        "inputs": [
            {
                "name": "member_id",
                "type": "string",
                "required": True,
                "description": "Member identifier.",
                "constraints": {"pattern": "^[0-9]+$"},
            }
        ],
        "outputs": [
            {
                "name": "confirmation_id",
                "type": "string",
                "description": "Confirmation identifier.",
                "extraction_source": {
                    "step_id": "read_confirmation",
                    "target": {
                        "semantic_name": "confirmation_id",
                        "target_kind": "TEXT",
                        "label": "Confirmation ID",
                    },
                },
            }
        ],
        "steps": [
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
            }
        ],
        "outcomes_and_errors": {
            "business_outcomes": [],
            "recoverable_conditions": [],
            "hard_failures": [],
        },
        "success_checkpoint": {
            "description": "Member lookup reached the expected panel.",
            "condition": {
                "type": "TARGET_VISIBLE",
                "target": {
                    "semantic_name": "member_detail_panel",
                    "target_kind": "REGION",
                },
            },
            "required_outputs": ["confirmation_id"],
        },
        "policy_metadata": {
            "risk_level": "RISKY",
            "allowed_action_types": ["TYPE", "CLICK"],
            "sensitive_data_handling": {
                "sensitive_inputs": ["member_id"],
                "sensitive_outputs": [],
                "persist_raw_values": False,
            },
            "step_policies": [
                {
                    "step_id": "enter_member_id",
                    "risk_class": "SENSITIVE",
                    "required_handling": "ALLOW",
                }
            ],
        },
    }


def test_valid_minimal_capability_artifact() -> None:
    artifact = CapabilityArtifact.model_validate(_minimal_artifact_payload())
    assert artifact.identity.capability_id == "open_subaccount"
    assert artifact.provenance.created_from_run_id == "discovery-run-001"
    assert len(artifact.inputs) == 1
    assert len(artifact.outputs) == 1
    assert len(artifact.steps) == 1
    assert artifact.policy_metadata.risk_level == "RISKY"


def test_input_constraints_pattern() -> None:
    constraints = InputConstraints.model_validate({"pattern": "^[0-9]+$"})
    assert constraints.pattern == "^[0-9]+$"
    assert constraints.allowed_values is None


def test_input_constraints_allowed_values() -> None:
    constraints = InputConstraints.model_validate(
        {"allowed_values": ["Savings", "Checking"]}
    )
    assert constraints.allowed_values == ["Savings", "Checking"]
    assert constraints.pattern is None


def test_output_extraction_source_uses_control_target() -> None:
    artifact = CapabilityArtifact.model_validate(_minimal_artifact_payload())
    source = artifact.outputs[0].extraction_source
    assert source.step_id == "read_confirmation"
    assert isinstance(source.target, ControlTarget)
    assert source.target.semantic_name == "confirmation_id"
    assert source.target.target_kind == "TEXT"


def test_invalid_nested_action_or_condition_fails_through_capability_artifact() -> None:
    action_payload = _minimal_artifact_payload()
    action_payload["steps"][0]["action"] = {
        "type": "CLICK",
        "value_binding": "{{member_id}}",
    }
    with pytest.raises(ValidationError):
        CapabilityArtifact.model_validate(action_payload)

    condition_payload = _minimal_artifact_payload()
    condition_payload["steps"][0]["expected_state"] = {
        "condition": {
            "type": "VALUE_EQUALS",
            "expected_value": "{{member_id}}",
        }
    }
    with pytest.raises(ValidationError):
        CapabilityArtifact.model_validate(condition_payload)


def test_unknown_extra_top_level_field_rejected() -> None:
    payload = _minimal_artifact_payload()
    payload["not_a_schema_field"] = True
    with pytest.raises(ValidationError):
        CapabilityArtifact.model_validate(payload)


def test_full_artifact_parses_retry_step_not_retry_max_attempts() -> None:
    payload = _minimal_artifact_payload()
    payload["outcomes_and_errors"] = {
        "business_outcomes": [
            {
                "code": "MEMBER_NOT_FOUND",
                "description": "No member exists for the supplied member_id.",
                "applies_at": "enter_member_id",
                "detection_condition": {
                    "type": "TEXT_PRESENT",
                    "text": "Member not found",
                },
            }
        ],
        "recoverable_conditions": [
            {
                "code": "SLOW_LOAD",
                "description": "Expected page remains in a loading state.",
                "applies_at": "enter_member_id",
                "detection_condition": {"type": "SEMANTIC_STATE", "state": "LOADING"},
                "recovery_policy": {"type": "RETRY_STEP", "max_retries": 1},
            }
        ],
        "hard_failures": [
            {
                "code": "PERMISSION_DENIED",
                "description": "Current session is not permitted.",
                "applies_at": "enter_member_id",
                "detection_condition": {
                    "type": "TEXT_PRESENT",
                    "text": "Permission denied",
                },
            }
        ],
    }
    artifact = CapabilityArtifact.model_validate(payload)
    recovery = artifact.outcomes_and_errors.recoverable_conditions[0].recovery_policy
    assert recovery.type == "RETRY_STEP"
    assert recovery.max_retries == 1
