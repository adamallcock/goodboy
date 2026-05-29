#!/usr/bin/env python3
"""Sync public README examples from completed Goodboy QA output folders."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageSequence


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from goodboy.contracts import ROW_FRAME_DURATIONS_MS, STATE_ORDER  # noqa: E402


@dataclass(frozen=True)
class ExampleSource:
    slug: str
    root: Path

    @property
    def previews_dir(self) -> Path:
        return self.root / "qa" / "previews"

    @property
    def contact_sheet(self) -> Path:
        return self.root / "qa" / "contact-sheet.png"


def parse_example(value: str) -> ExampleSource:
    try:
        slug, root = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("examples must be formatted as slug=/path/to/goodboy-output-root") from exc
    slug = slug.strip()
    if not slug or any(char in slug for char in "/\\:"):
        raise argparse.ArgumentTypeError(f"invalid example slug: {slug!r}")
    return ExampleSource(slug=slug, root=Path(root).expanduser())


def gif_durations(path: Path) -> list[int]:
    with Image.open(path) as image:
        return [int(frame.info.get("duration", 0)) for frame in ImageSequence.Iterator(image)]


def validate_preview(path: Path, state: str) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"missing pipeline preview: {path}")
    expected = ROW_FRAME_DURATIONS_MS[state]
    durations = gif_durations(path)
    if durations != expected:
        raise SystemExit(f"{path} durations {durations} != expected pipeline durations {expected}")
    return {
        "state": state,
        "file": f"previews/{state}.gif",
        "frames": len(durations),
        "durations_ms": durations,
        "total_duration_ms": sum(durations),
    }


def sync_example(source: ExampleSource, output_dir: Path) -> dict[str, object]:
    if not source.previews_dir.is_dir():
        raise SystemExit(f"missing pipeline previews directory: {source.previews_dir}")
    if not source.contact_sheet.is_file():
        raise SystemExit(f"missing pipeline contact sheet: {source.contact_sheet}")

    destination = output_dir / source.slug
    previews_destination = destination / "previews"
    if destination.exists():
        shutil.rmtree(destination)
    previews_destination.mkdir(parents=True)

    states = []
    for state in STATE_ORDER:
        source_preview = source.previews_dir / f"{state}.gif"
        states.append(validate_preview(source_preview, state))
        shutil.copy2(source_preview, previews_destination / source_preview.name)
    shutil.copy2(source.contact_sheet, destination / "contact-sheet.png")

    return {
        "slug": source.slug,
        "source_kind": "goodboy_qa_output",
        "display_preview": "previews/idle.gif",
        "contact_sheet": "contact-sheet.png",
        "states": states,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--example",
        action="append",
        type=parse_example,
        required=True,
        help="Example source formatted as slug=/path/to/completed-goodboy-output-root.",
    )
    parser.add_argument("--output-dir", default="assets/examples")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "description": "README examples synced from completed Goodboy QA output folders. These files are copied from qa/previews and qa/contact-sheet.png; they are not re-rendered by this script.",
        "examples": [sync_example(source, output_dir) for source in args.example],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    for example in manifest["examples"]:
        print(f"synced {example['slug']} from Goodboy QA previews")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
