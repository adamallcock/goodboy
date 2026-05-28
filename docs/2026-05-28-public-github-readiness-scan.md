---
title: Public GitHub Readiness Scan
date: 2026-05-28
type: review
status: current
---

# Public GitHub Readiness Scan

## Summary

Goodboy is ready to publish as an **alpha developer tool** once the current branch has passed the final validation gate and been committed/pushed.

This repo is not positioned as a finished hosted product. The CLI/pipeline, skill/plugin wrapper, QA policy, and Review Room demo are real; the Review Room still needs one-command launch, full live mutation wiring, and broader visual regression coverage.

## Completed Public-Readiness Work

- Added MIT `LICENSE`.
- Added `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and `CHANGELOG.md`.
- Added GitHub Actions CI for Python tests, skill validation, UI typecheck/build/e2e, and whitespace checks.
- Added GitHub issue templates for bugs, feature requests, pet-generation failures, and a PR checklist.
- Added public package metadata, project URLs, classifiers, and `dev` extras in `pyproject.toml`.
- Hardened `.gitignore` for local projects, generated artifacts, virtualenvs, logs, Playwright reports, and build metadata.
- Added `projects/.gitkeep` while keeping generated project contents ignored.
- Reworked `README.md` around public install, alpha status, Review Room usage, agent-safe workflow, and development checks.
- Updated the user guide, skill docs, plugin skill docs, tracking docs, and UI docs to remove local machine assumptions and stale inspector-first wording.
- Renamed the bundled UI demo to a generic companion fixture.
- Optimized demo assets to WebP while preserving the full-size final `spritesheet.webp` for real atlas preview behavior.
- Added asset notes under `ui/public/assets/demo/README.md` and `docs/assets/README.md`.
- Added `docs/2026-05-28-license-decision.md` with license pros/cons and the MIT decision.

## Current Asset Policy

The bundled Review Room demo assets are included as public UI fixtures. They are generic, optimized for package size, and covered by the repository license unless a future asset-specific notice says otherwise.

Tracked demo assets:

```text
ui/public/assets/demo/companion/
```

Ignored/private generated projects remain under:

```text
projects/
```

## Remaining Pre-Publish Checks

Run these from the repository root after final edits:

```bash
python -m unittest discover -s tests -v
python scripts/validate_skills.py codex-skill/goodboy plugins/goodboy/skills/goodboy
git diff --check
```

Run UI checks:

```bash
cd ui
npm ci
npm run typecheck
npm run build
npm run test:e2e
```

Check for accidental generated/private tracked files:

```bash
git ls-files | rg '(^projects/|ui/dist/|ui/node_modules/|ui/test-results/|\.DS_Store$|\.env)' | grep -v '^projects/.gitkeep$'
```

Check for obvious local home-directory paths or private pet references in public-facing docs with `rg`. The scan should return no actionable public-doc findings.

## Known Alpha Gaps

- One-command Review Room backend-plus-frontend launch is not complete.
- Live frontend wiring for every mutating backend action is not complete.
- Visual regression snapshots for every primary Review Room screen are not complete.
- Live OpenAI/Gemini provider smoke tests require intentionally supplied API keys.
- Deeper visual critique/source-analysis adapters remain future work.

## Publish Recommendation

Publish the branch only after the final validation gate passes and the work is committed in logical chunks.

Suggested GitHub positioning:

- Repository description: "Manifest-first pipeline for generating, QA'ing, and packaging Codex pets from reference images."
- Release label: `0.1.0-alpha`.
- README status: alpha developer tool.
- Avoid announcing as a fully automated pet generator until live provider execution and Review Room mutation wiring are stronger.
