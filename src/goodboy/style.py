"""Default emotion style sheet and row generation planning."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image, ImageDraw

from .contracts import CELL_HEIGHT, CELL_WIDTH, ROW_FRAME_COUNTS, STATE_ORDER
from .ingest import load_source_images
from .jsonio import read_json, write_json
from .schemas import EmotionStateSpec, EmotionStyleSheet, GenerationJob


STYLE_PATH = "style/emotion-style-sheet.json"
RUN_METADATA = "run-metadata.json"
LAYOUT_GUIDE_DIR = "layout-guides"
LAYOUT_GUIDE_SAFE_MARGIN_X = 18
LAYOUT_GUIDE_SAFE_MARGIN_Y = 16


CHROMA_KEY_CANDIDATES = [
    ("magenta", "#FF00FF"),
    ("cyan", "#00FFFF"),
    ("yellow", "#FFFF00"),
    ("blue", "#0000FF"),
    ("orange", "#FF7F00"),
    ("green", "#00FF00"),
]


STYLE_PRESETS = {
    "auto": {
        "base_mood": "generally happy, entertaining, warm, pet-safe, and unobtrusive",
        "prompt": "infer the best pet-safe style from the selected baseline and source images, then keep that exact style consistent across every row",
    },
    "soft-lifelike": {
        "base_mood": "generally happy, entertaining, warm, pet-safe, and unobtrusive",
        "prompt": "soft lifelike desktop mascot, realistic fur/material cues, friendly small-size readability",
    },
    "realistic": {
        "base_mood": "naturalistic, warm, believable, and expressive without becoming uncanny",
        "prompt": "realistic lighting and anatomy/material behavior, high identity fidelity, still readable as a desktop pet",
    },
    "anime": {
        "base_mood": "bright, charming, expressive, and emotionally readable",
        "prompt": "anime-inspired character design, clean shapes, expressive eyes or object features, crisp silhouette",
    },
    "storybook": {
        "base_mood": "gentle, whimsical, warm, and playful",
        "prompt": "storybook 3D character style with soft shapes, appealing expression, and clear motion poses",
    },
    "pixel": {
        "base_mood": "playful, readable, and game-like",
        "prompt": "pixel-art inspired sprite readability, simplified details, strong silhouette, no text or UI glyphs",
    },
    "sticker": {
        "base_mood": "cute, clean, energetic, and highly legible",
        "prompt": "soft sticker-like mascot render, crisp outline, simple details, high small-cell readability",
    },
    "plush": {
        "base_mood": "warm, cuddly, readable, and gentle",
        "prompt": "soft plush toy mascot with rounded stitched forms, fuzzy fabric feel, simple sewn details, and readable toy-like proportions",
    },
    "clay": {
        "base_mood": "handmade, charming, tactile, and playful",
        "prompt": "handmade clay or polymer-clay mascot with rounded sculpted forms, soft material texture, simple features, and clean readable edges",
    },
    "flat-vector": {
        "base_mood": "clean, friendly, graphic, and readable",
        "prompt": "flat vector-style mascot with simple geometric forms, crisp color areas, clean outline, and minimal shading",
    },
    "3d-toy": {
        "base_mood": "friendly, dimensional, polished, and toy-like",
        "prompt": "stylized 3D toy mascot with smooth rounded forms, simple materials, clear silhouette, and no photoreal complexity",
    },
    "painterly": {
        "base_mood": "warm, expressive, handcrafted, and readable",
        "prompt": "painterly mascot with simplified brush texture, readable forms, stable palette, and enough edge clarity for clean extraction",
    },
    "brand-inspired": {
        "base_mood": "on-brand, mascot-safe, compact, and expressive",
        "prompt": "brand-inspired mascot using approved broad cues such as colors, domain motifs, and vibe while avoiding readable text or logo copying unless explicitly approved",
    },
}

SUBJECT_KIND_GUIDANCE = {
    "pet": "The subject is an animal companion; express emotion through face, ears, tail, posture, and body motion.",
    "animal": "The subject is an animal; preserve species identity and express emotion through posture and natural body features.",
    "person": "The subject is a person-like character; keep it friendly, non-photorealistic enough for mascot use, and avoid real-person identity drift.",
    "inanimate_object": "The subject may be an inanimate object. Give it mascot-like life through squash/stretch, tilt, bounce, small feature motion, expressive highlights, or identity-bound appendages without adding unrelated limbs unless requested.",
    "object": "The subject may be an inanimate object. Animate through object-safe motion such as bounce, tilt, wobble, feature motion, or subtle expression while preserving object identity.",
    "fantasy_creature": "The subject is imaginary; keep the fantasy traits stable and readable across all frames.",
}


STATE_DEFAULTS = {
    "idle": {
        "purpose": "quiet always-on default presence",
        "mood": "happy, calm, warm, unobtrusive",
        "allowed_motion": "near-still pose with one tiny blink and barely perceptible breathing only",
        "forbidden_motion": "walking, waving, jumping, working, large gestures, tail wagging, bouncing, swaying, pawing, rhythmic head bobbing, attention-seeking motion",
        "prompt_notes": "Idle plays continuously, so make it calming and almost still. Prefer four or five near-identical frames plus a tiny blink or breathing cue; do not make a loop that demands attention.",
        "layout_notes": "Keep body centered and fully inside every frame with fixed apparent scale and baseline; avoid vertical bobbing.",
    },
    "running-right": {
        "purpose": "directional drag movement to the right",
        "mood": "happy and energetic",
        "allowed_motion": "right-facing trot/run cadence through legs, ears, tail, and body pose",
        "forbidden_motion": "speed lines, dust, shadows, motion trails, detached effects",
        "prompt_notes": "Face and travel right; alternate stride clearly.",
        "layout_notes": "Keep the pet centered within each slot even though the pose faces right.",
    },
    "running-left": {
        "purpose": "directional drag movement to the left",
        "mood": "happy and energetic",
        "allowed_motion": "left-facing trot/run cadence through legs, ears, tail, and body pose",
        "forbidden_motion": "speed lines, dust, shadows, motion trails, detached effects",
        "prompt_notes": "Face and travel left; alternate stride clearly.",
        "layout_notes": "Keep the pet centered within each slot even though the pose faces left.",
    },
    "waving": {
        "purpose": "friendly greeting",
        "mood": "cheerful and welcoming",
        "allowed_motion": "one paw or limb raises and lowers",
        "forbidden_motion": "wave marks, motion arcs, sparkles, symbols, text",
        "prompt_notes": "Show the wave through the body only.",
        "layout_notes": "Raised paw must stay inside the frame.",
    },
    "jumping": {
        "purpose": "happy hop",
        "mood": "joyful and playful",
        "allowed_motion": "crouch, lift, airborne, landing, recovery through body height",
        "forbidden_motion": "floor, shadows, dust, impact marks, bounce pads",
        "prompt_notes": "Show vertical movement only through body position.",
        "layout_notes": "Use enough top and bottom clearance for the jump arc.",
    },
    "failed": {
        "purpose": "gentle disappointment and recovery",
        "mood": "disappointed but adorable, hopeful at the end",
        "allowed_motion": "ears droop, head lowers, blink, small recovery smile",
        "forbidden_motion": "red X marks, symbols, detached tears, stars, smoke",
        "prompt_notes": "Avoid making the pet miserable or visually harsh.",
        "layout_notes": "Low poses should remain centered and readable.",
    },
    "waiting": {
        "purpose": "asking for input or approval",
        "mood": "expectant and sweet",
        "allowed_motion": "head tilt, paw raise, attentive sit or stand, gentle bounce",
        "forbidden_motion": "question marks, speech bubbles, UI symbols, text",
        "prompt_notes": "Make it distinct from idle and review.",
        "layout_notes": "Paw raise should not touch the frame edge.",
    },
    "running": {
        "purpose": "active task work or processing",
        "mood": "cheerful focused helper",
        "allowed_motion": "attentive lean, head turns, paw lift, concentrated posture",
        "forbidden_motion": "literal directional travel, jogging, speed effects, props unless identity-bound",
        "prompt_notes": "This state means working, not running across the screen.",
        "layout_notes": "Keep loop stable and centered.",
    },
    "review": {
        "purpose": "focused review or inspection",
        "mood": "warm concentration",
        "allowed_motion": "lean, head tilt, blink, nose-down look, pleased look-up",
        "forbidden_motion": "magnifying glass, papers, code, UI, punctuation, new props",
        "prompt_notes": "Use expression and posture only unless a prop is part of the pet identity.",
        "layout_notes": "Avoid clipping lowered head or tail.",
    },
}


def default_emotion_style_sheet(
    style_id: str = "happy-codex-default",
    *,
    style_preset: str = "soft-lifelike",
    subject_kind: str = "pet",
    user_style_overrides: list[str] | None = None,
    ai_critique_overrides: list[str] | None = None,
) -> EmotionStyleSheet:
    preset = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["soft-lifelike"])
    specs = []
    for state in STATE_ORDER:
        defaults = STATE_DEFAULTS[state]
        specs.append(
            EmotionStateSpec(
                state=state,
                frame_count=ROW_FRAME_COUNTS[state],
                purpose=defaults["purpose"],
                mood=defaults["mood"],
                allowed_motion=defaults["allowed_motion"],
                forbidden_motion=defaults["forbidden_motion"],
                prompt_notes=defaults["prompt_notes"],
                layout_notes=defaults["layout_notes"],
            )
        )
    return EmotionStyleSheet(
        id=style_id,
        base_mood=preset["base_mood"],
        state_specs=specs,
        global_avoid=[
            "text",
            "logos",
            "visible frame boxes",
            "layout guides",
            "detached effects",
            "floor shadows",
            "scenery",
            "selected chroma-key color in the pet",
        ],
        prop_policy="Use only identity-bound props from the selected character card.",
        effects_policy="Prefer pose and expression; avoid decorative effects by default.",
        background_policy="perfectly flat selected chroma-key background for row strips",
        centering_policy="component-centered with state-specific vertical baseline",
        qa_thresholds={
            "min_edge_px": 10,
            "max_horizontal_drift_px": 10,
            "transparent_rgb_residue": 0,
        },
        style_preset=style_preset,
        subject_kind=subject_kind,
        user_style_overrides=user_style_overrides or [],
        ai_critique_overrides=ai_critique_overrides or [],
    )


def save_default_style_sheet(
    project_dir: Path,
    style_id: str = "happy-codex-default",
    *,
    style_preset: str = "soft-lifelike",
    subject_kind: str = "pet",
    user_style_overrides: list[str] | None = None,
    ai_critique_overrides: list[str] | None = None,
) -> EmotionStyleSheet:
    sheet = default_emotion_style_sheet(
        style_id,
        style_preset=style_preset,
        subject_kind=subject_kind,
        user_style_overrides=user_style_overrides,
        ai_critique_overrides=ai_critique_overrides,
    )
    write_json(project_dir / STYLE_PATH, sheet.to_dict())
    return sheet


def load_style_sheet(project_dir: Path) -> EmotionStyleSheet:
    path = project_dir / STYLE_PATH
    if not path.is_file():
        return save_default_style_sheet(project_dir)
    return EmotionStyleSheet.from_dict(read_json(path))


def parse_hex_color(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"invalid color value: {value}")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def sampled_reference_pixels(paths: list[Path]) -> list[tuple[int, int, int]]:
    pixels: list[tuple[int, int, int]] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            with Image.open(path) as opened:
                image = opened.convert("RGBA")
                image.thumbnail((128, 128), Image.Resampling.LANCZOS)
                for red, green, blue, alpha in image.getdata():
                    if alpha <= 16:
                        continue
                    pixels.append((red, green, blue))
        except OSError:
            continue
    non_background = [
        pixel
        for pixel in pixels
        if not (pixel[0] > 244 and pixel[1] > 244 and pixel[2] > 244)
    ]
    return non_background or pixels


def choose_chroma_key(project_dir: Path, character_reference: str | None = None) -> dict[str, object]:
    reference_paths = [project_dir / image.path for image in load_source_images(project_dir)]
    if character_reference:
        reference_paths.append(project_dir / character_reference)
    pixels = sampled_reference_pixels(reference_paths)
    if not pixels:
        rgb = parse_hex_color("#FF00FF")
        return {
            "hex": "#FF00FF",
            "rgb": list(rgb),
            "name": "magenta",
            "selection": "fallback",
        }
    scored: list[tuple[float, int, str, tuple[int, int, int]]] = []
    for preference_index, (name, hex_color) in enumerate(CHROMA_KEY_CANDIDATES):
        rgb = parse_hex_color(hex_color)
        distances = sorted(color_distance(rgb, pixel) for pixel in pixels)
        percentile_index = max(0, min(len(distances) - 1, int(len(distances) * 0.01)))
        scored.append((distances[percentile_index], -preference_index, name, rgb))
    score, _preference, name, rgb = max(scored)
    return {
        "hex": rgb_to_hex(rgb),
        "rgb": list(rgb),
        "name": name,
        "selection": "auto",
        "score": round(score, 2),
    }


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    fill: str,
    dash: int = 8,
    gap: int = 6,
) -> None:
    x1, y1 = start
    x2, y2 = end
    if x1 == x2:
        for y in range(min(y1, y2), max(y1, y2), dash + gap):
            draw.line((x1, y, x2, min(y + dash, max(y1, y2))), fill=fill)
        return
    if y1 == y2:
        for x in range(min(x1, x2), max(x1, x2), dash + gap):
            draw.line((x, y1, min(x + dash, max(x1, x2)), y2), fill=fill)
        return
    raise ValueError("draw_dashed_line only supports horizontal or vertical lines")


def create_layout_guide(path: Path, state: str, frames: int) -> dict[str, object]:
    width = frames * CELL_WIDTH
    height = CELL_HEIGHT
    image = Image.new("RGB", (width, height), "#f7f7f7")
    draw = ImageDraw.Draw(image)
    for index in range(frames):
        left = index * CELL_WIDTH
        right = left + CELL_WIDTH - 1
        draw.rectangle((left, 0, right, height - 1), outline="#111111", width=2)
        safe_left = left + LAYOUT_GUIDE_SAFE_MARGIN_X
        safe_top = LAYOUT_GUIDE_SAFE_MARGIN_Y
        safe_right = right - LAYOUT_GUIDE_SAFE_MARGIN_X
        safe_bottom = height - 1 - LAYOUT_GUIDE_SAFE_MARGIN_Y
        draw.rectangle((safe_left, safe_top, safe_right, safe_bottom), outline="#2f80ed", width=2)
        center_x = left + CELL_WIDTH // 2
        center_y = height // 2
        draw_dashed_line(draw, (center_x, safe_top), (center_x, safe_bottom), fill="#b8b8b8")
        draw_dashed_line(draw, (safe_left, center_y), (safe_right, center_y), fill="#b8b8b8")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return {
        "state": state,
        "path": str(path),
        "width": width,
        "height": height,
        "frames": frames,
        "cell_width": CELL_WIDTH,
        "cell_height": CELL_HEIGHT,
        "safe_margin_x": LAYOUT_GUIDE_SAFE_MARGIN_X,
        "safe_margin_y": LAYOUT_GUIDE_SAFE_MARGIN_Y,
        "usage": "layout guide input only; do not copy visible guide lines into generated sprite strips",
    }


def create_layout_guides(run_dir: Path) -> dict[str, dict[str, object]]:
    guide_dir = run_dir / LAYOUT_GUIDE_DIR
    return {
        state: create_layout_guide(guide_dir / f"{state}.png", state, ROW_FRAME_COUNTS[state])
        for state in STATE_ORDER
    }


def plan_row_generation_jobs(
    *,
    project_dir: Path,
    run_id: str,
    provider: str,
    model_alias: str,
    character_reference: str | None = None,
) -> list[GenerationJob]:
    sheet = load_style_sheet(project_dir)
    run_dir = project_dir / "runs" / run_id
    prompts_dir = run_dir / "prompts" / "rows"
    output_dir = run_dir / "row-strips"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    layout_guides = create_layout_guides(run_dir)
    chroma_key = choose_chroma_key(project_dir, character_reference)
    write_json(
        run_dir / RUN_METADATA,
        {
            "run_id": run_id,
            "chroma_key": chroma_key,
            "layout_guides": {
                state: {
                    **metadata,
                    "path": str((Path(str(metadata["path"]))).relative_to(project_dir)),
                }
                for state, metadata in layout_guides.items()
            },
            "canonical_reference": character_reference,
        },
    )
    jobs = []
    for spec in sheet.state_specs:
        prompt_path = prompts_dir / f"{spec.state}.md"
        prompt = row_prompt(spec, sheet, chroma_key)
        prompt_path.write_text(prompt, encoding="utf-8")
        guide_path = str((run_dir / LAYOUT_GUIDE_DIR / f"{spec.state}.png").relative_to(project_dir))
        input_images = []
        input_image_roles = {
            guide_path: "layout guide only; use for spacing, do not copy guide lines",
        }
        if character_reference:
            input_images.append(character_reference)
            input_image_roles[character_reference] = "canonical identity reference"
        input_images.append(guide_path)
        jobs.append(
            GenerationJob(
                id=f"row-{spec.state}",
                kind="row-strip",
                state=spec.state,
                status="planned",
                provider=provider,
                model_alias=model_alias,
                prompt_path=str(prompt_path.relative_to(project_dir)),
                input_images=input_images,
                input_image_roles=input_image_roles,
                expected_output=str((output_dir / f"{spec.state}.png").relative_to(project_dir)),
                retry_policy={"max_attempts": 2, "use_retry_prompt": True},
            )
        )
    write_json(run_dir / "generation-jobs.json", {"jobs": [job.to_dict() for job in jobs]})
    return jobs


def row_prompt(spec: EmotionStateSpec, sheet: EmotionStyleSheet, chroma_key: dict[str, object]) -> str:
    avoid = ", ".join(sheet.global_avoid)
    preset_prompt = STYLE_PRESETS.get(sheet.style_preset, {"prompt": sheet.style_preset})["prompt"]
    subject_guidance = SUBJECT_KIND_GUIDANCE.get(sheet.subject_kind, f"Subject kind: {sheet.subject_kind}. Preserve its identity and make it work as a Codex pet.")
    user_overrides = "\n".join(f"- {item}" for item in sheet.user_style_overrides) or "- none"
    critique_overrides = "\n".join(f"- {item}" for item in sheet.ai_critique_overrides) or "- none"
    chroma_hex = str(chroma_key["hex"])
    chroma_name = str(chroma_key.get("name", "selected"))
    return (
        f"Create a horizontal sprite row strip for Codex pet state `{spec.state}`.\n\n"
        f"Use the attached canonical base for identity. Use the attached layout guide only for slot count, spacing, centering, and safe padding; do not draw the guide.\n"
        f"Frame count: exactly {spec.frame_count} evenly spaced full-body poses in one row.\n"
        f"Output exactly {spec.frame_count} full-body frames in one left-to-right row on flat pure {chroma_name} {chroma_hex} chroma-key background.\n"
        f"Treat the row as {spec.frame_count} invisible equal-width slots: one centered complete pose per slot, evenly spaced, with no overlap, clipping, empty slots, labels, borders, visible frame boxes, or guide marks.\n"
        f"Style preset: {sheet.style_preset} ({preset_prompt}).\n"
        f"Subject kind: {sheet.subject_kind}. {subject_guidance}\n"
        f"Base mood: {sheet.base_mood}.\n"
        f"State purpose: {spec.purpose}.\n"
        f"State mood: {spec.mood}.\n"
        f"Allowed motion: {spec.allowed_motion}.\n"
        f"Forbidden motion: {spec.forbidden_motion}.\n"
        f"Prompt notes: {spec.prompt_notes}.\n"
        f"Layout notes: {spec.layout_notes}.\n"
        f"Animation continuity: keep apparent pet scale and baseline stable within the row unless the state intentionally changes vertical position, such as `jumping`. Move the pose within the slot instead of redrawing the pet larger or smaller frame to frame.\n"
        f"Background policy: perfectly flat pure {chroma_name} {chroma_hex} chroma-key background; keep {chroma_hex} and close colors out of the pet, props, highlights, and effects.\n"
        f"Prop policy: {sheet.prop_policy}.\n"
        f"Effects policy: {sheet.effects_policy}.\n"
        f"User style overrides:\n{user_overrides}\n"
        f"AI critique overrides:\n{critique_overrides}\n"
        f"Clean extraction: crisp opaque edges, safe padding, no scenery, text, guide marks, checkerboard, shadows, glows, motion blur, speed lines, dust, detached effects, stray pixels, white border, white background, or chroma-key colors inside the pet.\n"
        f"Avoid: {avoid}.\n"
    )


def prompt_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
