"""Default emotion style sheet and row generation planning."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .contracts import ROW_FRAME_COUNTS, STATE_ORDER
from .jsonio import read_json, write_json
from .schemas import EmotionStateSpec, EmotionStyleSheet, GenerationJob


STYLE_PATH = "style/emotion-style-sheet.json"


STATE_DEFAULTS = {
    "idle": {
        "purpose": "calm default presence",
        "mood": "happy, calm, warm",
        "allowed_motion": "subtle breathing, blink, head bob, tiny tail movement",
        "forbidden_motion": "walking, waving, jumping, working, large gestures",
        "prompt_notes": "Keep visible micro-variation without turning idle into another action.",
        "layout_notes": "Keep body centered and fully inside every frame.",
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


def default_emotion_style_sheet(style_id: str = "happy-codex-default") -> EmotionStyleSheet:
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
        base_mood="generally happy, entertaining, warm, pet-safe, and unobtrusive",
        state_specs=specs,
        global_avoid=[
            "text",
            "logos",
            "visible frame boxes",
            "layout guides",
            "detached effects",
            "floor shadows",
            "scenery",
            "green chroma-key color in the pet",
        ],
        prop_policy="Use only identity-bound props from the selected character card.",
        effects_policy="Prefer pose and expression; avoid decorative effects by default.",
        background_policy="perfectly flat solid #00ff00 chroma-key background for row strips",
        centering_policy="component-centered with state-specific vertical baseline",
        qa_thresholds={
            "min_edge_px": 10,
            "max_horizontal_drift_px": 10,
            "transparent_rgb_residue": 0,
        },
    )


def save_default_style_sheet(project_dir: Path, style_id: str = "happy-codex-default") -> EmotionStyleSheet:
    sheet = default_emotion_style_sheet(style_id)
    write_json(project_dir / STYLE_PATH, sheet.to_dict())
    return sheet


def load_style_sheet(project_dir: Path) -> EmotionStyleSheet:
    path = project_dir / STYLE_PATH
    if not path.is_file():
        return save_default_style_sheet(project_dir)
    return EmotionStyleSheet.from_dict(read_json(path))


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
    jobs = []
    for spec in sheet.state_specs:
        prompt_path = prompts_dir / f"{spec.state}.md"
        prompt = row_prompt(spec, sheet)
        prompt_path.write_text(prompt, encoding="utf-8")
        input_images = [character_reference] if character_reference else []
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
                expected_output=str((output_dir / f"{spec.state}.png").relative_to(project_dir)),
                retry_policy={"max_attempts": 2, "use_retry_prompt": True},
            )
        )
    write_json(run_dir / "generation-jobs.json", {"jobs": [job.to_dict() for job in jobs]})
    return jobs


def row_prompt(spec: EmotionStateSpec, sheet: EmotionStyleSheet) -> str:
    avoid = ", ".join(sheet.global_avoid)
    return (
        f"Create a horizontal sprite row strip for Codex pet state `{spec.state}`.\n\n"
        f"Frame count: exactly {spec.frame_count} evenly spaced full-body poses in one row.\n"
        f"Base mood: {sheet.base_mood}.\n"
        f"State purpose: {spec.purpose}.\n"
        f"State mood: {spec.mood}.\n"
        f"Allowed motion: {spec.allowed_motion}.\n"
        f"Forbidden motion: {spec.forbidden_motion}.\n"
        f"Prompt notes: {spec.prompt_notes}.\n"
        f"Layout notes: {spec.layout_notes}.\n"
        f"Background policy: {sheet.background_policy}.\n"
        f"Prop policy: {sheet.prop_policy}.\n"
        f"Effects policy: {sheet.effects_policy}.\n"
        f"Avoid: {avoid}.\n"
    )


def prompt_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

