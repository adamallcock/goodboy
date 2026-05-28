---
title: Goodboy Agent Simplification And Centering Plan
date: 2026-05-26
type: plan
status: implemented
---

# Goodboy Agent Simplification And Centering Plan

## Problem

The sample-kitten run still required too much agent orchestration even after Agent Rail v1. The command log shows repeated validation, repeated planning, shell loops around row handoffs, manual copying from Codex generated-image folders, ad hoc Python to update generation metadata, environment probing that did not affect the chosen provider, and separate review/install checks.

The current idle animation also looks imperfectly centered. QA confirms that horizontal center is stable, but vertical positioning is not: idle has `cx_range = 0.5px`, `cy_range = 9.0px`, and every frame is bottom-pinned at a 12px margin. The visible issue is therefore not horizontal drift; it is pose-height/body-center bob caused by bottom anchoring plus differing generated pose heights.

## Principles

- Agents should call one command per conceptual stage, not assemble shell loops.
- Goodboy should be responsible for copying provider outputs into the expected paths and updating manifests.
- `goodboy next --agent-mode` should return executable next commands, not placeholders.
- Validating should be automatic after mutating commands unless explicitly disabled.
- QA should distinguish package validity from perceptual smoothness.
- Centering should be state-aware: idle/waiting/review need visual anchor stability; jumping/running may intentionally move more.

## Recommended Product Shape

Implementation status: the row-generation simplification, import flow, review build, finish command, executable `next` fields, idempotent planning behavior, state-aware centering, centering report, centering overlay, and QA drift thresholds are implemented. Agent Rail v3 also adds `start`, `advance --agent-mode`, default candidate-sheet rendering, short-form approval, and optional API accelerator reporting. Baseline image generation remains an interactive provider step, but `advance` can now select a baseline and continue when supplied `--candidate-id` and `--baseline-image`.

### 1. Add `goodboy doctor`

Purpose: replace environment-probing and repeated manual checks.

Command:

```bash
goodboy doctor <project-dir> --agent-mode
```

Responsibilities:

- report project validity
- report provider availability only for providers actually in use
- report next workflow stage
- report missing generated outputs
- report suspicious renderer scripts
- report whether tests are needed for source changes or only project-artifact changes

This lets agents stop running raw checks like `OPENAI_API_KEY`, `GEMINI_API_KEY`, `import openai`, `import google.genai`, and multiple `validate` calls.

### 2. Add `goodboy generate-handoff`

Purpose: replace one handoff command per row.

Command:

```bash
goodboy generate-handoff <project-dir> --run-id <run-id> --all
```

Responsibilities:

- prepare all missing provider handoff manifests
- print one concise checklist of prompt files and expected outputs
- write a `handoff-summary.json`
- return next action as `await_provider_outputs`

This removes shell loops over `row-idle`, `row-running-right`, etc.

### 3. Add `goodboy import-generated`

Purpose: replace `latest=$(ls -t ...)`, `cp`, `file`, and custom Python metadata updates.

Command:

```bash
goodboy import-generated <project-dir> \
  --run-id <run-id> \
  --state idle=/path/to/generated.png \
  --state running-right=/path/to/generated.png
```

Also support a manifest form:

```bash
goodboy import-generated <project-dir> --run-id <run-id> --map generated-output-map.json
```

Responsibilities:

- copy provider outputs to `runs/<run-id>/row-strips/<state>.png`
- validate image dimensions and type
- update `generation-jobs.json`
- update matching `provider-invocations/*.json`
- record original generated-image source path
- report missing states

This removes the largest error-prone section of the command log.

### 4. Add `goodboy build-review`

Purpose: combine build, QA, review status, and validation.

Command:

```bash
goodboy build-review <project-dir> --run-id <run-id> --row-provenance provider_generated
```

Responsibilities:

- build frames and spritesheet from `runs/<run-id>/row-strips`
- run QA and validate
- write review artifacts
- write a concise `review-summary.json`
- print paths to contact sheet and GIF previews
- block install until approval

This replaces separate `build-from-rows`, `validate`, and `review-status` calls for normal agent runs.

### 5. Add Approval/Install Finish Rail

Purpose: one final command after user approval. Agent Rail v3 prefers `advance`; `finish` remains available as the lower-level recovery command.

Command:

```bash
goodboy advance <project-dir> --agent-mode --run-id <run-id> --approval-notes "User approved ..."
# recovery equivalent:
goodboy finish <project-dir> --run-id <run-id> --approval-notes "User approved ..." --row-provenance provider_generated
```

Responsibilities:

- record approval
- run final install gates
- install package
- validate installed artifact
- print the installed pet path

Keep `approve`, `finish`, and `install` for lower-level control, but tell agents to use `advance`.

### 6. Make `goodboy next --agent-mode` Return Executable Commands

Current output contains placeholders like:

```text
goodboy select-candidate <project-dir> --candidate-id baseline-001 --image-path <generated.png>
```

New output should include:

- `recommended_command`
- `acceptable_commands`
- `missing_inputs`
- `do_not_run`
- `already_done`

For example:

```json
{
  "stage": "rows_planned",
  "recommended_command": "goodboy generate-handoff /path/project --run-id row-gen-20260526 --all",
  "after_provider_generation": "goodboy import-generated /path/project --run-id row-gen-20260526 --map /path/map.json",
  "do_not_run": ["plan-candidates", "local shell cp loops", "custom metadata python"]
}
```

### 7. Add Automatic Idempotence

Mutating commands should be safe to rerun and should say when work is already complete.

Examples:

- `make` should not re-plan candidates when candidates already exist unless `--refresh`.
- `plan-candidates` should warn or no-op when candidates already exist unless `--refresh`.
- `style-default` should no-op if unchanged unless `--refresh`.
- `plan-rows` should no-op if jobs already exist unless `--refresh`.

This would prevent the redundant `plan-candidates` call after `make`.

## Centering Plan

### Finding

The current raster pipeline bottom-pins most non-jump states:

```text
idle bottom_margin = 12
```

For sample-kitten idle, all frames have `bottom = 12`, but heights vary from 158px to 176px. That creates center movement from `cy = 108.0` to `cy = 117.0`. The pet is technically grounded, but visually bobbing.

### 1. Add State-Specific Anchor Policies

Introduce explicit anchor policies:

- `stable_center`: idle, waiting
- `stable_head_or_torso`: review, running/task
- `bottom_grounded`: running-left, running-right, waving, failed
- `motion_arc`: jumping

For idle, `stable_center` should use a per-row target visual center instead of bottom pinning.

### 2. Compute Row-Level Reference Geometry

During `build_row`, compute per-state row metrics:

- median bbox width
- median bbox height
- median subject center
- median bottom
- per-frame width/height variance

Then place each frame against the policy:

- idle: fixed target center y, with small allowed breathing offset only if generated pose indicates it
- waiting: fixed target center y with limited tilt offset
- review: fixed head/torso anchor if detectable, otherwise fixed center y
- running directional: preserve grounded bottom
- jumping: preserve motion arc

### 3. Add Default Idle Stabilization

Add default-on stabilization inside `build-review` and `build-from-rows`:

```bash
goodboy build-review <project-dir> --run-id <run-id> --row-provenance provider_generated
```

Implementation idea:

- after frame extraction, calculate idle frame alpha bboxes
- choose target `cy` as median `cy`
- shift each idle frame vertically toward target `cy`
- clamp to edge clearance
- write shift amounts to `frames/centering-report.json`

This is deliberately post-processing only; it does not touch the source row strips.

### 4. Add Centering QA Thresholds

Current QA only warns on horizontal drift for most states. Add state-specific vertical checks:

- idle `cy_range <= 4px`
- waiting `cy_range <= 6px`
- review `cy_range <= 8px`
- running/task `cy_range <= 10px`
- jumping allowed larger range
- failed allowed larger range but should be reported

For sample-kitten, idle would currently fail or warn because `cy_range = 9.0px`.

### 5. Add Centering Visual Preview

Create:

```text
runs/<run-id>/qa/centering-overlay.png
runs/<run-id>/qa/centering-report.json
```

The overlay should show each frame bbox and center line. This makes centering review less subjective and gives agents a concrete artifact to cite.

## Target Agent Workflow After Changes

For a new project:

```bash
goodboy start <project-dir> --pet-id sample-kitten --display-name "Sample Kitten" --species cat --source img1 --source img2
goodboy advance <project-dir> --agent-mode
# generate baseline candidates through the selected provider, then select one:
goodboy advance <project-dir> --agent-mode --candidate-id baseline-003 --baseline-image /path/to/generated-baseline.png --run-id row-gen-20260526
# generate row strips through the selected provider, then import/build:
goodboy advance <project-dir> --agent-mode --run-id row-gen-20260526 --generated-map row-map.json --row-provenance provider_generated
goodboy advance <project-dir> --agent-mode --run-id row-gen-20260526 --row-provenance provider_generated --approval-notes "User approved contact sheet and previews"
```

For a mature version, this can collapse further into:

```bash
goodboy start ...
goodboy advance <project-dir> --agent-mode
goodboy advance <project-dir> --agent-mode --approval-notes "..."
```

## Implementation Milestones

### M1: Command Simplification

- `[x]` Add `doctor`.
- `[x]` Add batch `generate-handoff`.
- `[x]` Add idempotent no-op/refresh behavior for planning commands.
- `[x]` Update `next --agent-mode` to return executable commands.

### M2: Import And Metadata Automation

- `[x]` Add `import-generated`.
- `[x]` Add generated-output mapping format.
- `[x]` Add tests that prove no shell copy/custom Python metadata update is needed.

### M3: Build Review And Finish

- `[x]` Add `build-review`.
- `[x]` Add `finish`.
- `[x]` Keep lower-level commands but demote them in docs/skill.
- `[x]` Add smoke tests for the complete simplified workflow.

### M4: Centering Stabilization

- `[x]` Add anchor policies.
- `[x]` Add idle stabilization.
- `[x]` Add `centering-report.json`.
- `[x]` Add `centering-overlay.png`.
- `[x]` Add QA thresholds for state-specific vertical drift.
- `[x]` Add regression test using a synthetic variable-height idle row.

### M5: Documentation And Skill Update

- `[x]` Update README and user guide to present only the simple flow first.
- `[x]` Move low-level commands into compatibility/manual recovery sections.
- `[x]` Update the installed skill to say: use `start` and `advance --agent-mode`; use `doctor`, `next`, `generate-handoff`, `import-generated`, `build-review`, and `finish` only for diagnostics or manual recovery; avoid shell loops and custom metadata scripts.

## Success Criteria

- A typical built-in Codex generation run should require fewer than 12 Goodboy/shell commands outside the actual image-generation actions.
- No command should require custom Python snippets for manifest updates.
- No row state should require a hand-written shell copy sequence.
- Idle QA should fail or warn when `cy_range > 4px`.
- The sample-kitten idle animation should have post-build idle `cy_range <= 4px` unless the user intentionally approves stronger bobbing.
