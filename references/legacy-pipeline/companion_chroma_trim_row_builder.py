#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image


CELL_W = 192
CELL_H = 208
ROW_COUNTS = {
    "idle": 6,
    "running-right": 8,
    "running-left": 8,
    "waving": 4,
    "jumping": 5,
    "failed": 8,
    "waiting": 6,
    "running": 6,
    "review": 6,
}


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index : index + 3] = b"\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def border_key(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    samples = []
    width, height = rgb.size
    for x in range(width):
        samples.append(rgb.getpixel((x, 0)))
        samples.append(rgb.getpixel((x, height - 1)))
    for y in range(height):
        samples.append(rgb.getpixel((0, y)))
        samples.append(rgb.getpixel((width - 1, y)))
    samples.sort()
    return samples[len(samples) // 2]


def remove_green_screen(image: Image.Image) -> Image.Image:
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
            # Generated fur often keeps green RGB in antialiased edge pixels.
            # Neutralize that spill before compositing so the edge reads as fur.
            neutral_green = max(red, blue, round((red + blue) / 2))
            green = neutral_green
            if distance < 330:
                alpha = min(alpha, round(alpha * max(0.22, distance / 360)))

        if alpha < 96:
            data.extend((0, 0, 0, 0))
        else:
            data.extend((red, green, blue, alpha))
    return trim_alpha_edge(clear_transparent_rgb(Image.frombytes("RGBA", rgb.size, bytes(data))))


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


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def keep_main_component(image: Image.Image, min_pixels: int = 260) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    width, height = rgba.size
    mask = alpha.load()
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []

    for y in range(height):
        for x in range(width):
            if (x, y) in visited or mask[x, y] == 0:
                continue
            stack = [(x, y)]
            component: list[tuple[int, int]] = []
            visited.add((x, y))
            while stack:
                cx, cy = stack.pop()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= width
                        or ny >= height
                        or (nx, ny) in visited
                        or mask[nx, ny] == 0
                    ):
                        continue
                    visited.add((nx, ny))
                    stack.append((nx, ny))
            components.append(component)

    if not components:
        return rgba
    main = max(components, key=len)
    keep = set(main)
    remove = [
        pixel
        for component in components
        if len(component) < len(main) or len(component) < min_pixels
        for pixel in component
        if pixel not in keep
    ]
    if not remove:
        return rgba
    data = bytearray(rgba.tobytes())
    for x, y in remove:
        index = (y * width + x) * 4
        data[index : index + 4] = b"\x00\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def crop_equal_slots(strip: Image.Image, count: int) -> list[Image.Image]:
    width, height = strip.size
    frames = []
    for index in range(count):
        left = round(index * width / count)
        right = round((index + 1) * width / count)
        frames.append(clear_transparent_rgb(strip.crop((left, 0, right, height)).convert("RGBA")))
    return frames


def slot_to_cell(slot: Image.Image, scale: float) -> Image.Image:
    resized = slot.resize(
        (max(1, round(slot.width * scale)), max(1, round(slot.height * scale))),
        Image.Resampling.LANCZOS,
    )
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    bbox = alpha_bbox(resized)
    if bbox is None:
        return cell
    # Preserve the generated strip's within-slot pose placement, while centering
    # the slot as a whole inside the Codex cell.
    x = (CELL_W - resized.width) // 2
    y = (CELL_H - resized.height) // 2
    cell.alpha_composite(resized, (x, y))
    return clear_transparent_rgb(keep_main_component(cell))


def save_state(frames_root: Path, state: str, frames: list[Image.Image]) -> None:
    state_dir = frames_root / state
    state_dir.mkdir(parents=True, exist_ok=True)
    for old in state_dir.glob("*.png"):
        old.unlink()
    for index, frame in enumerate(frames):
        frame.save(state_dir / f"{index:02d}.png")


def build_row(strip: Image.Image, count: int) -> list[Image.Image]:
    slots = crop_equal_slots(strip, count)
    bboxes = [alpha_bbox(slot) for slot in slots]
    visible = [bbox for bbox in bboxes if bbox is not None]
    if not visible:
        return [Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)) for _ in slots]
    max_right = max(bbox[2] for bbox in visible)
    min_left = min(bbox[0] for bbox in visible)
    max_bottom = max(bbox[3] for bbox in visible)
    min_top = min(bbox[1] for bbox in visible)
    content_w = max_right - min_left
    content_h = max_bottom - min_top
    scale = min((CELL_W - 18) / max(1, content_w), (CELL_H - 18) / max(1, content_h), 1.0)
    return [slot_to_cell(slot, scale) for slot in slots]


def main() -> None:
    run_dir = Path(__file__).resolve().parents[1]
    version = os.environ.get("COMPANION_ROW_STRIP_VERSION", "v5")
    strips_dir = run_dir / "generated" / f"{version}-transparent-strips"
    source_dir = run_dir / "generated" / f"{version}-row-strips"
    frames_root = run_dir / "frames"
    for state, count in ROW_COUNTS.items():
        transparent_path = strips_dir / f"{state}.png"
        source_path = source_dir / f"{state}.png"
        if transparent_path.is_file():
            strip = Image.open(transparent_path).convert("RGBA")
        else:
            strip = remove_green_screen(Image.open(source_path))
            strips_dir.mkdir(parents=True, exist_ok=True)
            strip.save(transparent_path)
        save_state(frames_root, state, build_row(strip, count))

    manifest = {
        "chroma_key": {"hex": "#00ff00", "rgb": [0, 255, 0]},
        "source": str(source_dir),
        "rows": [
            {"state": state, "frames": count, "method": "components"}
            for state, count in ROW_COUNTS.items()
        ],
    }
    (frames_root / "frames-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
