"""Loopback launcher for the packaged Goodboy Review Room."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def launch_dev_server(
    *,
    project_dir: Path | None,
    host: str,
    port: int,
    open_browser: bool,
) -> dict[str, str | int | bool | None]:
    """Run the packaged Review Room and API on a loopback-only Uvicorn server."""

    if host not in LOOPBACK_HOSTS:
        raise ValueError(
            "Review Room exposes local filesystem actions and may only bind to "
            "127.0.0.1, localhost, or ::1"
        )
    if not 1 <= port <= 65535:
        raise ValueError("UI port must be between 1 and 65535")
    resolved_project = project_dir.expanduser().resolve() if project_dir else None
    if resolved_project is not None and not (resolved_project / "goodboy.json").is_file():
        raise FileNotFoundError(f"not a Goodboy project: {resolved_project}")

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Review Room dependencies are missing; install `goodboy-codex[ui]`"
        ) from exc

    from .registry import ProjectRegistry
    from .server import create_app, packaged_ui_dir

    if not (packaged_ui_dir() / "index.html").is_file():
        raise RuntimeError(
            "packaged Review Room assets are missing; reinstall Goodboy or run "
            "`cd ui && npm run build:package` from a source checkout"
        )

    registry = ProjectRegistry()
    launch_project_id = registry.register(resolved_project) if resolved_project else None
    app = create_app(registry, launch_project_id=launch_project_id)
    display_host = "[::1]" if host == "::1" else host
    url = f"http://{display_host}:{port}/"
    print(f"Goodboy Review Room: {url}")
    if open_browser:
        timer = threading.Timer(0.6, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()
    uvicorn.run(app, host=host, port=port, log_level="info")

    return {
        "project_dir": str(resolved_project) if resolved_project else None,
        "host": host,
        "port": port,
        "open_browser": open_browser,
        "status": "stopped",
    }
