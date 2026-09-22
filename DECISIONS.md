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