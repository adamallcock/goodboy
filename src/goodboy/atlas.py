"""Atlas composition, validation, and visual QA media."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .contracts import (
    ATLAS_HEIGHT,
    ATLAS_WIDTH,
    CELL_HEIGHT,
    CELL_WIDTH,
    ROW_FRAME_DURATIONS_MS,
    ROW_FRAME_COUNTS,
    STATE_ORDER,
)
from .raster import clear_transparent_rgb
from .schemas import ValidationReport


def compose_atlas(frames_root: Path, *, output_png: Path, output_webp: Path | None = None) -> None:
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    for row, state in enumerate(STATE_ORDER):
        for column in range(ROW_FRAME_COUNTS[state]):
            frame_path = frames_root / state / f"{column:02d}.png"
            if not frame_path.is_file():
                raise FileNotFoundError(f"missing frame: {frame_path}")
            frame = Image.open(frame_path).convert("RGBA")
            if frame.size != (CELL_WIDTH, CELL_HEIGHT):
                raise ValueError(f"frame {frame_path} has size {frame.size}, expected {(CELL_WIDTH, CELL_HEIGHT)}")
            atlas.alpha_composite(clear_transparent_rgb(frame), (column * CELL_WIDTH, row * CELL_HEIGHT))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    clear_transparent_rgb(atlas).save(output_png)
    if output_webp is not None:
        output_webp.parent.mkdir(parents=True, exist_ok=True)
        clear_transparent_rgb(atlas).save(
            output_webp,
            format="WEBP",
            lossless=True,
            quality=100,
            method=6,
            exact=True,
        )


def validate_atlas(path: Path) -> ValidationReport:
    with Image.open(path) as opened:
        image_format = opened.format or ""
        image = opened.convert("RGBA")
    errors: list[str] = []
    warnings: list[str] = []
    if image.size != (ATLAS_WIDTH, ATLAS_HEIGHT):
        errors.append(f"atlas size {image.size} != {(ATLAS_WIDTH, ATLAS_HEIGHT)}")
    transparent_rgb_residue = 0
    for red, green, blue, alpha in image.getdata():
        if alpha == 0 and (red or green or blue):
            transparent_rgb_residue += 1
    if transparent_rgb_residue:
        errors.append(f"{transparent_rgb_residue} transparent pixels have nonzero RGB")

    cells: list[dict[str, object]] = []
    for row, state in enumerate(STATE_ORDER):
        used_count = ROW_FRAME_COUNTS[state]
        for column in range(8):
            cell = image.crop(
                (
                    column * CELL_WIDTH,
                    row * CELL_HEIGHT,
                    (column + 1) * CELL_WIDTH,
                    (row + 1) * CELL_HEIGHT,
                )
            )
            nontransparent = sum(1 for *_, alpha in cell.getdata() if alpha)
            used = column < used_count
            if used and nontransparent == 0:
                errors.append(f"{state} column {column} is empty")
            if not used and nontransparent != 0:
                errors.append(f"{state} unused column {column} is not transparent")
            cells.append(
                {
                    "state": state,
                    "row": row,
                    "column": column,
                    "used": used,
                    "nontransparent_pixels": nontransparent,
                }
            )
    return ValidationReport(
        ok=not errors,
        file=str(path),
        format=image_format,
        mode=image.mode,
        width=image.width,
        height=image.height,
        transparent_rgb_residue_pixels=transparent_rgb_residue,
        errors=errors,
        warnings=warnings,
        cells=cells,
    )


def make_contact_sheet(atlas_path: Path, output_path: Path) -> None:
    atlas = Image.open(atlas_path).convert("RGBA")
    cell_border = 2
    label_h = 20
    sheet_w = ATLAS_WIDTH + cell_border * 9
    sheet_h = ATLAS_HEIGHT + label_h * 9 + cell_border * 10
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for row, state in enumerate(STATE_ORDER):
        row_y = row * (CELL_HEIGHT + label_h + cell_border) + cell_border
        draw.rectangle((0, row_y, sheet_w, row_y + label_h), fill=(0, 0, 0))
        draw.text((6, row_y + 4), f"row {row} {state}", fill=(255, 255, 255))
        draw.text((sheet_w - 80, row_y + 4), f"{ROW_FRAME_COUNTS[state]} frames", fill=(255, 255, 255))
        for column in range(8):
            x = column * (CELL_WIDTH + cell_border) + cell_border
            y = row_y + label_h + cell_border
            cell = atlas.crop((column * CELL_WIDTH, row * CELL_HEIGHT, (column + 1) * CELL_WIDTH, (row + 1) * CELL_HEIGHT))
            bg = checkerboard((CELL_WIDTH, CELL_HEIGHT))
            bg.alpha_composite(cell)
            sheet.paste(bg.convert("RGB"), (x, y))
            outline = (0, 120, 65) if column < ROW_FRAME_COUNTS[state] else (180, 0, 0)
            draw.rectangle((x, y, x + CELL_WIDTH - 1, y + CELL_HEIGHT - 1), outline=outline, width=2)
            draw.text((x + 4, y + 4), str(column), fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def checkerboard(size: tuple[int, int], block: int = 16) -> Image.Image:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], block):
        for x in range(0, size[0], block):
            if (x // block + y // block) % 2:
                draw.rectangle((x, y, x + block - 1, y + block - 1), fill=(230, 230, 230, 255))
    return image


def render_animation_previews(frames_root: Path, output_dir: Path, duration_ms: int | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for state in STATE_ORDER:
        frames = []
        for path in sorted((frames_root / state).glob("*.png")):
            frame = checkerboard((CELL_WIDTH, CELL_HEIGHT))
            frame.alpha_composite(Image.open(path).convert("RGBA"))
            frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE))
        if frames:
            durations = duration_ms if duration_ms is not None else ROW_FRAME_DURATIONS_MS[state]
            frames[0].save(
                output_dir / f"{state}.gif",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2,
            )
