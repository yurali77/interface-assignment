# Artifact Schema v0

## 1. Purpose

A Capability Artifact is the reusable contract produced from a successful discovery run and consumed by the deterministic replay path.

The system separates discovery from production execution:

```text
Natural-language Goal
        ↓
Discovery Agent
        ↓
Structured DiscoveryTrace
        ↓
Artifact Builder
        ↓
Capability Artifact
        ↓
Capability Registry
        ↓
Replay Engine
        ↓
Surface Interface
        ↓
Target Application
```

During discovery, an LLM may reason about the current UI state and decide what action to take next. After a successful run, the Artifact Builder transforms the concrete `DiscoveryTrace` into a typed, parameterized, versioned Capability Artifact.

Production replay does not use the LLM to decide what to do next. The Replay Engine interprets the saved artifact deterministically, validates inputs, executes the recorded workflow through the Surface abstraction, handles expected outcomes and runtime failures, verifies the final success checkpoint, extracts declared outputs, and returns a structured result.

The Artifact is therefore not a raw execution log and not a model transcript. It is a reusable execution specification and agent-invocable capability contract.

---

## 2. Design Principles

### 2.1 Reusable, not run-specific

Concrete values from a discovery run should be parameterized when they vary between invocations.

For example:

```text
Discovery:
member_id = "12345"

Artifact:
member_id = {{member_id}}
```

The Artifact Builder performs this transformation rather than simply serializing the discovery trace.

### 2.2 Decoupled from raw LLM reasoning

The Artifact is built from a structured `DiscoveryTrace`, not directly from a raw model transcript.

The trace records structured observations, decisions, actions, results, outcomes, checkpoints, and actor information. Raw model transcripts may be retained separately as evidence, but they are not part of the production capability contract.

### 2.3 Surface-agnostic where practical

Artifacts describe computer-use intent rather than Playwright-specific implementation details.

For example, an artifact expresses:

```text
CLICK search_button
```

rather than:

```text
page.locator("#search").click()
```

The `Surface` implementation is responsible for translating abstract actions and targets into concrete UI operations.

### 2.4 Explicit target identity

UI references use an abstract `ControlTarget`.

A target describes what a control is, using semantic and accessible properties where possible. Raw CSS selectors, XPath expressions, or Playwright locators are not the primary identity of a target.

Surface-specific hints may be used as fallbacks when required by difficult legacy interfaces.

### 2.5 Deterministic replay

The Artifact contains enough information for the Replay Engine to know:

```text
what action to execute
what target to operate on
which invocation value to use
what state should follow the action
what outcomes or failures may occur
what outputs to extract
how final success is verified
```

Replay does not ask an LLM what action should happen next.

### 2.6 Explicit runtime semantics

Artifacts distinguish between:

```text
Business Outcome
Recoverable Condition
Hard Failure
```

For example, `MEMBER_NOT_FOUND` is a legitimate business result rather than an automation crash.

Known recovery behavior must be bounded. The Artifact Builder should not invent recovery strategies that were not established by discovery or explicit configuration.

### 2.7 Minimal sufficient verification

Checkpoints should verify enough business facts to establish that the requested operation really succeeded, without depending on unnecessary UI details.

For example:

```text
confirmation state is visible
AND displayed member ID matches {{member_id}}
AND displayed account type matches {{account_type}}
```

is preferable to comparing an entire page of exact text.

### 2.8 Base capability plus specialization

Base Capability Artifacts should represent stable vendor/product-level behavior where possible.

Tenant- or version-specific differences should be handled through an override or specialization layer:

```text
Base Capability Artifact
        +
Tenant / Version Override
        ↓
Effective Capability
```

This avoids rebuilding the complete capability independently for every institution.

### 2.9 Policy metadata is declarative

The Artifact describes capability risk, sensitive fields, expected action types, and step-level safety characteristics.

The Artifact does not have final safety authority.

The independent Policy/Safety layer remains responsible for the final:

```text
ALLOW
BLOCK
REQUIRE_HUMAN
```

decision before an action reaches the Surface.

---

## 3. Core Terminology

### DiscoveryTrace

A structured record of one discovery execution.

It records what actually happened, including concrete runtime values, actions, observations, outcomes, checkpoints, and human interventions.

It is an execution history, not a reusable capability.

### CapabilityArtifact

A typed, parameterized, versioned description of a reusable workflow.

It is produced by the Artifact Builder from a successful `DiscoveryTrace` and consumed by the Replay Engine.

### ControlTarget

A surface-independent description of a UI object that an action, condition, or output extraction refers to.

### Condition

A typed, reusable expression describing a UI or workflow state that should be true.

Conditions are reused for step verification, waits, business outcome detection, failure detection, and final success verification.

### Effective Capability

The capability that is actually executed after applying any applicable tenant- or version-specific overrides to a base Capability Artifact.

---

## 4. Top-Level Schema

```text
CapabilityArtifact
├── identity
├── provenance
├── compatibility
├── inputs
├── outputs
├── steps
├── outcomes_and_errors
├── success_checkpoint
└── policy_metadata
```

---

## 5. Section-by-Section Explanation

### 5.1 Identity

`identity` describes what the capability is.

```text
identity:
  capability_id
  name
  description
  schema_version
  capability_version
```

`capability_id` is the stable machine-readable identifier used by the Registry and callers.

`name` is the human-readable capability name.

`description` explains what the capability does and is intended to be useful to both human reviewers and calling agents.

`schema_version` identifies the version of the Capability Artifact format.

`capability_version` identifies the version of this specific capability.

For example:

```yaml
identity:
  capability_id: open_subaccount
  name: Open Member Sub-account
  description: >
    Looks up a member, opens the sub-account workflow,
    and reaches the confirmation state.
  schema_version: "1.0"
  capability_version: "1"
```

---

### 5.2 Provenance

`provenance` records where the artifact came from.

The minimum v0 field is:

```yaml
provenance:
  created_from_run_id: discovery-run-001
```

This allows the generated Artifact to be traced back to the successful discovery run and its evidence.

Future versions may add builder version, creation timestamp, approval metadata, or other provenance information.

---

### 5.3 Compatibility

`compatibility` describes the application context in which the base capability is expected to operate.

```text
compatibility:
  vendor_product
  app_family
  supported_versions
  surface_kind
```

Example:

```yaml
compatibility:
  vendor_product: local_legacy_banking_demo
  app_family: member_servicing
  supported_versions:
    - "v1"
  surface_kind: WEB
```

A base artifact should not normally bind itself directly to one tenant.

Tenant-specific branding, terminology, route differences, or version differences belong in the specialization/override layer.

`supported_versions` expresses the currently known compatibility range. It does not imply that the system has automatically proven compatibility across every listed version.

---

### 5.4 Inputs

`inputs` defines the invocation contract.

Each input contains:

```text
name
type
required
description
constraints?
```

Example:

```yaml
inputs:
  - name: member_id
    type: string
    required: true
    description: Member identifier used to locate the target member.
    constraints:
      pattern: "^[0-9]+$"

  - name: account_type
    type: string
    required: true
    description: Type of sub-account to open.
    constraints:
      allowed_values:
        - Savings
        - Checking
```

Stable constraints that can be checked before UI execution should be validated before Replay begins.

Conditions that can only be discovered by interacting with the live application are runtime outcomes rather than static input constraints.

---

### 5.5 Outputs

`outputs` defines the business data returned to the calling agent.

Each output contains:

```text
name
type
description
extraction_source
```

Example:

```yaml
outputs:
  - name: confirmation_id
    type: string
    description: Identifier displayed on the confirmation screen.
    extraction_source:
      step_id: read_confirmation
      target:
        semantic_name: confirmation_id
        target_kind: TEXT
        label: Confirmation ID
```

Output extraction uses the same abstract `ControlTarget` model as actions and conditions.

Whether an output is mandatory is tied to a result path rather than being universally required. Success-required outputs are declared by `success_checkpoint.required_outputs`.

---

### 5.6 Steps

`steps` contains the deterministic execution workflow.

Actions use a typed hierarchy rather than one large structure with many unrelated optional fields.

The v0 action types are:

```text
CLICK
TYPE
SELECT
READ
NAVIGATE
WAIT
```

Conceptually:

```text
BaseAction
├── ClickAction
├── TypeAction
├── SelectAction
├── ReadAction
├── NavigateAction
└── WaitAction
```

State-changing actions should normally declare an expected post-condition.

Example:

```yaml
- step_id: submit_member_search
  action:
    type: CLICK
    target:
      semantic_name: search_button
      target_kind: CONTROL
      role: button
      accessible_name: Search
  expected_state:
    condition:
      type: TARGET_VISIBLE
      target:
        semantic_name: member_detail_panel
        target_kind: REGION
```

A successful click does not prove that the workflow advanced correctly. The expected state verifies the resulting UI state before Replay continues.

`READ` actions use a result expectation rather than requiring UI state change.

`WAIT` is condition-based rather than a fixed sleep.

`NAVIGATE` is limited to allowlisted entry points or stable navigation contexts and should not be used to bypass the intended UI workflow.

---

### 5.7 ControlTarget

`ControlTarget` represents the semantic identity of a UI object.

```text
ControlTarget
  semantic_name
  target_kind
  role?
  accessible_name?
  label?
  context?
  fallbacks?
```

Example:

```yaml
target:
  semantic_name: search_button
  target_kind: CONTROL
  role: button
  accessible_name: Search
  context:
    region: member_search_form
  fallbacks:
    - text: Search
```

`semantic_name` is the stable canonical name used by the capability.

`role`, `accessible_name`, and `label` describe semantic or accessibility-level identity.

`context` disambiguates controls located inside a particular region, dialog, table, frame, or other container.

`fallbacks` provide additional resolution hints for legacy or non-semantic surfaces.

Fallback hints should not replace the semantic identity of the target.

---

### 5.8 Conditions

Conditions describe states that can be evaluated deterministically.

The v0 condition types are:

```text
TargetVisibleCondition
TargetNotVisibleCondition
TextPresentCondition
ValueEqualsCondition
RouteMatchesCondition
SemanticStateCondition
CompositeCondition
  AND
  OR
```

Example:

```yaml
condition:
  type: AND
  conditions:
    - type: SEMANTIC_STATE
      state: CONFIRMATION_SCREEN

    - type: VALUE_EQUALS
      target:
        semantic_name: member_id_display
        target_kind: TEXT
      expected_value: "{{member_id}}"

    - type: VALUE_EQUALS
      target:
        semantic_name: account_type_display
        target_kind: TEXT
      expected_value: "{{account_type}}"
```

Conditions describe what should be true.

Waiting behavior is separate:

```text
Condition
= what should become true

WaitPolicy
= how long and how to wait for it
```

This prevents state semantics from being tightly coupled to timing strategy.

---

### 5.9 Outcomes and Errors

The Artifact explicitly distinguishes:

```text
business_outcomes
recoverable_conditions
hard_failures
```

#### Business Outcome

A business outcome is a valid domain result rather than an automation crash.

Conceptually:

```text
BusinessOutcome
  code
  description
  applies_at
  detection_condition
  result_payload?
```

Example:

```yaml
business_outcomes:
  - code: MEMBER_NOT_FOUND
    description: No member exists for the supplied member_id.
    applies_at: submit_member_search
    detection_condition:
      type: TEXT_PRESENT
      text: Member not found
```

Replay should stop the happy-path workflow and return a structured `BUSINESS_OUTCOME` result.

#### Recoverable Condition

A recoverable condition is a known runtime problem with a bounded recovery strategy.

```text
RecoverableCondition
  code
  description
  applies_at
  detection_condition
  recovery_policy
```

Example:

```yaml
recoverable_conditions:
  - code: SLOW_LOAD
    description: Expected page remains in a loading state.
    applies_at: submit_member_search
    detection_condition:
      type: SEMANTIC_STATE
      state: LOADING
    recovery_policy:
      type: RETRY_STEP
      max_retries: 1
```
`max_retries` counts additional retries after the original execution attempt. For example, `max_retries: 1` allows one retry after the initial attempt.

After recovery, Replay re-observes the current state and checks the current step completion condition before deciding whether the original step needs to be retried.

Recovery must remain bounded and deterministic.

#### Hard Failure

A hard failure is a condition the capability cannot safely or deterministically recover from.

```text
HardFailure
  code
  description
  applies_at
  detection_condition
  escalation_policy?
```

Example failure codes may include:

```text
PERMISSION_DENIED
TARGET_UNRESOLVABLE
UNEXPECTED_DIALOG
```

The Artifact defines capability-specific failure semantics. The Replay Engine owns the common structured failure response and stopping behavior.

By default, a matched hard failure terminates Replay with a structured FAILURE.
A hard failure may explicitly declare:
escalation_policy: REQUIRE_HUMAN

When present, Replay pauses the current run and returns ESCALATED instead of terminating with FAILURE.
No other hard-failure escalation policies are supported in v0.
Example:
hard_failures:
  - code: UNEXPECTED_DIALOG
    description: An unexpected dialog blocks deterministic execution.
    applies_at: open_subaccount
    detection_condition:
      type: SEMANTIC_STATE
      state: UNEXPECTED_DIALOG
    escalation_policy: REQUIRE_HUMAN

If escalation_policy is omitted:
matched hard failure
→ FAILURE

If escalation_policy: REQUIRE_HUMAN is declared:
matched hard failure
→ ESCALATED
→ same-session human handoff

---

### 5.10 Success Checkpoint

`success_checkpoint` proves that the complete capability goal was actually achieved.

```text
success_checkpoint:
  description
  condition
  required_outputs
```

Example:

```yaml
success_checkpoint:
  description: >
    The requested sub-account workflow reached the confirmation
    state for the supplied member and account type.

  condition:
    type: AND
    conditions:
      - type: SEMANTIC_STATE
        state: CONFIRMATION_SCREEN

      - type: VALUE_EQUALS
        target:
          semantic_name: member_id_display
          target_kind: TEXT
        expected_value: "{{member_id}}"

      - type: VALUE_EQUALS
        target:
          semantic_name: account_type_display
          target_kind: TEXT
        expected_value: "{{account_type}}"

  required_outputs:
    - confirmation_id
```

Replay must not return `SUCCESS` merely because the final action did not throw an error.

Success requires:

```text
all required steps completed
        ↓
success checkpoint passed
        ↓
required outputs extracted
        ↓
SUCCESS
```

---

### 5.11 Policy Metadata

`policy_metadata` declares capability-level and step-level safety characteristics.

It does not replace the independent Policy/Safety module.

```text
policy_metadata:
  risk_level
  allowed_action_types
  sensitive_data_handling
  step_policies
```

Example:

```yaml
policy_metadata:
  risk_level: RISKY

  allowed_action_types:
    - NAVIGATE
    - TYPE
    - CLICK
    - SELECT
    - READ
    - WAIT

  sensitive_data_handling:
    sensitive_inputs:
      - member_id
    sensitive_outputs: []
    persist_raw_values: false

  step_policies:
    - step_id: open_subaccount
      risk_class: SENSITIVE
      required_handling: ALLOW
```

Possible step risk classes include:

```text
SAFE_REVERSIBLE
SENSITIVE
RISKY_IRREVERSIBLE
```

Possible handling declarations include:

```text
ALLOW
REQUIRE_HUMAN
BLOCK
```

These declarations provide context to the Policy Engine.

The Policy Engine remains the final enforcement authority and may apply stricter runtime policy based on tenant, environment, session, or invocation context.

---

## 6. Example Artifact

The following is a simplified example. It demonstrates the intended shape of the schema rather than acting as the final serialized implementation.

```yaml
identity:
  capability_id: open_subaccount
  name: Open Member Sub-account
  description: >
    Finds a member, enters the sub-account workflow,
    and reaches the confirmation state.
  schema_version: "1.0"
  capability_version: "1"

provenance:
  created_from_run_id: discovery-run-001

compatibility:
  vendor_product: local_legacy_banking_demo
  app_family: member_servicing
  supported_versions:
    - "v1"
  surface_kind: WEB

inputs:
  - name: member_id
    type: string
    required: true
    description: Member identifier.
    constraints:
      pattern: "^[0-9]+$"

  - name: account_type
    type: string
    required: true
    description: Requested sub-account type.
    constraints:
      allowed_values:
        - Savings
        - Checking

outputs:
  - name: confirmation_id
    type: string
    description: Confirmation identifier returned by the workflow.
    extraction_source:
      step_id: read_confirmation
      target:
        semantic_name: confirmation_id
        target_kind: TEXT
        label: Confirmation ID

steps:
  - step_id: enter_member_id
    action:
      type: TYPE
      target:
        semantic_name: member_id_field
        target_kind: CONTROL
        role: textbox
        label: Member ID
      value_binding: "{{member_id}}"

  - step_id: submit_member_search
    action:
      type: CLICK
      target:
        semantic_name: search_button
        target_kind: CONTROL
        role: button
        accessible_name: Search
    expected_state:
      condition:
        type: TARGET_VISIBLE
        target:
          semantic_name: member_detail_panel
          target_kind: REGION

  - step_id: open_subaccount
    action:
      type: CLICK
      target:
        semantic_name: open_subaccount_button
        target_kind: CONTROL
        role: button
        accessible_name: Open Sub-account

  - step_id: select_account_type
    action:
      type: SELECT
      target:
        semantic_name: account_type_selector
        target_kind: CONTROL
        role: combobox
        label: Account Type
      value_binding: "{{account_type}}"

  - step_id: continue_to_confirmation
    action:
      type: CLICK
      target:
        semantic_name: continue_button
        target_kind: CONTROL
        role: button
        accessible_name: Continue
    expected_state:
      condition:
        type: SEMANTIC_STATE
        state: CONFIRMATION_SCREEN

  - step_id: read_confirmation
    action:
      type: READ
      target:
        semantic_name: confirmation_id
        target_kind: TEXT
        label: Confirmation ID
      output_binding: confirmation_id
    result_expectation:
      type: string
      non_empty: true

outcomes_and_errors:
  business_outcomes:
    - code: MEMBER_NOT_FOUND
      description: No member exists for the supplied member_id.
      applies_at: submit_member_search
      detection_condition:
        type: TEXT_PRESENT
        text: Member not found

  recoverable_conditions:
    - code: SLOW_LOAD
      description: Expected page remains in a loading state.
      applies_at: submit_member_search
      detection_condition:
        type: SEMANTIC_STATE
        state: LOADING
      recovery_policy:
        type: RETRY
        max_attempts: 1

  hard_failures:
    - code: PERMISSION_DENIED
      description: Current session is not permitted to perform the operation.
      applies_at: open_subaccount
      detection_condition:
        type: TEXT_PRESENT
        text: Permission denied

success_checkpoint:
  description: >
    The workflow reached the confirmation state for the requested
    member and account type.

  condition:
    type: AND
    conditions:
      - type: SEMANTIC_STATE
        state: CONFIRMATION_SCREEN

      - type: VALUE_EQUALS
        target:
          semantic_name: member_id_display
          target_kind: TEXT
        expected_value: "{{member_id}}"

      - type: VALUE_EQUALS
        target:
          semantic_name: account_type_display
          target_kind: TEXT
        expected_value: "{{account_type}}"

  required_outputs:
    - confirmation_id

policy_metadata:
  risk_level: RISKY

  allowed_action_types:
    - TYPE
    - CLICK
    - SELECT
    - READ
    - WAIT
    - NAVIGATE

  sensitive_data_handling:
    sensitive_inputs:
      - member_id
    sensitive_outputs: []
    persist_raw_values: false

  step_policies:
    - step_id: open_subaccount
      risk_class: SENSITIVE
      required_handling: ALLOW
```

---

## 7. Versioning Strategy

The schema uses two independent versions.

### Schema Version

```text
schema_version
```

identifies the version of the Capability Artifact format itself.

A schema change may include adding, removing, or changing the meaning of structural fields.

The Replay Engine must know whether it supports the supplied schema version.

### Capability Version

```text
capability_version
```

identifies the version of one specific capability.

For example:

```text
open_subaccount v1
open_subaccount v2
open_subaccount v3
```

may all use the same Artifact schema version.

Capability versioning allows workflow behavior to evolve without treating every capability change as a schema change.

The Capability Registry will eventually own capability lookup, storage, and lifecycle/version selection. The Artifact Builder only creates and structurally validates artifacts.

---

## 8. Known Limitations / Future Extensions

Artifact Schema v0 intentionally focuses on the smallest complete contract required for the end-to-end system.

The current design has several deliberate limits.

Desktop and non-browser surfaces are represented by the abstraction but are not implemented in v0. The initial concrete Surface implementation is `PlaywrightSurface`.

Tenant/version override semantics are designed conceptually but the full resolution mechanism is not yet defined.

Drift detection and automatic compatibility assessment are not yet specified.

`ControlTarget` fallback resolution is intentionally limited. More sophisticated locator ranking, confidence scoring, and cross-tenant canonicalization may be added later.

The action taxonomy is deliberately small. Additional actions such as keyboard shortcuts, scrolling, file upload, drag-and-drop, or OS-specific actions should only be introduced if a real target requires them.

Human actions recorded during handoff are not automatically promoted into Capability Artifact steps. Any future human-to-automation promotion mechanism should require explicit review or approval.

Artifact Builder v0 is intended to perform deterministic transformation from structured discovery data rather than open-ended LLM-based artifact generation.

Confidence scoring, approval states, automatic artifact promotion, sophisticated migration tooling, and multi-run reliability scoring are outside the initial schema.

The goal of v0 is a small, reviewable, typed capability contract that supports a complete path from real LLM-driven discovery to deterministic replay while preserving clean seams for future extension.