---
name: goodboy
description: Create, continue, validate, QA, branch, and package Goodboy projects that turn pet source images into Codex pets. Use when the user asks to make a Codex pet from images, regenerate pet sprite sheets, record pet-generation feedback such as happier/centered/trim chroma edges, run Goodboy CLI workflows, validate Goodboy manifests, or install/export Goodboy pet packages.
---

# Goodboy

## Overview

Use Goodboy as the manifest-first workflow for producing Codex pets from source images. Keep source images, candidate prompts, selected baselines, feedback branches, provider handoffs, QA reports, and installable packages in the project folder rather than in chat history.

Default project root is `/path/to/goodboy` unless the user specifies another Goodboy checkout. Run commands from the Goodboy repository with:

```bash
goodboy <command>
```

For detailed user-facing instructions, read `docs/2026-05-26-goodboy-user-guide.md` in the Goodboy repository.

## Workflow

1. Prefer `goodboy start` for new projects; it initializes, ingests sources, drafts the source card, plans candidates, renders `candidates/contact-sheet.png`, writes `workflow-state.json`, and stops at the first real gate.
2. Use `goodboy advance <project-dir> --agent-mode` as the main loop. It runs safe deterministic steps, then stops only for provider generation, baseline choice, visual approval, or QA/user override.
3. When `advance` asks for baseline selection, rerun it with `--candidate-id`, `--baseline-image`, optional `--run-id`, and `--selection-notes`.
4. When `advance` asks for row generation, generate provider outputs from the planned handoffs. Row jobs include the canonical selected baseline plus run-local layout guides; attach both and treat guides as spacing references only.
5. When `advance` asks for approval, inspect the animated state preview or contact sheet, GIF previews, white edge preview, and centering overlay; then rerun it with `--approval-notes`.
6. Record every user or AI adjustment with `feedback`; branch names should reflect the reason, such as happier, center-subject, or trim-chroma.
7. Use style presets, subject kinds, and critique reports when the user asks for realistic/anime/object/inanimate customization.
8. Run tests and `goodboy validate` before claiming completion.

## Hard Guardrails

- Do not write ad hoc renderer, drawing, sprite-maker, or row-strip generator scripts inside a pet project.
- Do not synthesize row strips programmatically from observed traits unless the user explicitly asks for a placeholder/mock pet or a test fixture.
- Do not bypass provider generation by drawing mascot art with Pillow, SVG, canvas, or handwritten image code.
- Do not modify Goodboy source code during a pet run unless the user asks to improve Goodboy itself.
- If candidate images or row strips are missing, stop at the `advance` gate and tell the user what generation action is needed.
- Do not use shell loops, raw `cp` sequences, or one-off Python snippets to assemble provider outputs when `generate-handoff`, `import-generated`, `build-review`, or `finish` covers the step.
- Use `build-from-rows` only for advanced/manual recovery on row strips that came from an approved generation provider, an existing user-supplied source, or a deliberate test fixture.
- Prefer `goodboy advance` for normal installs. `finish` and `install` are lower-level recovery commands. Installation requires visual approval, approved row provenance, clean QA gates or explicit override, and no suspicious renderer scripts.
- Never install row strips marked or suspected as `mock_renderer`, `local_renderer`, `programmatic_renderer`, or `ad_hoc_renderer`.

## Core Commands

```bash
goodboy start <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>...
goodboy advance <project-dir> --agent-mode
goodboy advance <project-dir> --agent-mode --candidate-id baseline-001 --baseline-image <generated.png> --run-id <run-id> --selection-notes "<why>"
goodboy advance <project-dir> --agent-mode --run-id <run-id> --generated-map <generated-output-map.json> --row-provenance provider_generated
goodboy advance <project-dir> --agent-mode --run-id <run-id> --approval-notes "<human approval note>" --row-provenance provider_generated
goodboy doctor <project-dir> --agent-mode
goodboy ui [project-dir] --host 127.0.0.1 --port 8787 [--no-open]
goodboy next <project-dir> --agent-mode
goodboy make <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>...  # legacy alias for start
goodboy init <project-dir> --pet-id <id> --display-name <name> --species dog
goodboy ingest <project-dir> <image>... --role primary_reference --notes "<notes>"
goodboy source-card <project-dir> --notes "<source notes>"
goodboy provenance <project-dir>
goodboy plan-candidates <project-dir> --provider codex_builtin --model-alias codex-imagegen --count 6 [--refresh] [--no-sheet]
goodboy candidate-image <project-dir> --candidate-id baseline-001 --image-path <generated.png>
goodboy select-candidate <project-dir> --candidate-id baseline-001 --image-path <generated.png> --notes "<why>"
goodboy feedback <project-dir> --target baseline-001 --text "make him happier"
goodboy style-default <project-dir> [--preset anime] [--subject-kind inanimate_object] [--user-style "<style>"] [--ai-critique "<critique>"] [--refresh]
goodboy critique <project-dir> --critique-id vision-001 --target style --finding "<finding>" --recommendation "<recommendation>" [--apply-to-style]
goodboy plan-rows <project-dir> --run-id <run-id> --provider codex_builtin --model-alias codex-imagegen --character-reference character/selected-baseline.png [--refresh]
goodboy generate-handoff <project-dir> --run-id <run-id> --all
goodboy import-generated <project-dir> --run-id <run-id> --map <generated-output-map.json>
goodboy build-review <project-dir> --run-id <run-id> --row-provenance provider_generated [--extraction-method auto|components|slots|stable-slots]
goodboy finish <project-dir> --run-id <run-id> --row-provenance provider_generated --approval-notes "<human approval note>"
goodboy handoff <project-dir> --run-id <run-id> --job-id row-idle
goodboy execute-openai <project-dir> --run-id <run-id> --job-id row-idle --dry-run
goodboy execute-gemini <project-dir> --run-id <run-id> --job-id row-idle --dry-run
goodboy build-from-rows <project-dir> --run-id <run-id> --rows-dir <row-strip-dir> [--extraction-method auto|components|slots|stable-slots]
goodboy review-status <project-dir> --run-id <run-id> --agent-mode
goodboy approve <project-dir> --notes "<human approval note>"
goodboy approve <project-dir> --run-id <run-id> --artifact contact-sheet --decision approved --notes "<human approval note>"
goodboy install <project-dir> --run-id <run-id> --row-provenance provider_generated
goodboy export project <project-dir> --run-id <run-id>
goodboy export petdex <project-dir> --run-id <run-id>
goodboy validate <project-dir>
```

## Style And Critique

- Use `--preset auto`, `--preset soft-lifelike`, `--preset realistic`, `--preset anime`, `--preset storybook`, `--preset pixel`, `--preset sticker`, `--preset plush`, `--preset clay`, `--preset flat-vector`, `--preset 3d-toy`, `--preset painterly`, or `--preset brand-inspired` for durable style direction.
- Use `--subject-kind inanimate_object` or `--subject-kind object` when the user wants a pet-like mascot made from a non-animal object.
- Use `critique --apply-to-style` for AI or human recommendations that should affect later row prompts.
- Do not silently rewrite selected baselines or generated rows from critique; create critique/feedback artifacts and branch records.

## Provider Guidance

- `codex_builtin` is an interactive Codex handoff adapter. Use it for built-in image generation; write a generated-output map and let `import-generated` copy files and update manifests.
- `openai_images`, `gemini_nano_banana_2`, and `gemini_nano_banana_pro` are optional accelerators. Never present missing keys as a blocker for Codex built-in handoff.
- Use `execute-openai` only with `OPENAI_API_KEY` in the environment, and `execute-gemini` only with `GEMINI_API_KEY` in the environment. Use `--dry-run` for planning and validation. Never write raw API keys into manifests, docs, logs, or memory.
- Provider model names are aliases. Preserve the exact alias and invocation metadata in manifests.

## Row Generation Details

- `plan-rows` automatically writes `runs/<run-id>/layout-guides/<state>.png` and `runs/<run-id>/run-metadata.json`.
- Row prompts use the selected chroma key from run metadata rather than assuming green. Production sprites must not include white borders, white backgrounds, guide marks, or copied slot lines.
- Each row handoff includes `input_image_roles`. The selected baseline is the canonical identity reference. The layout guide is only for invisible equal-width slots, safe margins, center lines, and stable baseline/scale.
- Idle is the always-on animation. Keep it intentionally quiet: near-still, tiny blink or barely perceptible breathing only, no tail wagging, bouncing, rhythmic head bobbing, vertical bobbing, or attention-seeking motion.
- If a good generated row drifts because extraction cropped frames differently, rebuild with `--extraction-method stable-slots` and visually inspect the resulting centering and clipping warnings.

## QA Bar

Do not call a pet done until these artifacts exist and are current:

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

Compact visual QA prompt for agents:

```text
Inspect the contact sheet, GIF previews, white edge preview, and centering overlay. Return row-specific repair notes only: state name, issue type, visible evidence, and exact regeneration instruction. Check identity, clipping, drift, duplicated/static frames, copied guide marks, white/nontransparent backgrounds, and chroma-colored residue.
```

If QA fails, fix the source row/artifact or record an explicit user-approved override. Do not silently install a failing pet. Validation means technically packageable; final installation also requires provenance, a recorded approval, and a clean renderer-script scan.

## Review Room UI

Use the local Review Room UI when the user wants visual inspection, a hiring-manager demo, or a clearer way to review source/candidate/QA artifacts. The frontend lives under `ui/`, and the backend foundation lives under `src/goodboy/web/`.

Current UI validation commands:

```bash
cd /path/to/goodboy/ui
npm run typecheck
npm run build
npm run test:e2e
```

The current UI slice includes a demo fixture, simplified decision surface, Petdex-style animated state preview, details drawer, command palette, activity drawer, and approval demo flow. Full one-command launch and all live mutating frontend actions are still M10 follow-up work, so do not imply the UI replaces the `advance` rail yet.
