"""Artifact indexing and safe artifact lookup for the Goodboy Review Room UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .models import ArtifactRef, artifact_id_for, artifact_url_for, severity_for_stage


KNOWN_ARTIFACT_PATTERNS = [
    "sources/originals/*",
    "sources/thumbnails/*",
    "candidates/contact-sheet.png",
    "candidates/baseline-*/generated/*",
    "character/selected-baseline.png",
    "runs/*/row-strips/*",
    "runs/*/qa/contact-sheet.png",
    "runs/*/qa/edge-preview-white.png",
    "runs/*/qa/centering-overlay.png",
    "runs/*/qa/previews/*",
    "runs/*/final/spritesheet.webp",
    "runs/*/package/pet.json",
    "runs/*/package/spritesheet.webp",
    "exports/**/*",
]


@dataclass(frozen=True)
class ArtifactIndex:
    artifacts: list[ArtifactRef]
    by_id: dict[str, ArtifactRef]


def safe_artifact_path(project_dir: Path, relative_path: str) -> Path:
    root = project_dir.expanduser().resolve()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError(f"artifact path escapes project: {relative_path}")
    return candidate


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None, None


def kind_for(relative_path: str) -> str:
    if relative_path.startswith("sources/"):
        return "source"
    if relative_path.startswith("candidates/"):
        return "candidate"
    if relative_path.startswith("character/"):
        return "character"
    if "/qa/" in relative_path:
        return "qa"
    if "/row-strips/" in relative_path:
        return "row-strip"
    if "/final/" in relative_path:
        return "final"
    if "/package/" in relative_path:
        return "package"
    if relative_path.startswith("exports/"):
        return "export"
    return "artifact"


def stage_for(relative_path: str) -> str:
    if relative_path.startswith("sources/"):
        return "sources"
    if relative_path.startswith("candidates/"):
        return "baselines"
    if relative_path.startswith("character/"):
        return "baselines"
    if "/row-strips/" in relative_path:
        return "generation"
    if "/qa/" in relative_path:
        return "qa"
    if "/package/" in relative_path or "/final/" in relative_path or relative_path.startswith("exports/"):
        return "approval"
    return "project"


def state_for(relative_path: str, path: Path) -> str | None:
    if "/previews/" in relative_path or "/row-strips/" in relative_path:
        return path.stem
    return None


def build_artifact_index(project_dir: Path, project_id: str) -> ArtifactIndex:
    root = project_dir.expanduser().resolve()
    artifacts: list[ArtifactRef] = []
    seen: set[str] = set()
    for pattern in KNOWN_ARTIFACT_PATTERNS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root).as_posix()
            if relative_path in seen:
                continue
            seen.add(relative_path)
            artifact_id = artifact_id_for(relative_path)
            width, height = image_dimensions(path)
            stat = path.stat()
            stage = stage_for(relative_path)
            artifacts.append(
                {
                    "id": artifact_id,
                    "kind": kind_for(relative_path),
                    "label": path.name,
                    "relative_path": relative_path,
                    "url": artifact_url_for(project_id, artifact_id),
                    "exists": True,
                    "width": width,
                    "height": height,
                    "bytes": stat.st_size,
                    "modified_at": str(int(stat.st_mtime)),
                    "stage": stage,
                    "state": state_for(relative_path, path),
                    "severity": severity_for_stage(stage),
                }
            )
    return ArtifactIndex(artifacts=artifacts, by_id={item["id"]: item for item in artifacts})
