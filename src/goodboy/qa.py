"""Goodboy frame QA and preview helpers."""

from __future__ import annotations

import itertools
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageSequence, ImageStat

from .contracts import CELL_HEIGHT, CELL_WIDTH, ROW_FRAME_COUNTS, ROW_FRAME_DURATIONS_MS, STATE_ORDER
from .jsonio import read_json
from .jsonio import write_json
from .imageutil import pixel_data
from .schemas import QAPolicyDecision, QAReport, ValidationReport

APPROVED_ROW_PROVENANCE = {"provider_generated", "user_supplied", "test_fixture"}
DISALLOWED_ROW_PROVENANCE = {"mock_renderer", "local_renderer", "programmatic_renderer", "ad_hoc_renderer"}
VERTICAL_DRIFT_THRESHOLDS = {
    "idle": 4,
    "waiting": 6,
    "review": 8,
    "running": 10,
}
ANIMATION_REVIEW = "qa/animation-review.json"
ANIMATION_CORRECTNESS = "qa/animation-correctness.json"
ANIMATION_VERDICTS = {"pass", "warning", "fail"}


def audit_frames(frames_root: Path) -> QAReport:
    frame_manifest = load_frame_manifest(frames_root)
    chroma_key = manifest_chroma_key(frame_manifest)
    methods = {
        row.get("state"): row.get("method")
        for row in frame_manifest.get("rows", [])
        if isinstance(row, dict)
    }
    report = QAReport(
        ok=True,
        states={},
        duplicate_candidates=[],
        green_edge_pixels=0,
        visible_pixels=0,
        errors=[],
        warnings=[],
    )
    for state in STATE_ORDER:
        expected = ROW_FRAME_COUNTS[state]
        files = sorted((frames_root / state).glob("*.png"))
        if len(files) != expected:
            report.ok = False
            report.errors.append(f"{state} has {len(files)} frames, expected {expected}")
        imgs = [Image.open(path).convert("RGBA") for path in files]
        rows = []
        state_green = 0
        state_chroma_adjacent = 0
        state_guide_like = 0
        state_white_background_like = 0
        state_visible = 0
        max_components = 0
        hashes: dict[int, list[str]] = {}
        for path, img in zip(files, imgs, strict=True):
            bbox = img.getchannel("A").getbbox()
            hashes.setdefault(hash(img.tobytes()), []).append(path.name)
            components = count_alpha_components(img)
            max_components = max(max_components, components)
            if bbox:
                left, top, right, bottom = bbox
                rows.append(
                    {
                        "frame": path.name,
                        "bbox": bbox,
                        "cx": (left + right) / 2,
                        "cy": (top + bottom) / 2,
                        "w": right - left,
                        "h": bottom - top,
                        "components": components,
                        "edge": {
                            "left": left,
                            "top": top,
                            "right": CELL_WIDTH - right,
                            "bottom": CELL_HEIGHT - bottom,
                        },
                    }
                )
            for red, green, blue, alpha in pixel_data(img):
                if alpha:
                    state_visible += 1
                    if alpha < 230 and green > max(red, blue) + 8:
                        state_green += 1
                    if chroma_key and alpha > 16 and color_distance((red, green, blue), chroma_key) <= 150:
                        state_chroma_adjacent += 1
                    if alpha > 230 and is_guide_like_pixel(red, green, blue):
                        state_guide_like += 1
                    if alpha > 245 and red > 244 and green > 244 and blue > 244:
                        state_white_background_like += 1
        exact_duplicates = [names for names in hashes.values() if len(names) > 1]
        if exact_duplicates:
            report.ok = False
            report.errors.append(f"{state} has exact duplicate frames: {exact_duplicates}")

        near = near_duplicate_pairs(imgs)
        if near:
            report.duplicate_candidates.append({"state": state, "near_pairs": near[:10]})
            possible_pairs = expected * (expected - 1) // 2
            if state not in {"idle", "waiting"} and possible_pairs and len(near) >= possible_pairs - 1:
                report.ok = False
                report.errors.append(f"{state} has nearly static motion across the whole loop")
        cx_range = max((row["cx"] for row in rows), default=0) - min((row["cx"] for row in rows), default=0)
        cy_range = max((row["cy"] for row in rows), default=0) - min((row["cy"] for row in rows), default=0)
        min_edge = min((min(row["edge"].values()) for row in rows), default=None)
        if max_components > 8:
            report.ok = False
            report.errors.append(f"{state} has too many detached components in a frame: {max_components}")
        elif max_components > 4:
            report.warnings.append(f"{state} has high detached component count: {max_components}")
        if min_edge is not None and min_edge < 4:
            report.ok = False
            report.errors.append(f"{state} has frame edge clearance below 4px")
        elif min_edge is not None and min_edge < 10:
            report.warnings.append(f"{state} has tight frame edge clearance: {min_edge}px")
        if state != "jumping" and cx_range > 10:
            report.warnings.append(f"{state} horizontal drift is {cx_range:.1f}px")
        threshold = VERTICAL_DRIFT_THRESHOLDS.get(state)
        if threshold is not None and cy_range > threshold:
            report.warnings.append(f"{state} vertical center drift is {cy_range:.1f}px, threshold {threshold}px")
        method = methods.get(state)
        if method == "stable-slots":
            report.warnings.append(f"{state} used stable-slots extraction; visually confirm scale and clipping")
        if state_chroma_adjacent > 800:
            report.warnings.append(f"{state} has {state_chroma_adjacent} visible pixels close to the selected chroma key")
        if state_guide_like > 120:
            report.warnings.append(f"{state} has {state_guide_like} guide-colored pixels; check for copied layout guide marks")
        cell_pixels = CELL_WIDTH * CELL_HEIGHT * max(1, len(files))
        if state_visible > cell_pixels * 0.80 and state_white_background_like / state_visible > 0.65:
            report.warnings.append(f"{state} may contain a white or nontransparent cell background")
        report.states[state] = {
            "count": len(files),
            "expected": expected,
            "cx_range": round(cx_range, 2),
            "cy_range": round(cy_range, 2),
            "min_edge": min_edge,
            "max_components": max_components,
            "green_edge_pixels": state_green,
            "chroma_adjacent_pixels": state_chroma_adjacent,
            "guide_like_pixels": state_guide_like,
            "white_background_like_pixels": state_white_background_like,
            "extraction_method": method,
            "visible_pixels": state_visible,
            "frames": rows,
        }
        report.green_edge_pixels += state_green
        report.visible_pixels += state_visible
    return report


def load_frame_manifest(frames_root: Path) -> dict[str, object]:
    path = frames_root / "frames-manifest.json"
    if not path.is_file():
        return {}
    try:
        raw = read_json(path)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def manifest_chroma_key(raw: dict[str, object]) -> tuple[int, int, int] | None:
    chroma_key = raw.get("chroma_key")
    if not isinstance(chroma_key, dict):
        return None
    rgb = chroma_key.get("rgb")
    if isinstance(rgb, list) and len(rgb) == 3:
        return tuple(int(value) for value in rgb)
    return None


def color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def is_guide_like_pixel(red: int, green: int, blue: int) -> bool:
    guide_colors = ((17, 17, 17), (47, 128, 237), (184, 184, 184), (247, 247, 247))
    return any(color_distance((red, green, blue), guide) <= 18 for guide in guide_colors)


def count_alpha_components(img: Image.Image, *, min_pixels: int = 80) -> int:
    alpha = img.getchannel("A")
    width, height = alpha.size
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    components = 0
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] == 0:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            size = 0
            while stack:
                px, py = stack.pop()
                size += 1
                for ny in range(py - 1, py + 2):
                    for nx in range(px - 1, px + 2):
                        if nx == px and ny == py:
                            continue
                        if nx < 0 or ny < 0 or nx >= width or ny >= height:
                            continue
                        if (nx, ny) in seen or pixels[nx, ny] == 0:
                            continue
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            if size >= min_pixels:
                components += 1
    return components


def evaluate_qa_policy(
    validation: ValidationReport,
    qa_report: QAReport,
    *,
    override_reason: str | None = None,
    install_requested: bool = False,
    row_provenance: str | None = None,
    visual_approval: str | None = None,
) -> QAPolicyDecision:
    technical_failures = list(validation.errors) + list(qa_report.errors)
    hard_failures = list(technical_failures)
    warnings = list(validation.warnings) + list(qa_report.warnings)
    approval_note = visual_approval.strip() if visual_approval else None
    provenance = row_provenance.strip() if row_provenance else None
    if install_requested:
        if provenance in DISALLOWED_ROW_PROVENANCE:
            hard_failures.append(
                f"row strip provenance `{provenance}` is not installable; use provider_generated, user_supplied, or test_fixture"
            )
        elif provenance not in APPROVED_ROW_PROVENANCE:
            hard_failures.append(
                "row strip provenance is required for install; use provider_generated, user_supplied, or test_fixture"
            )
        if not approval_note:
            hard_failures.append("visual approval is required for install")
    technical_ok = not technical_failures or bool(override_reason)
    gate_failures = hard_failures[len(technical_failures) :]
    ok_to_install = technical_ok and not gate_failures
    return QAPolicyDecision(
        ok_to_install=ok_to_install,
        hard_failures=hard_failures,
        warnings=warnings,
        override_reason=override_reason,
        install_requested=install_requested,
        row_provenance=provenance,
        visual_approval=approval_note,
    )


def near_duplicate_pairs(imgs: list[Image.Image], threshold: float = 3.0) -> list[dict[str, object]]:
    near = []
    for (i, first), (j, second) in itertools.combinations(enumerate(imgs), 2):
        first_bbox = first.getbbox()
        second_bbox = second.getbbox()
        if not first_bbox or not second_bbox:
            continue
        first_crop = first.crop(first_bbox).resize((128, 128), Image.Resampling.LANCZOS)
        second_crop = second.crop(second_bbox).resize((128, 128), Image.Resampling.LANCZOS)
        diff = ImageChops.difference(first_crop, second_crop)
        rms = math.sqrt(sum(value * value for value in ImageStat.Stat(diff).rms) / 4)
        if rms < threshold:
            near.append({"pair": [i, j], "rms": round(rms, 3)})
    return near


def make_white_edge_preview(frames_root: Path, output_path: Path) -> None:
    items = []
    for state in STATE_ORDER:
        limit = 3 if state in {"idle", "waving", "waiting"} else 2
        for frame_path in sorted((frames_root / state).glob("*.png"))[:limit]:
            items.append((state, frame_path))
    cell_w, cell_h = 256, 290
    columns = 4
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (state, path) in enumerate(items):
        img = Image.open(path).convert("RGBA").resize((CELL_WIDTH * 2, CELL_HEIGHT * 2), Image.Resampling.NEAREST)
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        tile = bg.convert("RGB")
        tile.thumbnail((cell_w, cell_h - 24), Image.Resampling.LANCZOS)
        x = (index % columns) * cell_w + (cell_w - tile.width) // 2
        y = (index // columns) * cell_h + 22
        draw.text(((index % columns) * cell_w + 8, (index // columns) * cell_h + 6), f"{state} {path.stem}", fill=(0, 0, 0))
        canvas.paste(tile, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def make_centering_overlay(frames_root: Path, output_path: Path) -> None:
    items = []
    for state in STATE_ORDER:
        for frame_path in sorted((frames_root / state).glob("*.png")):
            items.append((state, frame_path))
    cell_w, cell_h = 220, 252
    columns = 8
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (state, path) in enumerate(items):
        frame = Image.open(path).convert("RGBA")
        bbox = frame.getchannel("A").getbbox()
        x0 = (index % columns) * cell_w
        y0 = (index // columns) * cell_h
        draw.rectangle((x0, y0, x0 + cell_w - 1, y0 + cell_h - 1), outline=(220, 220, 220))
        draw.text((x0 + 6, y0 + 5), f"{state} {path.stem}", fill=(0, 0, 0))
        scale = min((cell_w - 20) / CELL_WIDTH, (cell_h - 32) / CELL_HEIGHT)
        preview = frame.resize((round(CELL_WIDTH * scale), round(CELL_HEIGHT * scale)), Image.Resampling.NEAREST)
        px = x0 + (cell_w - preview.width) // 2
        py = y0 + 26
        bg = Image.new("RGBA", preview.size, "white")
        bg.alpha_composite(preview)
        canvas.paste(bg.convert("RGB"), (px, py))
        center_y = py + preview.height // 2
        center_x = px + preview.width // 2
        draw.line((px, center_y, px + preview.width, center_y), fill=(80, 140, 255), width=1)
        draw.line((center_x, py, center_x, py + preview.height), fill=(80, 140, 255), width=1)
        if bbox:
            left, top, right, bottom = bbox
            draw.rectangle(
                (
                    px + round(left * scale),
                    py + round(top * scale),
                    px + round(right * scale),
                    py + round(bottom * scale),
                ),
                outline=(230, 80, 80),
                width=1,
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def write_qa_report(path: Path, report: QAReport) -> None:
    write_json(path, report.to_dict())


def record_animation_review(
    project_dir: Path,
    *,
    run_id: str,
    verdicts: list[dict[str, object]],
    reviewed_by: str,
) -> dict[str, object]:
    """Record state-by-state semantic, temporal, and identity animation review."""

    if not reviewed_by.strip():
        raise ValueError("animation reviewer is required")
    normalized: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in verdicts:
        if not isinstance(item, dict):
            raise ValueError("every animation verdict must be an object")
        state = str(item.get("state", "")).strip()
        if state not in STATE_ORDER or state in seen:
            raise ValueError(f"animation state must be expected and unique: `{state}`")
        seen.add(state)
        verdict = str(item.get("verdict", "")).strip()
        if verdict not in ANIMATION_VERDICTS:
            raise ValueError(f"animation verdict for `{state}` must be pass, warning, or fail")
        evidence = {}
        for key in ("state_semantics", "motion_continuity", "identity_consistency"):
            text = str(item.get(key, "")).strip()
            if not text:
                raise ValueError(f"animation verdict for `{state}` requires `{key}` evidence")
            evidence[key] = text
        normalized.append({"state": state, "verdict": verdict, **evidence})
    missing = [state for state in STATE_ORDER if state not in seen]
    if missing:
        raise ValueError(f"animation review is incomplete; missing: {', '.join(missing)}")
    failures = [item["state"] for item in normalized if item["verdict"] == "fail"]
    warnings = [item["state"] for item in normalized if item["verdict"] == "warning"]
    review = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "failed" if failures else "approved",
        "reviewed_by": reviewed_by.strip(),
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "verdicts": sorted(normalized, key=lambda item: STATE_ORDER.index(str(item["state"]))),
        "failed_states": failures,
        "warning_states": warnings,
    }
    run_dir = project_dir / "runs" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"missing run: {run_dir}")
    write_json(run_dir / ANIMATION_REVIEW, review)
    write_animation_correctness_report(run_dir)
    return review


def animation_is_approved(project_dir: Path, run_id: str) -> bool:
    path = project_dir / "runs" / run_id / ANIMATION_REVIEW
    return bool(path.is_file() and read_json(path).get("status") == "approved")


def write_animation_correctness_report(run_dir: Path) -> dict[str, object]:
    """Aggregate exact playback checks with the required structured visual review."""

    qa_dir = run_dir / "qa"
    duplicate_path = qa_dir / "duplicate-audit.json"
    duplicate = read_json(duplicate_path) if duplicate_path.is_file() else {}
    rows: list[dict[str, object]] = []
    technical_failures: list[str] = []
    for state in STATE_ORDER:
        preview_path = qa_dir / "previews" / f"{state}.gif"
        expected_durations = list(ROW_FRAME_DURATIONS_MS[state])
        frame_count = 0
        durations: list[int] = []
        if preview_path.is_file():
            with Image.open(preview_path) as preview:
                frame_count = int(getattr(preview, "n_frames", 1))
                durations = [
                    int(frame.info.get("duration", 0))
                    for frame in ImageSequence.Iterator(preview)
                ]
        else:
            technical_failures.append(f"missing animation preview for {state}")
        temporal_contract_ok = (
            frame_count == ROW_FRAME_COUNTS[state]
            and durations == expected_durations
        )
        if preview_path.is_file() and not temporal_contract_ok:
            technical_failures.append(
                f"{state} preview timing/count mismatch: {frame_count} frames, durations {durations}"
            )
        state_audit = duplicate.get("states", {}).get(state, {}) if isinstance(duplicate, dict) else {}
        rows.append(
            {
                "state": state,
                "expected_frames": ROW_FRAME_COUNTS[state],
                "preview_frames": frame_count,
                "expected_durations_ms": expected_durations,
                "preview_durations_ms": durations,
                "temporal_contract_ok": temporal_contract_ok,
                "preview": str(preview_path.relative_to(run_dir)) if preview_path.is_file() else None,
                "automated_motion_signals": {
                    "cx_range": state_audit.get("cx_range"),
                    "cy_range": state_audit.get("cy_range"),
                    "min_edge": state_audit.get("min_edge"),
                    "extraction_method": state_audit.get("extraction_method"),
                },
            }
        )
    if isinstance(duplicate, dict):
        technical_failures.extend(str(item) for item in duplicate.get("errors", []))
    review_path = run_dir / ANIMATION_REVIEW
    review = read_json(review_path) if review_path.is_file() else None
    review_approved = bool(review and review.get("status") == "approved")
    report = {
        "schema_version": "1.0",
        "run_id": run_dir.name,
        "technical_ok": not technical_failures,
        "review_complete": review is not None,
        "review_approved": review_approved,
        "ok": not technical_failures and review_approved,
        "technical_failures": list(dict.fromkeys(technical_failures)),
        "rows": rows,
        "review": review,
        "direction_evidence": {
            "labeled_semantics": (qa_dir / "direction-semantics.json").is_file(),
            "blind_validation": (qa_dir / "direction-blind-validation.json").is_file(),
            "continuity": (qa_dir / "look-continuity.json").is_file(),
        },
        "policy": (
            "Automated timing, duplication, edge, and drift checks cannot establish state meaning. "
            "Approval requires explicit evidence for state semantics, motion continuity, and "
            "cross-state identity in every standard row, plus the separate v2 direction gates."
        ),
    }
    write_json(run_dir / ANIMATION_CORRECTNESS, report)
    return report
