"""Codex pet output contract and default state sheet."""

from __future__ import annotations

from dataclasses import dataclass


CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_COLUMNS = 8
ATLAS_ROWS = 9
ATLAS_WIDTH = CELL_WIDTH * ATLAS_COLUMNS
ATLAS_HEIGHT = CELL_HEIGHT * ATLAS_ROWS

STATE_ORDER = [
    "idle",
    "running-right",
    "running-left",
    "waving",
    "jumping",
    "failed",
    "waiting",
    "running",
    "review",
]

ROW_FRAME_COUNTS = {
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

ROW_FRAME_DURATIONS_MS = {
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
class OutputContract:
    cell_width: int = CELL_WIDTH
    cell_height: int = CELL_HEIGHT
    columns: int = ATLAS_COLUMNS
    rows: int = ATLAS_ROWS
    atlas_width: int = ATLAS_WIDTH
    atlas_height: int = ATLAS_HEIGHT
    states: tuple[str, ...] = tuple(STATE_ORDER)


DEFAULT_OUTPUT_CONTRACT = OutputContract()


def expected_frame_count(state: str) -> int:
    try:
        return ROW_FRAME_COUNTS[state]
    except KeyError as exc:
        raise ValueError(f"unknown Codex pet state: {state}") from exc


def expected_frame_durations_ms(state: str) -> list[int]:
    try:
        return list(ROW_FRAME_DURATIONS_MS[state])
    except KeyError as exc:
        raise ValueError(f"unknown Codex pet state: {state}") from exc
