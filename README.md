# Goodboy

Goodboy is a repeatable production pipeline for turning one or more pet reference images into a polished Codex pet package.

The project grew out of the Millie and Napoleon pet runs. Those runs proved that image generation can create charming, lifelike pet sprite rows, but the durable system needs more than prompts: it needs source-image ingestion, candidate tracking, character cards, provider-agnostic generation adapters, deterministic frame extraction, centering, edge cleanup, QA gates, package installation, and clear provenance.

## Current Status

This repository can initialize a project, ingest source images, capture EXIF/provenance, draft source and character cards, plan baseline candidates, store generated candidate images, record feedback and critique branches, customize style presets for animals or inanimate/object mascots, plan row-generation jobs, prepare or execute provider jobs, import generated row outputs, build review artifacts, stabilize frame centering, render candidate/review sheets, validate manifests, export packages, finish an approved install, enforce QA install policy, and run the first Review Room local UI slice for artifact-first visual inspection.

Seeded reference material lives under:

```text
references/legacy-pipeline/
```

These are copied references, not the live source of truth for Millie or Napoleon. The original projects remain intact at:

```text
/Users/adamallcock/Documents/Coding/pet-millie
/Users/adamallcock/Documents/Coding/pet-napoleon
```

## Primary Docs

- `docs/2026-05-26-goodboy-user-guide.md` - start here for day-to-day usage, command examples, and troubleshooting.
- `docs/000-goodboy-master-plan.md` - full project charter, requirements, architecture, modules, data model, QA gates, milestones, and delivery plan.
- `docs/2026-05-27-goodboy-local-web-ui-requirements.md` - M10 local web UI functional, technical, and design requirements.
- `docs/2026-05-27-goodboy-ui-component-scan-and-design-options.md` - M10 component scan and first design direction options.
- `docs/superpowers/plans/2026-05-27-goodboy-review-room-ui-implementation-plan.md` - M10 Review Room implementation plan.
- `docs/assets/review-room-ui-smoke-2026-05-27.png` - current smoke screenshot for the Review Room visual inspector.
- `docs/2026-05-27-goodboy-codex-plugin-feasibility.md` - Codex plugin feasibility decision and first implemented plugin slice.
- `docs/2026-05-27-goodboy-milestone-completion-audit.md` - milestone-by-milestone completion decisions before M10.
- `tracking/MILESTONES.md` - implementation milestones and progress tracking.
- `tracking/DECISIONS.md` - architecture decisions and open decisions.
- `tracking/RISK_REGISTER.md` - known risks, mitigations, and owners.
- `references/legacy-pipeline/README.md` - copied scripts and why they matter.

## Quick Start

Run from this repository with `PYTHONPATH=src` before packaging/installing the project:

```bash
cd /Users/adamallcock/Documents/Coding/goodboy

PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli start /tmp/goodboy-demo \
  --pet-id demo \
  --display-name Demo \
  --species dog \
  --source /absolute/path/to/source.png

PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli advance /tmp/goodboy-demo --agent-mode
```

`goodboy start` initializes the project, ingests source images, drafts the source card, plans baseline candidates, renders `candidates/contact-sheet.png`, writes `workflow-state.json`, and stops at the first real provider/user gate. `goodboy advance --agent-mode` runs every safe deterministic step it can, then stops only for provider generation, baseline choice, visual approval, or QA/user override. Use `goodboy doctor --agent-mode` for diagnostics.

After provider-generated baselines exist, select one and let `advance` plan row jobs plus handoffs:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli advance /tmp/goodboy-demo \
  --agent-mode \
  --candidate-id baseline-001 \
  --baseline-image /absolute/path/to/generated-baseline.png \
  --run-id planned-row-generation \
  --selection-notes "selected by the user"
```

After provider-generated row strips exist, import them and build for review with one command:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli advance /tmp/goodboy-demo \
  --agent-mode \
  --run-id planned-row-generation \
  --generated-map /absolute/path/to/generated-output-map.json \
  --row-provenance provider_generated
```

After visual approval, finish:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli advance /tmp/goodboy-demo \
  --agent-mode \
  --run-id planned-row-generation \
  --row-provenance provider_generated \
  --approval-notes "User approved contact sheet and previews on 2026-05-26"
```

The review build creates transparent strips, stabilized frames, atlas PNG/WebP, contact sheet, GIF previews, white edge preview, centering overlay, validation report, duplicate/drift/green-edge audit, install policy, run summary, and package files. Lower-level `make`, `next`, `plan-rows`, `generate-handoff`, `import-generated`, `build-review`, `review-status`, `approve`, `finish`, and `install` commands remain available for advanced/manual recovery.

For direct OpenAI Images API jobs, use:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli execute-openai /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --job-id row-idle \
  --dry-run

PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli execute-gemini /tmp/goodboy-demo \
  --run-id planned-row-generation \
  --job-id row-idle \
  --dry-run
```

OpenAI and Gemini API keys are optional accelerators, not requirements. Without keys, Goodboy uses Codex built-in handoff. With `OPENAI_API_KEY` or `GEMINI_API_KEY`, direct provider execution can be faster; Goodboy never writes raw API keys to disk.

## Review Room UI

The M10 local UI now has a first implementation slice under `ui/` plus a FastAPI backend foundation under `src/goodboy/web/`. The UI opens with onboarding paths for agent-led creation, existing projects, and a safe demo walkthrough. The Review Room shell uses the top current-step header as the primary workflow navigation, with persistent Home navigation, a large artifact canvas, zoom controls, draggable compare mode, a decision panel, command palette, activity drawer, approval gate, visible demo fixture materials, and Playwright coverage.

Run the frontend demo:

```bash
cd /Users/adamallcock/Documents/Coding/goodboy/ui
npm install
npm run dev
```

Then open `http://127.0.0.1:5173/`.

Run UI checks:

```bash
cd /Users/adamallcock/Documents/Coding/goodboy/ui
npm run typecheck
npm run build
npm run test:e2e
```

Backend API checks are included in the Python suite. The `goodboy ui` command is registered and the backend routes are in place; full one-command launch and all live mutating frontend actions remain M10 follow-up work.

Useful customization commands:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli provenance /tmp/goodboy-demo

PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli style-default /tmp/goodboy-demo \
  --preset anime \
  --subject-kind inanimate_object \
  --user-style "make the object feel cozy and magical"

PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli critique /tmp/goodboy-demo \
  --critique-id vision-001 \
  --target style \
  --finding "silhouette is weak" \
  --recommendation "increase contrast around the ears or object edges" \
  --apply-to-style

PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli export petdex /tmp/goodboy-demo \
  --run-id planned-row-generation
```

Run tests:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest discover -s tests -v
```

## Target Outputs

For each pet, Goodboy should ultimately produce:

- `pet.json`
- `spritesheet.webp`
- contact sheet
- animated previews
- source rows
- transparent rows
- extracted frames
- candidate images
- character card
- style sheet
- generation manifest
- feedback events and branch manifests
- critique reports
- QA reports
- run summary
- optional Petdex-ready package

## Planned Integrations

Generation adapters:

- Codex built-in image generation
- OpenAI Images API, default alias `gpt-image-2`
- Google Gemini Nano Banana 2, default alias `gemini-3.1-flash-image-preview`
- Google Gemini Nano Banana Pro, default alias `gemini-3-pro-image-preview`

Provider aliases are intentionally configurable. Goodboy records the provider and model alias used for each job because image-generation model names and capabilities can drift.

Product surfaces:

- CLI and Python library
- Codex skill wrapper
- Codex plugin package under `plugins/goodboy`
- repo marketplace under `.agents/plugins/marketplace.json`
- local Review Room UI under `ui/` for candidate, QA, approval, and visual-inspection workflows

To add the repo marketplace from this checkout:

```bash
codex plugin marketplace add /Users/adamallcock/Documents/Coding/goodboy
```
