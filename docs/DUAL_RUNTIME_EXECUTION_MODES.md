# Dual-Runtime Execution Modes (Claude + Codex)

**Date:** 2026-03-02  
**Status:** Proposed feature design

## Feature Summary

Add a dual-runtime orchestration feature that uses both Claude and Codex agent pools for the same System2 workflow, with two operating modes:

1. **Capacity-Max Mode (default dual-runtime mode)**  
   Maximize concurrent agent utilization across both runtimes, then maximize completed work volume.
2. **Mirror Review Mode (post-design only)**  
   Run one Claude agent and one Codex agent of the same role on identical tasks, then adjudicate with Pike's 5 rules plus mapped requirements.

Both modes assume outputs are evaluated against mapped requirements before acceptance.

## Goals

- Maximize active subagents without violating dependency order, file safety, or gate rules.
- Maximize completed work per orchestration cycle.
- Preserve a single shared `spec/*` artifact chain across runtimes.
- Ensure deterministic, requirements-based acceptance and rejection decisions.

## Non-Goals

- Model vendor benchmarking for quality, cost, or speed outside the workflow context.
- Concurrent editing of the same file by multiple agents.
- Replacing gate approvals with fully autonomous merging/deploy.

## Preconditions

- Shared artifacts exist in `spec/` with System2 gate flow.
- Requirements are mapped to tasks (`task -> requirement IDs`).
- Both runtimes are configured with multi-agent support.
- File ownership and write scopes are explicit per delegated task.

## Shared Inputs

- `spec/context.md`
- `spec/requirements.md`
- `spec/design.md`
- `spec/tasks.md`
- Task-to-requirement mapping table (inline in tasks or separate index)

## Runtime Capability Model

Per runtime, track:

- `token_window_total`
- `token_window_reserved` (system prompt + safety + response margin)
- `token_window_available = total - reserved - current_context_size`
- `agent_slots_available`
- `estimated_turn_latency`

Per agent role, track:

- `role`
- `runtime` (`claude` or `codex`)
- `availability` (`idle`, `busy`, `blocked`)
- `allowed_paths` / ownership scope

## Mode 1: Capacity-Max Mode

### Intent

Use both runtime pools to maximize agent parallelism first, then maximize weighted task throughput.

### Optimization Objectives

Primary objective:

- Maximize `active_agents_count` per scheduling wave.

Secondary objective:

- Maximize `sum(task_weight * completion_score)` per wave.

Suggested task weight:

- `priority_weight * requirement_coverage_weight * dependency_unblock_weight`

### Scheduling Logic

1. Build a DAG from `spec/tasks.md` dependencies.
2. Select ready tasks (all dependencies satisfied).
3. For each ready task, compute feasible agents:
   - role-compatible
   - required tools available
   - write scope compatible
   - enough token window available
4. Score assignment:
   - `fit_score * token_headroom_score * urgency_score`
5. Assign tasks to maximize count of active agents.
6. Break ties by maximizing weighted throughput score.
7. Reserve token margin per assignment to avoid overflow.

### Safety Constraints

- Single-writer lock per file path at a time.
- No task assignment without requirement references.
- No completion accepted without requirement validation result.
- Gate order preserved (no implementation before Gate 4 approval).

### Completion Criteria (per task)

- Output includes requirement coverage statement (`REQ IDs satisfied`).
- Validation result: pass/fail against mapped requirements.
- Any failed requirement generates follow-up tasks automatically.

## Mode 2: Mirror Review Mode (Post-Design Only)

### Availability Rule

This mode is only available after design phase approval:

- Gate 3 passed (`spec/design.md` approved).

### Intent

For each selected task, run two parallel implementations/reviews:

- one Claude agent of role `R`
- one Codex agent of role `R`

Both receive identical objective, inputs, constraints, and requirement mapping.

### Flow

1. Select eligible task with mapped requirements.
2. Spawn paired agents (`claude:R`, `codex:R`) with identical prompt contract.
3. Collect outputs independently.
4. Select adjudicator agent by highest current `token_window_available` and `idle` status.
5. Adjudicator evaluates both outputs using:
   - mapped requirements
   - Pike's 5 rules
   - architecture constraints from `spec/design.md`
6. Adjudicator emits:
   - accepted output (A/B/merged)
   - rationale
   - requirement coverage verdict
   - Pike rule findings
   - residual risk notes

### Pike's 5 Rules Rubric

The adjudicator explicitly scores each candidate output:

1. Data dominates  
   - Does the solution use the right data structures and representations?
2. Measure, do not guess  
   - Are claims tied to measurable checks/tests?
3. Keep it simple  
   - Is complexity justified by requirement pressure?
4. Avoid premature optimization  
   - Is optimization evidence-based?
5. Clarity over cleverness  
   - Is the implementation understandable and maintainable?

### Mirror Mode Constraints

- Both candidates must be assessed against the same requirement map.
- Adjudicator cannot approve output with uncovered required IDs.
- If both fail critical requirements, task returns to queue with clarified constraints.

## Requirement Mapping Model

Required per task:

- `task_id`
- `requirement_ids[]`
- `acceptance_checks[]`
- `disallowed_changes[]`

At completion:

- Agent returns `covered_requirement_ids[]`
- Validator compares expected vs covered IDs
- Mismatch => fail with explicit delta

## Suggested Task Contract (for both modes)

Each delegated task should include:

- Objective
- Inputs
- Output files
- Allowed paths
- Requirement IDs (mandatory)
- Acceptance checks
- Runtime-specific constraints

## Gate Integration

- Gate 0-2: planning only (no mode selection impact).
- Gate 3 (design): unlocks Mirror Review Mode.
- Gate 4 (tasks): Capacity-Max Mode can execute task graph.
- Gate 5 (ship): accepted outputs must include requirement validation summary.

## Observability and Metrics

Track per wave and per task:

- active agents (`claude`, `codex`, total)
- token headroom utilization
- tasks completed
- requirement pass/fail counts
- mirror divergence rate (Mode 2)
- adjudicator override frequency

## Failure Handling

- Token overflow risk: split context and retry with smaller payload.
- Conflicting file writes: enforce lock and requeue losing task.
- Missing requirement map: block execution and request mapping update.
- Repeated validation failures: escalate to design/requirements review.

## Rollout Plan

1. Add mode selector to orchestrator (`capacity-max`, `mirror-review`).
2. Implement requirement mapping enforcement in delegation contract.
3. Add token-window-aware scheduler for ready-task waves.
4. Enable Mirror Review Mode guard (`Gate 3 required`).
5. Add reporting for utilization and requirement pass rates.

## Acceptance Criteria

- Capacity-Max Mode increases active concurrent agents vs single-runtime baseline.
- Completed task throughput increases without reducing requirement pass rate.
- Mirror Review Mode only activates when Gate 3 is passed.
- Mirror adjudication decisions cite both Pike rule outcomes and requirement mapping results.
