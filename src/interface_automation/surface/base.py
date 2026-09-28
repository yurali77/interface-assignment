"""Technology-neutral Surface contract. No browser-automation framework types."""

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from interface_automation.models.artifact import Action

_FORBIDDEN_EXTRAS = ConfigDict(extra="forbid")


class SurfaceFailure(BaseModel):
    """Why a Surface operation failed. Not a ReplayResult."""

    model_config = _FORBIDDEN_EXTRAS

    category: Literal["TARGET_RESOLUTION", "SESSION", "OPERATION"]
    message: str


class SurfaceActionResult(BaseModel):
    """Surface operation outcome only. Does not mark a Replay step complete."""

    model_config = _FORBIDDEN_EXTRAS

    operation_succeeded: bool
    extracted_value: str | None = None
    failure: SurfaceFailure | None = None


class TargetVisibility(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    semantic_name: str
    visible: bool


class TargetValue(BaseModel):
    model_config = _FORBIDDEN_EXTRAS

    semantic_name: str
    value: str


class Observation(BaseModel):
    """Facts for Replay. Missing semantic_name means unknown, not not-visible."""

    model_config = _FORBIDDEN_EXTRAS

    target_visibilities: list[TargetVisibility]
    visible_text: str
    target_values: list[TargetValue]
    semantic_states: list[str]


class LiveSession(BaseModel):
    """Logical session identity and availability. No framework handles."""

    model_config = _FORBIDDEN_EXTRAS

    session_id: str
    available: bool


@runtime_checkable
class Surface(Protocol):
    def act(self, action: Action) -> SurfaceActionResult: ...

    def observe(self) -> Observation: ...

    def get_session(self) -> LiveSession: ...
