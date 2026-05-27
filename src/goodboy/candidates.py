"""Baseline candidate planning and selection."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from .adapters import get_capabilities
from .ingest import SOURCE_CARD, load_source_images
from .jsonio import read_json, write_json
from .schemas import CharacterCard, SourceCard, StyleCandidate, utc_now


CANDIDATE_INDEX = "candidates/baseline-candidates.json"
SELECTED_CANDIDATE = "character/selected-candidate.json"
CHARACTER_CARD = "character/character-card.json"
SELECTED_BASELINE = "character/selected-baseline.png"


BASELINE_VARIATIONS = [
    {
        "id": "soft-lifelike",
        "summary": "soft lifelike plush-realistic Codex pet, warm eyes, readable fur, gentle desktop mascot proportions",
        "delta": "balanced realism and mascot friendliness",
    },
    {
        "id": "toy-plush",
        "summary": "slightly more plush/toy-like, rounded silhouette, extra approachable expression, clean small-size readability",
        "delta": "more toy-like and forgiving at pet size",
    },
    {
        "id": "photo-faithful",
        "summary": "closest to the source pet identity, preserving face proportions, fur texture, markings, and accessories",
        "delta": "prioritize identity fidelity over stylization",
    },
    {
        "id": "storybook-3d",
        "summary": "gentle storybook 3D character, expressive eyes, charming pose, still lifelike enough to feel personal",
        "delta": "more whimsical and animated",
    },
    {
        "id": "sticker-soft",
        "summary": "clean sticker-like soft render, crisp silhouette, simplified details, high readability in small cells",
        "delta": "simplify detail for robust animation rows",
    },
    {
        "id": "senior-sweet",
        "summary": "sweet gentle companion style, warm expression, softer aging cues, cozy and affectionate energy",
        "delta": "emphasize age/personality warmth where appropriate",
    },
]


def plan_baseline_candidates(
    *,
    project_dir: Path,
    provider: str,
    model_alias: str,
    count: int = 6,
    render_sheet: bool = True,
) -> list[StyleCandidate]:
    get_capabilities(provider)
    card = load_or_empty_source_card(project_dir)
    source_images = load_source_images(project_dir)
    source_paths = [image.path for image in source_images]
    candidates: list[StyleCandidate] = []
    selected_variations = BASELINE_VARIATIONS[: max(1, min(count, len(BASELINE_VARIATIONS)))]
    for index, variation in enumerate(selected_variations, start=1):
        candidate_id = f"baseline-{index:03d}"
        candidate_dir = project_dir / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = candidate_dir / "prompt.md"
        prompt_path.write_text(candidate_prompt(card, variation), encoding="utf-8")
        candidate = StyleCandidate(
            id=candidate_id,
            image_path=None,
            prompt_path=str(prompt_path.relative_to(project_dir)),
            provider=provider,
            model=model_alias,
            source_images=source_paths,
            style_summary=variation["summary"],
            character_delta=variation["delta"],
            strengths=["planned baseline candidate with recorded style intent"],
            risks=["image has not been generated or reviewed yet"],
        )
        write_json(candidate_dir / "candidate.json", candidate.to_dict())
        candidates.append(candidate)
    write_json(project_dir / CANDIDATE_INDEX, {"candidates": [item.to_dict() for item in candidates]})
    if render_sheet:
        build_candidate_contact_sheet(project_dir=project_dir)
    return candidates


def candidate_prompt(card: SourceCard, variation: dict[str, str]) -> str:
    source_summary = "; ".join(
        item
        for item in [
            f"species: {card.species}" if card.species else "",
            f"breed/type: {card.breed_or_type}" if card.breed_or_type else "",
            f"face: {card.face_traits}" if card.face_traits else "",
            f"eyes: {card.eyes}" if card.eyes else "",
            f"fur: {card.fur}" if card.fur else "",
            f"tail: {card.tail}" if card.tail else "",
            f"props: {card.props}" if card.props else "",
            f"user notes: {card.user_notes}" if card.user_notes else "",
        ]
        if item
    )
    must_keep = ", ".join(card.must_keep) if card.must_keep else "source pet identity"
    avoid = ", ".join(card.avoid) if card.avoid else "text, logos, scenery, shadows"
    return (
        "Generate one baseline character image for a future Codex pet.\n\n"
        f"Variation: {variation['id']}.\n"
        f"Style summary: {variation['summary']}.\n"
        f"Character delta: {variation['delta']}.\n"
        f"Source card summary: {source_summary or 'manual source card details are not filled yet; rely on attached source images'}.\n"
        f"Must keep: {must_keep}.\n"
        f"Avoid: {avoid}.\n\n"
        "Output should be a single full-body pet character on a flat removable chroma-key background, "
        "with no text, no scenery, no floor shadow, and generous padding. Preserve identity over novelty."
    )


def select_baseline_candidate(
    *,
    project_dir: Path,
    candidate_id: str,
    image_path: Path | None = None,
    notes: str = "",
) -> CharacterCard:
    candidate_path = project_dir / "candidates" / candidate_id / "candidate.json"
    if not candidate_path.is_file():
        raise FileNotFoundError(f"missing candidate manifest: {candidate_path}")
    raw = read_json(candidate_path)
    raw["selected"] = True
    raw["selection_notes"] = notes
    raw["selected_at"] = utc_now()
    selected_baseline: str | None = raw.get("image_path")
    if image_path is not None:
        source = image_path.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"selected baseline image does not exist: {source}")
        target = project_dir / SELECTED_BASELINE
        target.parent.mkdir(parents=True, exist_ok=True)
        normalize_baseline_image(source, target)
        selected_baseline = str(target.relative_to(project_dir))
        raw["image_path"] = selected_baseline
    write_json(candidate_path, raw)
    update_candidate_index(project_dir, candidate_id, raw)
    build_candidate_contact_sheet(project_dir=project_dir)

    source_card = load_or_empty_source_card(project_dir)
    stable_traits = [
        item
        for item in [
            source_card.species,
            source_card.breed_or_type,
            source_card.face_traits,
            source_card.fur,
            source_card.tail,
            source_card.props,
            source_card.user_notes,
        ]
        if item
    ]
    character = CharacterCard(
        canonical_name=project_dir.name,
        one_sentence_identity=raw["style_summary"],
        stable_traits=stable_traits,
        style=raw["style_summary"],
        props=source_card.props,
        do_not_change=source_card.must_keep,
        selected_baseline_image=selected_baseline,
        provider_notes={raw["provider"]: raw["model"]},
    )
    write_json(project_dir / SELECTED_CANDIDATE, raw)
    write_json(project_dir / CHARACTER_CARD, character.to_dict())
    return character


def normalize_baseline_image(source: Path, target: Path) -> None:
    """Save selected baseline as PNG even if a provider returns another format."""
    try:
        with Image.open(source) as image:
            image.convert("RGBA").save(target)
    except Exception:
        shutil.copy2(source, target)


def update_candidate_index(project_dir: Path, selected_id: str, selected_raw: dict[str, object]) -> None:
    index_path = project_dir / CANDIDATE_INDEX
    if not index_path.is_file():
        write_json(index_path, {"candidates": [selected_raw]})
        return
    index = read_json(index_path)
    candidates = []
    found = False
    for item in index.get("candidates", []):
        item = dict(item)
        if item.get("id") == selected_id:
            item.update(selected_raw)
            found = True
        else:
            item["selected"] = False
            item["selection_notes"] = ""
        candidates.append(item)
    if not found:
        candidates.append(selected_raw)
    write_json(index_path, {"candidates": candidates})


def build_candidate_contact_sheet(
    *,
    project_dir: Path,
    output_path: Path | None = None,
    columns: int = 3,
) -> Path:
    index_path = project_dir / CANDIDATE_INDEX
    if not index_path.is_file():
        raise FileNotFoundError(f"missing candidate index: {index_path}")
    candidates = read_json(index_path).get("candidates", [])
    if not candidates:
        raise ValueError("candidate index contains no candidates")
    output = output_path or (project_dir / "candidates" / "contact-sheet.png")
    columns = max(1, columns)
    cell_width = 360
    cell_height = 330
    rows = (len(candidates) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    for index, candidate in enumerate(candidates):
        left = (index % columns) * cell_width
        top = (index // columns) * cell_height
        draw.rectangle((left, top, left + cell_width - 1, top + cell_height - 1), outline=(210, 210, 205))
        render_candidate_tile(sheet, draw, project_dir, candidate, left, top, cell_width, cell_height)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return output


def render_candidate_tile(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    project_dir: Path,
    candidate: dict[str, object],
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    image_path = candidate.get("image_path")
    image_box = (left + 70, top + 18, left + width - 70, top + 218)
    selected = bool(candidate.get("selected"))
    if image_path:
        path = project_dir / str(image_path)
        if path.is_file():
            with Image.open(path) as image:
                thumb = image.convert("RGBA")
                thumb.thumbnail((image_box[2] - image_box[0], image_box[3] - image_box[1]), Image.Resampling.LANCZOS)
                x = image_box[0] + ((image_box[2] - image_box[0]) - thumb.width) // 2
                y = image_box[1] + ((image_box[3] - image_box[1]) - thumb.height) // 2
                background = Image.new("RGB", thumb.size, (250, 250, 248))
                background.paste(thumb, mask=thumb.split()[-1])
                sheet.paste(background, (x, y))
        else:
            draw_placeholder(draw, image_box)
    else:
        draw_placeholder(draw, image_box)
    title = str(candidate.get("id", "candidate"))
    if selected:
        title = f"{title} selected"
    draw.text((left + 18, top + 235), title, fill=(20, 20, 20))
    summary = str(candidate.get("style_summary", ""))
    for line_index, line in enumerate(wrap_text(summary, 44)[:4]):
        draw.text((left + 18, top + 258 + (line_index * 16)), line, fill=(65, 65, 65))


def draw_placeholder(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rectangle(box, fill=(232, 232, 228), outline=(190, 190, 185))
    draw.text((box[0] + 34, box[1] + 88), "planned image", fill=(100, 100, 96))


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def load_or_empty_source_card(project_dir: Path) -> SourceCard:
    path = project_dir / SOURCE_CARD
    if not path.is_file():
        return SourceCard()
    return SourceCard.from_dict(read_json(path))
