# Replay Contract v0

## 1. Purpose and Scope

The Replay Contract defines how the Replay Engine executes a resolved `EffectiveCapability` deterministically.

Replay does not use an LLM to decide the next action. It executes only behavior already declared by the capability and applicable policy rules.

This document defines:
- what Replay receives,
- the execution order,
- when a step is considered complete,
- how runtime conditions are handled,
- when recovery and retry are allowed,
- when Replay stops,
- how human escalation and resume work,
- and what Replay returns.

`ARTIFACT_SCHEMA.md` defines the structure of actions, conditions, outputs, outcomes, recovery policies, and checkpoints. This document defines how Replay interprets and executes them.

---

## 2. Replay Entry Contract

Conceptually:

```text
ReplayEngine.execute(
    request: ReplayRequest,
    session: LiveSession
) -> ReplayResult
```

### ReplayRequest

```yaml
effective_capability: <EffectiveCapability>

inputs:
  member_id: "12345"
  account_type: "Savings"

execution_context:
  tenant_id: "credit_union_a"
  session_id: "session-001"
  environment: "local_demo"
```

Replay receives an already resolved `EffectiveCapability`.

Version selection, tenant override resolution, and capability lookup happen before Replay begins. Replay does not query the Capability Registry itself.

### LiveSession

`LiveSession` is the runtime handle to the actual live application session.

`session_id` is the stable identifier used for logging, evidence correlation, and handoff.

The same `LiveSession` must remain available during human handoff and resume.

---

## 3. Preflight Validation

Replay performs the following checks before executing UI actions:

```text
1. Validate ReplayRequest structure
2. Validate invocation inputs
3. Validate EffectiveCapability structure
4. Validate LiveSession availability
5. Run replay-level policy pre-check
6. Begin step execution
```

Static input validation checks artifact-declared constraints such as required values, types, allowed values, and stable patterns.

Invalid static input returns:

```yaml
status: FAILURE
failure:
  category: INPUT_VALIDATION
  code: INVALID_INPUT
```

Business validity discovered only through the live application is not an input validation failure. For example, a syntactically valid `member_id` that produces "Member not found" should return a declared `BUSINESS_OUTCOME`.

Replay also performs lightweight structural validation of the resolved capability. A malformed capability returns:

```yaml
status: FAILURE
failure:
  category: ARTIFACT_VALIDATION
  code: INVALID_EFFECTIVE_CAPABILITY
```

---

## 4. Per-Step Execution Order

For each step, Replay follows this order:

```text
set current_step_id
↓
run per-step policy check
↓
execute action through Surface
↓
observe resulting state
↓
evaluate declared runtime conditions
↓
if execution continues:
    verify step completion
↓
mark step completed
↓
move to next step
```

Replay interacts with the application only through the Surface abstraction and does not call Playwright APIs directly.

---

## 5. Policy Decisions

Policy is evaluated at two levels:
- replay-level pre-check,
- per-step policy check.

Per-step decisions are handled deterministically:

```text
ALLOW
→ execute the step

BLOCK
→ do not execute the step
→ return FAILURE / POLICY_BLOCK

REQUIRE_HUMAN
→ do not execute the step
→ pause replay
→ return ESCALATED
```

Human handoff must not be used to bypass a `BLOCK`.

---

## 6. Runtime Conditions

After an action executes, Replay observes the resulting state.

Declared runtime conditions are evaluated **before** the normal `expected_state`.

```text
action
↓
observe
↓
evaluate runtime conditions
↓
if none applies:
    verify expected_state
```

Runtime condition precedence is fixed in v0:

```text
HARD_FAILURE
>
BUSINESS_OUTCOME
>
RECOVERABLE_CONDITION
```

Replay must not use array order or "first match wins" behavior.

If multiple conditions in the same category match simultaneously, Replay stops with:

```yaml
status: FAILURE
failure:
  category: RUNTIME_CONDITION
  code: AMBIGUOUS_RUNTIME_MATCH
```

### Hard Failure Handling

A matched hard failure returns `FAILURE` by default.

If the matched hard failure declares:

```text
escalation_policy: REQUIRE_HUMAN

Replay returns ESCALATED and enters the same-session human handoff flow.

No other hard-failure escalation policies are supported in v0.
```

---

## 7. Recovery and Retry

Recovery must be:
- declared by the Artifact,
- deterministic,
- bounded.

Example:

```yaml
recovery_policy:
  type: RETRY_STEP
  max_retries: 1
```

`max_retries: 1` means one additional retry after the original attempt.

Recovery flow:

```text
detect recoverable condition
↓
execute declared recovery_policy
↓
re-observe
↓
check current step completion condition
```

Replay does **not** automatically repeat the original action after recovery.

If the step condition is already satisfied:

```text
expected_state = true
→ mark step completed
→ continue
```

If the condition is still false:

```text
expected_state = false
→ retry current step only if recovery_policy allows
```

If the retry budget is exhausted:

```yaml
status: FAILURE
failure:
  category: RUNTIME_CONDITION
  code: RECOVERY_EXHAUSTED
```

---

## 8. Step Completion Rules

A step is not complete merely because the automation API call succeeded.

### State-Changing Actions

For actions such as `CLICK`, `TYPE`, `SELECT`, and `NAVIGATE`:

```text
policy allowed
↓
action executed
↓
observe result
↓
no terminal runtime condition matched
↓
expected_state verified
↓
step completed
```

### READ

A `READ` step completes when:
- the target is resolved,
- the value is extracted,
- the result expectation is satisfied,
- and output binding succeeds if applicable.

### WAIT

A `WAIT` step completes when its declared condition becomes true within its wait policy.

Replay tracks:

```yaml
step_context:
  last_completed_step_id: enter_member_id
  current_step_id: submit_member_search
```

`last_completed_step_id` means the last step that fully satisfied its completion contract, not merely the last attempted step.

---

## 9. Output Extraction and Final Success

Outputs may be captured during execution and stored in replay state.

After all required steps complete:

```text
verify success_checkpoint
↓
verify all required_outputs are present
↓
return SUCCESS
```

If the checkpoint fails:

```yaml
status: FAILURE
failure:
  category: CHECKPOINT_FAILURE
  code: SUCCESS_CHECKPOINT_FAILED
```

If the checkpoint succeeds but a required output is missing:

```yaml
status: FAILURE
failure:
  category: OUTPUT_EXTRACTION
  code: REQUIRED_OUTPUT_MISSING
```

Replay may return `SUCCESS` only when all required steps completed, the final checkpoint is verified, and all required outputs are available.

---

## 10. ReplayResult Contract

`ReplayResult` is a typed union:

```text
ReplayResult =
    SuccessResult
  | BusinessOutcomeResult
  | FailureResult
  | EscalatedResult
```

Shared metadata includes:
- `run_id`
- `capability_id`
- `capability_version`
- `session_id`
- `started_at`
- `finished_at?`
- `step_context`
- `runtime_events[]`
- `evidence_refs[]`

### SUCCESS

```yaml
status: SUCCESS
outputs:
  confirmation_id: "ABC123"
checkpoint:
  checkpoint_id: final_success
  verified: true
```

### BUSINESS_OUTCOME

```yaml
status: BUSINESS_OUTCOME
outcome:
  code: MEMBER_NOT_FOUND
  description: No member exists for the supplied member_id.
  payload:
    member_id: "12345"
```

`BUSINESS_OUTCOME` does not reuse `SUCCESS.outputs`.

### FAILURE

```yaml
status: FAILURE
failure:
  category: STEP_VERIFICATION
  code: EXPECTED_STATE_NOT_REACHED
  message: Member detail page did not appear after Search.
  expected:
    summary: Member detail panel is visible.
  observed:
    summary: Search page remained visible.
```

Initial v0 categories:

```text
INPUT_VALIDATION
ARTIFACT_VALIDATION
TARGET_RESOLUTION
STEP_VERIFICATION
RUNTIME_CONDITION
OUTPUT_EXTRACTION
CHECKPOINT_FAILURE
POLICY_BLOCK
SESSION_FAILURE
UNKNOWN
```

### ESCALATED

```yaml
status: ESCALATED
escalation:
  intervention_id: intervention-001
  reason_code: UNEXPECTED_DIALOG
  reason: Automation cannot safely continue.
  control_owner: HUMAN
  resume_allowed: true
```

`ESCALATED` is a paused replay state, not automatically a terminal failure.

---

## 11. Runtime Events

Recoverable events may be exposed through lightweight `runtime_events`.

Example:

```yaml
runtime_events:
  - type: RECOVERY
    code: SLOW_LOAD
    step_id: submit_member_search
    retry_number: 1
    resolved: true
```

A recoverable event does not change the final status if recovery succeeds.

Large screenshots, DOM snapshots, traces, and other evidence are referenced through `evidence_refs` rather than embedded directly in `ReplayResult`.

---

## 12. Human Escalation and Resume

Human escalation pauses the same logical replay run.

```text
RUNNING
↓
ESCALATED
↓
HUMAN_IN_CONTROL
↓
RESUME
↓
RUNNING
↓
SUCCESS / BUSINESS_OUTCOME / FAILURE
```

The following remain unchanged across handoff:
- `run_id`
- `session_id`
- `capability_id`
- `capability_version`

Each intervention receives its own `intervention_id`.

Automation must not execute UI actions while `control_owner = HUMAN`.

### Resume Rule

Replay must not blindly re-execute the interrupted step after human intervention.

Instead:

```text
human returns control
↓
re-observe the same LiveSession
↓
evaluate the current step completion condition
```

If the current step is already satisfied, mark it completed and continue.

If it is not satisfied, Replay continues only through declared deterministic behavior:
- allowed retry,
- known recovery,
- re-escalation,
- or failure.

Replay does not invoke an LLM to invent a new path during normal resume.

Human actions are recorded as execution history and evidence, but they are not automatically promoted into the Capability Artifact.

---

## 13. End-to-End Replay Algorithm

```text
receive:
    EffectiveCapability
    invocation inputs
    execution context
    LiveSession

↓
validate ReplayRequest
↓
validate inputs
↓
validate EffectiveCapability
↓
validate LiveSession
↓
run replay-level policy pre-check

↓
for each step:

    set current_step_id

    ↓
    per-step policy check

    BLOCK
        → FAILURE

    REQUIRE_HUMAN
        → ESCALATED

    ALLOW
        → continue

    ↓
    execute through Surface

    ↓
    observe

    ↓
    evaluate runtime conditions

    HARD_FAILURE
        → stop or escalate according to declared handling

    BUSINESS_OUTCOME
        → stop
        → BUSINESS_OUTCOME

    RECOVERABLE_CONDITION
        → execute bounded recovery
        → re-observe
        → check step completion condition
        → retry only if needed and allowed

    ambiguous same-category match
        → FAILURE

    ↓
    verify step completion

    ↓
    mark step completed

↓
verify success_checkpoint

    false
        → FAILURE

↓
verify required_outputs

    missing
        → FAILURE

↓
SUCCESS
```

---

## 14. Execution Invariants

1. Replay does not use an LLM for normal execution decisions.
2. Replay receives an already resolved `EffectiveCapability`.
3. Every executable action passes through Policy before Surface execution.
4. Replay interacts with the application only through Surface.
5. An action API returning successfully does not mean the step is complete.
6. State-changing steps require post-condition verification.
7. Declared runtime conditions are evaluated before generic step verification failure.
8. Runtime condition conflicts are resolved deterministically.
9. Recovery must be explicit and bounded.
10. Recovery does not automatically repeat the original action.
11. `SUCCESS` requires a verified final checkpoint.
12. `SUCCESS` also requires all required outputs.
13. Human escalation pauses the same logical run and live session.
14. Replay re-observes state before resuming after human intervention.
15. Policy `BLOCK` cannot be bypassed through handoff.
16. Human actions are recorded but not automatically added to the Artifact.
17. Failures must identify enough context to explain where execution stopped, what was expected, and what was observed.

---

## 15. v0 Scope

Replay Contract v0 intentionally does not attempt to implement:
- open-ended recovery planning,
- LLM-assisted production replay,
- automatic artifact repair,
- automatic drift remediation,
- distributed execution,
- cross-machine session migration,
- automatic learning from human actions,
- or production-scale orchestration.

The goal is a small, deterministic, reviewable replay engine with clear execution and failure semantics.
