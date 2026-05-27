"""Backend actions for the Goodboy Review Room UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from goodboy.candidates import CANDIDATE_INDEX, SELECTED_CANDIDATE, plan_baseline_candidates, select_baseline_candidate, store_candidate_image
from goodboy.critique import record_critique
from goodboy.exports import export_petdex_package, export_project_bundle
from goodboy.feedback import create_feedback_event
from goodboy.ingest import SOURCE_CARD, SOURCE_MANIFEST, draft_source_card, ingest_images
from goodboy.jsonio import read_json, write_json
from goodboy.project import init_project, load_project
from goodboy.style import STYLE_PATH, plan_row_generation_jobs, save_default_style_sheet
from goodboy.validation import validate_project
from goodboy.workflow import (
    approve_artifact,
    build_review,
    finish_run,
    generate_handoffs,
    import_generated_outputs,
    latest_run_id,
    next_status,
    review_status,
)

from .artifacts import ArtifactIndex, build_artifact_index
from .models import ProjectState


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    return read_json(path) if path.is_file() else None


def list_json_items(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = read_json(path)
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def project_state(project_dir: Path, project_id: str) -> ProjectState:
    project_dir = project_dir.expanduser().resolve()
    project = load_project(project_dir)
    gate_status = next_status(project_dir)
    active_run_id = latest_run_id(project_dir)
    artifact_index = build_artifact_index(project_dir, project_id)
    validation = validate_project(project_dir, write_report=False)
    review = review_status(project_dir, active_run_id) if active_run_id else None
    gate = gate_status.to_dict()
    gate["install_ready"] = bool(review and review.get("install_ready"))
    return {
        "project_id": project_id,
        "project_dir": str(project_dir),
        "manifest": project.to_dict(),
        "gate": {
            "stage": str(gate.get("stage", "")),
            "next_action": str(gate.get("next_action", "")),
            "required_user_input": list(gate.get("required_user_input", [])),
            "artifacts_to_show_user": list(gate.get("artifacts_to_show_user", [])),
            "blocked_actions": list(gate.get("blocked_actions", [])),
            "recommended_command": gate.get("recommended_command"),
            "install_ready": bool(gate.get("install_ready")),
        },
        "artifacts": artifact_index.artifacts,
        "sources": list_json_items(project_dir / SOURCE_MANIFEST, "images"),
        "candidates": list_json_items(project_dir / CANDIDATE_INDEX, "candidates"),
        "selected_candidate": read_json_if_exists(project_dir / SELECTED_CANDIDATE),
        "character_card": read_json_if_exists(project_dir / "character" / "character-card.json"),
        "style_sheet": read_json_if_exists(project_dir / STYLE_PATH),
        "active_run_id": active_run_id,
        "qa": review,
        "approvals": list(review.get("approvals", [])) if review else [],
        "exports": [item for item in artifact_index.artifacts if item["kind"] == "export"],
        "validation": {
            "ok": validation.ok,
            "issues": [issue.to_dict() for issue in validation.issues],
            "checked_files": validation.checked_files,
        },
    }


def artifact_index(project_dir: Path, project_id: str) -> ArtifactIndex:
    return build_artifact_index(project_dir, project_id)


def create_project_action(project_dir: Path, project_id: str, pet_id: str, display_name: str, species: str) -> ProjectState:
    init_project(project_dir, pet_id=pet_id, display_name=display_name, species=species)
    return project_state(project_dir, project_id)


def ingest_source_images(project_dir: Path, project_id: str, sources: list[Path], notes: str = "") -> ProjectState:
    ingest_images(project_dir, sources, role="primary_reference", notes=notes)
    draft_source_card(project_dir, user_notes=notes)
    return project_state(project_dir, project_id)


def update_source_card_action(project_dir: Path, project_id: str, data: dict[str, Any]) -> ProjectState:
    current = read_json_if_exists(project_dir / SOURCE_CARD) or {}
    current.update(data)
    write_json(project_dir / SOURCE_CARD, current)
    return project_state(project_dir, project_id)


def plan_candidates_action(project_dir: Path, project_id: str, provider: str, model_alias: str, count: int) -> ProjectState:
    plan_baseline_candidates(project_dir=project_dir, provider=provider, model_alias=model_alias, count=count)
    return project_state(project_dir, project_id)


def register_candidate_image_action(project_dir: Path, project_id: str, candidate_id: str, image_path: Path) -> ProjectState:
    store_candidate_image(project_dir=project_dir, candidate_id=candidate_id, image_path=image_path)
    return project_state(project_dir, project_id)


def select_candidate_action(project_dir: Path, project_id: str, candidate_id: str, image_path: Path | None, notes: str) -> ProjectState:
    select_baseline_candidate(project_dir=project_dir, candidate_id=candidate_id, image_path=image_path, notes=notes)
    return project_state(project_dir, project_id)


def style_default_action(
    project_dir: Path,
    project_id: str,
    preset: str = "soft-lifelike",
    subject_kind: str = "pet",
    user_style: list[str] | None = None,
    ai_critique: list[str] | None = None,
    refresh: bool = True,
) -> ProjectState:
    if refresh or not (project_dir / STYLE_PATH).is_file():
        save_default_style_sheet(
            project_dir,
            style_preset=preset,
            subject_kind=subject_kind,
            user_style_overrides=user_style or [],
            ai_critique_overrides=ai_critique or [],
        )
    return project_state(project_dir, project_id)


def record_critique_action(
    project_dir: Path,
    project_id: str,
    critique_id: str,
    target: str,
    author: str,
    findings: list[str],
    recommendations: list[str],
    identity_score: float | None = None,
    style_score: float | None = None,
    apply_to_style: bool = False,
) -> ProjectState:
    record_critique(
        project_dir=project_dir,
        critique_id=critique_id,
        target=target,
        author=author,
        findings=findings,
        recommendations=recommendations,
        identity_score=identity_score,
        style_score=style_score,
        apply_to_style=apply_to_style,
    )
    return project_state(project_dir, project_id)


def record_feedback_action(
    project_dir: Path,
    project_id: str,
    target: str,
    text: str,
    author: str = "human",
    branch_id: str | None = None,
    parent: str = "main",
    create_branch: bool = True,
) -> ProjectState:
    create_feedback_event(
        project_dir=project_dir,
        target=target,
        text=text,
        author=author,
        branch_id=branch_id,
        parent=parent,
        create_branch=create_branch,
    )
    return project_state(project_dir, project_id)


def plan_rows_action(project_dir: Path, project_id: str, run_id: str, provider: str, model_alias: str, character_reference: str | None) -> ProjectState:
    plan_row_generation_jobs(
        project_dir=project_dir,
        run_id=run_id,
        provider=provider,
        model_alias=model_alias,
        character_reference=character_reference,
    )
    return project_state(project_dir, project_id)


def generate_handoff_action(project_dir: Path, project_id: str, run_id: str, all_jobs: bool = True, job_ids: list[str] | None = None) -> ProjectState:
    generate_handoffs(project_dir, run_id=run_id, all_jobs=all_jobs, job_ids=job_ids)
    return project_state(project_dir, project_id)


def import_generated_action(project_dir: Path, project_id: str, run_id: str, mapping: dict[str, str]) -> ProjectState:
    import_generated_outputs(project_dir, run_id=run_id, mapping=mapping)
    return project_state(project_dir, project_id)


def build_review_action(project_dir: Path, project_id: str, run_id: str, row_provenance: str = "provider_generated") -> ProjectState:
    build_review(project_dir, run_id=run_id, row_provenance=row_provenance)
    return project_state(project_dir, project_id)


def approve_action(project_dir: Path, project_id: str, run_id: str, notes: str, artifact: str = "contact-sheet", decision: str = "approved") -> ProjectState:
    approve_artifact(project_dir=project_dir, run_id=run_id, artifact=artifact, decision=decision, notes=notes)
    return project_state(project_dir, project_id)


def finish_action(
    project_dir: Path,
    project_id: str,
    run_id: str,
    approval_notes: str,
    row_provenance: str = "provider_generated",
    install_root: Path | None = None,
    override_reason: str | None = None,
) -> ProjectState:
    finish_run(
        project_dir=project_dir,
        run_id=run_id,
        approval_notes=approval_notes,
        row_provenance=row_provenance,
        install_root=install_root,
        override_reason=override_reason,
    )
    return project_state(project_dir, project_id)


def export_action(project_dir: Path, project_id: str, kind: str, run_id: str, output_dir: Path | None = None) -> ProjectState:
    if kind == "project":
        export_project_bundle(project_dir, run_id=run_id, output_dir=output_dir, zip_output=True)
    elif kind == "petdex":
        export_petdex_package(project_dir, run_id=run_id, output_dir=output_dir, zip_output=True)
    else:
        raise ValueError("export kind must be project or petdex")
    return project_state(project_dir, project_id)
