"""Development launcher for the Goodboy local web UI."""

from __future__ import annotations

from pathlib import Path


def launch_dev_server(
    *,
    project_dir: Path | None,
    host: str,
    port: int,
    open_browser: bool,
) -> dict[str, str | int | bool | None]:
    """Return launch metadata for the local UI.

    The actual server runner is added after the read-only API is in place. Keeping
    this function dependency-light lets `goodboy ui --help` work even when the
    optional UI extra has not been installed yet.
    """

    return {
        "project_dir": str(project_dir.resolve()) if project_dir else None,
        "host": host,
        "port": port,
        "open_browser": open_browser,
        "status": "server_not_started_yet",
    }
