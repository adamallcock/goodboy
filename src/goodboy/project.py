"""Goodboy project workspace management."""

from __future__ import annotations

from pathlib import Path

from .contracts import DEFAULT_OUTPUT_CONTRACT
from .jsonio import read_json, write_json
from .locking import project_lock
from .migrations import migrate_project_manifest
from .schemas import PetProject, utc_now


PROJECT_MANIFEST = "goodboy.json"


def init_project(path: Path, *, pet_id: str, display_name: str, species: str = "pet") -> PetProject:
    path.mkdir(parents=True, exist_ok=True)
    for child in [
        "sources/originals",
        "sources/thumbnails",
        "sources/provider-derivatives",
        "identity",
        "candidates",
        "character",
        "style",
        "feedback",
        "branches",
        "runs",
        "decisions",
        "validation",
        "archives",
        "exports",
    ]:
        (path / child).mkdir(parents=True, exist_ok=True)
    manifest = path / PROJECT_MANIFEST
    with project_lock(path):
        if manifest.exists():
            migrated, _changes = migrate_project_manifest(read_json(manifest))
            project = PetProject.from_dict(migrated)
            project.updated_at = utc_now()
        else:
            project = PetProject(
                id=pet_id,
                display_name=display_name,
                species=species,
                contract_id=DEFAULT_OUTPUT_CONTRACT.contract_id,
                contract_version=DEFAULT_OUTPUT_CONTRACT.contract_version,
            )
        write_json(manifest, project.to_dict())
    return project


def load_project(path: Path) -> PetProject:
    manifest = path / PROJECT_MANIFEST
    if not manifest.is_file():
        raise FileNotFoundError(f"missing Goodboy project manifest: {manifest}")
    migrated, _changes = migrate_project_manifest(read_json(manifest))
    return PetProject.from_dict(migrated)


def save_project(path: Path, project: PetProject) -> None:
    with project_lock(path):
        project.updated_at = utc_now()
        write_json(path / PROJECT_MANIFEST, project.to_dict())
