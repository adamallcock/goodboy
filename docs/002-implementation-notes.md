# Implementation Notes

## 2026-05-25: First Executable Slice

Goodboy now has an executable Python package skeleton under `src/goodboy`.

Implemented modules:

- `contracts.py` - Codex pet dimensions, state order, and frame counts.
- `schemas.py` - initial manifest dataclasses.
- `project.py` - project initialization and manifest loading.
- `ingest.py` - source-image import, hashing, dedupe, thumbnails, EXIF capture, provenance reporting, and source-card scaffolding.
- `candidates.py` - baseline candidate planning, candidate prompts, selection, selected-baseline normalization, character-card creation, and candidate contact-sheet rendering.
- `feedback.py` - feedback events and branch manifests for human or AI critique.
- `style.py` - default/custom emotion style sheets, style presets, subject-kind guidance, critique-aware row prompts, automatic chroma-key selection, layout-guide generation, and row-generation job planning.
- `critique.py` - structured human/AI critique reports and optional style override application.
- `exports.py` - Goodboy project and Petdex-ready export bundles.
- `adapters.py` - provider capability registry, provider handoff manifest preparation, dry-run-safe OpenAI text-to-image plus image-input edit execution, and dry-run-safe Gemini/Nano Banana execution.
- `validation.py` - strict manifest validation for project, source, candidate, character, style, feedback, branch, job, invocation, and run-summary manifests.
- `raster.py` - chroma-key cleanup, despill, component/slot/stable-slot extraction, state-aware centering, idle stabilization, frame generation, and frame centering reports.
- `atlas.py` - atlas composition, WebP output, validation, contact sheets, and GIF previews.
- `qa.py` - duplicate, drift, component-count, motion, edge-clearance, chroma-residue, copied-guide, white-background, centering-overlay, state-specific drift threshold, and install-policy audits.
- `pipeline.py` - high-level build from existing row strips.
- `workflow.py` - agent-safe `make`, `next`, `doctor`, batch handoff, generated-output import, review build, approval, finish, review-status, and approved-install workflow rails.
- `safety.py` - suspicious local renderer script detection before install.
- `cli.py` - project, ingest, candidate, style, adapter handoff, and build commands.

Important implementation detail:

The WebP writer must use `exact=True`; otherwise transparent pixels can acquire hidden RGB residue when decoded. This was caught by the first legacy row-strip regression and is covered by `test_webp_validation_preserves_transparent_rgb_invariant`.

Current proof:

```bash
goodboy build-from-rows /tmp/goodboy-legacy-rebuild \
  --pet-id legacy \
  --display-name legacy pet \
  --run-id legacy-v7-centered \
  --rows-dir /path/to/legacy-row-strips
```

This produces a passing Goodboy run with:

- transparent strips
- centered frames
- `spritesheet.png`
- `spritesheet.webp`
- `validation.json`
- contact sheet
- GIF previews
- white edge preview
- duplicate/drift/chroma-edge audit
- install policy
- package `pet.json`
- package `spritesheet.webp`

Current CLI coverage:

- `goodboy init`
- `goodboy inspect`
- `goodboy ingest`
- `goodboy source-card`
- `goodboy plan-candidates`
- `goodboy select-candidate`
- `goodboy candidate-sheet`
- `goodboy feedback`
- `goodboy style-default`
- `goodboy plan-rows`
- `goodboy adapters`
- `goodboy start`
- `goodboy advance`
- `goodboy doctor`
- `goodboy generate-handoff`
- `goodboy import-generated`
- `goodboy build-review`
- `goodboy finish`
- `goodboy handoff`
- `goodboy execute-openai`
- `goodboy execute-gemini`
- `goodboy build-from-rows`
- `goodboy make`
- `goodboy next`
- `goodboy approve`
- `goodboy review-status`
- `goodboy install`
- `goodboy validate`

## 2026-05-26: Validation, Feedback, Skill, And QA Hardening

Added strict project validation, explicit feedback/branch manifests, a portable synthetic row-strip fixture, component-count sanity checks, state motion checks, install-policy output, and a Goodboy Codex skill wrapper draft under `codex-skill/goodboy`.

Install policy now separates "build for review" from "install into Codex." `build-from-rows` can still create contact sheets, previews, QA reports, and packages from existing row strips, but `build-from-rows --install` requires approved row provenance plus a human visual approval note. Approved provenance values are `provider_generated`, `user_supplied`, and `test_fixture`; local renderer/mock provenance is blocked so an agent cannot quietly install programmatically drawn sprites.

Agent Rail v1 adds simpler commands and a durable workflow state. `goodboy make` creates the project, ingests source images, drafts the source card, plans baselines, writes `workflow-state.json`, and stops at the next safe action. `goodboy next --agent-mode` reports allowed commands and blocked actions as JSON. `goodboy approve`, `goodboy review-status`, and `goodboy install` split final review from installation, and `goodboy install` refuses suspicious project-local renderer scripts.

Agent Rail v2 adds the higher-level path agents should use by default: `doctor`, `generate-handoff --all`, `import-generated --map`, `build-review`, and `finish`. `next --agent-mode` now includes executable command fields such as `recommended_command`, `acceptable_commands`, `missing_inputs`, `after_provider_generation`, `already_done`, and `do_not_run`. Planning commands are idempotent unless `--refresh` is supplied, which prevents accidental candidate or row-plan churn during retries.

Agent Rail v3 collapses the normal agent loop further. `goodboy start` is the preferred new-project entrypoint and renders `candidates/contact-sheet.png` by default. `goodboy advance --agent-mode` runs safe deterministic steps until the next real gate, then reports `gate`, `actions`, `next_human_action`, `artifacts_to_show_user`, and optional API accelerators. `goodboy approve <project-dir> --notes ...` now defaults to the latest run's contact sheet approval for the common case.

State-aware centering now stabilizes idle/waiting/review/task-style rows without flattening directional or jumping motion. Builds write `frames/centering-report.json`, copy it to `qa/centering-report.json`, generate `qa/centering-overlay.png`, and apply state-specific vertical drift thresholds such as a strict idle `cy_range <= 4px` budget.

The OpenAI Images API adapter now has direct text-to-image and image-input edit execution paths with dry-run support. It reads `OPENAI_API_KEY` from the environment when actually executing and does not write raw keys to disk. OpenAI and Gemini keys are optional accelerators; missing keys are not blockers for Codex built-in handoff.

The Gemini/Nano Banana adapters now use Google AI's REST `generateContent` shape with text and optional inline base64 image inputs. They read `GEMINI_API_KEY` from the environment when actually executing and do not write raw keys to disk.

Provider failures now update the relevant generation job's retry metadata with attempt count, last error, and retry availability, so agents do not need custom bookkeeping after a failed API call.

Style sheets now support style presets, subject kinds, user overrides, and AI critique overrides. This lets Goodboy handle realistic pets, anime/sticker/pixel/storybook variants, and mascot-like inanimate objects while keeping the chosen direction in `style/emotion-style-sheet.json`.

Hatch-informed row planning now writes `runs/<run-id>/layout-guides/<state>.png`, records an automatic selected chroma key in `runs/<run-id>/run-metadata.json`, attaches input image roles to row jobs, and strengthens prompts around invisible equal-width slots, safe padding, stable baseline/scale, and not copying guide marks. New style presets include `auto`, `plush`, `clay`, `flat-vector`, `3d-toy`, `painterly`, and `brand-inspired`. The idle prompt is deliberately low-motion because it plays continuously: near-still, tiny blink or barely perceptible breathing only, and no tail wagging, bouncing, rhythmic head bobbing, or vertical bobbing.

Raster builds now read the stored chroma key when available and fall back to border-color inference for legacy rows. `build-review` and `build-from-rows` accept `--extraction-method auto|components|slots|stable-slots`; `stable-slots` is an explicit recovery mode for visually good rows that drift because frame extraction crops each pose differently.

Review builds write `qa/human-review-checklist.json`. Export commands can produce a full Goodboy project bundle or a Petdex-ready folder/zip from an approved package run.

The skill wrapper was initialized with the system skill creator. After adding a temporary Python environment with PyYAML, the official skill validator passed for both `codex-skill/goodboy` and the installed copy at `$CODEX_HOME/skills/goodboy`.

Test command:

```bash
python -m unittest discover -s tests -v
```
