"""Regenerate deterministic synthetic v2 direction-strip test fixtures.

These images are deliberately geometric test data, not a fallback pet renderer.
They exist only to exercise extraction, registration, assembly, and package
validation without private source photos or provider calls.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic-row-strips"
BACKGROUND = (0, 255, 0)
BODY = (235, 216, 184)
MARKING = (117, 76, 45)
INK = (22, 19, 17)


def draw_pose(image: Image.Image, *, center_x: int, center_y: int, angle: float) -> None:
    draw = ImageDraw.Draw(image)
    draw.ellipse((center_x - 43, center_y - 28, center_x + 43, center_y + 50), fill=BODY)
    head_x = center_x + round(math.sin(math.radians(angle)) * 11)
    head_y = center_y - 45 + round((1 - math.cos(math.radians(angle))) * 5)
    draw.ellipse((head_x - 34, head_y - 31, head_x + 34, head_y + 35), fill=BODY)
    draw.polygon(
        [(head_x - 27, head_y - 21), (head_x - 20, head_y - 48), (head_x - 7, head_y - 25)],
        fill=BODY,
    )
    draw.polygon(
        [(head_x + 27, head_y - 21), (head_x + 20, head_y - 48), (head_x + 7, head_y - 25)],
        fill=BODY,
    )
    direction_x = round(math.sin(math.radians(angle)) * 15)
    direction_y = round(-math.cos(math.radians(angle)) * 9)
    draw.ellipse(
        (head_x - 13 + direction_x, head_y - 4 + direction_y, head_x - 6 + direction_x, head_y + 3 + direction_y),
        fill=INK,
    )
    draw.ellipse(
        (head_x + 6 + direction_x, head_y - 4 + direction_y, head_x + 13 + direction_x, head_y + 3 + direction_y),
        fill=INK,
    )
    draw.ellipse(
        (head_x - 5 + direction_x, head_y + 9 + direction_y, head_x + 5 + direction_x, head_y + 17 + direction_y),
        fill=MARKING,
    )
    marking_x = center_x - 25 if angle < 180 else center_x + 10
    draw.ellipse((marking_x, center_y - 5, marking_x + 24, center_y + 25), fill=MARKING)


def make_strip(path: Path, directions: list[float]) -> None:
    slot_width = 192
    image = Image.new("RGB", (slot_width * len(directions), 240), BACKGROUND)
    for index, direction in enumerate(directions):
        draw_pose(
            image,
            center_x=index * slot_width + slot_width // 2,
            center_y=137,
            angle=direction,
        )
    image.save(path)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    make_strip(ROOT / "look-cardinals.png", [0, 90, 180, 270])
    make_strip(ROOT / "look-row-9.png", [index * 22.5 for index in range(8)])
    make_strip(ROOT / "look-row-10.png", [180 + index * 22.5 for index in range(8)])


if __name__ == "__main__":
    main()
