"""Structured human/AI critique reports."""

from __future__ import annotations

from pathlib import Path

from .feedback import create_feedback_event
from .jsonio import read_json, write_json
from .schemas import CritiqueReport
from .style import STYLE_PATH


def record_critique(
    *,
    project_dir: Path,
    critique_id: str,
    target: str,
    author: str,
    findings: list[str],
    recommendations: list[str],
    identity_score: float | None = None,
    style_score: float | None = None,
    apply_to_style: bool = False,
) -> CritiqueReport:
    if author not in {"human", "vision_critic", "system"}:
        raise ValueError("author must be human, vision_critic, or system")
    if not findings and not recommendations:
        raise ValueError("critique requires at least one finding or recommendation")
    report = CritiqueReport(
        id=critique_id,
        target=target,
        author=author,
        findings=findings,
        recommendations=recommendations,
        identity_score=identity_score,
        style_score=style_score,
        apply_to_style=apply_to_style,
    )
    path = project_dir / "critiques" / f"{critique_id}.json"
    write_json(path, report.to_dict())
    create_feedback_event(
        project_dir=project_dir,
        target=target,
        text="; ".join(findings + recommendations),
        author=author,
        create_branch=True,
        branch_id=f"critique-{critique_id}",
    )
    if apply_to_style:
        apply_critique_to_style(project_dir, recommendations)
    return report


def apply_critique_to_style(project_dir: Path, recommendations: list[str]) -> None:
    style_path = project_dir / STYLE_PATH
    if not style_path.is_file():
        return
    raw = read_json(style_path)
    existing = list(raw.get("ai_critique_overrides", []))
    for item in recommendations:
        if item and item not in existing:
            existing.append(item)
    raw["ai_critique_overrides"] = existing
    write_json(style_path, raw)

