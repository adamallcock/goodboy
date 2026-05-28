# Contributing

Thanks for helping improve Goodboy.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[ui,dev]"
cd ui
npm ci
```

## Validation

Run the Python suite:

```bash
python -m unittest discover -s tests -v
```

Run the Review Room UI checks:

```bash
cd ui
npm run typecheck
npm run build
npm run test:e2e
```

Validate Codex skills after editing skill files:

```bash
python scripts/validate_skills.py codex-skill/goodboy plugins/goodboy/skills/goodboy
```

## Pull Request Checklist

- Keep generated/private pet projects out of the commit.
- Do not commit API keys, `.env` files, local provider logs, or installed pet packages.
- Update user-facing docs when changing commands, workflow gates, manifests, or UI behavior.
- Add or update focused tests for behavior changes.
- Run the relevant validation commands before opening a PR.
