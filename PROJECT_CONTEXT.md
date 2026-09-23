# Project Context

## Project

interface.ai Take-Home Project — Computer-Use Automation System

## Goal

Build a small but complete end-to-end computer-use automation system that can:

1. Accept a natural-language goal.
2. Use an LLM-driven discovery loop against a live UI.
3. Record a successful run as a reusable capability.
4. Replay that capability deterministically without LLM next-action decisions.
5. Handle expected business outcomes, recoverable conditions, hard failures, and human escalation.
6. Preserve evidence and enforce safety constraints.

## Target Application

Local legacy-style banking back-office demo.

Initial workflow:

```text
Member Search
→ Member Detail
→ Accounts
→ Open Sub-account
→ Review
→ Confirmation
```

The target choice is considered locked unless explicitly revisited.

## Tech Stack

- Python
- Playwright
- Pydantic
- pytest
- Git / GitHub
- LLM provider: TBD

## Architecture Summary

Primary flow:

```text
Discovery:
Natural-language Goal
→ Discovery Agent
→ Surface
→ Target Application
→ DiscoveryTrace
→ Artifact Builder
→ CapabilityArtifact

Replay:
Capability Invocation
→ Capability Registry
→ EffectiveCapability
→ Replay Engine
→ Surface
→ Target Application
→ ReplayResult
```

Key rules:

- Discovery and Replay use a shared `Surface` abstraction.
- Playwright-specific logic stays inside `PlaywrightSurface`.
- Policy checks happen before Surface execution.
- Replay receives an already resolved `EffectiveCapability`.
- Replay does not query the Registry or use an LLM for next-action decisions.
- Runtime conditions are evaluated before generic step verification.
- Human handoff preserves the same logical run and live session.
- Human actions are recorded but are not automatically promoted into automation.
- Drift is surfaced for review and does not silently rewrite production artifacts.

## Current Design Status

Architecture v0 is considered frozen enough to begin implementation.

Major design decisions are recorded through D028 in:

`DECISIONS.md`

Important contracts are defined in:

- `docs/ARCHITECTURE.md`
- `docs/ARTIFACT_SCHEMA.md`
- `docs/REPLAY_CONTRACT.md`
- `docs/CAPABILITY_REGISTRY.md`

These documents are the source of truth.

## Current Progress

Completed:

- Git/GitHub setup
- target application selection
- Architecture v0
- Artifact Schema v0
- Replay Contract v0
- Capability Registry v0
- multi-tenant override semantics
- drift handling semantics
- human handoff semantics
- architecture consistency review
- design decisions through D028

Implementation has not yet begun beyond basic Playwright experiments.

## Implementation Principle

Build one small, complete vertical slice before adding breadth.

Prefer:

```text
small + working + testable + explainable
```

over:

```text
large + abstract + incomplete
```

Do not redesign Architecture v0 unless implementation reveals a concrete blocker.

## Recommended Implementation Order

```text
1. Core Pydantic models
2. Minimal local banking demo
3. Surface interface
4. PlaywrightSurface
5. Replay Engine skeleton
6. Deterministic happy-path replay
7. Capability Registry
8. Policy / Evidence / Handoff
9. Discovery Agent + LLM
10. Artifact Builder
11. End-to-end vertical slice
```

## Next Task

Begin implementation.

Immediate focus:

1. Define Python package structure.
2. Implement core Pydantic models.
3. Define the `Surface` interface.
4. Create the Replay Engine skeleton.

Implementation should follow the frozen contracts first.
If code and design conflict, record the conflict before changing the design.