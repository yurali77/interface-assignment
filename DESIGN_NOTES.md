# Implementation notes

These are local implementation gaps. Frozen architecture/schema docs are unchanged.

## Local banking demo (Member Search only)

`interface_automation.demo.member_search` is a stdlib HTTP page for the first UI slice. Valid member is hard-coded `12345` / `Demo Member`. Invalid search shows `Member not found`. No accounts flow, auth, DB, or Replay wiring.

## PlaywrightSurface (Member Search slice)

`PlaywrightSurface` implements `act` / `observe` / `get_session` against a caller-provided Playwright `Page`. TYPE/CLICK/READ are implemented. SELECT/NAVIGATE/WAIT fail closed as `OPERATION`.

- **TYPE** fills `TypeAction.value_binding` as a literal string. Replay parameter expansion of `{{...}}` is not performed in Surface.
- **observe()** reports `[data-semantic-name]` visibilities/values plus `body` `visible_text`. `semantic_states` is empty: Artifact examples use `CONFIRMATION_SCREEN` later in the flow; there is no documented mapping for Member Detail, so none is invented.
- Playwright `Page`/`Browser`/`Locator` stay on the adapter, not on Observation/LiveSession/SurfaceActionResult.

## Incomplete v0 types

The typed Action and Condition taxonomies include `NAVIGATE`, `WAIT`, and `ROUTE_MATCHES`. Their executable payload fields are not fully specified by the frozen docs.

- **NAVIGATE:** the schema names the action type and constrains it to allowlisted entry points / stable navigation contexts. It does not define a serialized payload. `NavigateAction` currently carries only `type`.
- **WAIT:** the schema and D020 require a condition to become true within a wait policy. Condition vs WaitPolicy ownership in the serialized action/step is not fully specified. `WaitAction` currently carries only `type`. A typed `Condition` must be bound later without inventing timing fields now.
- **ROUTE_MATCHES:** the condition type exists in the hierarchy. No comparison/pattern field is documented. `RouteMatchesCondition` currently carries only `type`.
- **BusinessOutcome.result_payload:** the frozen schema lists an optional `result_payload` conceptually. Its serialized shape is not defined. It is not implemented.

No replacement schema is being invented until implementation actually requires resolution.

## Surface implementation contract

These types are a Surface→Replay implementation snapshot. They are not Artifact Schema.

- **Observation** is a fact snapshot for Replay condition evaluation. Facts about targets are keyed by `semantic_name`.
- A missing `semantic_name` in Observation means UNKNOWN / NOT OBSERVED. It must not be treated as `visible=False`.
- **SurfaceActionResult** reports only whether the Surface operation succeeded (plus optional READ `extracted_value`). It does not mark a Replay step complete.
- **LiveSession** exposes only `session_id` and `available`. Playwright Page/Browser/BrowserContext/Locator/DOM handles stay private to `PlaywrightSurface`.
- There is no `Surface.evaluate(condition)`. Replay evaluates Condition truth against Observation facts.
- Architecture names `capture_evidence()`, but its request/result types are not frozen. Evidence method typing and Evidence Logger are deferred. Do not add a silent no-op `capture_evidence()`.

## ReplayResult checkpoint identity

ReplayResult SUCCESS examples include `checkpoint.checkpoint_id`. `CapabilityArtifact.success_checkpoint` has no stable checkpoint identifier. `checkpoint_id` is optional on the result model. Replay must not synthesize an ID until the contract is clarified.

## ReplayEngine skeleton

`ReplayEngine.execute` implements orchestration order only. Production defaults are fail-closed:

- Unimplemented policy and verification seams raise `_SeamNotImplemented` and return `FailureResult` (`UNKNOWN` / `SEAM_NOT_IMPLEMENTED`).
- Policy does not default to ALLOW, so `Surface.act` is not reached until a real Policy Engine exists (or a test subclass opts in).
- Runtime-condition, success-checkpoint, and required-output seams still fail closed.
- Step completion is implemented for CLICK/TYPE/SELECT (`expected_state` required) and READ (`extracted_value` / `non_empty`). NAVIGATE/WAIT remain unimplemented.
- Missing Observation facts for a `semantic_name` are unresolved (fail closed), not treated as not-visible/false.
- `SUCCESS` is intentionally unavailable in production until checkpoint and output semantics are implemented.

Tests may subclass and override seams to exercise call order. That opt-in does not change production defaults.




