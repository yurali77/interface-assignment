import pytest
from pydantic import ValidationError

from interface_automation.models.artifact import (
    PolicyMetadata,
    SensitiveDataHandling,
    StepPolicy,
)


def _policy_payload() -> dict:
    return {
        "risk_level": "RISKY",
        "allowed_action_types": ["NAVIGATE", "TYPE", "CLICK", "SELECT", "READ", "WAIT"],
        "sensitive_data_handling": {
            "sensitive_inputs": ["member_id"],
            "sensitive_outputs": [],
            "persist_raw_values": False,
        },
        "step_policies": [
            {
                "step_id": "open_subaccount",
                "risk_class": "SENSITIVE",
                "required_handling": "ALLOW",
            }
        ],
    }


def test_valid_policy_metadata_and_step_policy() -> None:
    metadata = PolicyMetadata.model_validate(_policy_payload())
    handling = metadata.sensitive_data_handling
    assert isinstance(handling, SensitiveDataHandling)
    assert handling.sensitive_inputs == ["member_id"]
    assert handling.sensitive_outputs == []
    assert handling.persist_raw_values is False
    assert len(metadata.step_policies) == 1
    assert isinstance(metadata.step_policies[0], StepPolicy)
    assert metadata.step_policies[0].required_handling == "ALLOW"


def test_invalid_required_handling_rejected() -> None:
    payload = _policy_payload()
    payload["step_policies"][0]["required_handling"] = "MAYBE"
    with pytest.raises(ValidationError):
        PolicyMetadata.model_validate(payload)


def test_unknown_extra_policy_field_rejected() -> None:
    payload = _policy_payload()
    payload["enforced_by_artifact"] = True
    with pytest.raises(ValidationError):
        PolicyMetadata.model_validate(payload)
