# @adamallcock/goodboy

npm launcher for [Goodboy](https://github.com/adamallcock/goodboy), a Python-first studio that creates source-faithful Codex pet v2 projects with identity, privacy, direction, likeness, repair, and package gates.

For Codex, prefer the Goodboy plugin. Users add the Git marketplace and plugin;
the plugin performs a read-only version check on first use and asks before it
bootstraps the matching runtime. No manual Python or uv tool command comes
before the plugin install.

This npm package is the standalone Node launcher. It intentionally does not
auto-install Python dependencies. Install its exact runtime first:

```bash
uv tool install "goodboy-codex[ui]==0.2.0"
```

Then run:

```bash
npx @adamallcock/goodboy --help
npx @adamallcock/goodboy start <project-dir> --pet-id <id> --display-name <name> --species dog --source <image>
npx @adamallcock/goodboy advance <project-dir> --agent-mode
```

The launcher discovers the executable in uv's tool bin even when that directory
has not yet been added to `PATH`, and refuses a runtime whose version differs
from the launcher. Set `GOODBOY_COMMAND=/path/to/goodboy` for an explicit
executable, `GOODBOY_PYTHON=/path/to/python` for a specific virtual environment,
or `GOODBOY_UV_COMMAND=/path/to/uv` for a nonstandard uv install.
