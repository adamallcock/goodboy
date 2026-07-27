# Goodboy Agent Instructions

## Public Repo Boundary

- This is a public project. Keep this file contributor-safe: no private pet photos, generated private identities, provider credentials, local package paths, or unpublished customer/user details.

## Default Workflow

- Treat Goodboy as a pipeline product, not as a one-off pet build.
- Prefer `goodboy start` for new projects and `goodboy advance --agent-mode` for normal continuation.
- Stop at real gates: provider image generation, baseline selection, visual approval, or QA/user override.
- Do not create local renderer scripts, Pillow drawing scripts, SVG/canvas generators, or one-off metadata patchers during a pet run.
- Use `doctor`, `next`, `generate-handoff`, `import-generated`, `build-review`, `finish`, and lower-level commands only for diagnostics, compatibility, or manual recovery.

## Privacy And Artifacts

- Do not commit local pet project folders under `projects/`; they can contain private source photos, generated pet identity art, approvals, and install packages.
- Do not commit raw API keys, provider responses containing secrets, local `.env` files, or installed Codex pet packages.
- Commit synthetic fixtures and reusable legacy reference scripts only when they are intentionally part of the public project surface.

## Validation

- Run focused tests after code changes and the full suite before publishing:

```bash
python -m unittest discover -s tests -v
```

- `codex-skill/goodboy/SKILL.md` and `plugins/goodboy/skills/goodboy/SKILL.md` must stay byte-identical. Edit both together, then validate:

```bash
python scripts/validate_skills.py codex-skill/goodboy plugins/goodboy/skills/goodboy
```

- CI and `tests/test_distribution_contract.py` enforce that parity, so a one-sided edit fails the build.
- For UI release changes, run `cd ui && npm run build:package`,
  `npm run check:package`, `npm run typecheck`, and `npm run test:e2e` so the
  compiled loopback Review Room under `src/goodboy/web/static/` stays current.
- Keep user-facing docs aligned with the current happy path: `start`, `advance`, provider generation, generated-output map import, visual approval, and install.

## Definition Of Done

- Pipeline changes are covered by tests or a reproducible local smoke.
- Public docs match the actual CLI and skill behavior.
- Private artifacts remain ignored and uncommitted.
- Any provider/image-generation blocker is reported as a real gate, not worked around with hand-made output.
