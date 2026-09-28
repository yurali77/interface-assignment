from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from interface_automation.models.artifact import (
    ClickAction,
    ExpectedState,
    SelectAction,
    Step,
    TargetVisibleCondition,
    TypeAction,
    ValueEqualsCondition,
)

step_adapter = TypeAdapter(Step)


def test_click_step_with_expected_state() -> None:
    step = Step.model_validate(
        {
            "step_id": "submit_member_search",
            "action": {
                "type": "CLICK",
                "target": {
                    "semantic_name": "search_button",
                    "target_kind": "CONTROL",
                    "role": "button",
                    "accessible_name": "Search",
                },
            },
            "expected_state": {
                "condition": {
                    "type": "TARGET_VISIBLE",
                    "target": {
                        "semantic_name": "member_detail_panel",
                        "target_kind": "REGION",
                    },
                }
            },
        }
    )
    assert step.step_id == "submit_member_search"
    assert isinstance(step.action, ClickAction)
    assert isinstance(step.expected_state, ExpectedState)
    assert isinstance(step.expected_state.condition, TargetVisibleCondition)
    assert step.result_expectation is None


@pytest.mark.parametrize(
    ("payload", "expected_action_type"),
    [
        (
            {
                "step_id": "enter_member_id",
                "action": {
                    "type": "TYPE",
                    "target": {
                        "semantic_name": "member_id_field",
                        "target_kind": "CONTROL",
                        "role": "textbox",
                        "label": "Member ID",
                    },
                    "value_binding": "{{member_id}}",
                },
                "expected_state": {
                    "condition": {
                        "type": "TARGET_VISIBLE",
                        "target": {
                            "semantic_name": "search_button",
                            "target_kind": "CONTROL",
                        },
                    }
                },
            },
            TypeAction,
        ),
        (
            {
                "step_id": "select_account_type",
                "action": {
                    "type": "SELECT",
                    "target": {
                        "semantic_name": "account_type_selector",
                        "target_kind": "CONTROL",
                        "role": "combobox",
                        "label": "Account Type",
                    },
                    "value_binding": "{{account_type}}",
                },
                "expected_state": {
                    "condition": {
                        "type": "SEMANTIC_STATE",
                        "state": "ACCOUNT_TYPE_SELECTED",
                    }
                },
            },
            SelectAction,
        ),
    ],
)
def test_type_and_select_steps_with_expected_state(
    payload: dict[str, Any], expected_action_type: type
) -> None:
    step = step_adapter.validate_python(payload)
    assert isinstance(step.action, expected_action_type)
    assert step.expected_state is not None


def test_read_step_with_result_expectation() -> None:
    step = Step.model_validate(
        {
            "step_id": "read_confirmation",
            "action": {
                "type": "READ",
                "target": {
                    "semantic_name": "confirmation_id",
                    "target_kind": "TEXT",
                    "label": "Confirmation ID",
                },
                "output_binding": "confirmation_id",
            },
            "result_expectation": {
                "type": "string",
                "non_empty": True,
            },
        }
    )
    assert step.action.type == "READ"
    assert step.expected_state is None
    assert step.result_expectation is not None
    assert step.result_expectation.type == "string"
    assert step.result_expectation.non_empty is True


def test_invalid_condition_inside_expected_state_rejected() -> None:
    with pytest.raises(ValidationError):
        Step.model_validate(
            {
                "step_id": "submit_member_search",
                "action": {
                    "type": "CLICK",
                    "target": {
                        "semantic_name": "search_button",
                        "target_kind": "CONTROL",
                    },
                },
                "expected_state": {
                    "condition": {
                        "type": "VALUE_EQUALS",
                        "expected_value": "{{member_id}}",
                    }
                },
            }
        )


def test_invalid_action_inside_step_rejected() -> None:
    with pytest.raises(ValidationError):
        Step.model_validate(
            {
                "step_id": "submit_member_search",
                "action": {
                    "type": "CLICK",
                    "value_binding": "{{member_id}}",
                },
            }
        )


def test_nested_discriminators_parse_inside_step() -> None:
    step = step_adapter.validate_python(
        {
            "step_id": "submit_member_search",
            "action": {
                "type": "CLICK",
                "target": {
                    "semantic_name": "search_button",
                    "target_kind": "CONTROL",
                },
            },
            "expected_state": {
                "condition": {
                    "type": "VALUE_EQUALS",
                    "target": {
                        "semantic_name": "member_id_display",
                        "target_kind": "TEXT",
                    },
                    "expected_value": "{{member_id}}",
                }
            },
        }
    )
    assert isinstance(step.action, ClickAction)
    assert isinstance(step.expected_state.condition, ValueEqualsCondition)
    assert isinstance(step.expected_state.condition.target.semantic_name, str)
