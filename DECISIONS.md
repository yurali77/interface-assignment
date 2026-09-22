## D001 — Use a Local Legacy Banking Demo as the Target

Decision:
Use a locally hosted mock legacy banking back-office application as the concrete automation target.

Reason:
- Closely matches interface.ai's real use case.
- Lets us control legacy-like UI behavior and failure states.
- Makes it possible to test business outcomes, runtime errors, risky actions, and human handoff.
- Avoids real banking systems, real credentials, and real PII.

Initial Flow:
Member Search
→ Member Detail
→ Accounts
→ Open Sub-account
→ Review
→ Confirmation

Planned Exceptional States:
- Member not found
- Validation error
- Slow loading
- Unexpected dialog
- Risky confirmation step

## D002 — Separate Discovery Execution from Artifact Construction

Decision:
The Discovery Agent does not directly build the final Capability Artifact. It produces a structured `DiscoveryTrace`. After a successful discovery run, the Artifact Builder converts that trace into a reusable Capability Artifact.

Reason:
- The Discovery Agent is responsible for completing the goal-driven discovery loop.
- The Artifact Builder is responsible for transforming a concrete successful run into a reusable capability.
- These responsibilities change for different reasons and should remain decoupled.
- The Capability Artifact should be derived from structured execution data rather than directly from the raw LLM transcript.

Trade-off / Consequence:
- An intermediate `DiscoveryTrace` data model must be maintained.
- The extra abstraction adds some implementation overhead, but gives a clearer boundary between runtime discovery and reusable automation.


## D003 — Discovery and Replay Operate Through a Surface Abstraction

Decision:
The Discovery Agent and Replay Engine do not call Playwright directly. Both interact with the target application through a shared `Surface` interface. `PlaywrightSurface` implements this interface for the browser-based banking demo.

Reason:
- Discovery and replay should depend on general computer-use operations rather than Playwright-specific APIs.
- Surface-specific details such as DOM access, frames, locators, waiting, and browser interaction remain inside the surface adapter.
- The same Discovery Agent and Replay Engine design can later support other surface implementations, such as legacy web or desktop automation.
- This keeps the boundary between recorded workflow semantics and concrete UI-control technology explicit.

Trade-off / Consequence:
- The Surface interface must define stable action, observation, and result contracts.
- Some Playwright-specific functionality may need to be translated into more general surface-level concepts rather than exposed directly.


## D004 — Policy Checks Precede Surface Execution

Decision:
Every proposed action must be evaluated by the Policy/Safety layer before it is executed through the Surface.

The execution order is:

LLM decision or artifact step  
→ Policy evaluation  
→ ALLOW / BLOCK / REQUIRE_HUMAN  
→ Surface execution

Reason:
- Safety checks must happen before an action affects the live application.
- The same policy model should apply to both discovery and deterministic replay.
- Risky or irreversible actions can be blocked or escalated before they occur.
- Centralizing policy evaluation avoids embedding safety rules directly inside the Discovery Agent or Replay Engine.

Trade-off / Consequence:
- Every executable action must carry enough structured information for the Policy/Safety layer to evaluate it.
- Policy evaluation becomes part of the critical execution path.


## D005 — Evidence Persistence Is Separate from Execution Orchestration

Decision:
The Discovery Agent and Replay Engine emit structured run events and evidence requests. A separate Evidence Logger is responsible for formatting, redaction, and persistence of logs and richer evidence such as screenshots or traces.

Reason:
- Discovery and replay should focus on execution orchestration rather than file formats, screenshot naming, storage paths, or persistence details.
- Both execution paths require consistent observability and debugging evidence.
- Centralized evidence handling makes sensitive-data redaction easier to apply consistently.
- Evidence storage can evolve without changing the core discovery or replay logic.

Trade-off / Consequence:
- Execution modules must emit structured events rather than writing arbitrary logs directly.
- The Evidence Logger must define a clear event and evidence contract shared by discovery, replay, and handoff flows.


## D006 — Human Intervention Is Recorded but Not Automatically Promoted Into Automation

Decision:
Actions performed by a human during a handoff are recorded in the `DiscoveryTrace` with the actor explicitly identified as `HUMAN`. These actions are not automatically converted into production Capability Artifact steps.

Reason:
- Human actions change the state of the same live session and must be recorded so the run remains understandable and auditable.
- Human intervention may involve judgment, risky actions, recovery behavior, or automation gaps.
- A single successful manual action is not sufficient evidence that the same action is safe, deterministic, and reusable in production.
- Human-assisted behavior should require deliberate review before becoming automated behavior.

Trade-off / Consequence:
- The `DiscoveryTrace` must distinguish between automated and human-performed actions.
- The Artifact Builder must ignore human steps by default or treat them as intervention evidence rather than reusable production steps.
- A future approval or promotion mechanism could deliberately convert reviewed human actions into automation, but that is outside the initial scope.

## D007 — Artifact Builder Is a Transformation Layer, Not a Serializer

Decision:
The Artifact Builder transforms a successful `DiscoveryTrace` into a reusable Capability Artifact. It is responsible for generalization, parameterization, and normalization rather than simply serializing the concrete discovery run.

Reason:
- A discovery trace records what happened in one concrete execution, while a Capability Artifact must describe what should be reusable across future invocations.
- Per-invocation values should become typed parameters instead of being hard-coded into the artifact.
- Reusable steps, targets, checkpoints, and outcome semantics should be normalized from the concrete runtime trace.
- Keeping this transformation separate from the Discovery Agent preserves a clear boundary between runtime exploration and reusable automation.

Trade-off / Consequence:
- The `DiscoveryTrace` must contain enough structured metadata for deterministic transformation.
- The Artifact Builder adds an additional transformation step, but produces a cleaner and more reusable capability definition.
- The Builder should generalize only what the discovery run or explicit configuration supports and should not invent unsupported production behavior.


## D008 — Capability Artifacts Use Abstract Control Targets Rather Than Playwright-Specific Locators

Decision:
Capability Artifacts represent UI elements using an abstract `ControlTarget` model rather than embedding Playwright-specific selectors or APIs as the primary target representation.

Surface-specific adapters are responsible for resolving a `ControlTarget` into a concrete control on the target application.

Reason:
- The Artifact should express which control a step intends to operate on, while the Surface Adapter should determine how that control is located and manipulated on a particular technology.
- This keeps Capability Artifacts decoupled from Playwright and supports future surface implementations such as legacy web or desktop automation.
- Stable semantic properties such as control role, accessible name, label, or contextual identity can be represented independently of a specific automation framework.
- This creates a clear seam between reusable workflow semantics and surface-specific perception and execution.

Trade-off / Consequence:
- The Surface layer must implement target-resolution logic.
- `ControlTarget` may need optional surface-specific hints or fallbacks for difficult legacy interfaces, but those hints should not replace the abstract target identity.
- Designing a sufficiently expressive target model requires more care than storing a raw selector.


## D009 — Structural Validation Is Separate from Behavioral Validation

Decision:
The Artifact Builder is responsible for structural and schema validation of a generated Capability Artifact. The Replay Engine is responsible for validating the artifact behavior against the live application.

Artifact Builder validation includes checks such as:
- required fields are present,
- inputs and outputs have valid types,
- steps have valid actions and required targets,
- checkpoints are defined,
- the artifact schema version is valid.

Replay validation determines whether the artifact can actually execute successfully against the target application and satisfy its declared checkpoints and outputs.

Reason:
- Structural correctness can be determined without executing the capability.
- Behavioral correctness requires interaction with the live surface and therefore belongs to the Replay Engine.
- Keeping these responsibilities separate prevents the Artifact Builder from becoming an execution engine.
- This makes failures easier to classify as either invalid artifact structure or runtime execution failure.

Trade-off / Consequence:
- A structurally valid artifact is not guaranteed to work successfully at runtime.
- Replay testing remains necessary before an artifact can be considered behaviorally reliable.


## D010 — Base Capabilities Use Tenant and Version Overrides for Specialization

Decision:
Capability Artifacts should represent reusable vendor- or product-level behavior whenever possible. Tenant-specific or version-specific differences should be represented through an override or specialization layer rather than being permanently embedded into the base Capability Artifact.

Conceptually:

Base Capability Artifact  
→ Tenant / Version Override  
→ Effective Capability

Reason:
- Many institutions may run the same underlying vendor application with different branding, configuration, terminology, routes, or versions.
- A reusable base capability avoids rebuilding or re-recording the same automation independently for every tenant.
- Tenant- and version-specific overrides allow localized differences to be managed without duplicating the entire workflow.
- Separating stable capability semantics from tenant-specific details provides a cleaner foundation for drift detection and controlled specialization.

Trade-off / Consequence:
- The system will need a clear mechanism for resolving base artifacts together with applicable tenant or version overrides.
- The boundary between stable base behavior and tenant-specific variation must be defined carefully.
- Drift management becomes an explicit concern, but changes can be localized to overrides instead of forcing full artifact replacement.

## D011 — Capability Artifacts Use Typed Action and Condition Hierarchies

Decision:
Capability Artifacts use typed action and condition hierarchies rather than a single generic object with many optional fields.

The initial action hierarchy is:

- `ClickAction`
- `TypeAction`
- `SelectAction`
- `ReadAction`
- `NavigateAction`
- `WaitAction`

The initial condition hierarchy is:

- `TargetVisibleCondition`
- `TargetNotVisibleCondition`
- `TextPresentCondition`
- `ValueEqualsCondition`
- `RouteMatchesCondition`
- `SemanticStateCondition`
- `CompositeCondition` with `AND` / `OR`

Reason:
- Different action types require different fields and validation rules.
- Typed schemas make invalid combinations easier to detect before execution.
- Replay can dispatch deterministically based on the action type.
- A shared condition model allows the same verification abstraction to be reused across step expectations, waits, outcome detection, failure detection, and final success checkpoints.
- This keeps the Artifact strongly typed and reviewable rather than relying on loosely structured dictionaries.

Trade-off / Consequence:
- More schema types must be defined and maintained.
- Adding a new action or condition requires an explicit schema extension.
- The stronger type system adds some implementation overhead, but improves validation, replay clarity, and long-term extensibility.


## D012 — All UI References Use the Shared ControlTarget Abstraction

Decision:
All UI element references in a Capability Artifact should use the same abstract `ControlTarget` model whenever possible.

This includes UI references used by:

- actions,
- output extraction,
- step expected states,
- runtime outcome detection,
- failure detection,
- success checkpoints.

`ControlTarget` represents semantic target identity rather than a Playwright-specific locator.

Reason:
- Using one target abstraction prevents different parts of the Artifact from developing separate locator models.
- Actions, reads, checkpoints, and conditions all ultimately need to identify UI objects and should share the same representation.
- Keeping target identity abstract preserves the Surface boundary and avoids coupling the Artifact to Playwright or a clean DOM.
- The same Artifact model can later be resolved through other surface implementations such as accessibility-based or desktop automation.

Trade-off / Consequence:
- The Surface layer must support target resolution consistently across actions, observations, extraction, and verification.
- Some legacy interfaces may require surface-specific fallback hints.
- Those hints may be stored as secondary resolution information, but they should not replace the semantic `ControlTarget` identity.


## D013 — Step Verification and Capability Success Verification Are Separate

Decision:
The system distinguishes between step-level expected state verification and capability-level success verification.

A state-changing step should normally define an `expected_state` that verifies the workflow advanced correctly after the action.

The Capability Artifact separately defines a final `success_checkpoint` that verifies the complete requested goal was achieved.

Conceptually:

`step.expected_state`
= verifies that one execution step produced the expected local state.

`success_checkpoint`
= verifies that the overall capability completed successfully for the supplied invocation inputs.

Reason:
- A UI action completing without an execution error does not prove that the workflow reached the correct next state.
- Step-level verification detects problems early instead of allowing Replay to continue blindly.
- The final success checkpoint provides stronger end-to-end verification than relying on the final step alone.
- Capability success may require checking multiple business facts and required outputs rather than one local UI transition.

Trade-off / Consequence:
- Artifacts contain more verification metadata.
- Replay must evaluate conditions throughout execution rather than only at the end.
- Checkpoints must be designed carefully to be strong enough to prove success without becoming unnecessarily brittle.


## D014 — Runtime Conditions Are Declared in Artifacts and Executed Deterministically

Decision:
Capability Artifacts explicitly declare capability-specific runtime conditions in three categories:

- business outcomes,
- recoverable conditions,
- hard failures.

Each declared condition includes a deterministic detection rule. Recoverable conditions may also include a bounded recovery policy.

The Replay Engine executes these rules deterministically and does not invoke an LLM to decide how to handle normal runtime conditions.

Reason:
- Expected business outcomes must be distinguishable from automation failures.
- Known recoverable conditions should be handled predictably rather than through open-ended reasoning.
- Hard failures need clear stopping semantics and debuggable structured results.
- Declaring runtime semantics in the Artifact allows capability-specific behavior to remain reviewable and reusable while the Replay Engine provides a common execution model.
- This follows the requirement that deterministic replay deliberately handle business outcomes, recoverable runtime conditions, and hard failures rather than blindly continuing.

Trade-off / Consequence:
- Artifact authors and the Artifact Builder must explicitly model known runtime states.
- Recovery behavior must remain bounded, such as a limited retry count or a known one-time recovery action.
- Unknown runtime conditions still require a hard failure or human-escalation path.
- The Artifact should only declare recovery behavior supported by discovery evidence or explicit configuration and should not invent unsupported production behavior.

## D015 — Replay Receives a Resolved Effective Capability

Decision:
The Replay Engine receives an already resolved `EffectiveCapability` rather than a `capability_id` or version-selection request.

Capability lookup, version selection, and tenant/version override resolution happen before Replay begins.

The Replay Engine is responsible only for deterministic execution of the capability it receives.

Reason:
- Keeps capability resolution separate from execution.
- Prevents Replay from taking on registry, version-selection, or override-resolution responsibilities.
- Makes the Replay contract simpler and easier to test.
- Allows the same Replay Engine to execute capabilities from different registry or storage implementations.

Trade-off / Consequence:
- An orchestration or registry layer must resolve the capability before invoking Replay.
- The resolved capability must contain all information needed for execution.
- Replay cannot independently fall back to another capability version if execution fails.


## D016 — Replay Results Use a Typed Union

Decision:
`ReplayResult` is represented as a typed union:

- `SuccessResult`
- `BusinessOutcomeResult`
- `FailureResult`
- `EscalatedResult`

Each result type has a distinct payload associated with its status.

Reason:
- Prevents invalid combinations such as `status: SUCCESS` with a failure payload.
- Makes caller handling explicit and deterministic.
- Preserves the semantic distinction between successful completion, expected business outcomes, execution failures, and human escalation.
- Aligns with the typed action and condition approach used by the Capability Artifact.

Trade-off / Consequence:
- Multiple result models must be defined and maintained.
- Callers must explicitly handle each supported result variant.
- Adding a new top-level replay outcome requires extending the result union.


## D017 — Human Escalation Pauses Rather Than Terminates Replay

Decision:
`ESCALATED` represents a paused replay state rather than an automatic terminal failure.

When escalation occurs, control may be transferred to a human while preserving the same logical replay run and live session.

The same `run_id`, `session_id`, `capability_id`, and `capability_version` remain associated with the replay across handoff and resume.

Reason:
- Human handoff is part of the required execution model rather than equivalent to failure.
- Preserving the same run and live session allows a human to operate on the exact application state reached by automation.
- It keeps evidence, execution history, and intervention context connected to one logical run.

Trade-off / Consequence:
- Replay lifecycle is no longer purely terminal; a run may temporarily enter a paused state.
- Runtime state must remain available while the human owns the session.
- Individual interventions require their own identifiers so multiple handoffs within one run can be distinguished.


## D018 — Replay Re-Observes State Before Resuming Automation

Decision:
After human intervention or recovery, Replay must re-observe the current live application state before deciding how to continue.

Replay first evaluates whether the interrupted step's completion condition is already satisfied.

If it is satisfied, the step is marked complete and Replay continues without repeating the original action.

If it is not satisfied, Replay may continue only through declared deterministic behavior such as an allowed retry, known recovery path, re-escalation, or failure.

Reason:
- Human or recovery actions may already have advanced the application state.
- Blindly repeating the interrupted action could cause duplicate submissions or other unsafe state changes.
- Re-observation keeps resume behavior deterministic without requiring LLM reasoning.

Trade-off / Consequence:
- Resume requires the interrupted step to have a well-defined completion condition.
- Replay must preserve enough execution state to know which step was interrupted.
- Some ambiguous post-handoff states may require another escalation or failure rather than automatic continuation.


## D019 — Runtime Conditions Use Deterministic Precedence and Bounded Recovery

Decision:
Replay evaluates declared runtime conditions before generic step verification.

When multiple condition categories match the same observation, v0 uses the fixed precedence:

`HARD_FAILURE > BUSINESS_OUTCOME > RECOVERABLE_CONDITION`

Multiple matches within the same category are treated as an ambiguous runtime state rather than resolved by declaration order.

Recoverable conditions may execute only artifact-declared, deterministic, bounded recovery policies.

Retry limits use `max_retries`, where the original attempt is not counted as a retry.

Reason:
- Known runtime states should not be misclassified as generic expected-state failures.
- Fixed precedence avoids nondeterministic "first match wins" behavior.
- Bounded recovery prevents open-ended retry loops.
- Explicit recovery behavior preserves deterministic replay without an LLM in the loop.

Trade-off / Consequence:
- Artifact condition rules must be designed to avoid unnecessary overlap.
- Unknown or ambiguous states may terminate or escalate instead of being automatically repaired.
- Replay cannot improvise recovery behavior that is not declared by the capability.


## D020 — Step Completion Requires Verified Post-Conditions

Decision:
A Replay step is not considered complete merely because the underlying automation action executed without an API error.

For state-changing actions, the declared `expected_state` must be verified before the step is marked complete.

`READ` steps complete when the declared value is successfully extracted and its result expectation is satisfied.

`WAIT` steps complete only when their declared condition becomes true within the allowed wait policy.

`last_completed_step_id` therefore refers to the last step that fully satisfied its completion contract, not the last step attempted.

Reason:
- Successful UI interaction does not prove that the application reached the intended state.
- Post-condition verification detects drift and runtime failures close to the step where they occur.
- It gives `step_context`, failure reporting, and resume logic precise semantics.
- It supports reliable final checkpoint verification instead of assuming workflow success from action execution alone.

Trade-off / Consequence:
- Artifacts must define meaningful completion conditions for executable steps.
- Replay performs additional observation and verification work after actions.
- Poorly designed or overly brittle conditions can cause false failures and must be reviewed carefully.

## D021 — Capability Registry Selects an Approved, Active, Compatible Capability Version

Decision:
The Capability Registry is responsible for selecting the capability version that is approved, active, and compatible with the current execution context before Replay begins.

Replay does not select versions itself.

A capability version may be approved without being active, and a version may be active in principle but still be incompatible with the current tenant or application version.

Reason:
- Keeps version selection outside the Replay Engine.
- Separates review state from execution state.
- Prevents unapproved or incompatible capability versions from reaching deterministic replay.
- Allows new versions to be reviewed before they are activated.

Trade-off / Consequence:
- Registry metadata must track approval and active state.
- Resolution may fail before Replay if no valid version exists.
- Version lifecycle becomes an explicit Registry responsibility rather than an execution concern.


## D022 — Capability Resolution Uses Tenant and Application Context

Decision:
Capability resolution is based on more than `capability_id`.

The Registry uses resolution context including:

- `capability_id`,
- `tenant_id`,
- vendor/product context,
- application version context.

Conceptually:

`capability_id + tenant_id + app/vendor version context -> EffectiveCapability`

The Registry selects a compatible base capability and then applies any applicable tenant/version specialization.

Reason:
- The same vendor product may behave differently across tenants or application versions.
- A capability that is active may still be incompatible with the current application version.
- Resolution context makes multi-tenant and version specialization explicit rather than embedding it in Replay.

Trade-off / Consequence:
- Registry resolution logic is more complex than a simple lookup by `capability_id`.
- Execution callers must provide enough context for deterministic resolution.
- Missing or ambiguous application context may cause resolution to fail rather than guessing.


## D023 — Tenant and Version Overrides Are Narrow, Explicit Patches

Decision:
Tenant/version overrides use a narrow specialization model.

Overrides may adapt surface-specific or tenant-specific details such as:

- `ControlTarget` resolution hints,
- frame, region, or context hints,
- route metadata,
- compatibility metadata,
- surface-specific fallback information.

Overrides must not silently redefine:

- step order,
- business semantics,
- declared outputs,
- success meaning,
- risk policy,
- or the overall workflow.

Overrides are applied as field-level explicit patches over an allowlist of overrideable fields.

Generic deep merge is not used.

Reason:
- Preserves a meaningful shared base capability across tenants.
- Prevents tenant overrides from becoming hidden copies of entirely different workflows.
- Explicit patching makes specialization reviewable and predictable.
- Avoids unsafe or ambiguous merge behavior for arrays, steps, conditions, and policy fields.

Trade-off / Consequence:
- The override schema must explicitly define which fields may be patched.
- Some tenant differences cannot be represented as a simple override.
- Material workflow differences require a separately reviewed capability variant or specialization.


## D024 — Override Resolution Uses Deterministic Specificity Precedence

Decision:
When multiple overrides could apply, the Registry resolves them using fixed specificity precedence:

1. tenant + exact application version
2. tenant + version family or range
3. global version-specific override
4. base capability

The Registry must not rely on declaration order or "first match wins" behavior.

If multiple overrides match at the same highest specificity level, resolution fails with an explicit conflict rather than choosing one arbitrarily.

Reason:
- Makes capability resolution deterministic.
- Prevents configuration ordering from silently changing production behavior.
- Ensures the most specific compatible specialization is selected.
- Makes overlapping override definitions visible during resolution.

Trade-off / Consequence:
- Override metadata must contain enough context to determine specificity.
- Conflicting configuration causes resolution failure instead of automatic fallback.
- Teams must review and remove overlapping overrides when conflicts are detected.


## D025 — Drift Is Detected and Escalated, Not Automatically Repaired

Decision:
Drift handling in v0 is conservative.

If Registry-time or Replay-time evidence indicates that the current capability assumptions no longer match the target application, the system may mark the affected capability or override as incompatible or `needs_review`.

The system does not automatically:

- rewrite the production Capability Artifact,
- modify overrides,
- promote human actions into automation,
- or use an LLM to repair production behavior.

Registry handles resolution-time compatibility and drift signals, while Replay reports execution-time drift evidence through structured failures and evidence.

Reason:
- Automatic repair could silently change production behavior without review.
- Drift often indicates that the existing artifact assumptions are no longer trustworthy.
- Preserving evidence and requiring review keeps changes explicit and auditable.
- This keeps v0 focused on detection and safe failure rather than autonomous repair.

Trade-off / Consequence:
- Some drift situations require manual review before automation can resume.
- Capabilities may temporarily become unavailable instead of being automatically repaired.
- The system must preserve enough failure and evidence context to support later diagnosis and artifact updates.