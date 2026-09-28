from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from interface_automation.models.artifact import (
    Action,
    ClickAction,
    ControlTarget,
    NavigateAction,
    ReadAction,
    SelectAction,
    TypeAction,
    WaitAction,
)

action_adapter = TypeAdapter(Action)


def _search_button() -> ControlTarget:
    return ControlTarget(
        semantic_name="search_button",
        target_kind="CONTROL",
        role="button",
        accessible_name="Search",
        context={"region": "member_search_form"},
        fallbacks=[{"text": "Search"}],
    )


def test_valid_control_target() -> None:
    target = _search_button()
    assert target.semantic_name == "search_button"
    assert target.target_kind == "CONTROL"
    assert target.role == "button"
    assert target.accessible_name == "Search"
    assert target.context == {"region": "member_search_form"}
    assert target.fallbacks == [{"text": "Search"}]


def test_valid_click_action() -> None:
    action = ClickAction(target=_search_button())
    assert action.type == "CLICK"
    assert action.target.semantic_name == "search_button"


def test_valid_type_action() -> None:
    action = TypeAction(
        target=ControlTarget(
            semantic_name="member_id_field",
            target_kind="CONTROL",
            role="textbox",
            label="Member ID",
        ),
        value_binding="{{member_id}}",
    )
    assert action.type == "TYPE"
    assert action.value_binding == "{{member_id}}"


def test_valid_select_action() -> None:
    action = SelectAction(
        target=ControlTarget(
            semantic_name="account_type_selector",
            target_kind="CONTROL",
            role="combobox",
            label="Account Type",
        ),
        value_binding="{{account_type}}",
    )
    assert action.type == "SELECT"
    assert action.value_binding == "{{account_type}}"


def test_valid_read_action() -> None:
    action = ReadAction(
        target=ControlTarget(
            semantic_name="confirmation_id",
            target_kind="TEXT",
            label="Confirmation ID",
        ),
        output_binding="confirmation_id",
    )
    assert action.type == "READ"
    assert action.output_binding == "confirmation_id"


def test_navigate_and_wait_remain_in_taxonomy_but_are_incomplete() -> None:
    """NAVIGATE and WAIT stay in the Action union; discriminator-only is not executable."""
    navigate = action_adapter.validate_python({"type": "NAVIGATE"})
    wait = action_adapter.validate_python({"type": "WAIT"})
    assert isinstance(navigate, NavigateAction)
    assert isinstance(wait, WaitAction)
    assert NavigateAction.model_fields.keys() == {"type"}
    assert WaitAction.model_fields.keys() == {"type"}


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        (
            {
                "type": "CLICK",
                "target": {
                    "semantic_name": "search_button",
                    "target_kind": "CONTROL",
                },
            },
            ClickAction,
        ),
        (
            {
                "type": "TYPE",
                "target": {
                    "semantic_name": "member_id_field",
                    "target_kind": "CONTROL",
                },
                "value_binding": "{{member_id}}",
            },
            TypeAction,
        ),
        (
            {
                "type": "SELECT",
                "target": {
                    "semantic_name": "account_type_selector",
                    "target_kind": "CONTROL",
                },
                "value_binding": "{{account_type}}",
            },
            SelectAction,
        ),
        (
            {
                "type": "READ",
                "target": {
                    "semantic_name": "confirmation_id",
                    "target_kind": "TEXT",
                },
                "output_binding": "confirmation_id",
            },
            ReadAction,
        ),
    ],
)
def test_action_discriminator_parsing(
    payload: dict[str, Any], expected_type: type
) -> None:
    parsed = action_adapter.validate_python(payload)
    assert isinstance(parsed, expected_type)
    assert parsed.type == payload["type"]


def test_invalid_action_shape_rejected() -> None:
    with pytest.raises(ValidationError):
        action_adapter.validate_python(
            {
                "type": "CLICK",
                "value_binding": "{{member_id}}",
            }
        )
