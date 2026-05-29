# @adamallcock/goodboy

npm launcher for [Goodboy](https://github.com/adamallcock/goodboy), a Python-first CLI that creates Codex pet packages from reference images.

This package intentionally does not auto-install Python dependencies. Install Goodboy first:

```bash
python3 -m pip install goodboy-codex
```

Then run:

```bash
npx @adamallcock/goodboy --help
npx @adamallcock/goodboy start <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>
npx @adamallcock/goodboy advance <project-dir> --agent-mode
```

Set `GOODBOY_PYTHON=/path/to/python` if Goodboy is installed in a specific virtual environment.
