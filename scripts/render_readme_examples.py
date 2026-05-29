#!/usr/bin/env python3
"""Render public README animation examples from Codex pet spritesheets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


CELL_WIDTH = 192
CELL_HEIGHT = 208

STATE_ROWS = {
    "idle": 0,
    "running-right": 1,
    "running-left": 2,
    "waving": 3,
    "jumping": 4,
    "failed": 5,
    "waiting": 6,
    "running": 7,
    "review": 8,
}

STATE_DURATIONS = {
    "idle": [280, 110, 110, 140, 140, 320],
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [140, 140, 140, 280],
    "jumping": [140, 140, 140, 140, 280],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 220],
    "review": [150, 150, 150, 150, 150, 280],
}


@dataclass(frozen=True)
class Example:
    name: str
    spritesheet: Path
    state: str
    output: Path


def scaled_durations(state: str, speed_scale: float) -> list[int]:
    return [max(20, round(duration * speed_scale)) for duration in STATE_DURATIONS[state]]


def extract_state_frames(spritesheet: Path, state: str) -> list[Image.Image]:
    if not spritesheet.is_file():
        raise SystemExit(f"Missing spritesheet: {spritesheet}")
    row = STATE_ROWS[state]
    expected = len(STATE_DURATIONS[state])
    sheet = Image.open(spritesheet).convert("RGBA")
    frames = []
    for index in range(expected):
        left = index * CELL_WIDTH
        top = row * CELL_HEIGHT
        frames.append(sheet.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT)))
    return frames


def flatten_on_white(frame: Image.Image) -> Image.Image:
    background = Image.new("RGBA", frame.size, (255, 255, 255, 255))
    background.alpha_composite(frame)
    return background


def save_gif(frames: list[Image.Image], durations: list[int], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    prepared = []
    for frame in frames:
        rgb = flatten_on_white(frame).convert("RGB")
        paletted = rgb.convert(
            "P",
            palette=Image.Palette.ADAPTIVE,
            colors=255,
            dither=Image.Dither.NONE,
        )
        paletted.info["disposal"] = 2
        prepared.append(paletted)
    prepared[0].save(
        output,
        save_all=True,
        append_images=prepared[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )


def render(example: Example, speed_scale: float) -> None:
    frames = extract_state_frames(example.spritesheet, example.state)
    durations = scaled_durations(example.state, speed_scale)
    save_gif(frames, durations, example.output)
    written = Image.open(example.output)
    actual_frames = getattr(written, "n_frames", 1)
    if actual_frames != len(frames):
        raise SystemExit(f"{example.output} has {actual_frames} frames; expected {len(frames)}")
    print(f"wrote {example.output} ({actual_frames} frames)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--napoleon-spritesheet", required=True)
    parser.add_argument("--millie-spritesheet", required=True)
    parser.add_argument("--shoulder-cat-spritesheet", required=True)
    parser.add_argument("--output-dir", default="assets/examples")
    parser.add_argument(
        "--speed-scale",
        type=float,
        default=1.6,
        help="Multiplier applied to QA preview durations for slower public README demos.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    examples = [
        Example(
            name="Napoleon",
            spritesheet=Path(args.napoleon_spritesheet).expanduser(),
            state="running-left",
            output=output_dir / "napoleon-running-left.gif",
        ),
        Example(
            name="Millie",
            spritesheet=Path(args.millie_spritesheet).expanduser(),
            state="jumping",
            output=output_dir / "millie-jumping.gif",
        ),
        Example(
            name="Shoulder Cat",
            spritesheet=Path(args.shoulder_cat_spritesheet).expanduser(),
            state="waiting",
            output=output_dir / "shoulder-cat-waiting.gif",
        ),
    ]
    for example in examples:
        render(example, args.speed_scale)


if __name__ == "__main__":
    main()
