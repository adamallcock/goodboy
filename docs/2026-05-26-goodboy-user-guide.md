---
title: Goodboy User Guide
date: 2026-05-26
type: guide
status: current
---

# Goodboy User Guide

Goodboy turns pet reference images into Codex pet projects with durable manifests, feedback branches, provider generation handoffs, deterministic sprite processing, QA reports, and installable pet packages.

Use this guide for day-to-day operation. Use `docs/000-goodboy-master-plan.md` for the broader architecture.

## Where Things Live

- Goodboy repository: `/Users/adamallcock/Documents/Coding/goodboy`
- Installed Goodboy Codex skill: `/Users/adamallcock/.codex/skills/goodboy`
- Goodboy Codex plugin package: `/Users/adamallcock/Documents/Coding/goodboy/plugins/goodboy`
- Goodboy repo marketplace: `/Users/adamallcock/Documents/Coding/goodboy/.agents/plugins/marketplace.json`
- Legacy reference scripts: `references/legacy-pipeline/`
- Portable test fixture: `tests/fixtures/synthetic-row-strips/`

Run CLI commands from the repository:

```bash
cd /Users/adamallcock/Documents/Coding/goodboy
export GOODBOY_PY=/Applications/Xcode.app/Contents/Developer/usr/bin/python3
```

Then use:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli <command>
```

## Use From Codex

The Goodboy skill is installed. In Codex, ask for Goodboy explicitly when you want the guided workflow, for example:

```text
Use the Goodboy skill to create a Codex pet from these source images.
```

The skill is designed to keep decisions in project artifacts rather than chat-only state. It should record generated candidates, selected baselines, feedback branches, provider metadata, QA reports, and package outputs.

Important guardrail: Goodboy agents should not write one-off renderer scripts or draw row strips programmatically as a substitute for image generation. If generated candidate images or row strips are missing, the correct behavior is to stop at the handoff/provider-execution step and ask for generation, not to create a handcrafted placeholder pet. Programmatic row strips are only appropriate for deliberate test fixtures or explicit mock/demo requests.

## Happy Path

### Agent-Safe Shortcut

Prefer this when asking Codex agents to start a new pet project:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli start /tmp/goodboy-demo \
  --pet-id demo \
  --display-name Demo \
  --species dog \
  --source /absolute/path/to/source.png
```

This creates the project, ingests sources, drafts `sources/source-card.json`, plans baseline candidates, renders `candidates/contact-sheet.png`, writes `workflow-state.json`, and stops at the first provider/user gate.

Then use `advance` as the fast pass:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo --agent-mode
```

`advance` runs every safe deterministic step it can, then stops only at a real gate: provider generation, baseline choice, visual approval, or QA/user override. It reports `gate`, `actions`, `next_human_action`, `artifacts_to_show_user`, and optional API accelerators. Use `doctor --agent-mode` for diagnostics when the state looks surprising.

OpenAI and Gemini API keys are optional accelerators. Without keys, Goodboy uses Codex built-in handoff. With `OPENAI_API_KEY` or `GEMINI_API_KEY`, direct provider execution can be faster.

## Style And Subject Customization

Goodboy style sheets preserve style as a durable artifact rather than only a prompt phrase. Use `style-default` with options to create realistic, anime, storybook, pixel, sticker, or soft-lifelike directions, including mascot-style inanimate objects.

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli style-default /tmp/goodboy-demo \
  --preset anime \
  --subject-kind inanimate_object \
  --user-style "make the lamp look cozy and magical"
```

Supported preset IDs include `soft-lifelike`, `realistic`, `anime`, `storybook`, `pixel`, and `sticker`.

Useful subject kinds include `pet`, `animal`, `person`, `object`, `inanimate_object`, and `fantasy_creature`.

For AI or human critique, write a structured critique report. If the recommendation should affect later row prompts, pass `--apply-to-style`.

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli critique /tmp/goodboy-demo \
  --critique-id vision-001 \
  --target style \
  --finding "object reads too flat" \
  --recommendation "add subtle bounce and tilt while preserving object identity" \
  --apply-to-style
```

For source provenance and EXIF:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli provenance /tmp/goodboy-demo
```

## Codex Plugin

Goodboy includes a repo-scoped Codex plugin package. The plugin bundles the Goodboy skill and exposes it through the repo marketplace, so Codex can install the workflow as a plugin rather than only as a loose local skill.

Plugin files:

```text
plugins/goodboy/.codex-plugin/plugin.json
plugins/goodboy/skills/goodboy/SKILL.md
.agents/plugins/marketplace.json
```

To add this marketplace from the local checkout:

```bash
codex plugin marketplace add /Users/adamallcock/Documents/Coding/goodboy
```

The current plugin does not replace visual QA artifacts. Continue reviewing `qa/contact-sheet.png`, `qa/previews/*.gif`, `qa/edge-preview-white.png`, and `qa/centering-overlay.png` before approval.

Typical loop:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli start /tmp/goodboy-demo --pet-id demo --display-name Demo --species dog --source /absolute/path/to/source.png
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo --agent-mode
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo --agent-mode --candidate-id baseline-001 --baseline-image /absolute/path/to/generated-baseline.png --run-id planned-row-generation --selection-notes "selected by the user"
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo --agent-mode --run-id planned-row-generation --generated-map /absolute/path/to/generated-output-map.json --row-provenance provider_generated
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo --agent-mode --run-id planned-row-generation --row-provenance provider_generated --approval-notes "User approved contact sheet and previews"
```

### 1. Create A Project

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli init /tmp/goodboy-demo \
  --pet-id demo \
  --display-name Demo \
  --species dog
```

This creates `goodboy.json` and the standard folders.

### 2. Ingest Source Images

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli ingest /tmp/goodboy-demo \
  /absolute/path/to/source.png \
  --role primary_reference \
  --notes "clear front-facing reference"
```

Goodboy copies the image into `sources/originals/`, hashes it, deduplicates by hash, and creates a thumbnail.

### 3. Create The Source Card

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli source-card /tmp/goodboy-demo \
  --notes "friendly, fluffy, keep the red bandana"
```

Edit `sources/source-card.json` manually if needed before planning candidates.

### 4. Plan Baseline Candidates

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli plan-candidates /tmp/goodboy-demo \
  --provider codex_builtin \
  --model-alias codex-imagegen \
  --count 6
```

This writes candidate prompts and metadata under `candidates/` and renders `candidates/contact-sheet.png` by default. Generate those candidate images through the chosen provider, then save the chosen generated image path for selection. Use `--no-sheet` only for tests or headless scripting.

### 5. Select The Canonical Baseline

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli select-candidate /tmp/goodboy-demo \
  --candidate-id baseline-001 \
  --image-path /absolute/path/to/generated-baseline.png \
  --notes "best likeness and warmest expression"
```

This writes:

- `character/selected-baseline.png`
- `character/selected-candidate.json`
- `character/character-card.json`

### 6. Record Feedback As Branches

Do this whenever a user or vision critic asks for a change:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli feedback /tmp/goodboy-demo \
  --target baseline-001 \
  --text "make him happier and trim green closer"
```

This writes:

- `feedback/events.json`
- `branches/<branch-id>/branch.json`

Examples of good feedback targets:

- `baseline-001`
- `row:running-left`
- `qa:green-edge`
- `qa:centering`

### 7. Plan Rows

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli style-default /tmp/goodboy-demo

PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli plan-rows /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --provider codex_builtin \
  --model-alias codex-imagegen \
  --character-reference character/selected-baseline.png
```

This writes one generation job per Codex state. `style-default` and `plan-rows` are idempotent by default; pass `--refresh` only when you intentionally want to rewrite existing plans.

### 8. Generate Or Handoff Provider Jobs

For Codex built-in generation:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli generate-handoff /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --all
```

This writes all row handoff manifests under `runs/<run-id>/provider-invocations/`. Use the handoff manifests to generate the row strips in Codex, then create a generated-output map rather than copying files by hand:

```json
{
  "idle": "/absolute/path/to/generated-idle.png",
  "running-right": "/absolute/path/to/generated-running-right.png",
  "running-left": "/absolute/path/to/generated-running-left.png",
  "waving": "/absolute/path/to/generated-waving.png",
  "jumping": "/absolute/path/to/generated-jumping.png",
  "failed": "/absolute/path/to/generated-failed.png",
  "waiting": "/absolute/path/to/generated-waiting.png",
  "running": "/absolute/path/to/generated-running.png",
  "review": "/absolute/path/to/generated-review.png"
}
```

Import those generated outputs:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli import-generated /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --map /absolute/path/to/generated-output-map.json
```

`import-generated` verifies each image, copies it into `runs/<run-id>/row-strips/`, and updates the job/provider manifests. This replaces shell loops, raw `cp` commands, and one-off metadata scripts in normal agent runs.

For OpenAI Images API:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli execute-openai /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --job-id row-idle \
  --dry-run
```

Remove `--dry-run` only when `OPENAI_API_KEY` is set in the environment.

For Gemini/Nano Banana:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli execute-gemini /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --job-id row-idle \
  --dry-run
```

Remove `--dry-run` only when `GEMINI_API_KEY` is set in the environment.

Goodboy records provider invocations under `runs/<run-id>/provider-invocations/`. It does not write raw API keys to disk.

### 9. Build Review Artifacts

When all generated rows are imported, build the pet for review:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli build-review /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --row-provenance provider_generated
```

The build writes:

- `runs/<run-id>/transparent-strips/`
- `runs/<run-id>/frames/`
- `runs/<run-id>/frames/centering-report.json`
- `runs/<run-id>/final/spritesheet.png`
- `runs/<run-id>/final/spritesheet.webp`
- `runs/<run-id>/final/validation.json`
- `runs/<run-id>/qa/contact-sheet.png`
- `runs/<run-id>/qa/previews/*.gif`
- `runs/<run-id>/qa/edge-preview-white.png`
- `runs/<run-id>/qa/centering-overlay.png`
- `runs/<run-id>/qa/centering-report.json`
- `runs/<run-id>/qa/duplicate-audit.json`
- `runs/<run-id>/qa/install-policy.json`
- `runs/<run-id>/run-summary.json`
- `runs/<run-id>/package/pet.json`
- `runs/<run-id>/package/spritesheet.webp`

This build step is intentionally allowed before final approval so you can inspect the contact sheet, GIF previews, edge preview, centering overlay, and QA reports. Installing is stricter. If you want a read-only review summary after building, run:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli review-status /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --agent-mode
```

### 10. Finish After Visual Approval

After the user approves the contact sheet and previews:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli finish /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --row-provenance provider_generated \
  --approval-notes "User approved contact sheet and previews on 2026-05-26"
```

`advance --approval-notes ...` records approval, runs install policy gates, installs to `~/.codex/pets/<pet-id>`, and validates the project. `finish` remains available as the lower-level command behind that step.

### 11. Validate The Project

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli validate /tmp/goodboy-demo
```

This validates manifests and referenced artifact paths. It writes:

```text
validation/manifest-validation.json
```

Use `--no-write` for a read-only check.

## Install Policy

`finish` installs to `~/.codex/pets/<pet-id>`, but Goodboy blocks installation unless all of these are true:

- the rows have approved provenance
- a human visual approval note is recorded
- hard QA failures are absent, or the user has explicitly accepted them with an override reason

Approved row provenance values are:

- `provider_generated` for rows from Codex built-in image generation, OpenAI Images, or Gemini/Nano Banana
- `user_supplied` for rows supplied directly by the user
- `test_fixture` for deliberate fixtures used in tests or demos

Renderer/mock provenance values such as `mock_renderer`, `local_renderer`, `programmatic_renderer`, and `ad_hoc_renderer` are not installable.

## Exports

Export a full Goodboy project bundle:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli export project /tmp/goodboy-demo \
  --run-id planned-row-generation
```

Export a Petdex-ready folder and zip:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli export petdex /tmp/goodboy-demo \
  --run-id planned-row-generation
```

Goodboy writes exports under `exports/<run-id>/` by default.

Normal command after visual review:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo \
  --agent-mode \
  --run-id planned-row-generation \
  --row-provenance provider_generated \
  --approval-notes "User approved contact sheet and previews on 2026-05-26"
```

Use a QA override only when the user has explicitly accepted a remaining technical issue:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli advance /tmp/goodboy-demo \
  --agent-mode \
  --run-id planned-row-generation \
  --row-provenance provider_generated \
  --approval-notes "User approved contact sheet and previews on 2026-05-26" \
  --install-override-reason "User approved minor remaining edge artifact after visual review"
```

Lower-level `build-from-rows`, `approve`, `review-status`, `build-review`, `finish`, and `install` remain available for compatibility and manual recovery, but agent workflows should prefer `advance`.

Previous installed packages are archived before overwrite.

## Testing

Run the full suite:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m unittest discover -s tests -v
```

Run a portable fixture smoke:

```bash
rm -rf /tmp/goodboy-smoke

PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli build-from-rows /tmp/goodboy-smoke \
  --run-id smoke \
  --rows-dir tests/fixtures/synthetic-row-strips \
  --pet-id smoke \
  --display-name Smoke

PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli validate /tmp/goodboy-smoke
```

The fixture smoke intentionally uses the lower-level `build-from-rows` command because it starts from preexisting row strips. Normal generated projects should use `advance`.

## Common Troubleshooting

### `validate` Fails On Missing Paths

Open `validation/manifest-validation.json`, find the first error path, and either restore the missing artifact or update the manifest to the correct project-relative path.

### Candidate Selection Feels Wrong

Record feedback rather than overwriting:

```bash
PYTHONPATH=src "$GOODBOY_PY" -m goodboy.cli feedback /tmp/goodboy-demo \
  --target baseline-001 \
  --text "make the expression happier but keep the face shape"
```

Then generate a new branch/candidate from that recorded intent.

### Green Halo Or Edge Clipping

Inspect:

- `runs/<run-id>/qa/edge-preview-white.png`
- `runs/<run-id>/qa/duplicate-audit.json`
- `runs/<run-id>/qa/install-policy.json`

Then regenerate or repair the affected row strip before rebuilding.

### Pet Drifts During Animation

Inspect:

- `runs/<run-id>/qa/centering-overlay.png`
- `runs/<run-id>/qa/centering-report.json`
- `runs/<run-id>/qa/duplicate-audit.json`

Idle uses the strictest center stabilization and should stay within a small vertical drift budget. Regenerate the affected row if the subject changes size or pose too dramatically; adjust deterministic centering only when the row is visually good but the anchor policy is wrong.

### Provider Keys

Use environment variables only:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Do not put raw keys in docs, manifests, command history snippets, or feedback text.
