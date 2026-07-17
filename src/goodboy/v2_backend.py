"""Goodboy wrapper around the pinned Hatch-compatible deterministic backend."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .contracts import CELL_HEIGHT, CELL_WIDTH, LOOK_DIRECTIONS, V2_OUTPUT_CONTRACT
from .jsonio import read_json, write_json
from .raster import extract_subjects, fit_viewport_to_cell, remove_chroma_background
from .vendor.hatch_pet import BACKEND_NAME, BACKEND_VERSION


VENDOR_ROOT = Path(__file__).resolve().parent / "vendor" / "hatch_pet"
SCRIPT_DIR = VENDOR_ROOT / "scripts"


class V2BackendError(RuntimeError):
    """A deterministic v2 backend command could not complete."""


@dataclass(frozen=True)
class BackendCommand:
    script: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "script": self.script,
            "command": [
                portable_command_argument(argument, index=index, script=self.script)
                for index, argument in enumerate(self.command)
            ],
            "returncode": self.returncode,
            "stdout_recorded": bool(self.stdout.strip()),
            "stderr_recorded": bool(self.stderr.strip()),
        }


def portable_command_argument(value: str, *, index: int, script: str) -> str:
    """Keep backend receipts reproducible without leaking local filesystem paths."""

    if index == 0:
        return "<python>"
    if index == 1:
        return f"<vendored-hatch-backend>/scripts/{script}"
    path = Path(value)
    if not path.is_absolute():
        return value
    parts = path.parts
    if "runs" in parts:
        run_index = parts.index("runs")
        return "<project>/" + "/".join(parts[run_index:])
    return f"<local-path>/{path.name}"


def portableize_artifact_paths(value: Any, *, run_dir: Path) -> Any:
    """Recursively replace machine-local paths while retaining run-relative provenance."""

    if isinstance(value, dict):
        return {
            key: portableize_artifact_paths(item, run_dir=run_dir)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [portableize_artifact_paths(item, run_dir=run_dir) for item in value]
    if not isinstance(value, str):
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        relative = path.resolve().relative_to(run_dir.resolve())
    except (OSError, ValueError):
        try:
            relative = path.resolve().relative_to(VENDOR_ROOT.resolve())
        except (OSError, ValueError):
            return f"<local-path>/{path.name}"
        return f"<vendored-hatch-backend>/{relative.as_posix()}"
    return f"runs/{run_dir.name}/{relative.as_posix()}"


def normalize_run_json_paths(run_dir: Path) -> list[str]:
    """Make deterministic reports portable without altering raw provider responses."""

    updated: list[str] = []
    for path in sorted(run_dir.rglob("*.json")):
        if path.name.endswith(".response.json"):
            continue
        try:
            raw = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        normalized = portableize_artifact_paths(raw, run_dir=run_dir)
        if normalized != raw:
            write_json(path, normalized)
            updated.append(str(path.relative_to(run_dir)))
    return updated


def backend_metadata() -> dict[str, Any]:
    snapshot_path = VENDOR_ROOT / "SNAPSHOT.json"
    snapshot = read_json(snapshot_path) if snapshot_path.is_file() else {}
    return {
        "name": BACKEND_NAME,
        "version": BACKEND_VERSION,
        "contract_id": V2_OUTPUT_CONTRACT.contract_id,
        "contract_version": V2_OUTPUT_CONTRACT.contract_version,
        "sprite_version_number": V2_OUTPUT_CONTRACT.sprite_version_number,
        "license": "Apache-2.0",
        "source": snapshot.get("source", "vendored Hatch Pet snapshot"),
        "source_skill_sha256": snapshot.get("source_skill_sha256"),
    }


def script_path(name: str) -> Path:
    path = SCRIPT_DIR / name
    if not path.is_file():
        raise V2BackendError(f"missing vendored Hatch backend script: {path}")
    return path


def run_backend_script(
    name: str,
    arguments: list[str | Path],
    *,
    allow_failure: bool = False,
) -> BackendCommand:
    command = [sys.executable, str(script_path(name)), *[str(item) for item in arguments]]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    result = BackendCommand(
        script=name,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if completed.returncode and not allow_failure:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown backend failure"
        raise V2BackendError(f"{name} failed: {message}")
    return result


def chroma_hex(run_dir: Path) -> str:
    for path in (run_dir / "run-metadata.json", run_dir / "pet_request.json"):
        if not path.is_file():
            continue
        raw = read_json(path)
        chroma = raw.get("chroma_key")
        if isinstance(chroma, dict) and isinstance(chroma.get("hex"), str):
            return str(chroma["hex"])
    return "#00FF00"


def compose_directional_anchor_reference(
    anchors_dir: Path,
    output: Path,
    directions: tuple[str, ...],
) -> None:
    """Compose a direction-specific reference without exposing the opposite turn family."""

    strip = Image.new("RGBA", (CELL_WIDTH * len(directions), CELL_HEIGHT), (0, 0, 0, 0))
    for index, direction in enumerate(directions):
        path = anchors_dir / f"{direction}.png"
        if not path.is_file():
            raise FileNotFoundError(f"missing approved cardinal reference: {path}")
        with Image.open(path) as opened:
            reference = opened.convert("RGBA")
        if reference.size != (CELL_WIDTH, CELL_HEIGHT):
            raise V2BackendError(
                f"approved cardinal reference {path} is {reference.size}; "
                f"expected {(CELL_WIDTH, CELL_HEIGHT)}"
            )
        if reference.getbbox() is None:
            raise V2BackendError(f"approved cardinal reference is empty: {path}")
        strip.alpha_composite(reference, (index * CELL_WIDTH, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    strip.save(output)


def extract_and_compose_cardinals(run_dir: Path) -> dict[str, Any]:
    source = run_dir / "row-strips" / "look-cardinals.png"
    if not source.is_file():
        raise FileNotFoundError(f"missing four-cardinal strip: {source}")
    anchors_dir = run_dir / "decoded" / "look-anchors"
    report_path = run_dir / "qa" / "cardinal-anchors.json"
    approved = run_dir / "decoded" / "look-anchors-approved.png"
    anchors_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    slot_extraction = run_backend_script(
        "extract_cardinal_anchors.py",
        [
            "--strip",
            source,
            "--output-dir",
            anchors_dir,
            "--chroma-key",
            chroma_hex(run_dir),
            "--json-out",
            report_path,
        ],
        allow_failure=True,
    )
    if slot_extraction.returncode:
        failed_report = read_json(report_path) if report_path.is_file() else {}
        chroma = chroma_hex(run_dir).lstrip("#")
        chroma_rgb = tuple(int(chroma[index : index + 2], 16) for index in (0, 2, 4))
        try:
            with Image.open(source) as opened:
                transparent = remove_chroma_background(opened, chroma_rgb)
            subjects, method = extract_subjects(transparent, 4, "components")
        except (OSError, ValueError) as exc:
            message = slot_extraction.stderr.strip() or slot_extraction.stdout.strip() or str(exc)
            raise V2BackendError(f"extract_cardinal_anchors.py failed: {message}") from exc
        labels = ["000", "090", "180", "270"]
        anchors: list[dict[str, Any]] = []
        for label, (subject, source_bbox) in zip(labels, subjects, strict=True):
            output = anchors_dir / f"{label}.png"
            cell = fit_viewport_to_cell(subject)
            cell.save(output)
            bbox = cell.getchannel("A").getbbox()
            if bbox is None or bbox[0] < 4 or bbox[1] < 4 or bbox[2] > cell.width - 4 or bbox[3] > cell.height - 4:
                raise V2BackendError(
                    f"component-registered cardinal `{label}` does not retain safe cell padding"
                )
            anchors.append(
                {
                    "direction": label,
                    "source_box": list(source_bbox) if source_bbox is not None else None,
                    "output": str(output),
                    "output_bbox": list(bbox),
                }
            )
        write_json(
            report_path,
            {
                "ok": True,
                "strip": str(source),
                "directions": labels,
                "errors": [],
                "warnings": [
                    "equal-slot extraction crossed source-slot margins; four disconnected poses were registered left-to-right by component"
                ],
                "extraction_method": method,
                "fallback_trigger": failed_report.get("errors", []),
                "anchors": anchors,
            },
        )
    run_backend_script(
        "compose_cardinal_anchor_strip.py",
        ["--anchors-dir", anchors_dir, "--output", approved],
    )
    row_9_reference = run_dir / "decoded" / "look-anchors-row-9.png"
    row_10_reference = run_dir / "decoded" / "look-anchors-row-10.png"
    compose_directional_anchor_reference(
        anchors_dir,
        row_9_reference,
        ("000", "090", "180"),
    )
    compose_directional_anchor_reference(
        anchors_dir,
        row_10_reference,
        ("180", "270", "000"),
    )
    report = read_json(report_path)
    report["approved_strip"] = str(approved)
    report["row_specific_references"] = {
        "look-row-9": {
            "path": str(row_9_reference),
            "directions": ["000", "090", "180"],
        },
        "look-row-10": {
            "path": str(row_10_reference),
            "directions": ["180", "270", "000"],
        },
    }
    write_json(report_path, report)
    return report


def build_standard_rows(
    run_dir: Path,
    *,
    extraction_method: str = "auto",
) -> dict[str, Any]:
    """Build and inspect the canonical rows 0-8 intermediate."""

    rows_dir = run_dir / "row-strips"
    frames_dir = run_dir / "frames"
    qa_dir = run_dir / "qa"
    final_dir = run_dir / "final"
    frames_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    extract = run_backend_script(
        "extract_strip_frames.py",
        [
            "--decoded-dir",
            rows_dir,
            "--output-dir",
            frames_dir,
            "--states",
            "all",
            "--chroma-key",
            chroma_hex(run_dir),
            "--method",
            extraction_method,
        ],
    )
    review_path = qa_dir / "review-standard.json"
    inspect = run_backend_script(
        "inspect_frames.py",
        [
            "--frames-root",
            frames_dir,
            "--json-out",
            review_path,
            "--states",
            "all",
            "--require-components",
            *([] if extraction_method != "stable-slots" else ["--allow-stable-slots"]),
        ],
        allow_failure=True,
    )
    standard_png = final_dir / "spritesheet-standard.png"
    standard_webp = final_dir / "spritesheet-standard.webp"
    run_backend_script(
        "compose_atlas.py",
        [
            "--frames-root",
            frames_dir,
            "--output",
            standard_png,
            "--webp-output",
            standard_webp,
        ],
    )
    contact_sheet = qa_dir / "contact-sheet-standard.png"
    run_backend_script("make_contact_sheet.py", [standard_webp, "--output", contact_sheet])
    run_backend_script(
        "render_animation_previews.py",
        ["--frames-root", frames_dir, "--output-dir", qa_dir / "previews"],
    )
    review = read_json(review_path)
    if inspect.returncode and not review.get("ok"):
        raise V2BackendError(
            "standard row inspection failed: " + "; ".join(str(item) for item in review.get("errors", []))
        )
    return {
        "extract": extract.to_dict(),
        "inspection": review,
        "standard_png": str(standard_png),
        "standard_webp": str(standard_webp),
        "contact_sheet": str(contact_sheet),
    }


def register_look_row_9(
    run_dir: Path,
    *,
    standard_atlas: Path,
    neutral_cell: Path,
) -> dict[str, Any]:
    row_9 = run_dir / "row-strips" / "look-row-9.png"
    if not row_9.is_file():
        raise FileNotFoundError(f"missing look row 9: {row_9}")
    registered = run_dir / "qa" / "look-row-9-registered.png"
    manifest = run_dir / "qa" / "look-row-9-registration.json"
    run_backend_script(
        "assemble_extended_atlas.py",
        [
            "--base-atlas",
            standard_atlas,
            "--look-row-9",
            row_9,
            "--neutral-cell",
            neutral_cell,
            "--chroma-key",
            chroma_hex(run_dir),
            "--chroma-threshold",
            "96",
            "--registered-row-output",
            registered,
            "--registration-manifest-output",
            manifest,
        ],
    )
    return read_json(manifest)


def assemble_extended_atlas(
    run_dir: Path,
    *,
    standard_atlas: Path,
    neutral_cell: Path,
) -> dict[str, Any]:
    registered = run_dir / "qa" / "look-row-9-registered.png"
    registration = run_dir / "qa" / "look-row-9-registration.json"
    row_10 = run_dir / "row-strips" / "look-row-10.png"
    if not registered.is_file() or not registration.is_file():
        register_look_row_9(run_dir, standard_atlas=standard_atlas, neutral_cell=neutral_cell)
    if not row_10.is_file():
        raise FileNotFoundError(f"missing look row 10: {row_10}")
    final_dir = run_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    output_png = final_dir / "spritesheet-v2.png"
    output_webp = final_dir / "spritesheet-v2.webp"
    manifest = final_dir / "spritesheet-v2.json"
    run_backend_script(
        "assemble_extended_atlas.py",
        [
            "--base-atlas",
            standard_atlas,
            "--registered-row-9",
            registered,
            "--row-9-registration",
            registration,
            "--look-row-10",
            row_10,
            "--neutral-cell",
            neutral_cell,
            "--chroma-key",
            chroma_hex(run_dir),
            "--chroma-threshold",
            "96",
            "--output",
            output_png,
            "--webp-output",
            output_webp,
            "--manifest-output",
            manifest,
        ],
    )
    return read_json(manifest)


def final_despill_and_validate(run_dir: Path) -> dict[str, Any]:
    final_dir = run_dir / "final"
    qa_dir = run_dir / "qa"
    atlas_png = final_dir / "spritesheet-v2.png"
    atlas_webp = final_dir / "spritesheet-v2.webp"
    if not atlas_png.is_file():
        raise FileNotFoundError(f"missing assembled v2 atlas: {atlas_png}")
    despill_report = qa_dir / "chroma-despill-v2.json"
    validation_path = final_dir / "validation-v2.json"
    run_backend_script(
        "despill_chroma_edges.py",
        [
            atlas_png,
            "--output",
            atlas_png,
            "--webp-output",
            atlas_webp,
            "--chroma-key",
            chroma_hex(run_dir),
            "--json-out",
            despill_report,
        ],
    )
    validation_command = run_backend_script(
        "validate_atlas.py",
        [
            atlas_webp,
            "--json-out",
            validation_path,
            "--chroma-key",
            chroma_hex(run_dir),
            "--require-v2",
        ],
        allow_failure=True,
    )
    validation = read_json(validation_path)
    validation["backend_returncode"] = validation_command.returncode
    if not validation.get("ok"):
        raise V2BackendError(
            "v2 atlas validation failed: " + "; ".join(str(item) for item in validation.get("errors", []))
        )
    despill = read_json(despill_report)
    if not despill.get("ok"):
        raise V2BackendError("v2 chroma despill report did not pass")
    return {"validation": validation, "despill": despill}


def create_v2_review_media(run_dir: Path) -> dict[str, str]:
    atlas = run_dir / "final" / "spritesheet-v2.webp"
    qa_dir = run_dir / "qa"
    contact_sheet = qa_dir / "contact-sheet-v2.png"
    direction_sheet = qa_dir / "look-directions.png"
    blind_sheet = qa_dir / "direction-blind-pairs.png"
    blind_key = qa_dir / "direction-blind-answer-key.json"
    continuity = qa_dir / "look-continuity.json"
    run_backend_script("make_contact_sheet.py", [atlas, "--output", contact_sheet])
    run_backend_script("make_direction_qa_sheet.py", [atlas, "--output", direction_sheet])
    run_backend_script(
        "make_direction_blind_qa_sheet.py",
        [atlas, "--output", blind_sheet, "--answer-key", blind_key],
    )
    run_backend_script(
        "measure_direction_continuity.py",
        [atlas, "--json-out", continuity],
    )
    semantics = qa_dir / "direction-semantics.json"
    if not semantics.is_file():
        write_json(
            semantics,
            {
                "status": "awaiting-independent-review",
                "directions": [
                    {
                        "direction": direction,
                        "expected": expected_direction(direction),
                        "verdict": "pending",
                        "observed": "",
                        "reason": "",
                    }
                    for direction in LOOK_DIRECTIONS
                ],
            },
        )
    return {
        "contact_sheet": str(contact_sheet),
        "direction_sheet": str(direction_sheet),
        "blind_sheet": str(blind_sheet),
        "blind_answer_key": str(blind_key),
        "continuity": str(continuity),
        "direction_semantics": str(semantics),
    }


def expected_direction(direction: str) -> str:
    value = float(direction)
    if value == 0:
        return "up"
    if value == 90:
        return "right"
    if value == 180:
        return "down"
    if value == 270:
        return "left"
    vertical = "up" if value > 270 or value < 90 else "down"
    horizontal = "right" if 0 < value < 180 else "left"
    return f"{vertical}-{horizontal}"


def record_direction_semantics(run_dir: Path, directions: list[dict[str, Any]], *, reviewer: str) -> dict[str, Any]:
    if not reviewer.strip():
        raise ValueError("direction reviewer is required")
    supplied = [str(item.get("direction")) for item in directions]
    duplicates = sorted({direction for direction in supplied if supplied.count(direction) > 1})
    if duplicates:
        raise ValueError(f"duplicate direction semantic verdicts: {', '.join(duplicates)}")
    unknown = sorted(set(supplied) - set(LOOK_DIRECTIONS))
    if unknown:
        raise ValueError(f"unknown direction semantic verdicts: {', '.join(unknown)}")
    by_direction = {str(item.get("direction")): item for item in directions}
    missing = [direction for direction in LOOK_DIRECTIONS if direction not in by_direction]
    if missing:
        raise ValueError(f"missing direction semantic verdicts: {', '.join(missing)}")
    normalized = []
    for direction in LOOK_DIRECTIONS:
        item = dict(by_direction[direction])
        verdict = str(item.get("verdict", ""))
        if verdict not in {"pass", "warning", "fail"}:
            raise ValueError(f"invalid direction verdict `{verdict}` for {direction}")
        observed = str(item.get("observed", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not observed or not reason:
            raise ValueError(f"direction verdict `{direction}` requires observed direction and visible evidence")
        normalized.append(
            {
                "direction": direction,
                "expected": expected_direction(direction),
                "observed": observed,
                "verdict": verdict,
                "reason": reason,
            }
        )
    result = {
        "status": "failed" if any(item["verdict"] == "fail" for item in normalized) else "reviewed",
        "reviewer": reviewer,
        "directions": normalized,
    }
    write_json(run_dir / "qa" / "direction-semantics.json", result)
    return result


def combine_and_validate_blind_reviews(run_dir: Path, verdict_paths: list[Path]) -> dict[str, Any]:
    if len(verdict_paths) != 3:
        raise ValueError("exactly three isolated blind direction verdict files are required")
    combined = run_dir / "qa" / "direction-blind-verdicts.json"
    validation = run_dir / "qa" / "direction-blind-validation.json"
    arguments: list[str | Path] = []
    for path in verdict_paths:
        arguments.extend(["--verdicts", path])
    arguments.extend(["--json-out", combined])
    run_backend_script("combine_direction_blind_verdicts.py", arguments)
    run_backend_script(
        "validate_direction_blind_verdicts.py",
        [
            "--answer-key",
            run_dir / "qa" / "direction-blind-answer-key.json",
            "--verdicts",
            combined,
            "--json-out",
            validation,
        ],
        allow_failure=True,
    )
    return read_json(validation)


def v2_review_gate(run_dir: Path, *, allow_test_fixture: bool = False) -> dict[str, Any]:
    semantics_path = run_dir / "qa" / "direction-semantics.json"
    blind_path = run_dir / "qa" / "direction-blind-validation.json"
    validation_path = run_dir / "final" / "validation-v2.json"
    despill_path = run_dir / "qa" / "chroma-despill-v2.json"
    failures: list[str] = []
    warnings: list[str] = []
    for path, label in (
        (validation_path, "v2 atlas validation"),
        (despill_path, "final chroma despill"),
    ):
        if not path.is_file() or not read_json(path).get("ok"):
            failures.append(f"{label} is missing or failed")
    if allow_test_fixture:
        warnings.append("direction semantics and blind review were explicitly bypassed for a synthetic test fixture")
    else:
        if not semantics_path.is_file():
            failures.append("direction semantics are missing")
        else:
            semantics = read_json(semantics_path)
            items = semantics.get("directions", [])
            if len(items) != 16 or any(item.get("verdict") == "pending" for item in items):
                failures.append("direction semantics are incomplete")
            if any(item.get("verdict") == "fail" for item in items):
                failures.append("direction semantics contain failed directions")
        if not blind_path.is_file() or not read_json(blind_path).get("ok"):
            failures.append("blind direction validation is missing or failed")
    return {"ok": not failures, "hard_failures": failures, "warnings": warnings}


def build_v2_backend(
    run_dir: Path,
    *,
    standard_atlas: Path,
    neutral_cell: Path,
) -> dict[str, Any]:
    registration = register_look_row_9(
        run_dir,
        standard_atlas=standard_atlas,
        neutral_cell=neutral_cell,
    )
    assembly = assemble_extended_atlas(
        run_dir,
        standard_atlas=standard_atlas,
        neutral_cell=neutral_cell,
    )
    deterministic = final_despill_and_validate(run_dir)
    review_media = create_v2_review_media(run_dir)
    receipt = {
        "backend": backend_metadata(),
        "registration": registration,
        "assembly": assembly,
        "deterministic": deterministic,
        "review_media": review_media,
    }
    write_json(run_dir / "qa" / "v2-backend-receipt.json", receipt)
    return receipt


def validate_v2_package(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "pet.json"
    atlas_path = package_dir / "spritesheet.webp"
    errors: list[str] = []
    if not manifest_path.is_file():
        errors.append("missing pet.json")
        manifest: dict[str, Any] = {}
    else:
        manifest = read_json(manifest_path)
        if manifest.get("spriteVersionNumber") != 2:
            errors.append("pet.json spriteVersionNumber must be 2")
    if not atlas_path.is_file():
        errors.append("missing spritesheet.webp")
    else:
        from PIL import Image

        with Image.open(atlas_path) as image:
            if image.size != (V2_OUTPUT_CONTRACT.atlas_width, V2_OUTPUT_CONTRACT.atlas_height):
                errors.append(
                    f"spritesheet size {image.size} != "
                    f"{(V2_OUTPUT_CONTRACT.atlas_width, V2_OUTPUT_CONTRACT.atlas_height)}"
                )
    return {"ok": not errors, "errors": errors, "manifest": manifest}


def backend_source_hashes() -> dict[str, str]:
    import hashlib

    hashes: dict[str, str] = {}
    for path in sorted(SCRIPT_DIR.glob("*.py")):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def write_backend_snapshot(path: Path) -> dict[str, Any]:
    payload = {**backend_metadata(), "source_hashes": backend_source_hashes()}
    write_json(path, payload)
    return payload
