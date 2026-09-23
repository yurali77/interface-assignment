# Architecture v0

## 1. Purpose

This system implements a small end-to-end computer-use automation platform for applications that do not expose a usable API.

The initial concrete target is a locally hosted legacy-style banking back-office demo. The system accepts a natural-language goal, uses an LLM-driven discovery loop to complete that goal on a live UI, records the successful run as a reusable Capability Artifact, and later replays that artifact deterministically without using an LLM for next-action decisions.

The architecture is designed around three primary execution paths:

```text
Discovery
→ learn how to complete a goal

Artifact construction
→ convert a successful run into a reusable capability

Production replay
→ invoke the capability deterministically
```

The core architectural principle is:

```text
The model discovers.
The artifact records reusable behavior.
The replay engine executes that behavior deterministically.
```

The design also includes explicit safety enforcement, evidence collection, structured runtime outcomes, and same-session human handoff when automation cannot safely continue.

---

## 2. Scope

Architecture v0 implements one concrete surface:

```text
Local Legacy Banking Demo
        ↑
PlaywrightSurface
```

The initial technology direction is:

```text
Python
Playwright
Pydantic
pytest
LLM provider: TBD
```

The system does not attempt to implement production-scale infrastructure such as distributed workers, queues, clusters, or a full multi-tenant platform.

Instead, the architecture keeps the boundaries necessary to support future:

```text
legacy web surfaces
desktop applications
tenant-specific specialization
version drift handling
capability registry expansion
```

without requiring the current implementation to build those systems in full.

---

## 3. High-Level Architecture

The system contains the following major responsibilities:

```text
Discovery Agent
LLM Client
Policy / Safety
Surface Interface
PlaywrightSurface
Evidence Logger
Artifact Builder
Capability Artifact
Capability Registry
Replay Engine
Handoff Manager
```

The primary relationships are:

```text
                 DISCOVERY

          Natural-language Goal
                   ↓
            Discovery Agent
             /     |      \
            /      |       \
      LLM Client Policy   Evidence
            \      |       /
                   ↓
           Surface Interface
                   ↓
           PlaywrightSurface
                   ↓
      Local Legacy Banking Demo
                   ↓
             New Observation
                   ↓
            Discovery Agent
                   │
             goal complete
                   ↓
       Structured DiscoveryTrace
                   ↓
            Artifact Builder
                   ↓
          Capability Artifact
                   ↓
         Capability Registry
```

```text
                   REPLAY

       Capability Invocation
          + Input Parameters
                   ↓
         Capability Registry
                   ↓
          Effective Capability
                   ↓
             Replay Engine
             /     |      \
            /      |       \
       Policy   Evidence   Handoff
            \      |       /
                   ↓
           Surface Interface
                   ↓
           PlaywrightSurface
                   ↓
      Local Legacy Banking Demo
                   ↓
       Step / Checkpoint Results
                   ↓
           Output Extraction
                   ↓
       Structured Replay Result
```

---

## 4. Discovery Path

The Discovery Agent owns the goal-driven discovery loop.

Conceptually:

```text
Goal
↓
Observe
↓
Ask LLM for proposed next action
↓
Policy check
↓
Execute through Surface
↓
Observe resulting state
↓
Continue / stop / escalate
```

The Discovery Agent does not directly call Playwright.

It depends only on the Surface abstraction for UI observation and action execution.

The Discovery Agent also does not directly build the final Capability Artifact. Its output is a structured `DiscoveryTrace` representing what happened during the discovery run.

A successful discovery flow is therefore:

```text
Goal
↓
Discovery Agent
↓
LLM proposes action
↓
Policy/Safety evaluates action
↓
Surface executes action
↓
Observation returned
↓
repeat
↓
LLM proposes goal completion
↓
explicit success condition is verified
↓
Successful DiscoveryTrace
```

The LLM may reason about semantic goal completion, but deterministic stopping conditions remain under Discovery Agent control.

Examples include:

```text
max steps
timeout
policy block
repeated failures
dead-end
```

The Discovery Agent remains the orchestration authority even when the LLM contributes semantic judgments.

---

## 5. DiscoveryTrace Boundary

A `DiscoveryTrace` represents a concrete execution history.

It records structured facts such as:

```text
goal
concrete input values
ordered actions
observations
action results
semantic outcomes
verified success state
human intervention
final run status
```

The trace answers:

> What happened during this run?

It does not answer:

> What should every future run do?

That second question belongs to the Capability Artifact.

The DiscoveryTrace is therefore the boundary between runtime discovery and reusable automation:

```text
Concrete Run
↓
DiscoveryTrace
↓
Artifact Builder
↓
Reusable Capability
```

Human actions during a handoff are recorded in the trace with their actor explicitly identified as `HUMAN`.

Human-performed actions are evidence of intervention and are not automatically promoted into production automation steps.

---

## 6. Artifact Builder

The Artifact Builder converts a successful `DiscoveryTrace` into a reusable Capability Artifact.

It is a transformation layer, not a serializer.

Its responsibilities include:

```text
parameterizing per-invocation values
normalizing reusable actions
generalizing UI targets
carrying forward known outcomes
creating reusable checkpoints
constructing typed input/output contracts
performing structural schema validation
```

For example:

```text
Discovery:
type "12345" into Member ID

Artifact:
type {{member_id}} into member_id_field
```

The Artifact Builder should operate deterministically from structured discovery data in v0 rather than acting as another open-ended reasoning agent.

The Builder only performs structural validation.

It may validate that:

```text
required fields exist
inputs and outputs have valid types
steps contain required action data
checkpoints exist
schema version is supported
```

It does not prove that the artifact works against the live application.

Behavioral validation belongs to the Replay Engine.

---

## 7. Capability Artifact

The Capability Artifact is the primary contract between discovery and production execution.

It describes:

```text
identity and version
compatibility
typed inputs
typed outputs
ordered actions
abstract UI targets
expected states
runtime outcomes and failures
success checkpoint
policy metadata
```

Detailed schema definitions are maintained separately in:

```text
docs/ARTIFACT_SCHEMA.md
```

The Replay Engine must be able to execute the Artifact without depending on Discovery Agent internals or raw LLM transcripts.

This means:

```text
Discovery Agent can disappear
and Replay must still function
```

as long as a valid Capability Artifact exists.

---

## 8. Capability Registry

The Capability Registry owns artifact storage and lifecycle concerns.

The Artifact Builder creates Capability Artifacts but does not store or register them.

Conceptually:

```text
Artifact Builder
↓
Capability Artifact
↓
Capability Registry
```

The Registry is responsible for concerns such as:

```text
capability lookup
capability version selection
base artifact resolution
tenant/version overrides
active or approved version selection
```

Architecture v0 does not require a production registry implementation.

A simple local file-backed registry is sufficient for the first implementation as long as the interface does not couple Replay directly to file paths.

---

## 9. Replay / Production Path

The Replay Engine executes a Capability Artifact deterministically.

The key distinction from Discovery is:

```text
Discovery Agent:
"What should I do next?"

Replay Engine:
"What does the artifact say the next step is?"
```

Replay does not invoke an LLM for normal next-action decisions.

The basic replay flow is:

```text
EffectiveCapability + Inputs
↓
Validate request, inputs, capability, and live session
↓
Select current artifact step
↓
Policy check
↓
Execute action through Surface
↓
Observe resulting state
↓
Evaluate declared runtime conditions
↓
If execution continues:
    verify step completion
↓
Mark step completed
↓
Continue to next step
↓
Verify final success checkpoint
↓
Verify required outputs
↓
Structured Replay Result
```

The Replay Engine owns execution semantics, including:

```text
input binding
step sequencing
expected-state verification
bounded recovery behavior
checkpoint verification
output extraction
structured result generation
```

It does not reason about a new workflow.

---

## 10. Runtime Result Model

Replay distinguishes three important runtime categories:

```text
Business Outcome
Recoverable Condition
Hard Failure
```

A business outcome is a legitimate domain result.

Example:

```text
MEMBER_NOT_FOUND
```

This should be returned to the caller as a structured result rather than treated as a crash.

A recoverable condition is a known runtime condition with a bounded, deterministic recovery strategy.

Example:

```text
SLOW_LOAD
→ retry once
```

A hard failure is a condition the capability cannot safely or deterministically recover from.

Examples:

```text
PERMISSION_DENIED
TARGET_UNRESOLVABLE
UNEXPECTED_DIALOG
```

The Capability Artifact defines capability-specific runtime semantics.

The Replay Engine owns the common execution and structured result contract.

---

## 11. Surface Abstraction

The Surface abstraction separates workflow semantics from UI technology.

Both Discovery Agent and Replay Engine depend on the same Surface interface:

```text
Discovery Agent ─┐
                 ├→ Surface Interface
Replay Engine ───┘
                         ↓
                 PlaywrightSurface
                         ↓
              Local Legacy Banking Demo
```

The Surface interface exposes general computer-use capabilities rather than Playwright-specific APIs.

Conceptually:

```text
observe()
act(action)
capture_evidence()
get_session()
```

Actions describe what should happen:

```text
CLICK
TYPE
SELECT
READ
NAVIGATE
WAIT
```

The Surface Adapter decides how the action is implemented.

For example:

```text
Artifact / Replay:
CLICK search_button

PlaywrightSurface:
resolve ControlTarget
→ locate control
→ click using Playwright
```

A future desktop implementation could reuse the same upper layers:

```text
Replay Engine
↓
Surface Interface
↓
DesktopSurface
↓
OS accessibility / desktop automation
```

The Replay Engine should not need to change.

---

## 12. ControlTarget and Target Resolution

Workflow layers refer to UI elements through abstract `ControlTarget` objects.

A `ControlTarget` describes the semantic identity of a UI object rather than a raw framework selector.

Examples of target properties include:

```text
semantic name
control kind
role
accessible name
label
context
fallback hints
```

The architectural boundary is:

```text
Artifact
= what UI object is intended

Surface Adapter
= how that object is located
```

This prevents Capability Artifacts from being tightly bound to Playwright or a clean DOM.

Legacy-specific fallback hints may exist, but they remain secondary to the abstract identity of the target.

---

## 13. Condition and Verification Model

The architecture uses a shared `Condition` abstraction to describe states that can be evaluated deterministically.

Conditions are reused for:

```text
step expected states
WAIT actions
business outcome detection
recoverable-condition detection
hard-failure detection
success checkpoints
```

Conceptually:

```text
Condition
= what should be true

WaitPolicy
= how long and how to wait for it
```

State-changing steps should normally declare a post-condition.

For example:

```text
CLICK Search
↓
expected:
Member Detail state visible
```

This avoids assuming that a successful UI API call means the workflow actually advanced.

The final success checkpoint is separate from individual step post-conditions.

---

## 14. Policy / Safety Boundary

Policy evaluation occurs before Surface execution.

The execution invariant is:

```text
LLM proposed action
or
Artifact step
        ↓
Policy / Safety
        ↓
ALLOW / BLOCK / REQUIRE_HUMAN
        ↓
Surface execution
```

The Discovery Agent and Replay Engine do not embed policy rules directly.

They provide action and execution context to the Policy/Safety module and react to the result.

The Policy/Safety layer is the final enforcement authority.

Capability Artifact policy metadata is declarative only.

The system-level Policy Engine may impose stricter runtime behavior based on:

```text
tenant
environment
session
action risk
invocation context
```

---

## 15. Evidence / Observability

Discovery Agent and Replay Engine do not directly manage log files or screenshot persistence.

Instead they emit structured run events and evidence requests to the Evidence Logger.

Conceptually:

```text
Discovery Agent ─┐
                 ├→ Evidence Logger
Replay Engine ───┤
Handoff Manager ─┘
```

The Evidence Logger owns:

```text
event formatting
redaction
persistence
screenshots
trace references
failure evidence
```

Centralized evidence handling makes redaction and debugging behavior consistent across discovery, replay, and human handoff.

Sensitive values should not be persisted raw when policy marks them as protected.

---

## 16. Human Handoff

Both Discovery and Replay may reach a state where automation cannot safely continue.

The architecture supports same-session human intervention:

```text
Discovery Agent / Replay Engine
        ↓
cannot safely continue
        ↓
Handoff Manager
        ↓
automation paused
        ↓
control owner = HUMAN
        ↓
human operates the same live session
        ↓
human completes or repairs manual step
        ↓
resume signal
        ↓
control owner = AUTOMATION
        ↓
automation re-observes current state
        ↓
execution continues or completes
```

The Handoff Manager owns the mechanics of control transfer.

The Discovery Agent or Replay Engine owns the decision that escalation is required.

The distinction is:

```text
Execution layer
= when escalation is needed

Handoff Manager
= how control is transferred
```

After human control is returned, automation re-observes the current UI state rather than assuming the state remained unchanged.

Human actions remain part of the run evidence.

They are not automatically converted into production automation.

---

## 17. Multi-Tenant and Version Specialization

The architecture separates stable base capability behavior from tenant- or version-specific differences.

Conceptually:

```text
Base Capability Artifact
        ↓
Tenant / Version Override
        ↓
Effective Capability
        ↓
Replay Engine
```

The base artifact should capture stable vendor/product behavior.

Overrides may specialize details such as:

```text
terminology
target resolution hints
route patterns
application versions
tenant-specific configuration
```

The initial implementation does not need to implement production-scale multi-tenant resolution.

The important architectural requirement is that tenant differences do not require duplicating the complete capability whenever the underlying workflow remains the same.

Drift detection and override resolution are defined by the Capability Registry contract in `docs/CAPABILITY_REGISTRY.md`.

---

## 18. Key Architectural Seams

The primary module boundaries are summarized below.

### Orchestration ↔ Capability Registry

```text
Input:
capability_id
+ tenant context
+ application/vendor context
+ application version

Output:
EffectiveCapability
or
ResolutionFailure
```
The Registry resolves capabilities before Replay begins.

Replay does not query the Registry during normal execution.

### Orchestration ↔ Replay Engine

```text
Input:
EffectiveCapability
+ invocation inputs
+ execution context
+ LiveSession

Output:
ReplayResult
```
Replay executes the already resolved capability deterministically.

The Replay Engine does not select capability versions, apply tenant overrides, or perform Registry resolution.

### Discovery / Replay ↔ Policy

```text
Input:
Action + execution context

Output:
ALLOW / BLOCK / REQUIRE_HUMAN
```

Policy decides whether execution is permitted.

### Discovery / Replay ↔ Surface

```text
Input:
Action / observation request

Output:
ActionResult / Observation
```

Upper layers express intent; the Surface implements UI interaction.

### Discovery Agent ↔ Artifact Builder

```text
Input:
Successful DiscoveryTrace

Output:
Capability Artifact
```

Discovery records concrete execution; the Builder creates reusable automation.

### Execution Layer ↔ Evidence Logger

```text
Input:
structured event / evidence request

Output:
persisted evidence reference
```

Execution describes what happened; Evidence Logger persists it.

### Discovery / Replay ↔ Handoff Manager

```text
Input:
InterventionRequest

Output:
handoff result / resume signal
```

Execution detects the need for human intervention; Handoff manages control transfer.

---

## 19. Relationship to Other Design Documents

The repository separates design intent, current architecture, and detailed contracts.

```text
DECISIONS.md
```

Records major design choices, their rationale, and trade-offs.

```text
docs/ARCHITECTURE.md
```

Describes the current system structure, module responsibilities, execution paths, and architectural seams.

```text
docs/ARTIFACT_SCHEMA.md
```

Defines the Capability Artifact contract in detail, including inputs, outputs, actions, targets, conditions, runtime outcomes, checkpoints, and policy metadata.

```text
REPORT.md
```

Will contain the final concise submission write-up and summarize the architecture and important trade-offs rather than duplicating the full internal design documentation.

---

## 20. Architecture v0 Cut Lines

Architecture v0 deliberately avoids premature production infrastructure.

The initial implementation may keep modules in a single Python process and repository.

The module boundaries described here are logical responsibility boundaries, not requirements for separate deployed services.

The following are intentionally not required for v0:

```text
microservices
distributed queues
cluster deployment
production database registry
full operator console
desktop surface implementation
full multi-tenant infrastructure
automatic drift remediation
automatic human-action promotion
```

The goal is a small end-to-end vertical slice with clean seams:

```text
real LLM discovery
→ structured trace
→ reusable artifact
→ deterministic replay
→ explicit runtime outcomes
→ policy enforcement
→ same-session human handoff
→ evidence
```

The architecture should remain simple enough to implement and defend while preserving credible extension points for the real banking environment.