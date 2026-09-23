# TODO

## Phase 1 — Foundation / Design
- [x] Initialize Git repo
- [x] Create project context files
- [x] Choose target application
- [x] Draft Architecture v0
- [x] Define Capability Artifact schema
- [x] Define Replay Contract v0
- [x] Define Capability Registry v0
- [x] Define multi-tenant override and drift semantics
- [x] Complete architecture consistency review
- [ ] Confirm implementation tech stack and package layout

## Phase 2 — Core Implementation

### 2.1 Models / Contracts
- [ ] Implement Pydantic models for CapabilityArtifact
- [ ] Implement action and condition model hierarchy
- [ ] Implement ControlTarget model
- [ ] Implement ReplayResult typed union
- [ ] Implement EffectiveCapability and Registry models

### 2.2 Target Surface
- [ ] Build local legacy banking demo
- [ ] Implement Surface interface
- [ ] Implement PlaywrightSurface
- [ ] Implement ControlTarget resolution

### 2.3 Deterministic Replay
- [ ] Implement Replay Engine skeleton
- [ ] Implement input validation and parameter binding
- [ ] Implement step execution and post-condition verification
- [ ] Implement runtime condition precedence
- [ ] Implement bounded recovery / retry
- [ ] Implement success checkpoint and output extraction

### 2.4 Registry
- [ ] Implement local file-backed Capability Registry
- [ ] Implement approved / active / compatible resolution
- [ ] Implement target override resolution
- [ ] Implement EffectiveCapability construction

### 2.5 Safety / Handoff / Evidence
- [ ] Implement Policy/Safety interface
- [ ] Implement evidence/event logging
- [ ] Implement same-session human handoff
- [ ] Implement resume + re-observation behavior

### 2.6 Discovery
- [ ] Implement Discovery Agent loop
- [ ] Integrate LLM client
- [ ] Produce structured DiscoveryTrace
- [ ] Implement Artifact Builder

### 2.7 Integration
- [ ] Run discovery → artifact → registry → replay vertical slice
- [ ] Test business outcome
- [ ] Test recoverable condition
- [ ] Test hard failure
- [ ] Test human handoff

## Phase 3 — Finalization
- [ ] Write README
- [ ] Write REPORT
- [ ] Run end-to-end demo
- [ ] Review repo
- [ ] Prepare defense / architecture walkthrough