"""Playwright adapter. Framework types stay in this module."""

from __future__ import annotations

from playwright.sync_api import Error, Locator, Page

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
from interface_automation.surface.base import (
    LiveSession,
    Observation,
    SurfaceActionResult,
    SurfaceFailure,
    TargetValue,
    TargetVisibility,
)

_CONTAINER_TAGS = frozenset({"form", "section", "div", "table", "tbody", "tr"})


def _failed(category: str, message: str) -> SurfaceActionResult:
    return SurfaceActionResult(
        operation_succeeded=False,
        failure=SurfaceFailure(category=category, message=message),
    )


class PlaywrightSurface:
    """Resolves ControlTarget and drives a provided Playwright Page."""

    def __init__(self, *, page: Page, session_id: str) -> None:
        self._page = page
        self._session_id = session_id

    def act(self, action: Action) -> SurfaceActionResult:
        if self._page.is_closed():
            return _failed("SESSION", "Playwright page is closed.")
        if isinstance(action, TypeAction):
            return self._type(action)
        if isinstance(action, ClickAction):
            return self._click(action)
        if isinstance(action, ReadAction):
            return self._read(action)
        if isinstance(action, (SelectAction, NavigateAction, WaitAction)):
            return _failed(
                "OPERATION",
                f"Action type {action.type} is not implemented.",
            )
        return _failed("OPERATION", "Unsupported action.")

    def observe(self) -> Observation:
        visibilities: list[TargetVisibility] = []
        values: list[TargetValue] = []
        nodes = self._page.locator("[data-semantic-name]")
        for index in range(nodes.count()):
            node = nodes.nth(index)
            name = node.get_attribute("data-semantic-name")
            if not name:
                continue
            visible = node.is_visible()
            visibilities.append(TargetVisibility(semantic_name=name, visible=visible))
            if not visible:
                continue
            extracted = self._node_value(node)
            if extracted is not None:
                values.append(TargetValue(semantic_name=name, value=extracted))
        return Observation(
            target_visibilities=visibilities,
            visible_text=self._page.locator("body").inner_text(),
            target_values=values,
            semantic_states=[],
        )

    def get_session(self) -> LiveSession:
        return LiveSession(
            session_id=self._session_id,
            available=not self._page.is_closed(),
        )

    def _type(self, action: TypeAction) -> SurfaceActionResult:
        locator, failure = self._resolve(action.target)
        if failure is not None:
            return failure
        try:
            locator.fill(action.value_binding)
        except Exception as exc:
            return _failed("OPERATION", str(exc))
        return SurfaceActionResult(operation_succeeded=True)

    def _click(self, action: ClickAction) -> SurfaceActionResult:
        locator, failure = self._resolve(action.target)
        if failure is not None:
            return failure
        try:
            locator.click()
            self._page.wait_for_load_state("domcontentloaded")
        except Exception as exc:
            return _failed("OPERATION", str(exc))
        return SurfaceActionResult(operation_succeeded=True)

    def _read(self, action: ReadAction) -> SurfaceActionResult:
        locator, failure = self._resolve(action.target)
        if failure is not None:
            return failure
        try:
            value = self._node_value(locator)
        except Exception as exc:
            return _failed("OPERATION", str(exc))
        if value is None:
            return _failed("OPERATION", "Could not extract a value from the target.")
        return SurfaceActionResult(operation_succeeded=True, extracted_value=value)

    def _resolve(self, target: ControlTarget) -> tuple[Locator, SurfaceActionResult | None]:
        try:
            scope = self._scope(target)
            strategies: list[Locator] = []
            if target.label:
                strategies.append(scope.get_by_label(target.label, exact=True))
            if target.role and target.accessible_name:
                strategies.append(
                    scope.get_by_role(
                        target.role,
                        name=target.accessible_name,
                        exact=True,
                    )
                )
            for locator in strategies:
                unique, error = self._unique(locator, target.semantic_name)
                if error is not None:
                    return locator, error
                if unique is not None:
                    return unique, None
            fallback = self._fallback_locator(scope, target)
            unique, error = self._unique(fallback, target.semantic_name)
            if error is not None:
                return fallback, error
            if unique is not None:
                return unique, None
        except Error as exc:
            return self._page.locator("body"), _failed("TARGET_RESOLUTION", str(exc))
        return scope, _failed(
            "TARGET_RESOLUTION",
            f"Could not resolve target {target.semantic_name!r}.",
        )

    def _scope(self, target: ControlTarget) -> Locator:
        if target.context and "region" in target.context:
            region = self._page.locator(
                f"[data-semantic-name={target.context['region']!r}]"
            )
            if region.count() == 1:
                return region
        return self._page.locator("body")

    def _fallback_locator(self, scope: Locator, target: ControlTarget) -> Locator:
        if target.fallbacks:
            for hint in target.fallbacks:
                text = hint.get("text")
                if text:
                    return scope.get_by_text(text, exact=True)
                semantic = hint.get("data-semantic-name")
                if semantic:
                    return scope.locator(f"[data-semantic-name={semantic!r}]")
        return scope.locator(f"[data-semantic-name={target.semantic_name!r}]")

    def _unique(
        self,
        locator: Locator,
        semantic_name: str,
    ) -> tuple[Locator | None, SurfaceActionResult | None]:
        count = locator.count()
        if count == 1:
            return locator.first, None
        if count > 1:
            return None, _failed(
                "TARGET_RESOLUTION",
                f"Ambiguous target {semantic_name!r} ({count} matches).",
            )
        return None, None

    def _node_value(self, node: Locator) -> str | None:
        tag = node.evaluate("el => el.tagName.toLowerCase()")
        if tag in {"input", "textarea", "select"}:
            return node.input_value()
        if tag in _CONTAINER_TAGS:
            return None
        text = node.inner_text().strip()
        return text if text else None
