"""Versioned Codex pet output contracts.

Goodboy treats the 8x9 v1 layout as an import and migration surface. New
projects target the 8x11 v2 contract used by the current Codex pet renderer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_COLUMNS = 8
STANDARD_ATLAS_ROWS = 9
V2_ATLAS_ROWS = 11
STANDARD_ATLAS_WIDTH = CELL_WIDTH * ATLAS_COLUMNS
STANDARD_ATLAS_HEIGHT = CELL_HEIGHT * STANDARD_ATLAS_ROWS
V2_ATLAS_WIDTH = CELL_WIDTH * ATLAS_COLUMNS
V2_ATLAS_HEIGHT = CELL_HEIGHT * V2_ATLAS_ROWS

# Public aliases describe the default contract. Code that intentionally builds
# the rows 0-8 intermediate must use STANDARD_ATLAS_* explicitly.
ATLAS_ROWS = V2_ATLAS_ROWS
ATLAS_WIDTH = V2_ATLAS_WIDTH
ATLAS_HEIGHT = V2_ATLAS_HEIGHT

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

LOOK_ROW_STATES = [
    "look-000-to-157.5",
    "look-180-to-337.5",
]

V2_STATE_ORDER = [*STATE_ORDER, *LOOK_ROW_STATES]

LOOK_DIRECTIONS = [
    "000",
    "022.5",
    "045",
    "067.5",
    "090",
    "112.5",
    "135",
    "157.5",
    "180",
    "202.5",
    "225",
    "247.5",
    "270",
    "292.5",
    "315",
    "337.5",
]

LOOK_ROW_DIRECTIONS = {
    LOOK_ROW_STATES[0]: LOOK_DIRECTIONS[:8],
    LOOK_ROW_STATES[1]: LOOK_DIRECTIONS[8:],
}

V2_NEUTRAL_LOOK_FRAME = (0, 6)

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
    LOOK_ROW_STATES[0]: 8,
    LOOK_ROW_STATES[1]: 8,
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
    LOOK_ROW_STATES[0]: [100] * 8,
    LOOK_ROW_STATES[1]: [100] * 8,
}


@dataclass(frozen=True)
class OutputContract:
    contract_id: str
    contract_version: str
    sprite_version_number: int
    cell_width: int
    cell_height: int
    columns: int
    rows: int
    atlas_width: int
    atlas_height: int
    states: tuple[str, ...]
    look_directions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


V1_OUTPUT_CONTRACT = OutputContract(
    contract_id="codex-pet-v1",
    contract_version="1.0",
    sprite_version_number=1,
    cell_width=CELL_WIDTH,
    cell_height=CELL_HEIGHT,
    columns=ATLAS_COLUMNS,
    rows=STANDARD_ATLAS_ROWS,
    atlas_width=STANDARD_ATLAS_WIDTH,
    atlas_height=STANDARD_ATLAS_HEIGHT,
    states=tuple(STATE_ORDER),
)

V2_OUTPUT_CONTRACT = OutputContract(
    contract_id="codex-pet-v2",
    contract_version="2.0",
    sprite_version_number=2,
    cell_width=CELL_WIDTH,
    cell_height=CELL_HEIGHT,
    columns=ATLAS_COLUMNS,
    rows=V2_ATLAS_ROWS,
    atlas_width=V2_ATLAS_WIDTH,
    atlas_height=V2_ATLAS_HEIGHT,
    states=tuple(V2_STATE_ORDER),
    look_directions=tuple(LOOK_DIRECTIONS),
)

CONTRACT_REGISTRY = {
    V1_OUTPUT_CONTRACT.contract_id: V1_OUTPUT_CONTRACT,
    V2_OUTPUT_CONTRACT.contract_id: V2_OUTPUT_CONTRACT,
}

DEFAULT_OUTPUT_CONTRACT = V2_OUTPUT_CONTRACT


def get_output_contract(contract_id: str = DEFAULT_OUTPUT_CONTRACT.contract_id) -> OutputContract:
    try:
        return CONTRACT_REGISTRY[contract_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown Codex pet contract `{contract_id}`; expected one of {sorted(CONTRACT_REGISTRY)}"
        ) from exc


def contract_from_dict(raw: dict[str, Any] | None) -> OutputContract:
    if not raw:
        return V1_OUTPUT_CONTRACT
    contract_id = raw.get("contract_id")
    if isinstance(contract_id, str) and contract_id in CONTRACT_REGISTRY:
        return CONTRACT_REGISTRY[contract_id]
    sprite_version = raw.get("sprite_version_number")
    if sprite_version == 2 or raw.get("rows") == V2_ATLAS_ROWS or raw.get("atlas_height") == V2_ATLAS_HEIGHT:
        return V2_OUTPUT_CONTRACT
    return V1_OUTPUT_CONTRACT


def detect_contract_from_dimensions(width: int, height: int) -> OutputContract:
    for contract in CONTRACT_REGISTRY.values():
        if (width, height) == (contract.atlas_width, contract.atlas_height):
            return contract
    raise ValueError(
        f"unsupported atlas dimensions {(width, height)}; expected "
        f"{(STANDARD_ATLAS_WIDTH, STANDARD_ATLAS_HEIGHT)} or {(V2_ATLAS_WIDTH, V2_ATLAS_HEIGHT)}"
    )


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
