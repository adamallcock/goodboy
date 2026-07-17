"""Baseline candidate planning and selection."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from .adapters import get_capabilities
from .identity import (
    identity_prompt_block,
    load_identity_profile,
    prepare_provider_derivatives,
    provider_reference_images,
)
from .ingest import SOURCE_CARD, load_source_images
from .jsonio import read_json, write_json
from .raster import alpha_bbox, remove_chroma_background
from .schemas import CharacterCard, SourceCard, StyleCandidate, utc_now


CANDIDATE_INDEX = "candidates/baseline-candidates.json"
SELECTED_CANDIDATE = "character/selected-candidate.json"
CHARACTER_CARD = "character/character-card.json"
SELECTED_BASELINE = "character/selected-baseline.png"
IDENTITY_ANCHOR = "character/identity-anchor.png"
IDENTITY_ANCHOR_RECORD = "character/identity-anchor.json"
STYLED_BASELINE_RECORD = "character/styled-baseline.json"


CONTROLLED_LIKENESS_STYLE = (
    "source-faithful neutral identity study with natural anatomy, coat volume, and "
    "age cues; minimal mascot stylization; keep camera, lighting, pose, framing, "
    "materials, and rendering treatment fixed across candidates"
)

LIKENESS_VARIATIONS = [
    {
        "id": "identity-balanced",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": "literal balanced interpretation of every confirmed identity trait",
    },
    {
        "id": "identity-gestalt",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": (
            "prioritize the pet's holistic head mass, muzzle length, eye placement, ear set, "
            "torso depth, limb proportions, coat volume, stance, and overall individual gestalt"
        ),
    },
    {
        "id": "identity-markings",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": "prioritize exact colors, markings, asymmetry, and anatomical side without changing anatomy or treatment",
    },
    {
        "id": "identity-face",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": "prioritize confirmed head, muzzle, eye, nose, and ear geometry without changing treatment",
    },
    {
        "id": "identity-silhouette",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": "prioritize confirmed body proportions, coat length, stance, and silhouette without changing treatment",
    },
    {
        "id": "identity-age-expression",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": "prioritize confirmed age cues and habitual expression without changing style",
    },
    {
        "id": "identity-tail-accessory",
        "summary": CONTROLLED_LIKENESS_STYLE,
        "delta": "prioritize confirmed tail and identity-bearing accessories without changing style or inventing missing details",
    },
]

STYLE_VARIATIONS = [
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

# Backward-compatible public name for callers that imported the original list.
BASELINE_VARIATIONS = STYLE_VARIATIONS


def plan_baseline_candidates(
    *,
    project_dir: Path,
    provider: str,
    model_alias: str,
    count: int = 3,
    render_sheet: bool = True,
    evaluation_dimension: str = "likeness",
    provider_consent: bool = False,
) -> list[StyleCandidate]:
    get_capabilities(provider)
    if evaluation_dimension not in {"likeness", "style"}:
        raise ValueError("evaluation_dimension must be `likeness` or `style`")
    card = load_or_empty_source_card(project_dir)
    identity = load_identity_profile(project_dir)
    identity_block = (
        identity_prompt_block(project_dir, require_confirmed=True)
        if identity is not None
        else "Preserve the specific identity in the attached sources."
    )
    source_images = load_source_images(project_dir)
    if provider_consent:
        prepare_provider_derivatives(project_dir, provider=provider, consent=True)
    max_references = get_capabilities(provider).max_reference_images or max(1, len(source_images) + 1)
    reserve_for_anchor = 1 if evaluation_dimension == "style" else 0
    reference_budget = max(0, max_references - reserve_for_anchor)
    provider_references = (
        provider_reference_images(
            project_dir,
            provider=provider,
            max_sources=reference_budget,
        )
        if reference_budget
        else []
    )
    source_paths = [path for path, _role in provider_references]
    if evaluation_dimension == "style":
        anchor_path = project_dir / IDENTITY_ANCHOR
        if not anchor_path.is_file():
            raise ValueError(
                "select a source-fidelity likeness candidate before planning style candidates; "
                f"missing {IDENTITY_ANCHOR}"
            )
        source_paths = [IDENTITY_ANCHOR, *source_paths]
    if evaluation_dimension == "likeness" and source_images and not source_paths:
        raise ValueError(
            f"provider consent is required before planning likeness candidates for `{provider}`; "
            "pass --provider-consent to create EXIF-stripped derivatives"
        )
    candidates: list[StyleCandidate] = []
    variation_pool = (
        LIKENESS_VARIATIONS
        if evaluation_dimension == "likeness"
        else STYLE_VARIATIONS
    )
    selected_variations = variation_pool[: max(1, min(count, len(variation_pool)))]
    for index, variation in enumerate(selected_variations, start=1):
        candidate_id = f"{'baseline' if evaluation_dimension == 'likeness' else 'style'}-{index:03d}"
        candidate_dir = project_dir / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = candidate_dir / "prompt.md"
        prompt_path.write_text(
            candidate_prompt(
                card,
                variation,
                identity_block=identity_block,
                evaluation_dimension=evaluation_dimension,
            ),
            encoding="utf-8",
        )
        candidate = StyleCandidate(
            id=candidate_id,
            image_path=None,
            prompt_path=str(prompt_path.relative_to(project_dir)),
            provider=provider,
            model=model_alias,
            source_images=source_paths,
            style_summary=variation["summary"],
            character_delta=variation["delta"],
            strengths=[
                (
                    "controlled likeness interpretation with style held constant"
                    if evaluation_dimension == "likeness"
                    else "planned style treatment with confirmed identity held constant"
                )
            ],
            risks=["image has not been generated or reviewed yet"],
            evaluation_dimension=evaluation_dimension,
            identity_profile_version=identity.version if identity else None,
            variation_id=variation["id"],
            likeness_mode=(
                "source-fidelity-v2"
                if evaluation_dimension == "likeness"
                else "identity-anchor-style-v2"
            ),
            identity_role=(
                "identity_anchor"
                if evaluation_dimension == "likeness"
                else "styled_baseline"
            ),
        )
        write_json(candidate_dir / "candidate.json", candidate.to_dict())
        candidates.append(candidate)
    existing: list[dict[str, object]] = []
    index_path = project_dir / CANDIDATE_INDEX
    if index_path.is_file():
        existing = [
            item
            for item in read_json(index_path).get("candidates", [])
            if isinstance(item, dict) and item.get("evaluation_dimension") != evaluation_dimension
        ]
    write_json(index_path, {"candidates": [*existing, *[item.to_dict() for item in candidates]]})
    if render_sheet:
        build_candidate_contact_sheet(project_dir=project_dir)
    return candidates


def candidate_prompt(
    card: SourceCard,
    variation: dict[str, str],
    *,
    identity_block: str = "",
    evaluation_dimension: str = "likeness",
) -> str:
    source_summary = "; ".join(
        item
        for item in [
            f"species: {card.species}" if card.species else "",
            f"breed/type: {card.breed_or_type}" if card.breed_or_type else "",
            f"age cues: {card.age_traits}" if card.age_traits else "",
            f"size/proportions: {card.size_traits}" if card.size_traits else "",
            f"face: {card.face_traits}" if card.face_traits else "",
            f"eyes: {card.eyes}" if card.eyes else "",
            f"nose: {card.nose}" if card.nose else "",
            f"ears: {card.ears}" if card.ears else "",
            f"fur: {card.fur}" if card.fur else "",
            f"tail: {card.tail}" if card.tail else "",
            f"markings: {card.markings}" if card.markings else "",
            f"props: {card.props}" if card.props else "",
            f"colors: {card.colors}" if card.colors else "",
            f"personality: {card.personality}" if card.personality else "",
            f"user notes: {card.user_notes}" if card.user_notes else "",
        ]
        if item
    )
    must_keep = ", ".join(card.must_keep) if card.must_keep else "source pet identity"
    avoid = ", ".join(card.avoid) if card.avoid else "text, logos, scenery, shadows"
    review_instruction = (
        "Hold style treatment relatively stable so the user can judge which result most resembles the source pet."
        if evaluation_dimension == "likeness"
        else "Hold the confirmed pet identity fixed so the user can judge only the rendering treatment."
    )
    if evaluation_dimension == "likeness":
        task = "Generate one source-faithful identity anchor candidate for a future Codex pet."
        output_contract = (
            "Use one neutral standing three-quarter pose at the animal's natural eye level. Keep the complete "
            "animal centered and occupying 72-78% of canvas height so every candidate has comparable scale. "
            "Do not enlarge the eyes, shorten the muzzle, inflate the head, compress the torso, simplify the "
            "coat, beautify asymmetry, or add a generic cute expression. Output one full-body pet on a perfectly "
            "flat removable chroma-key background, with no text, scenery, floor shadow, or detached effects. "
            "Preserve individual identity and holistic resemblance over novelty or mascot appeal."
        )
    else:
        task = "Generate one animation-safe style treatment from the attached canonical identity anchor."
        output_contract = (
            "Treat the identity anchor as the anatomical source of truth. Change rendering treatment only: keep "
            "head and muzzle geometry, eye placement, ear set, body depth, limb proportions, coat volume, exact "
            "markings and asymmetry unchanged. Use the same neutral three-quarter pose, camera height, 72-78% "
            "subject height, and flat removable chroma-key background across style candidates. Do not trade "
            "holistic resemblance for cuteness or small-cell simplification. No text, scenery, floor shadow, or "
            "detached effects."
        )
    return (
        f"{task}\n\n"
        f"{identity_block}\n\n"
        f"Review dimension: {evaluation_dimension}. {review_instruction}\n"
        f"Variation: {variation['id']}.\n"
        f"Style summary: {variation['summary']}.\n"
        f"Character delta: {variation['delta']}.\n"
        f"Source card summary: {source_summary or 'manual source card details are not filled yet; rely on attached source images'}.\n"
        f"Must keep: {must_keep}.\n"
        f"Avoid: {avoid}.\n\n"
        f"{output_contract}"
    )


def record_candidate_review(
    *,
    project_dir: Path,
    candidate_id: str,
    holistic_gestalt_score: float,
    signature_trait_score: float,
    small_size_readability_score: float,
    notes: str,
    reviewed_by: str,
) -> dict[str, object]:
    """Record the human/model evidence used for likeness-first selection."""

    candidate_path = project_dir / "candidates" / candidate_id / "candidate.json"
    if not candidate_path.is_file():
        raise FileNotFoundError(f"missing candidate manifest: {candidate_path}")
    if not notes.strip():
        raise ValueError("candidate review notes are required")
    if not reviewed_by.strip():
        raise ValueError("candidate reviewer is required")
    scores = {
        "holistic_gestalt_score": holistic_gestalt_score,
        "signature_trait_score": signature_trait_score,
        "small_size_readability_score": small_size_readability_score,
    }
    for label, score in scores.items():
        if not 1.0 <= float(score) <= 5.0:
            raise ValueError(f"{label} must be between 1 and 5")
    raw = read_json(candidate_path)
    raw.update(scores)
    raw["overall_identity_score"] = round(
        (float(holistic_gestalt_score) * 0.55)
        + (float(signature_trait_score) * 0.35)
        + (float(small_size_readability_score) * 0.10),
        3,
    )
    raw["likeness_score"] = raw["overall_identity_score"]
    raw["review_notes"] = notes.strip()
    raw["reviewed_by"] = reviewed_by.strip()
    raw["reviewed_at"] = utc_now()
    write_json(candidate_path, raw)
    update_candidate_index(project_dir, candidate_id, raw, deselect_same_dimension=False)
    build_candidate_contact_sheet(project_dir=project_dir)
    return raw


def assert_source_fidelity_selection(project_dir: Path, raw: dict[str, object]) -> None:
    dimension = str(raw.get("evaluation_dimension", "likeness"))
    source_fidelity_likeness = (
        dimension == "likeness" and raw.get("likeness_mode") == "source-fidelity-v2"
    )
    anchor_preserving_style = (
        dimension == "style" and raw.get("likeness_mode") == "identity-anchor-style-v2"
    )
    if not source_fidelity_likeness and not anchor_preserving_style:
        return
    required = (
        "holistic_gestalt_score",
        "signature_trait_score",
        "small_size_readability_score",
    )
    missing = [name for name in required if raw.get(name) is None]
    if missing:
        raise ValueError(
            "identity-preserving selection requires a candidate review; missing " + ", ".join(missing)
        )
    if float(raw["holistic_gestalt_score"]) < 3.0:
        raise ValueError("candidate is blocked because holistic gestalt scored below 3/5")
    if float(raw["signature_trait_score"]) < 3.0:
        raise ValueError("candidate is blocked because signature-trait fidelity scored below 3/5")

    index_path = project_dir / CANDIDATE_INDEX
    candidates = read_json(index_path).get("candidates", []) if index_path.is_file() else []
    generated = [
        item
        for item in candidates
        if isinstance(item, dict)
        and item.get("evaluation_dimension") == dimension
        and item.get("image_path")
    ]
    unreviewed = [
        str(item.get("id"))
        for item in generated
        if any(item.get(name) is None for name in required)
    ]
    if unreviewed:
        raise ValueError(
            f"review every generated {dimension} candidate before selection; missing reviews for "
            + ", ".join(unreviewed)
        )
    best_gestalt = max(
        (float(item["holistic_gestalt_score"]) for item in generated),
        default=float(raw["holistic_gestalt_score"]),
    )
    if float(raw["holistic_gestalt_score"]) < best_gestalt - 1.0:
        raise ValueError(
            "candidate is blocked because its holistic gestalt is more than one point below "
            "the strongest reviewed candidate"
        )


def select_baseline_candidate(
    *,
    project_dir: Path,
    candidate_id: str,
    image_path: Path | None = None,
    notes: str = "",
    likeness_score: float | None = None,
    style_score: float | None = None,
    holistic_gestalt_score: float | None = None,
    signature_trait_score: float | None = None,
    small_size_readability_score: float | None = None,
    review_notes: str = "",
    reviewed_by: str = "human",
) -> CharacterCard:
    candidate_path = project_dir / "candidates" / candidate_id / "candidate.json"
    if not candidate_path.is_file():
        raise FileNotFoundError(f"missing candidate manifest: {candidate_path}")
    if image_path is not None:
        source = image_path.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"selected baseline image does not exist: {source}")
        store_candidate_image(
            project_dir=project_dir,
            candidate_id=candidate_id,
            image_path=source,
        )
    supplied_review_scores = (
        holistic_gestalt_score,
        signature_trait_score,
        small_size_readability_score,
    )
    if any(score is not None for score in supplied_review_scores):
        if not all(score is not None for score in supplied_review_scores):
            raise ValueError("all three source-fidelity review scores must be supplied together")
        record_candidate_review(
            project_dir=project_dir,
            candidate_id=candidate_id,
            holistic_gestalt_score=float(holistic_gestalt_score),
            signature_trait_score=float(signature_trait_score),
            small_size_readability_score=float(small_size_readability_score),
            notes=review_notes or notes,
            reviewed_by=reviewed_by,
        )
    raw = read_json(candidate_path)
    assert_source_fidelity_selection(project_dir, raw)
    raw["selected"] = True
    raw["selection_notes"] = notes
    raw["selected_at"] = utc_now()
    if likeness_score is not None:
        raw["likeness_score"] = likeness_score
    raw["style_score"] = style_score
    selected_baseline: str | None = raw.get("image_path")
    if selected_baseline:
        source = project_dir / str(selected_baseline)
        target = project_dir / SELECTED_BASELINE
        target.parent.mkdir(parents=True, exist_ok=True)
        normalize_baseline_image(source, target)
        selected_baseline = str(target.relative_to(project_dir))
    write_json(candidate_path, raw)
    update_candidate_index(project_dir, candidate_id, raw, deselect_same_dimension=True)
    build_candidate_contact_sheet(project_dir=project_dir)

    identity_anchor_record: dict[str, object] = {}
    identity_anchor_path = project_dir / IDENTITY_ANCHOR
    if raw.get("evaluation_dimension") == "likeness" and selected_baseline:
        normalize_baseline_image(project_dir / SELECTED_BASELINE, identity_anchor_path)
        identity_anchor_record = {
            **raw,
            "identity_anchor_image": IDENTITY_ANCHOR,
            "source_baseline_image": selected_baseline,
        }
        write_json(project_dir / IDENTITY_ANCHOR_RECORD, identity_anchor_record)
    elif (project_dir / IDENTITY_ANCHOR_RECORD).is_file():
        identity_anchor_record = read_json(project_dir / IDENTITY_ANCHOR_RECORD)
    if raw.get("evaluation_dimension") == "style":
        if not identity_anchor_path.is_file():
            raise ValueError("style selection requires a preserved source-fidelity identity anchor")
        write_json(project_dir / STYLED_BASELINE_RECORD, raw)

    source_card = load_or_empty_source_card(project_dir)
    identity = load_identity_profile(project_dir)
    stable_traits = [
        item
        for item in [
            source_card.species,
            source_card.breed_or_type,
            source_card.face_traits,
            source_card.eyes,
            source_card.nose,
            source_card.ears,
            source_card.fur,
            source_card.tail,
            source_card.markings,
            source_card.colors,
            source_card.size_traits,
            source_card.age_traits,
            source_card.personality,
            source_card.props,
            source_card.user_notes,
        ]
        if item
    ]
    character = CharacterCard(
        canonical_name=project_dir.name,
        one_sentence_identity=(
            identity.identity_summary
            if identity and identity.identity_summary
            else raw["style_summary"]
        ),
        stable_traits=stable_traits,
        style=raw["style_summary"],
        props=source_card.props,
        do_not_change=source_card.must_keep,
        selected_baseline_image=selected_baseline,
        provider_notes={raw["provider"]: raw["model"]},
        identity_profile_version=identity.version if identity else None,
        identity_anchor_image=(IDENTITY_ANCHOR if identity_anchor_path.is_file() else None),
        identity_anchor_candidate_id=(
            str(identity_anchor_record.get("id")) if identity_anchor_record.get("id") else None
        ),
        likeness_selection_notes=(
            notes
            if raw.get("evaluation_dimension") == "likeness"
            else str(identity_anchor_record.get("selection_notes", ""))
        ),
        style_selection_notes=notes if raw.get("evaluation_dimension") == "style" else "",
    )
    write_json(project_dir / SELECTED_CANDIDATE, raw)
    write_json(project_dir / CHARACTER_CARD, character.to_dict())
    return character


def store_candidate_image(*, project_dir: Path, candidate_id: str, image_path: Path) -> str:
    candidate_path = project_dir / "candidates" / candidate_id / "candidate.json"
    if not candidate_path.is_file():
        raise FileNotFoundError(f"missing candidate manifest: {candidate_path}")
    source = image_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"candidate image does not exist: {source}")
    target = project_dir / "candidates" / candidate_id / "generated" / "candidate.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    normalize_baseline_image(source, target)
    raw = read_json(candidate_path)
    raw["image_path"] = str(target.relative_to(project_dir))
    review_target = project_dir / "candidates" / candidate_id / "generated" / "review-normalized.png"
    normalize_candidate_review_image(target, review_target)
    raw["review_image_path"] = str(review_target.relative_to(project_dir))
    if "image stored for candidate review" not in raw.get("strengths", []):
        raw["strengths"] = [*raw.get("strengths", []), "image stored for candidate review"]
    write_json(candidate_path, raw)
    update_candidate_index(project_dir, candidate_id, raw, deselect_same_dimension=False)
    build_candidate_contact_sheet(project_dir=project_dir)
    return str(target.relative_to(project_dir))


def normalize_baseline_image(source: Path, target: Path) -> None:
    """Save selected baseline as PNG even if a provider returns another format."""
    try:
        with Image.open(source) as image:
            image.convert("RGBA").save(target)
    except Exception:
        shutil.copy2(source, target)


def normalize_candidate_review_image(source: Path, target: Path) -> None:
    """Create a non-destructive, common-scale likeness review tile."""

    with Image.open(source) as opened:
        rgba = opened.convert("RGBA")
    bbox = alpha_bbox(rgba)
    if bbox is None or bbox == (0, 0, rgba.width, rgba.height):
        keyed = remove_chroma_background(rgba)
        keyed_bbox = alpha_bbox(keyed)
        if keyed_bbox is not None:
            rgba, bbox = keyed, keyed_bbox
    if bbox is None:
        raise ValueError(f"candidate image has no visible subject: {source}")
    subject = rgba.crop(bbox)
    canvas = Image.new("RGBA", (240, 200), (0, 0, 0, 0))
    scale = min(208 / max(1, subject.width), 164 / max(1, subject.height))
    subject = subject.resize(
        (max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (canvas.width - subject.width) // 2
    top = 184 - subject.height
    canvas.alpha_composite(subject, (left, top))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


def update_candidate_index(
    project_dir: Path,
    selected_id: str,
    selected_raw: dict[str, object],
    *,
    deselect_same_dimension: bool,
) -> None:
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
        elif deselect_same_dimension and item.get("evaluation_dimension") == selected_raw.get("evaluation_dimension"):
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
    image_path = candidate.get("review_image_path") or candidate.get("image_path")
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
    score_text = ""
    if candidate.get("holistic_gestalt_score") is not None:
        score_text = (
            f"G {candidate.get('holistic_gestalt_score')}  "
            f"T {candidate.get('signature_trait_score')}  "
            f"R {candidate.get('small_size_readability_score')}"
        )
        draw.text((left + 18, top + 254), score_text, fill=(45, 70, 100))
    summary = str(candidate.get("character_delta") or candidate.get("style_summary", ""))
    summary_top = 274 if score_text else 258
    for line_index, line in enumerate(wrap_text(summary, 44)[:3]):
        draw.text((left + 18, top + summary_top + (line_index * 16)), line, fill=(65, 65, 65))


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
