"""Goodboy project workspace management."""

from __future__ import annotations

from pathlib import Path

from .jsonio import read_json, write_json
from .schemas import PetProject, utc_now


PROJECT_MANIFEST = "goodboy.json"


def init_project(path: Path, *, pet_id: str, display_name: str, species: str = "pet") -> PetProject:
    path.mkdir(parents=True, exist_ok=True)
    for child in [
        "sources/originals",
        "sources/thumbnails",
        "candidates",
        "character",
        "style",
        "feedback",
        "branches",
        "runs",
        "archives",
        "exports",
    ]:
        (path / child).mkdir(parents=True, exist_ok=True)
    manifest = path / PROJECT_MANIFEST
    if manifest.exists():
        project = PetProject.from_dict(read_json(manifest))
        project.updated_at = utc_now()
    else:
        project = PetProject(id=pet_id, display_name=display_name, species=species)
    write_json(manifest, project.to_dict())
    return project


def load_project(path: Path) -> PetProject:
    manifest = path / PROJECT_MANIFEST
    if not manifest.is_file():
        raise FileNotFoundError(f"missing Goodboy project manifest: {manifest}")
    return PetProject.from_dict(read_json(manifest))


def save_project(path: Path, project: PetProject) -> None:
    project.updated_at = utc_now()
    write_json(path / PROJECT_MANIFEST, project.to_dict())
