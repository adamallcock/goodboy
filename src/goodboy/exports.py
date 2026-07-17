"""Goodboy export helpers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .jsonio import read_json, write_json
from .project import load_project
from .schemas import utc_now
from .v2_backend import normalize_run_json_paths, validate_v2_package


PRIVATE_RUN_PATHS = {
    "identity/source-contact-sheet.png",
    "qa/likeness-qa-sheet.png",
}


def private_run_ignore(run_dir: Path):
    run_root = run_dir.resolve()

    def ignore(directory: str, names: list[str]) -> list[str]:
        ignored: list[str] = []
        directory_path = Path(directory).resolve()
        for name in names:
            candidate = directory_path / name
            try:
                relative = str(candidate.relative_to(run_root))
            except ValueError:
                continue
            if relative in PRIVATE_RUN_PATHS:
                ignored.append(name)
        return ignored

    return ignore


def export_project_bundle(
    project_dir: Path,
    *,
    run_id: str,
    output_dir: Path | None = None,
    zip_output: bool = False,
    include_sources: bool = False,
) -> dict[str, object]:
    project = load_project(project_dir)
    run_dir = project_dir / "runs" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run does not exist: {run_dir}")
    export_root = output_dir or (project_dir / "exports" / run_id / "goodboy-project")
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)
    project_files = [
        "goodboy.json",
        "candidates/baseline-candidates.json",
        "character/character-card.json",
        "character/identity-anchor.json",
        "character/identity-anchor.png",
        "character/styled-baseline.json",
        "character/selected-baseline.png",
        "style/emotion-style-sheet.json",
        "identity/identity-profile.json",
        "identity/reference-coverage.json",
    ]
    if include_sources:
        project_files.extend(["sources/source-images.json", "sources/source-card.json"])
    for rel in project_files:
        source = project_dir / rel
        if source.exists():
            target = export_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    shutil.copytree(
        run_dir,
        export_root / "runs" / run_id,
        ignore=None if include_sources else private_run_ignore(run_dir),
    )
    if not include_sources:
        normalize_run_json_paths(export_root / "runs" / run_id)
    if include_sources:
        for child in ("originals", "thumbnails", "provider-derivatives"):
            source_dir = project_dir / "sources" / child
            if source_dir.is_dir():
                shutil.copytree(source_dir, export_root / "sources" / child)
    manifest = {
        "kind": "goodboy_project_export",
        "project_id": project.id,
        "display_name": project.display_name,
        "run_id": run_id,
        "contains_source_manifests": include_sources,
        "contains_source_images": include_sources,
        "contains_run_artifacts": True,
        "privacy_default": "source images and source-bearing QA sheets are excluded unless explicitly requested",
        "excluded_private_run_paths": [] if include_sources else sorted(PRIVATE_RUN_PATHS),
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
    if pet.get("spriteVersionNumber") == 2:
        result = validate_v2_package(export_root)
        if not result["ok"]:
            raise ValueError(f"invalid v2 Petdex export: {'; '.join(result['errors'])}")


def export_diagnostic_bundle(
    project_dir: Path,
    *,
    run_id: str,
    output_dir: Path | None = None,
    zip_output: bool = True,
) -> dict[str, object]:
    """Export support evidence without source pixels, prompts, raw responses, or secrets."""

    project = load_project(project_dir)
    run_dir = project_dir / "runs" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run does not exist: {run_dir}")
    export_root = output_dir or (project_dir / "exports" / run_id / "diagnostic")
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)
    manifest = project.to_dict()
    manifest["display_name"] = "<redacted>"
    write_json(export_root / "goodboy.json", manifest)
    for relative in (
        "workflow-state.json",
        "migration-receipt.json",
        "validation/manifest-validation.json",
    ):
        source = project_dir / relative
        if source.is_file():
            target = export_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for relative in (
        "run.json",
        "run-summary.json",
        "backend-snapshot.json",
        "events.jsonl",
        "qa/review.json",
        "qa/install-policy.json",
        "qa/v2-backend-receipt.json",
        "qa/look-continuity.json",
        "qa/identity-drift.json",
        "final/validation.json",
        "final/validation-v2.json",
        "package/validation.json",
    ):
        source = run_dir / relative
        if source.is_file():
            target = export_root / "runs" / run_id / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    jobs_path = run_dir / "generation-jobs.json"
    if jobs_path.is_file():
        jobs = read_json(jobs_path)
        for job in jobs.get("jobs", []):
            job["input_images"] = [
                classify_input_path(str(path)) for path in job.get("input_images", [])
            ]
            job["input_image_roles"] = {
                classify_input_path(str(path)): role
                for path, role in job.get("input_image_roles", {}).items()
            }
        write_json(export_root / "runs" / run_id / "generation-jobs.json", jobs)
    invocation_dir = run_dir / "provider-invocations"
    for source in sorted(invocation_dir.glob("*.json")) if invocation_dir.is_dir() else []:
        if source.name.endswith(".response.json"):
            continue
        raw = read_json(source)
        raw["request_id"] = None
        raw["raw_response_path"] = None
        raw["input_image_hashes"] = []
        metadata = raw.get("request_metadata")
        if isinstance(metadata, dict):
            if "input_images" in metadata:
                metadata["input_images"] = [
                    classify_input_path(str(path)) for path in metadata.get("input_images", [])
                ]
            metadata.pop("input_image_roles", None)
        write_json(
            export_root / "runs" / run_id / "provider-invocations" / source.name,
            raw,
        )
    diagnostic_manifest = {
        "kind": "goodboy_diagnostic",
        "project_id": project.id,
        "run_id": run_id,
        "contains_source_images": False,
        "contains_prompts": False,
        "contains_raw_provider_responses": False,
        "contains_request_ids": False,
        "contains_api_keys": False,
        "generated_at": utc_now(),
    }
    write_json(export_root / "diagnostic-manifest.json", diagnostic_manifest)
    assert_diagnostic_bundle_safe(export_root)
    zip_path = make_zip(export_root) if zip_output else None
    return {
        "export_dir": str(export_root),
        "zip": str(zip_path) if zip_path else None,
        "manifest": diagnostic_manifest,
    }


def classify_input_path(value: str) -> str:
    path = Path(value).as_posix()
    if path.startswith("sources/"):
        return "<source-reference-redacted>"
    if "selected-baseline" in path:
        return "<canonical-baseline>"
    if "layout-guides/" in path:
        return f"<layout-guide:{Path(path).name}>"
    if "look-anchors" in path:
        return "<cardinal-anchors>"
    if "row-strips/" in path:
        return f"<generated-row:{Path(path).name}>"
    return f"<artifact:{Path(path).name}>"


def assert_diagnostic_bundle_safe(export_root: Path) -> None:
    forbidden_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}
    image_files = [path for path in export_root.rglob("*") if path.suffix.lower() in forbidden_suffixes]
    if image_files:
        raise ValueError(f"diagnostic bundle unexpectedly contains images: {image_files}")
    secret_pattern = re.compile(
        r"(sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,}|authorization\\s*[:=]\\s*bearer)",
        re.IGNORECASE,
    )
    for path in export_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if secret_pattern.search(text):
            raise ValueError(f"diagnostic bundle contains a credential-like value: {path}")


def make_zip(export_root: Path) -> Path:
    archive = shutil.make_archive(str(export_root), "zip", export_root)
    return Path(archive)
