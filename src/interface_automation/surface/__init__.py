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
from interface_automation.surface.playwright import PlaywrightSurface

__all__ = [
    "LiveSession",
    "Observation",
    "PlaywrightSurface",
    "Surface",
    "SurfaceActionResult",
    "SurfaceFailure",
    "TargetValue",
    "TargetVisibility",
]
