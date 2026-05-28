# Goodboy Status

Last updated: 2026-05-28

## Current Phase

Public-readiness alpha hardening on branch `review-room-ui`.

Goodboy now has the CLI/pipeline core, Hatch-informed row planning, optional provider adapters, QA/install gates, Codex skill and plugin surfaces, a generic bundled Review Room demo, CI/governance files, public package metadata, and user-facing documentation for installation, day-to-day operation, and release validation.

## Completed

- Manifest-first project model, validation, source ingest, provenance, baseline candidate planning, selected character cards, feedback branches, style sheets, critique records, and provider/job manifests.
- Agent-safe fast path: `goodboy start`, `goodboy advance --agent-mode`, `doctor`, `generate-handoff --all`, `import-generated --map`, `build-review`, `finish`, `review-status`, and `validate`.
- Generation adapters and handoffs for Codex built-in generation, OpenAI Images, Gemini Nano Banana 2, and Gemini Nano Banana Pro aliases.
- Hatch-informed row generation: layout guides, canonical baseline references, automatic chroma-key choice, stronger invisible-slot prompt language, object/inanimate subject guidance, and deliberately quiet idle prompts.
- Deterministic raster pipeline: chroma cleanup, despill, component/slot/stable-slot extraction, state-aware centering, atlas composition, WebP exact-alpha output, previews, and package generation.
- QA/install policy: clipping, drift, duplicate/static frames, component sanity checks, transparent RGB residue, chroma residue, copied guide pixels, white/nontransparent backgrounds, visual review checklist, approval records, suspicious renderer-script blocking, and explicit override recording.
- Review Room UI first slice: onboarding, Codex/create/open/demo modes, simplified decision surface, Petdex-style animated state viewer, generic companion demo assets, details drawer, preview modal, command/activity drawers, and Playwright coverage.
- Codex integration: standalone skill under `codex-skill/goodboy`, repo-scoped plugin under `plugins/goodboy`, marketplace descriptor under `.agents/plugins/marketplace.json`, and lightweight CI skill validation.
- Public repo hygiene: MIT license, contribution/security/code-of-conduct docs, changelog, GitHub Actions workflow, package metadata, dev extras, `.gitignore` hardening, generic optimized demo assets, and public install docs.

## Still Not Complete

- One-command Review Room launch that serves the backend and built frontend together.
- Full live frontend wiring for every mutating backend action.
- Visual regression screenshots for each primary Review Room screen.
- Live provider smoke tests with real `OPENAI_API_KEY` and `GEMINI_API_KEY`.
- Deeper source-analysis/visual-critic adapters.

## Current Release Posture

Recommended public label: **alpha developer tool**.

The CLI and review pipeline are usable with provider handoffs. The UI is useful for demo/review and still evolving toward full live operation.

## Verification Gate

Before publishing or tagging:

- `python -m unittest discover -s tests -v`
- `python scripts/validate_skills.py codex-skill/goodboy plugins/goodboy/skills/goodboy`
- `cd ui && npm ci && npm run typecheck && npm run build && npm run test:e2e`
- `git diff --check`
- secret/path/generated-file scan from `docs/2026-05-28-public-github-readiness-scan.md`

## Next Recommended Work

1. Run the full validation gate after final docs and commits.
2. Commit in logical chunks and push `review-room-ui`.
3. Add one-command Review Room launch and live project auto-open.
4. Run live OpenAI/Gemini smoke tests when keys are intentionally available.
