---
name: goodboy
description: Create, continue, validate, QA, branch, and package Goodboy projects that turn pet source images into Codex pets. Use when the user asks to make a Codex pet from images, regenerate pet sprite sheets, record pet-generation feedback such as happier/centered/trim green, run Goodboy CLI workflows, validate Goodboy manifests, or install/export Goodboy pet packages.
---

# Goodboy

## Overview

Use Goodboy as the manifest-first workflow for producing Codex pets from source images. Keep source images, candidate prompts, selected baselines, feedback branches, provider handoffs, QA reports, and installable packages in the project folder rather than in chat history.

Default project root is `/Users/adamallcock/Documents/Coding/goodboy` unless the user specifies another Goodboy checkout. Run commands from the Goodboy repository with:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli <command>
```

For detailed user-facing instructions, read `docs/2026-05-26-goodboy-user-guide.md` in the Goodboy repository.

## Workflow

1. Prefer `goodboy start` for new projects; it initializes, ingests sources, drafts the source card, plans candidates, renders `candidates/contact-sheet.png`, writes `workflow-state.json`, and stops at the first real gate.
2. Use `goodboy advance <project-dir> --agent-mode` as the main loop. It runs safe deterministic steps, then stops only for provider generation, baseline choice, visual approval, or QA/user override.
3. When `advance` asks for baseline selection, rerun it with `--candidate-id`, `--baseline-image`, optional `--run-id`, and `--selection-notes`.
4. When `advance` asks for row generation, generate provider outputs and rerun it with `--generated-map <generated-output-map.json>`.
5. When `advance` asks for approval, inspect contact sheet, GIF previews, edge preview, and centering overlay; then rerun it with `--approval-notes`.
6. Record every user or AI adjustment with `feedback`; branch names should reflect the reason, such as happier, center-napoleon, or trim-green.
7. Run tests and `goodboy validate` before claiming completion.

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
goodboy next <project-dir> --agent-mode
goodboy make <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>...  # legacy alias for start
goodboy init <project-dir> --pet-id <id> --display-name <name> --species dog
goodboy ingest <project-dir> <image>... --role primary_reference --notes "<notes>"
goodboy source-card <project-dir> --notes "<source notes>"
goodboy plan-candidates <project-dir> --provider codex_builtin --model-alias codex-imagegen --count 6 [--refresh] [--no-sheet]
goodboy select-candidate <project-dir> --candidate-id baseline-001 --image-path <generated.png> --notes "<why>"
goodboy feedback <project-dir> --target baseline-001 --text "make him happier"
goodboy style-default <project-dir> [--refresh]
goodboy plan-rows <project-dir> --run-id <run-id> --provider codex_builtin --model-alias codex-imagegen --character-reference character/selected-baseline.png [--refresh]
goodboy generate-handoff <project-dir> --run-id <run-id> --all
goodboy import-generated <project-dir> --run-id <run-id> --map <generated-output-map.json>
goodboy build-review <project-dir> --run-id <run-id> --row-provenance provider_generated
goodboy finish <project-dir> --run-id <run-id> --row-provenance provider_generated --approval-notes "<human approval note>"
goodboy handoff <project-dir> --run-id <run-id> --job-id row-idle
goodboy execute-openai <project-dir> --run-id <run-id> --job-id row-idle --dry-run
goodboy execute-gemini <project-dir> --run-id <run-id> --job-id row-idle --dry-run
goodboy build-from-rows <project-dir> --run-id <run-id> --rows-dir <row-strip-dir>
goodboy review-status <project-dir> --run-id <run-id> --agent-mode
goodboy approve <project-dir> --notes "<human approval note>"
goodboy approve <project-dir> --run-id <run-id> --artifact contact-sheet --decision approved --notes "<human approval note>"
goodboy install <project-dir> --run-id <run-id> --row-provenance provider_generated
goodboy validate <project-dir>
```

## Provider Guidance

- `codex_builtin` is an interactive Codex handoff adapter. Use it for built-in image generation; write a generated-output map and let `import-generated` copy files and update manifests.
- `openai_images`, `gemini_nano_banana_2`, and `gemini_nano_banana_pro` are optional accelerators. Never present missing keys as a blocker for Codex built-in handoff.
- Use `execute-openai` only with `OPENAI_API_KEY` in the environment, and `execute-gemini` only with `GEMINI_API_KEY` in the environment. Use `--dry-run` for planning and validation. Never write raw API keys into manifests, docs, logs, or memory.
- Provider model names are aliases. Preserve the exact alias and invocation metadata in manifests.

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

If QA fails, fix the source row/artifact or record an explicit user-approved override. Do not silently install a failing pet. Validation means technically packageable; final installation also requires provenance, a recorded approval, and a clean renderer-script scan.
