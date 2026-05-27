"""Goodboy export helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from .jsonio import read_json, write_json
from .project import load_project


def export_project_bundle(project_dir: Path, *, run_id: str, output_dir: Path | None = None, zip_output: bool = False) -> dict[str, object]:
    project = load_project(project_dir)
    run_dir = project_dir / "runs" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run does not exist: {run_dir}")
    export_root = output_dir or (project_dir / "exports" / run_id / "goodboy-project")
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)
    for rel in [
        "goodboy.json",
        "sources/source-images.json",
        "sources/source-card.json",
        "candidates/baseline-candidates.json",
        "character/character-card.json",
        "style/emotion-style-sheet.json",
    ]:
        source = project_dir / rel
        if source.exists():
            target = export_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    shutil.copytree(run_dir, export_root / "runs" / run_id)
    manifest = {
        "kind": "goodboy_project_export",
        "project_id": project.id,
        "display_name": project.display_name,
        "run_id": run_id,
        "contains_source_manifests": True,
        "contains_run_artifacts": True,
    }
    write_json(export_root / "export-manifest.json", manifest)
    zip_path = make_zip(export_root) if zip_output else None
    return {"export_dir": str(export_root), "zip": str(zip_path) if zip_path else None, "manifest": manifest}


def export_petdex_package(project_dir: Path, *, run_id: str, output_dir: Path | None = None, zip_output: bool = True) -> dict[str, object]:
    project = load_project(project_dir)
    package_dir = project_dir / "runs" / run_id / "package"
    if not package_dir.is_dir():
        raise FileNotFoundError(f"run package does not exist: {package_dir}")
    export_root = output_dir or (project_dir / "exports" / run_id / "petdex" / project.id)
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)
    shutil.copy2(package_dir / "pet.json", export_root / "pet.json")
    shutil.copy2(package_dir / "spritesheet.webp", export_root / "spritesheet.webp")
    readme = (
        f"# {project.display_name}\n\n"
        "Petdex-ready Goodboy export.\n\n"
        f"- Project id: `{project.id}`\n"
        f"- Run id: `{run_id}`\n"
        "- Files: `pet.json`, `spritesheet.webp`, `goodboy-export.json`\n"
    )
    (export_root / "README.md").write_text(readme, encoding="utf-8")
    manifest = {
        "kind": "petdex_export",
        "project_id": project.id,
        "display_name": project.display_name,
        "run_id": run_id,
        "pet_json": "pet.json",
        "spritesheet": "spritesheet.webp",
        "source_run_summary": str((project_dir / "runs" / run_id / "run-summary.json").relative_to(project_dir)),
    }
    write_json(export_root / "goodboy-export.json", manifest)
    validate_petdex_export(export_root)
    zip_path = make_zip(export_root) if zip_output else None
    return {"export_dir": str(export_root), "zip": str(zip_path) if zip_path else None, "manifest": manifest}


def validate_petdex_export(export_root: Path) -> None:
    pet = read_json(export_root / "pet.json")
    if not isinstance(pet.get("id"), str) or not pet["id"]:
        raise ValueError("pet.json must include id")
    if not (export_root / "spritesheet.webp").is_file():
        raise ValueError("Petdex export requires spritesheet.webp")


def make_zip(export_root: Path) -> Path:
    archive = shutil.make_archive(str(export_root), "zip", export_root)
    return Path(archive)

