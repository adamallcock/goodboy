"""View models for the Goodboy Review Room web UI."""

from __future__ import annotations

import re
from typing import Any, Literal, TypedDict


Severity = Literal["info", "success", "warning", "danger"]


class ArtifactRef(TypedDict):
    id: str
    kind: str
    label: str
    relative_path: str
    url: str
    exists: bool
    width: int | None
    height: int | None
    bytes: int | None
    modified_at: str | None
    stage: str
    state: str | None
    severity: Severity


class WorkflowGate(TypedDict):
    stage: str
    next_action: str
    required_user_input: list[str]
    artifacts_to_show_user: list[str]
    blocked_actions: list[str]
    recommended_command: str | None
    install_ready: bool


class ProjectState(TypedDict):
    project_id: str
    project_dir: str
    manifest: dict[str, Any]
    animation_contract: dict[str, Any]
    gate: WorkflowGate
    artifacts: list[ArtifactRef]
    sources: list[dict[str, Any]]
    reference_coverage: dict[str, Any] | None
    identity_profile: dict[str, Any] | None
    identity_pack: dict[str, Any] | None
    candidates: list[dict[str, Any]]
    selected_candidate: dict[str, Any] | None
    character_card: dict[str, Any] | None
    style_sheet: dict[str, Any] | None
    active_run_id: str | None
    jobs: list[dict[str, Any]]
    job_graph: dict[str, Any] | None
    events: list[dict[str, Any]]
    qa: dict[str, Any] | None
    likeness: dict[str, Any] | None
    animation_review: dict[str, Any] | None
    animation_correctness: dict[str, Any] | None
    direction_review: dict[str, Any] | None
    direction_blind: dict[str, Any] | None
    approvals: list[dict[str, Any]]
    exports: list[ArtifactRef]
    validation: dict[str, Any]


def artifact_id_for(relative_path: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", relative_path).strip("-").lower()
    return cleaned or "artifact"


def artifact_url_for(project_id: str, artifact_id: str) -> str:
    return f"/api/projects/{project_id}/artifacts/{artifact_id}"


def severity_for_stage(stage: str) -> Severity:
    if stage in {"qa-fail", "blocked"}:
        return "danger"
    if stage in {"qa-warning", "needs-review"}:
        return "warning"
    if stage in {"approved", "installed", "exported"}:
        return "success"
    return "info"
