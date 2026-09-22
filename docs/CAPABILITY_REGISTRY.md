# Capability Registry v0

## 1. Purpose

The Capability Registry resolves the executable capability that will be passed to the Replay Engine.

It owns capability version selection, approval and active-state filtering, compatibility checks, tenant/version override resolution, explicit override application, and resolution-time drift handling.

The Registry does **not** execute the capability. Its output is a resolved `EffectiveCapability`.

```text
ResolveCapabilityRequest
→ Capability Registry
→ EffectiveCapability
→ Replay Engine
```

---

## 2. Resolve Request

The Registry resolves a capability using both capability identity and execution context.

```yaml
capability_id: open_subaccount
tenant_id: credit_union_a
app_context:
  vendor_product: legacy_bank
  app_version: "3.2.1"
  surface_kind: web
```

The minimum resolution context is:

- `capability_id`
- `tenant_id`
- vendor/product context
- application version context

The Registry must not resolve only by `capability_id` when tenant or application compatibility could affect the result.

---

## 3. Base Capability Selection

The Registry first finds a valid base capability version.

A base capability is eligible only if it is:

- approved,
- active,
- compatible with the current application context.

These concepts are separate:

```text
approved = reviewed and allowed for use
active = currently selected for execution
compatible = valid for the current vendor/product/version context
```

A capability may be approved but inactive. It may also be approved and active but incompatible with the current application version.

The Registry must not pass an unapproved or incompatible base capability to Replay.

If no eligible base capability exists, resolution fails.

Example failure codes:

```text
NO_ACTIVE_APPROVED_CAPABILITY
NO_COMPATIBLE_CAPABILITY
```

---

## 4. Override Resolution

After selecting the base capability, the Registry resolves any applicable tenant/version override.

Overrides use a narrow specialization model.

They may adapt:

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

If a tenant requires a materially different workflow, that should be modeled as a separately reviewed capability variant rather than a large override.

### Override Precedence

When multiple overrides could apply, v0 uses this fixed specificity order:

```text
tenant + exact app version
>
tenant + version family/range
>
global version-specific override
>
base capability
```

The Registry must not use declaration order or "first match wins".

If multiple overrides match at the same highest specificity level, resolution fails with:

```text
OVERRIDE_RESOLUTION_CONFLICT
```

---

## 5. Override Application

Overrides are applied as field-level explicit patches.

The Registry does not perform a generic deep merge.

```text
Base Capability
+
Explicit Override Patch
→ validate patch
→ apply patch
→ EffectiveCapability
```

Before applying a patch, the Registry verifies that:

- every patched field is explicitly overrideable,
- the patch does not modify protected workflow semantics,
- the resulting artifact remains structurally valid.

If the patch touches a protected or unsupported field, resolution fails with:

```text
INVALID_OVERRIDE_PATCH
```

The allowlist of overrideable fields should remain small in v0.

---

## 6. EffectiveCapability

The output of Registry resolution is an `EffectiveCapability`.

It represents the exact capability definition Replay should execute after:

- base version selection,
- compatibility filtering,
- tenant/version specialization,
- patch validation.

Conceptually:

```text
EffectiveCapability
=
approved active compatible base capability
+
one valid resolved specialization
```

The Replay Engine does not re-select versions or re-apply overrides.

Once resolution succeeds, Replay treats the `EffectiveCapability` as the executable contract.

---

## 7. Resolution Algorithm

```text
receive:
    capability_id
    tenant_id
    vendor/product context
    app_version

→ find candidate capability versions
→ filter to approved versions
→ filter to active version
→ filter by compatibility

if none:
    fail resolution

→ select base capability
→ find matching tenant/version overrides
→ rank overrides by specificity

if multiple overrides tie at highest specificity:
    OVERRIDE_RESOLUTION_CONFLICT

if one override applies:
    validate explicit patch
    apply patch

→ validate resulting EffectiveCapability
→ return EffectiveCapability
```

Resolution must be deterministic for the same Registry state and the same request context.

---

## 8. Drift Handling

Drift handling in v0 is conservative.

The system may detect that a capability or override no longer matches the target application, but it must not silently repair production artifacts.

### Resolution-Time Drift

The Registry may detect drift before Replay begins, for example:

- the current application version is outside supported compatibility,
- an override no longer applies,
- compatibility metadata indicates the capability should not run.

The affected capability or override may be marked:

```text
incompatible
```

or:

```text
needs_review
```

Resolution then fails rather than guessing.

Example failure:

```text
DRIFT_REQUIRES_REVIEW
```

### Execution-Time Drift

Some drift is discovered only during Replay, for example:

- a declared target can no longer be resolved,
- an expected state no longer appears,
- observed UI structure no longer matches capability assumptions.

Replay reports structured failure and evidence.

The Registry or review workflow may later use that evidence to mark the relevant capability or override as `needs_review`.

Replay itself does not rewrite the Artifact.

---

## 9. Registry Failure Contract

Capability resolution may fail before Replay is invoked.

Initial v0 resolution failures include:

```text
NO_ACTIVE_APPROVED_CAPABILITY
NO_COMPATIBLE_CAPABILITY
OVERRIDE_RESOLUTION_CONFLICT
INVALID_OVERRIDE_PATCH
DRIFT_REQUIRES_REVIEW
```

These are Registry/resolution failures, not Replay failures.

The caller should receive enough context to identify:

- requested `capability_id`,
- tenant/application context,
- failure code,
- and a short reason.

Example:

```yaml
status: RESOLUTION_FAILURE
capability_id: open_subaccount
failure:
  code: NO_COMPATIBLE_CAPABILITY
  message: No active approved capability supports application version 4.0.
```

---

## 10. What the Registry Does Not Own

The Capability Registry does not own:

- Replay execution,
- UI interaction,
- artifact construction,
- discovery,
- evidence persistence,
- automatic drift repair,
- open-ended workflow specialization.

Material workflow changes require a reviewed capability variant rather than an unrestricted override.

---

## 11. Registry v0 Invariants

1. Replay receives a resolved `EffectiveCapability`, not an unresolved capability request.
2. Only approved and active capability versions may be selected.
3. Compatibility is checked before Replay begins.
4. Resolution uses tenant and application context, not only `capability_id`.
5. Overrides are narrow and may not silently redefine business workflow semantics.
6. Overrides use explicit field-level patches rather than generic deep merge.
7. Override selection uses deterministic specificity precedence.
8. Same-specificity override conflicts fail resolution instead of choosing arbitrarily.
9. Drift may mark a capability or override as incompatible or `needs_review`.
10. v0 never silently repairs or rewrites production capabilities.

---

## 12. v0 Scope

Capability Registry v0 intentionally does not attempt to provide:

- a production database-backed registry service,
- distributed consistency,
- automatic rollout infrastructure,
- automatic drift repair,
- automatic override generation,
- complex semantic-version solving,
- or large-scale capability governance.

The goal is a small, explicit, deterministic resolution layer that produces a valid `EffectiveCapability` for Replay.
