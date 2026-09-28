from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from interface_automation.models.artifact import (
    CompositeCondition,
    Condition,
    ControlTarget,
    RouteMatchesCondition,
    SemanticStateCondition,
    TargetNotVisibleCondition,
    TargetVisibleCondition,
    TextPresentCondition,
    ValueEqualsCondition,
)

condition_adapter = TypeAdapter(Condition)


def _member_id_display() -> ControlTarget:
    return ControlTarget(
        semantic_name="member_id_display",
        target_kind="TEXT",
    )


def test_valid_target_visible_condition() -> None:
    condition = TargetVisibleCondition(
        target=ControlTarget(
            semantic_name="member_detail_panel",
            target_kind="REGION",
        )
    )
    assert condition.type == "TARGET_VISIBLE"
    assert condition.target.semantic_name == "member_detail_panel"


def test_valid_target_not_visible_condition() -> None:
    condition = TargetNotVisibleCondition(
        target=ControlTarget(
            semantic_name="loading_indicator",
            target_kind="CONTROL",
        )
    )
    assert condition.type == "TARGET_NOT_VISIBLE"
    assert condition.target.semantic_name == "loading_indicator"


def test_valid_text_present_condition() -> None:
    condition = TextPresentCondition(text="Member not found")
    assert condition.type == "TEXT_PRESENT"
    assert condition.text == "Member not found"


def test_valid_value_equals_condition_uses_control_target() -> None:
    condition = ValueEqualsCondition(
        target=_member_id_display(),
        expected_value="{{member_id}}",
    )
    assert condition.type == "VALUE_EQUALS"
    assert isinstance(condition.target, ControlTarget)
    assert condition.target.semantic_name == "member_id_display"
    assert condition.target.target_kind == "TEXT"
    assert condition.expected_value == "{{member_id}}"


def test_route_matches_remains_in_taxonomy_but_is_incomplete() -> None:
    """ROUTE_MATCHES stays in the Condition union; discriminator-only is not executable."""
    condition = condition_adapter.validate_python({"type": "ROUTE_MATCHES"})
    assert isinstance(condition, RouteMatchesCondition)
    assert RouteMatchesCondition.model_fields.keys() == {"type"}


def test_valid_semantic_state_condition() -> None:
    condition = SemanticStateCondition(state="CONFIRMATION_SCREEN")
    assert condition.type == "SEMANTIC_STATE"
    assert condition.state == "CONFIRMATION_SCREEN"


def test_nested_and_or_composite_conditions() -> None:
    condition = CompositeCondition(
        type="AND",
        conditions=[
            SemanticStateCondition(state="CONFIRMATION_SCREEN"),
            CompositeCondition(
                type="OR",
                conditions=[
                    ValueEqualsCondition(
                        target=_member_id_display(),
                        expected_value="{{member_id}}",
                    ),
                    TextPresentCondition(text="Member not found"),
                ],
            ),
        ],
    )
    assert condition.type == "AND"
    assert isinstance(condition.conditions[0], SemanticStateCondition)
    nested = condition.conditions[1]
    assert isinstance(nested, CompositeCondition)
    assert nested.type == "OR"
    assert isinstance(nested.conditions[0], ValueEqualsCondition)
    assert isinstance(nested.conditions[0].target, ControlTarget)
    assert isinstance(nested.conditions[1], TextPresentCondition)


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        (
            {
                "type": "TARGET_VISIBLE",
                "target": {
                    "semantic_name": "member_detail_panel",
                    "target_kind": "REGION",
                },
            },
            TargetVisibleCondition,
        ),
        (
            {
                "type": "TARGET_NOT_VISIBLE",
                "target": {
                    "semantic_name": "loading_indicator",
                    "target_kind": "CONTROL",
                },
            },
            TargetNotVisibleCondition,
        ),
        (
            {"type": "TEXT_PRESENT", "text": "Permission denied"},
            TextPresentCondition,
        ),
        (
            {
                "type": "VALUE_EQUALS",
                "target": {
                    "semantic_name": "account_type_display",
                    "target_kind": "TEXT",
                },
                "expected_value": "{{account_type}}",
            },
            ValueEqualsCondition,
        ),
        (
            {"type": "SEMANTIC_STATE", "state": "LOADING"},
            SemanticStateCondition,
        ),
        (
            {
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
            CompositeCondition,
        ),
        (
            {
                "type": "OR",
                "conditions": [
                    {"type": "TEXT_PRESENT", "text": "Member not found"},
                    {"type": "SEMANTIC_STATE", "state": "LOADING"},
                ],
            },
            CompositeCondition,
        ),
    ],
)
def test_condition_discriminator_parsing(
    payload: dict[str, Any], expected_type: type
) -> None:
    parsed = condition_adapter.validate_python(payload)
    assert isinstance(parsed, expected_type)
    assert parsed.type == payload["type"]


def test_invalid_condition_payload_rejected() -> None:
    with pytest.raises(ValidationError):
        condition_adapter.validate_python(
            {
                "type": "VALUE_EQUALS",
                "expected_value": "{{member_id}}",
            }
        )
