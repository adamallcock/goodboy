"""Deterministic raster processing for generated pet row strips."""

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image

from .contracts import CELL_HEIGHT, CELL_WIDTH, ROW_FRAME_COUNTS, STATE_ORDER
from .jsonio import write_json
from .schemas import default_frame_manifest


RGBA = tuple[int, int, int, int]

ANCHOR_POLICIES = {
    "idle": "stable_center",
    "waiting": "stable_center",
    "review": "stable_head_or_torso",
    "running": "stable_head_or_torso",
    "running-right": "bottom_grounded",
    "running-left": "bottom_grounded",
    "waving": "bottom_grounded",
    "failed": "bottom_grounded",
    "jumping": "motion_arc",
}

STABILIZED_POLICIES = {"stable_center", "stable_head_or_torso"}
MIN_CENTERING_EDGE = 4


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index : index + 3] = b"\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def border_key(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    samples: list[tuple[int, int, int]] = []
    width, height = rgb.size
    for x in range(width):
        samples.append(rgb.getpixel((x, 0)))
        samples.append(rgb.getpixel((x, height - 1)))
    for y in range(height):
        samples.append(rgb.getpixel((0, y)))
        samples.append(rgb.getpixel((width - 1, y)))
    samples.sort()
    return samples[len(samples) // 2]


def trim_alpha_edge(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    remove: list[tuple[int, int]] = []
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            if alpha < 112:
                remove.append((x, y))
                continue
            if alpha < 176 and green > max(red, blue) + 8:
                remove.append((x, y))
                continue
            if alpha < 176:
                for nx in range(max(0, x - 1), min(rgba.width, x + 2)):
                    for ny in range(max(0, y - 1), min(rgba.height, y + 2)):
                        if pixels[nx, ny][3] == 0:
                            remove.append((x, y))
                            break
                    else:
                        continue
                    break
    if not remove:
        return rgba
    data = bytearray(rgba.tobytes())
    for x, y in remove:
        index = (y * rgba.width + x) * 4
        data[index : index + 4] = b"\x00\x00\x00\x00"
    return clear_transparent_rgb(Image.frombytes("RGBA", rgba.size, bytes(data)))


def remove_chroma_background(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    key = border_key(rgb)
    data = bytearray()
    for red, green, blue in rgb.getdata():
        distance = ((red - key[0]) ** 2 + (green - key[1]) ** 2 + (blue - key[2]) ** 2) ** 0.5
        if distance <= 28:
            alpha = 0
        elif distance >= 235:
            alpha = 255
        else:
            alpha = round((distance - 28) / (235 - 28) * 255)

        green_excess = green - max(red, blue)
        if green_excess > 2:
            neutral_green = max(red, blue, round((red + blue) / 2))
            green = neutral_green
            if distance < 330:
                alpha = min(alpha, round(alpha * max(0.22, distance / 360)))

        if alpha < 96:
            data.extend((0, 0, 0, 0))
        else:
            data.extend((red, green, blue, alpha))
    return trim_alpha_edge(clear_transparent_rgb(Image.frombytes("RGBA", rgb.size, bytes(data))))


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def connected_components(image: Image.Image) -> list[dict[str, Any]]:
    alpha = image.getchannel("A")
    width, height = image.size
    data = alpha.tobytes()
    visited = bytearray(width * height)
    components: list[dict[str, Any]] = []

    for start, alpha_value in enumerate(data):
        if alpha_value == 0 or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        pixels: list[int] = []
        min_x, min_y = width, height
        max_x, max_y = 0, 0
        while stack:
            current = stack.pop()
            pixels.append(current)
            x = current % width
            y = current // width
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            for nx, ny in (
                (x - 1, y - 1),
                (x, y - 1),
                (x + 1, y - 1),
                (x - 1, y),
                (x + 1, y),
                (x - 1, y + 1),
                (x, y + 1),
                (x + 1, y + 1),
            ):
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                neighbor = ny * width + nx
                if not visited[neighbor] and data[neighbor] > 0:
                    visited[neighbor] = 1
                    stack.append(neighbor)
        components.append(
            {
                "pixels": pixels,
                "area": len(pixels),
                "bbox": (min_x, min_y, max_x + 1, max_y + 1),
                "center_x": (min_x + max_x + 1) / 2,
            }
        )
    return components


def component_bounds(components: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    return (
        min(component["bbox"][0] for component in components),
        min(component["bbox"][1] for component in components),
        max(component["bbox"][2] for component in components),
        max(component["bbox"][3] for component in components),
    )


def component_frame_groups(strip: Image.Image, frame_count: int) -> list[list[dict[str, Any]]] | None:
    components = connected_components(strip)
    if not components:
        return None
    largest_area = max(component["area"] for component in components)
    seed_threshold = max(240, largest_area * 0.20)
    seeds = [component for component in components if component["area"] >= seed_threshold]
    if len(seeds) < frame_count:
        seeds = sorted(components, key=lambda component: component["area"], reverse=True)[:frame_count]
    if len(seeds) < frame_count:
        return None
    seeds = sorted(
        sorted(seeds, key=lambda component: component["area"], reverse=True)[:frame_count],
        key=lambda component: component["center_x"],
    )
    seed_ids = {id(seed) for seed in seeds}
    groups: list[list[dict[str, Any]]] = [[seed] for seed in seeds]
    noise_threshold = max(16, largest_area * 0.002)
    for component in components:
        if id(component) in seed_ids or component["area"] < noise_threshold:
            continue
        nearest_index = min(
            range(len(seeds)),
            key=lambda index: abs(seeds[index]["center_x"] - component["center_x"]),
        )
        groups[nearest_index].append(component)
    return groups


def component_group_image(strip: Image.Image, components: list[dict[str, Any]], padding: int = 8) -> Image.Image:
    width, height = strip.size
    left, top, right, bottom = component_bounds(components)
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(width, right + padding)
    bottom = min(height, bottom + padding)
    output = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
    source_pixels = strip.load()
    output_pixels = output.load()
    for component in components:
        for pixel_index in component["pixels"]:
            x = pixel_index % width
            y = pixel_index // width
            if left <= x < right and top <= y < bottom:
                output_pixels[x - left, y - top] = source_pixels[x, y]
    return clear_transparent_rgb(output)


def crop_equal_slots(strip: Image.Image, count: int) -> list[tuple[Image.Image, tuple[int, int, int, int] | None]]:
    width, height = strip.size
    frames = []
    for index in range(count):
        left = round(index * width / count)
        right = round((index + 1) * width / count)
        frame = clear_transparent_rgb(strip.crop((left, 0, right, height)).convert("RGBA"))
        frames.append((frame, alpha_bbox(frame)))
    return frames


def extract_subjects(strip: Image.Image, count: int) -> list[tuple[Image.Image, tuple[int, int, int, int] | None]]:
    groups = component_frame_groups(strip, count)
    if groups is None:
        return crop_equal_slots(strip, count)
    return [(component_group_image(strip, group), component_bounds(group)) for group in groups]


def keep_main_component(image: Image.Image, min_pixels: int = 260) -> Image.Image:
    components = connected_components(image)
    if not components:
        return image.convert("RGBA")
    main = max(components, key=lambda component: component["area"])
    keep = set(main["pixels"])
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for component in components:
        if component is main or component["area"] >= min_pixels:
            continue
        for pixel_index in component["pixels"]:
            if pixel_index in keep:
                continue
            index = pixel_index * 4
            data[index : index + 4] = b"\x00\x00\x00\x00"
    return clear_transparent_rgb(Image.frombytes("RGBA", rgba.size, bytes(data)))


def subject_to_cell(
    subject: Image.Image,
    *,
    scale: float,
    state: str,
    original_bbox: tuple[int, int, int, int] | None,
    row_bbox: tuple[int, int, int, int] | None,
) -> Image.Image:
    bbox = alpha_bbox(subject)
    if bbox is None:
        return Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    subject = subject.crop(bbox).convert("RGBA")
    resized = subject.resize(
        (max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
        Image.Resampling.LANCZOS,
    )
    cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    x = (CELL_WIDTH - resized.width) // 2
    policy = ANCHOR_POLICIES.get(state, "bottom_grounded")
    if state == "jumping" and original_bbox is not None and row_bbox is not None:
        row_top, row_bottom = row_bbox[1], row_bbox[3]
        row_span = max(1, row_bottom - row_top)
        original_center = (original_bbox[1] + original_bbox[3]) / 2
        normalized = (original_center - row_top) / row_span
        center_y = 76 + normalized * 58
        y = round(center_y - resized.height / 2)
        y = max(8, min(CELL_HEIGHT - resized.height - 8, y))
    elif policy in STABILIZED_POLICIES:
        center_y = 108 if policy == "stable_center" else 112
        y = round(center_y - resized.height / 2)
        y = max(MIN_CENTERING_EDGE, min(CELL_HEIGHT - resized.height - MIN_CENTERING_EDGE, y))
    else:
        bottom_margin = 18
        if state in {"running-right", "running-left"}:
            bottom_margin = 30
        elif state in {"idle", "waving", "waiting", "failed", "running", "review"}:
            bottom_margin = 12
        y = CELL_HEIGHT - resized.height - bottom_margin
        y = max(8, min(CELL_HEIGHT - resized.height - 8, y))
    cell.alpha_composite(resized, (x, y))
    return clear_transparent_rgb(keep_main_component(cell))


def build_row(strip: Image.Image, state: str, count: int) -> list[Image.Image]:
    subjects = extract_subjects(strip, count)
    bboxes = [alpha_bbox(subject) for subject, _ in subjects]
    visible = [bbox for bbox in bboxes if bbox is not None]
    if not visible:
        return [Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0)) for _ in subjects]
    content_w = max(bbox[2] for bbox in visible) - min(bbox[0] for bbox in visible)
    content_h = max(bbox[3] for bbox in visible) - min(bbox[1] for bbox in visible)
    scale = min((CELL_WIDTH - 28) / max(1, content_w), (CELL_HEIGHT - 32) / max(1, content_h), 1.0)
    original_bboxes = [original_bbox for _, original_bbox in subjects if original_bbox is not None]
    row_bbox = (
        (
            min(bbox[0] for bbox in original_bboxes),
            min(bbox[1] for bbox in original_bboxes),
            max(bbox[2] for bbox in original_bboxes),
            max(bbox[3] for bbox in original_bboxes),
        )
        if original_bboxes
        else None
    )
    return [
        subject_to_cell(subject, scale=scale, state=state, original_bbox=original_bbox, row_bbox=row_bbox)
        for subject, original_bbox in subjects
    ]


def save_state_frames(frames_root: Path, state: str, frames: list[Image.Image]) -> None:
    state_dir = frames_root / state
    state_dir.mkdir(parents=True, exist_ok=True)
    for old in state_dir.glob("*.png"):
        old.unlink()
    for index, frame in enumerate(frames):
        clear_transparent_rgb(frame).save(state_dir / f"{index:02d}.png")


def frame_geometry(frame: Image.Image) -> dict[str, Any]:
    bbox = alpha_bbox(frame)
    if bbox is None:
        return {
            "bbox": None,
            "cx": None,
            "cy": None,
            "w": 0,
            "h": 0,
            "edge": None,
        }
    left, top, right, bottom = bbox
    return {
        "bbox": bbox,
        "cx": (left + right) / 2,
        "cy": (top + bottom) / 2,
        "w": right - left,
        "h": bottom - top,
        "edge": {
            "left": left,
            "top": top,
            "right": CELL_WIDTH - right,
            "bottom": CELL_HEIGHT - bottom,
        },
    }


def cy_range(metrics: list[dict[str, Any]]) -> float:
    values = [item["cy"] for item in metrics if item["cy"] is not None]
    return float(max(values) - min(values)) if values else 0.0


def shift_frame(frame: Image.Image, shift_y: int) -> Image.Image:
    if shift_y == 0:
        return clear_transparent_rgb(frame)
    output = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    output.alpha_composite(frame.convert("RGBA"), (0, shift_y))
    return clear_transparent_rgb(output)


def stabilize_state_frames(frames: list[Image.Image], state: str) -> tuple[list[Image.Image], dict[str, Any]]:
    policy = ANCHOR_POLICIES.get(state, "bottom_grounded")
    before = [frame_geometry(frame) for frame in frames]
    target_cy = None
    shifts = [0 for _ in frames]
    stabilized = [clear_transparent_rgb(frame) for frame in frames]
    if policy in STABILIZED_POLICIES:
        centers = [item["cy"] for item in before if item["cy"] is not None]
        if centers:
            target_cy = float(median(centers))
            shifted = []
            for index, frame in enumerate(frames):
                bbox = alpha_bbox(frame)
                if bbox is None:
                    shifted.append(clear_transparent_rgb(frame))
                    continue
                desired = round(target_cy - before[index]["cy"])
                min_shift = MIN_CENTERING_EDGE - bbox[1]
                max_shift = CELL_HEIGHT - bbox[3] - MIN_CENTERING_EDGE
                shift_y = max(min_shift, min(max_shift, desired))
                shifts[index] = shift_y
                shifted.append(shift_frame(frame, shift_y))
            stabilized = shifted
    after = [frame_geometry(frame) for frame in stabilized]
    return stabilized, {
        "anchor_policy": policy,
        "target_cy": target_cy,
        "before_cy_range": round(cy_range(before), 2),
        "after_cy_range": round(cy_range(after), 2),
        "frames": [
            {
                "frame": f"{index:02d}.png",
                "shift_y": shifts[index],
                "before": before[index],
                "after": after[index],
            }
            for index in range(len(frames))
        ],
    }


def build_frames_from_row_strips(
    *,
    source_dir: Path,
    transparent_dir: Path,
    frames_root: Path,
    force: bool = False,
) -> None:
    transparent_dir.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)
    centering_report: dict[str, Any] = {"states": {}}
    for state in STATE_ORDER:
        count = ROW_FRAME_COUNTS[state]
        source_path = source_dir / f"{state}.png"
        transparent_path = transparent_dir / f"{state}.png"
        if not source_path.is_file():
            raise FileNotFoundError(f"missing row strip for {state}: {source_path}")
        if transparent_path.is_file() and not force:
            strip = Image.open(transparent_path).convert("RGBA")
        else:
            strip = remove_chroma_background(Image.open(source_path))
            strip.save(transparent_path)
        frames = build_row(strip, state, count)
        frames, report = stabilize_state_frames(frames, state)
        centering_report["states"][state] = report
        save_state_frames(frames_root, state, frames)
    manifest = default_frame_manifest(
        source_dir,
        centering_policy="component-centered-state-baseline",
        cleanup_policy="chroma-key-despill-low-alpha-trim",
    )
    write_json(frames_root / "frames-manifest.json", manifest.to_dict())
    write_json(frames_root / "centering-report.json", centering_report)
