# Goodboy Agent Instructions

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

- Validate the Codex skill after editing `codex-skill/goodboy/SKILL.md`.
- Keep user-facing docs aligned with the current happy path: `start`, `advance`, provider generation, generated-output map import, visual approval, and install.
