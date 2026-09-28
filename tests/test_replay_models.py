from pathlib import Path

import pytest
from pydantic import ValidationError

from interface_automation.models.artifact import CapabilityArtifact
from interface_automation.models.replay import (
    EffectiveCapability,
    ExecutionContext,
    ReplayRequest,
    ResolutionMetadata,
)


def _artifact() -> CapabilityArtifact:
    from importlib.util import module_from_spec, spec_from_file_location

    path = Path(__file__).with_name("test_capability_artifact.py")
    spec = spec_from_file_location("test_capability_artifact", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return CapabilityArtifact.model_validate(module._minimal_artifact_payload())


def _resolution(**overrides: object) -> ResolutionMetadata:
    payload: dict = {
        "base_capability_version": "1",
        "tenant_id": "credit_union_a",
        "app_version": "3.2.1",
    }
    payload.update(overrides)
    return ResolutionMetadata.model_validate(payload)


def test_effective_capability_wraps_artifact() -> None:
    artifact = _artifact()
    effective = EffectiveCapability(
        artifact=artifact,
        resolution_metadata=_resolution(),
    )
    assert effective.artifact is artifact
    assert effective.artifact.identity.capability_id == "open_subaccount"


def test_resolution_metadata_without_override_id() -> None:
    metadata = _resolution()
    assert metadata.applied_override_id is None


def test_resolution_metadata_with_override_id() -> None:
    metadata = _resolution(applied_override_id="override-cu-a-v3")
    assert metadata.applied_override_id == "override-cu-a-v3"


def test_replay_request_contains_inputs_and_execution_context() -> None:
    request = ReplayRequest(
        effective_capability=EffectiveCapability(
            artifact=_artifact(),
            resolution_metadata=_resolution(),
        ),
        inputs={"member_id": "12345", "account_type": "Savings"},
        execution_context=ExecutionContext(
            tenant_id="credit_union_a",
            session_id="session-001",
            environment="local_demo",
        ),
    )
    assert request.inputs["member_id"] == "12345"
    assert request.execution_context.session_id == "session-001"
    assert request.effective_capability.resolution_metadata.tenant_id == (
        "credit_union_a"
    )


def test_unknown_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ResolutionMetadata.model_validate(
            {
                "base_capability_version": "1",
                "tenant_id": "credit_union_a",
                "app_version": "3.2.1",
                "extra": True,
            }
        )
    with pytest.raises(ValidationError):
        ReplayRequest.model_validate(
            {
                "effective_capability": {
                    "artifact": _artifact().model_dump(),
                    "resolution_metadata": _resolution().model_dump(),
                },
                "inputs": {"member_id": "12345"},
                "execution_context": {
                    "tenant_id": "credit_union_a",
                    "session_id": "session-001",
                    "environment": "local_demo",
                },
                "capability_id": "open_subaccount",
            }
        )
