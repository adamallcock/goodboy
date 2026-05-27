"""Source image ingest and source-card scaffolding."""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
from pathlib import Path

from PIL import ExifTags, Image

from .jsonio import read_json, write_json
from .project import load_project
from .schemas import SourceCard, SourceImage, utc_now


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}
SOURCE_MANIFEST = "sources/source-images.json"
SOURCE_CARD = "sources/source-card.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source_images(project_dir: Path) -> list[SourceImage]:
    path = project_dir / SOURCE_MANIFEST
    if not path.is_file():
        return []
    raw = read_json(path)
    return [SourceImage.from_dict(item) for item in raw.get("images", [])]


def save_source_images(project_dir: Path, images: list[SourceImage]) -> None:
    write_json(project_dir / SOURCE_MANIFEST, {"images": [image.to_dict() for image in images]})


def next_source_id(images: list[SourceImage]) -> str:
    seen = []
    for image in images:
        if image.id.startswith("source-"):
            try:
                seen.append(int(image.id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"source-{max(seen, default=0) + 1:03d}"


def ingest_images(
    project_dir: Path,
    image_paths: list[Path],
    *,
    role: str = "primary_reference",
    notes: str = "",
) -> list[SourceImage]:
    load_project(project_dir)
    existing = load_source_images(project_dir)
    by_hash = {image.sha256: image for image in existing}
    originals_dir = project_dir / "sources" / "originals"
    thumbs_dir = project_dir / "sources" / "thumbnails"
    originals_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    added: list[SourceImage] = []

    for raw_path in image_paths:
        source_path = raw_path.expanduser().resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"source image does not exist: {source_path}")
        if source_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(f"unsupported source image type: {source_path}")
        digest = sha256_file(source_path)
        if digest in by_hash:
            added.append(by_hash[digest])
            continue
        source_id = next_source_id(existing)
        dest = originals_dir / f"{source_id}{source_path.suffix.lower()}"
        shutil.copy2(source_path, dest)
        width, height = image_dimensions(dest)
        thumbnail_path = create_thumbnail(dest, thumbs_dir / f"{source_id}.png")
        source_image = SourceImage(
            id=source_id,
            path=str(dest.relative_to(project_dir)),
            sha256=digest,
            original_filename=source_path.name,
            mime_type=mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
            width=width,
            height=height,
            role=role,
            notes=notes,
            thumbnail_path=str(thumbnail_path.relative_to(project_dir)) if thumbnail_path else None,
            exif=extract_exif_summary(dest),
        )
        existing.append(source_image)
        by_hash[digest] = source_image
        added.append(source_image)
    save_source_images(project_dir, existing)
    return added


def extract_exif_summary(path: Path) -> dict[str, object]:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif:
                return {}
            summary: dict[str, object] = {}
            for key, value in exif.items():
                name = ExifTags.TAGS.get(key, str(key))
                if name in {"MakerNote", "UserComment"}:
                    continue
                if isinstance(value, bytes):
                    value = f"<{len(value)} bytes>"
                elif isinstance(value, tuple):
                    value = [str(item) for item in value]
                elif not isinstance(value, (str, int, float, bool)):
                    value = str(value)
                summary[str(name)] = value
            return summary
    except Exception:
        return {}


def write_provenance_report(project_dir: Path) -> dict[str, object]:
    project = load_project(project_dir)
    images = load_source_images(project_dir)
    report: dict[str, object] = {
        "project_id": project.id,
        "display_name": project.display_name,
        "generated_at": utc_now(),
        "source_count": len(images),
        "images": [
            {
                "id": image.id,
                "path": image.path,
                "sha256": image.sha256,
                "original_filename": image.original_filename,
                "mime_type": image.mime_type,
                "width": image.width,
                "height": image.height,
                "role": image.role,
                "notes": image.notes,
                "thumbnail_path": image.thumbnail_path,
                "exif_present": bool(image.exif),
                "exif": image.exif,
            }
            for image in images
        ],
    }
    write_json(project_dir / "sources" / "provenance-report.json", report)
    return report


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.width, image.height


def create_thumbnail(source: Path, output: Path, size: int = 512) -> Path | None:
    try:
        with Image.open(source) as image:
            thumb = image.convert("RGBA")
            thumb.thumbnail((size, size), Image.Resampling.LANCZOS)
            output.parent.mkdir(parents=True, exist_ok=True)
            thumb.save(output)
            return output
    except Exception:
        return None


def draft_source_card(project_dir: Path, *, user_notes: str = "") -> SourceCard:
    project = load_project(project_dir)
    images = load_source_images(project_dir)
    card = SourceCard(
        species=project.species,
        user_notes=user_notes,
        source_image_ids=[image.id for image in images],
        source_image_paths=[image.path for image in images],
        must_keep=[
            "preserve identity traits from source images",
            "preserve approved collar, bandana, tag, or charm if present",
        ],
        avoid=[
            "text",
            "logos",
            "background scenery",
            "detached effects",
            "floor shadows",
            "green or chroma-key colors in the pet",
        ],
        uncertainties=[
            "manual or vision-model source analysis has not yet filled detailed trait fields"
        ],
    )
    write_json(project_dir / SOURCE_CARD, card.to_dict())
    return card


def update_source_card_notes(project_dir: Path, user_notes: str) -> SourceCard:
    path = project_dir / SOURCE_CARD
    if path.is_file():
        card = SourceCard.from_dict(read_json(path))
    else:
        card = draft_source_card(project_dir)
    card.user_notes = user_notes
    card.updated_at = utc_now()
    write_json(path, card.to_dict())
    return card
