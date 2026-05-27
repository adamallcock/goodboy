"""Human and AI feedback events plus explicit branch manifests."""

from __future__ import annotations

import re
from pathlib import Path

from .jsonio import read_json, write_json
from .project import load_project
from .schemas import BranchManifest, FeedbackEvent


FEEDBACK_EVENTS = "feedback/events.json"


def create_feedback_event(
    *,
    project_dir: Path,
    target: str,
    text: str,
    author: str = "human",
    create_branch: bool = True,
    branch_id: str | None = None,
    parent: str = "main",
) -> FeedbackEvent:
    load_project(project_dir)
    if author not in {"human", "vision_critic", "system"}:
        raise ValueError("author must be one of: human, vision_critic, system")
    if not target.strip():
        raise ValueError("feedback target is required")
    if not text.strip():
        raise ValueError("feedback text is required")

    events = load_feedback_events(project_dir)
    event_id = next_event_id(events)
    branch = branch_id or branch_slug(target, text, len(events) + 1)
    event = FeedbackEvent(
        id=event_id,
        author=author,
        target=target,
        text=text,
        creates_branch=branch if create_branch else None,
        branch_id=branch if create_branch else None,
    )
    events.append(event)
    write_json(project_dir / FEEDBACK_EVENTS, {"events": [item.to_dict() for item in events]})
    if create_branch:
        create_branch_manifest(
            project_dir=project_dir,
            branch_id=branch,
            parent=parent,
            target=target,
            reason=text,
            author=author,
            source_event_id=event_id,
        )
    return event


def load_feedback_events(project_dir: Path) -> list[FeedbackEvent]:
    path = project_dir / FEEDBACK_EVENTS
    if not path.is_file():
        return []
    raw = read_json(path)
    return [FeedbackEvent.from_dict(item) for item in raw.get("events", [])]


def create_branch_manifest(
    *,
    project_dir: Path,
    branch_id: str,
    parent: str,
    target: str,
    reason: str,
    author: str,
    source_event_id: str,
) -> BranchManifest:
    branch = BranchManifest(
        id=branch_id,
        parent=parent,
        target=target,
        reason=reason,
        author=author,
        source_event_id=source_event_id,
    )
    write_json(project_dir / "branches" / branch_id / "branch.json", branch.to_dict())
    return branch


def next_event_id(events: list[FeedbackEvent]) -> str:
    seen = []
    for event in events:
        if event.id.startswith("feedback-"):
            try:
                seen.append(int(event.id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"feedback-{max(seen, default=0) + 1:03d}"


def branch_slug(target: str, text: str, index: int) -> str:
    target_part = slugify(target.replace(":", "-"))[:28] or "artifact"
    text_part = slugify(text)[:36] or "feedback"
    return f"{index:03d}-{target_part}-{text_part}".strip("-")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-+", "-", normalized)
