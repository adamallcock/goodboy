---
title: Agent Rail V1 Implementation Plan
date: 2026-05-26
type: plan
status: implemented
---

# Agent Rail V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Goodboy much harder for agents to misuse by adding simple golden-path commands, workflow-state guidance, explicit approval records, safe install, and renderer-script blocking.

Note: Agent Rail v1 is implemented and has since been extended by Agent Rail v2 and v3. Current agent-facing docs should prefer `start` and `advance --agent-mode`; lower-level commands such as `doctor`, `generate-handoff --all`, `import-generated --map`, `build-review`, `finish`, `build-from-rows`, `review-status`, and `install` remain available for diagnostics, compatibility, and manual recovery.

**Architecture:** Add a small workflow layer beside the existing pipeline. It reads current project artifacts, writes durable state/approval manifests, reports the next allowed action, and gives the CLI simple commands that fail closed instead of relying on agent judgment.

**Tech Stack:** Python stdlib, existing Goodboy JSON/dataclass patterns, existing unittest suite, Pillow-based fixture tests.

---

### Task 1: Workflow State And Next Action

**Files:**
- Create: `src/goodboy/workflow.py`
- Modify: `src/goodboy/cli.py`
- Test: `tests/test_core.py`

- [x] Write failing tests for `goodboy next` on a fresh project and after source ingest.
- [x] Implement `WorkflowStatus`, `next_action`, and `write_workflow_state`.
- [x] Add `goodboy next <project-dir> [--agent-mode]`.
- [x] Verify text and JSON output both identify allowed and blocked actions.

### Task 2: Golden Path `make`

**Files:**
- Modify: `src/goodboy/workflow.py`
- Modify: `src/goodboy/cli.py`
- Test: `tests/test_core.py`

- [x] Write failing test that `goodboy make` creates a project, ingests sources, drafts a source card, plans candidates, and stops at baseline generation.
- [x] Implement `make_project`.
- [x] Add `goodboy make <project-dir> --pet-id ... --display-name ... --species ... --source ...`.
- [x] Verify `workflow-state.json` and `goodboy next --agent-mode`.

### Task 3: Approval Records And Review Status

**Files:**
- Modify: `src/goodboy/schemas.py`
- Modify: `src/goodboy/workflow.py`
- Modify: `src/goodboy/cli.py`
- Test: `tests/test_core.py`

- [x] Write failing tests for `goodboy approve` and `goodboy review-status`.
- [x] Add an `ApprovalRecord` dataclass.
- [x] Write approvals to `runs/<run-id>/approvals/<artifact>.json`.
- [x] Make review-status summarize artifacts, approval state, and install readiness.

### Task 4: Safe Install Command And Renderer Detection

**Files:**
- Modify: `src/goodboy/pipeline.py`
- Modify: `src/goodboy/workflow.py`
- Modify: `src/goodboy/cli.py`
- Test: `tests/test_core.py`

- [x] Write failing tests that `goodboy install` refuses missing approval and suspicious renderer scripts.
- [x] Add renderer-script scanning for project-local ad hoc drawing code.
- [x] Implement `goodboy install <project-dir> --run-id ... --row-provenance ...`.
- [x] Keep `build-from-rows --install` backward compatible but subject to the same gates.

### Task 5: Docs, Skill Sync, And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/2026-05-26-goodboy-user-guide.md`
- Modify: `docs/002-implementation-notes.md`
- Modify: `codex-skill/goodboy/SKILL.md`
- Modify: `$CODEX_HOME/skills/goodboy/SKILL.md`

- [x] Document the simple agent path. Agent Rail v3 now documents the preferred path as `start`, `advance --agent-mode`, provider generation, generated-output map import through `advance`, and approval/install through `advance`.
- [x] Update the installed skill to prefer the simple commands.
- [x] Run full unittest discovery.
- [x] Run skill validation.
- [x] Run CLI smoke checks for blocked and approved installs.

Self-review: This plan covers the requested simplification and agent-proofing. It intentionally does not build a full visual LLM critic yet; the current goal is to make agent behavior safe and repeatable with hard gates.
