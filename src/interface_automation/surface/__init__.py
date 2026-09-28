"""Surface abstraction for observing and acting on a target application."""

from interface_automation.surface.base import (
    LiveSession,
    Observation,
    Surface,
    SurfaceActionResult,
    SurfaceFailure,
    TargetValue,
    TargetVisibility,
)

__all__ = [
    "LiveSession",
    "Observation",
    "Surface",
    "SurfaceActionResult",
    "SurfaceFailure",
    "TargetValue",
    "TargetVisibility",
]
