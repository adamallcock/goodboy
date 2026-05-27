# Goodboy Status

Last updated: 2026-05-26

## Current Phase

Early implementation. Goodboy now has a Python package skeleton, CLI entrypoint, manifest dataclasses, strict manifest validation, source ingest, source-card scaffolding, baseline candidate planning and selection, candidate contact-sheet rendering, explicit feedback events and branch manifests, emotion style-sheet generation, row-job planning, provider handoff manifests, dry-run-safe OpenAI Images and Gemini/Nano Banana execution paths, deterministic raster pipeline, state-aware centering, centering reports/overlays, atlas validation, QA reports, install policy, installer/package generation, Agent Rail commands for safer Codex operation, an installed Codex skill wrapper, a portable synthetic fixture, and regression tests against existing Napoleon row strips.

## Completed This Session

- Created `/Users/adamallcock/Documents/Coding/goodboy`.
- Copied reference scripts from hatch-pet, Napoleon, and Millie.
- Added project README.
- Added master plan.
- Added module catalog.
- Added milestone tracker.
- Added decisions log.
- Added risk register.
- Added legacy reference README.
- Added `pyproject.toml`.
- Added `src/goodboy` package skeleton.
- Added project manifest creation/loading.
- Added Codex pet constants and manifest dataclasses.
- Added strict manifest validation for project, source, candidate, character, style, feedback, branch, job, invocation, and run-summary manifests.
- Added source image ingest with hash-based dedupe, thumbnails, and manual source-card scaffolding.
- Added baseline style candidate planning with preserved prompts, provider/model metadata, character deltas, selection notes, selected-baseline preservation, and character-card creation.
- Added human/AI feedback events and explicit branch manifests.
- Added candidate contact-sheet rendering for planned or generated candidates.
- Added default happy Codex emotion style sheet and row-generation job planner.
- Added generation adapter capability registry for `codex_builtin`, `openai_images`, `gemini_nano_banana_2`, and `gemini_nano_banana_pro`.
- Added provider handoff manifests for planned generation jobs.
- Added dry-run-safe OpenAI Images API execution path for text-to-image and image-input edit jobs.
- Added dry-run-safe Gemini/Nano Banana execution path for text and image-input jobs.
- Added generalized chroma-key cleanup, despill, component extraction, state-aware centering, atlas composition, validation, contact sheet, GIF preview, white edge preview, centering overlay/report, QA audit, package generation, and optional install.
- Added install-blocking QA policy with explicit override reason support.
- Added Agent Rail v1: `goodboy make`, `goodboy next`, `goodboy approve`, `goodboy review-status`, `goodboy install`, `workflow-state.json`, approval records, and suspicious renderer-script install blocking.
- Added Agent Rail v2: `goodboy doctor`, batch `goodboy generate-handoff --all`, `goodboy import-generated --map`, `goodboy build-review`, `goodboy finish`, executable `next --agent-mode` fields, and idempotent `plan-candidates`/`style-default`/`plan-rows` behavior with `--refresh`.
- Added Agent Rail v3: `goodboy start`, `goodboy advance --agent-mode`, default baseline candidate-sheet rendering, short-form `goodboy approve --notes`, and optional API accelerator reporting for OpenAI/Gemini keys.
- Added portable synthetic row-strip fixture.
- Added Codex skill wrapper under `codex-skill/goodboy`, installed it to `/Users/adamallcock/.codex/skills/goodboy`, and validated both copies with the official skill validator using a temporary Python environment with PyYAML.
- Added `goodboy init`, `goodboy inspect`, `goodboy start`, `goodboy advance`, `goodboy make`, `goodboy doctor`, `goodboy next`, `goodboy ingest`, `goodboy source-card`, `goodboy plan-candidates`, `goodboy select-candidate`, `goodboy candidate-sheet`, `goodboy feedback`, `goodboy style-default`, `goodboy plan-rows`, `goodboy adapters`, `goodboy generate-handoff`, `goodboy import-generated`, `goodboy build-review`, `goodboy finish`, `goodboy handoff`, `goodboy execute-openai`, `goodboy execute-gemini`, `goodboy build-from-rows`, `goodboy approve`, `goodboy review-status`, `goodboy install`, and `goodboy validate`.
- Added tests for project init, ingest/source-card/candidate/feedback/style/handoff/validation flow, Agent Rail command flow, simplified handoff/import/build/finish flow, planning idempotence, approval/install command flow, suspicious renderer blocking, negative manifest validation across named manifest types, OpenAI and Gemini dry-run execution, QA policy, centering stabilization, portable synthetic fixture build, WebP transparency invariants, and existing Napoleon row-strip regression.

## Not Yet Started

- Codex plugin feasibility spike.
- Local web UI.

## In Progress

- Live OpenAI/Gemini execution smoke testing with real API keys.
- EXIF/provenance reporting for source ingest.
- Petdex-ready export.

## Next Recommended Work

1. Run live OpenAI and Gemini image execution smoke testing when keys are available.
2. Harden provider execution error parsing and retry policy.
3. Add source-analysis and visual-critic adapters.
4. Add EXIF/provenance reporting for source ingest.
5. Run a Codex plugin feasibility spike.
6. Add Petdex-ready export.
7. Review whether the installed Goodboy skill should be expanded with helper scripts or kept CLI-only.

## Reference Projects

- Napoleon current final: `v7-happier-green-trim-centered`
- Millie current final: `v5-green-trim`
