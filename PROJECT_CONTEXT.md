# Project Context

## Project
interface.ai Take-Home Project — Computer-Use Automation System

## Goal
Build a small but complete end-to-end computer-use automation system.

The system should:
1. Accept a natural-language goal for a target application.
2. Use an LLM-driven observe → decide → act loop to complete the goal on a real UI.
3. Record the successful run as a structured, reusable capability artifact.
4. Replay that artifact deterministically without using the LLM for decisions.
5. Handle expected business outcomes, recoverable conditions, and hard failures.
6. Escalate to a human when the system cannot safely continue.
7. Preserve evidence and logs for discovery, replay, and handoff.
8. Enforce safety guardrails such as allowlists and sensitive-data redaction.

## Core Mental Model

Discovery:
Goal
→ LLM
→ Surface Adapter
→ Playwright
→ UI
→ successful run
→ capability artifact

Production Replay:
Capability call
→ artifact
→ replay engine
→ Surface Adapter
→ Playwright
→ UI
→ structured result

## Planned Tech Stack
- Python
- Playwright
- Pydantic
- pytest
- Model API: TBD
- Git / GitHub

## Current Design Direction
- Use a Surface abstraction so the replay engine is not tightly coupled to Playwright.
- Keep reusable artifacts separate from per-run logs/evidence.
- Deterministic replay should not use an LLM for decisions.
- Use stable semantic locators where possible.
- Human escalation should pause automation and allow a person to take over the same live session.
- Human actions should be logged but should not automatically modify production artifacts.

## Current Status
- Local project folder created.
- Python virtual environment created and activated.
- Playwright installed.
- Git repository initialized.
✓ local Git repo
✓ GitHub remote
✓ first push complete
✓ .gitignore fixed
- Target application selected: Local legacy banking demo.
- Core architecture not finalized.
- Artifact schema not yet designed.





## Next Task
draft Architecture v0.
