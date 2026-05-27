"""Project handle registry for the local Review Room web UI."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ProjectRegistry:
    """Maps opaque project ids to local project roots for one server process."""

    def __init__(self) -> None:
        self._projects: dict[str, Path] = {}
        self._recent: list[str] = []

    def register(self, project_dir: Path) -> str:
        resolved = project_dir.expanduser().resolve()
        project_id = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        self._projects[project_id] = resolved
        if project_id in self._recent:
            self._recent.remove(project_id)
        self._recent.insert(0, project_id)
        return project_id

    def resolve(self, project_id: str) -> Path:
        if project_id not in self._projects:
            raise KeyError(project_id)
        return self._projects[project_id]

    def recent(self) -> list[dict[str, str]]:
        return [
            {"project_id": project_id, "project_dir": str(self._projects[project_id])}
            for project_id in self._recent
            if project_id in self._projects
        ]
