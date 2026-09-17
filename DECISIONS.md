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
