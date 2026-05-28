"""FastAPI server for the Goodboy local Review Room UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .actions import (
    approve_action,
    artifact_index,
    build_review_action,
    create_project_action,
    export_action,
    finish_action,
    generate_handoff_action,
    import_generated_action,
    ingest_source_images,
    plan_candidates_action,
    plan_rows_action,
    project_state,
    record_critique_action,
    record_feedback_action,
    register_candidate_image_action,
    select_candidate_action,
    style_default_action,
    update_source_card_action,
)
from .artifacts import safe_artifact_path
from .registry import ProjectRegistry


class OpenProjectRequest(BaseModel):
    project_dir: str


class CreateProjectRequest(BaseModel):
    project_dir: str
    pet_id: str
    display_name: str
    species: str = "pet"


class IngestSourcesRequest(BaseModel):
    sources: list[str]
    notes: str = ""


class CandidatePlanRequest(BaseModel):
    provider: str = "codex_builtin"
    model_alias: str = "codex-imagegen"
    count: int = 6


class CandidateImageRequest(BaseModel):
    image_path: str


class CandidateSelectRequest(BaseModel):
    image_path: Optional[str] = None
    notes: str = ""


class StyleDefaultRequest(BaseModel):
    preset: str = "soft-lifelike"
    subject_kind: str = "pet"
    user_style: list[str] = []
    ai_critique: list[str] = []
    refresh: bool = True


class CritiqueRequest(BaseModel):
    critique_id: str
    target: str
    author: str = "vision_critic"
    findings: list[str] = []
    recommendations: list[str] = []
    identity_score: Optional[float] = None
    style_score: Optional[float] = None
    apply_to_style: bool = False


class FeedbackRequest(BaseModel):
    target: str
    text: str
    author: str = "human"
    branch_id: Optional[str] = None
    parent: str = "main"
    create_branch: bool = True


class PlanRowsRequest(BaseModel):
    run_id: str
    provider: str = "codex_builtin"
    model_alias: str = "codex-imagegen"
    character_reference: Optional[str] = "character/selected-baseline.png"


class GenerateHandoffRequest(BaseModel):
    run_id: str
    all_jobs: bool = True
    job_ids: Optional[list[str]] = None


class ImportGeneratedRequest(BaseModel):
    run_id: str
    mapping: dict[str, str]


class BuildReviewRequest(BaseModel):
    run_id: str
    row_provenance: str = "provider_generated"


class ApprovalRequest(BaseModel):
    run_id: str
    notes: str
    artifact: str = "contact-sheet"
    decision: str = "approved"


class FinishRequest(BaseModel):
    run_id: str
    approval_notes: str
    row_provenance: str = "provider_generated"
    install_root: Optional[str] = None
    override_reason: Optional[str] = None


class ExportRequest(BaseModel):
    kind: str
    run_id: str
    output_dir: Optional[str] = None


def create_app(registry: ProjectRegistry | None = None) -> FastAPI:
    app = FastAPI(title="Goodboy Review Room")
    projects = registry or ProjectRegistry()

    def resolve_project(project_id: str) -> Path:
        try:
            return projects.resolve(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown project") from exc

    def state_after(project_id: str, call):
        project_dir = resolve_project(project_id)
        try:
            return call(project_dir)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/projects/recent")
    def recent() -> list[dict[str, str]]:
        return projects.recent()

    @app.post("/api/projects/open")
    def open_project(payload: OpenProjectRequest) -> dict[str, str]:
        project_dir = Path(payload.project_dir).expanduser().resolve()
        if not (project_dir / "goodboy.json").is_file():
            raise HTTPException(status_code=400, detail="not a Goodboy project")
        project_id = projects.register(project_dir)
        return {"project_id": project_id, "project_dir": str(project_dir)}

    @app.post("/api/projects/create")
    def create_project(payload: CreateProjectRequest) -> dict[str, Any]:
        project_dir = Path(payload.project_dir).expanduser().resolve()
        project_id = projects.register(project_dir)
        try:
            return create_project_action(project_dir, project_id, payload.pet_id, payload.display_name, payload.species)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/state")
    def state(project_id: str):
        return state_after(project_id, lambda project_dir: project_state(project_dir, project_id))

    @app.get("/api/projects/{project_id}/artifacts")
    def artifacts(project_id: str):
        return state_after(project_id, lambda project_dir: artifact_index(project_dir, project_id).artifacts)

    @app.get("/api/projects/{project_id}/artifacts/{artifact_id}")
    def artifact(project_id: str, artifact_id: str):
        project_dir = resolve_project(project_id)
        index = artifact_index(project_dir, project_id)
        ref = index.by_id.get(artifact_id)
        if not ref:
            raise HTTPException(status_code=404, detail="unknown artifact")
        try:
            path = safe_artifact_path(project_dir, ref["relative_path"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return FileResponse(path)

    @app.post("/api/projects/{project_id}/sources/ingest")
    def ingest_sources(project_id: str, payload: IngestSourcesRequest):
        return state_after(
            project_id,
            lambda project_dir: ingest_source_images(
                project_dir,
                project_id,
                [Path(item).expanduser().resolve() for item in payload.sources],
                notes=payload.notes,
            ),
        )

    @app.post("/api/projects/{project_id}/source-card")
    def update_source_card(project_id: str, payload: dict[str, Any]):
        return state_after(project_id, lambda project_dir: update_source_card_action(project_dir, project_id, payload))

    @app.post("/api/projects/{project_id}/candidates/plan")
    def plan_candidates(project_id: str, payload: CandidatePlanRequest):
        return state_after(project_id, lambda project_dir: plan_candidates_action(project_dir, project_id, payload.provider, payload.model_alias, payload.count))

    @app.post("/api/projects/{project_id}/candidates/{candidate_id}/image")
    def candidate_image(project_id: str, candidate_id: str, payload: CandidateImageRequest):
        return state_after(project_id, lambda project_dir: register_candidate_image_action(project_dir, project_id, candidate_id, Path(payload.image_path).expanduser().resolve()))

    @app.post("/api/projects/{project_id}/candidates/{candidate_id}/select")
    def select_candidate(project_id: str, candidate_id: str, payload: CandidateSelectRequest):
        image_path = Path(payload.image_path).expanduser().resolve() if payload.image_path else None
        return state_after(project_id, lambda project_dir: select_candidate_action(project_dir, project_id, candidate_id, image_path, payload.notes))

    @app.post("/api/projects/{project_id}/style/default")
    def style_default(project_id: str, payload: StyleDefaultRequest):
        return state_after(
            project_id,
            lambda project_dir: style_default_action(
                project_dir,
                project_id,
                preset=payload.preset,
                subject_kind=payload.subject_kind,
                user_style=payload.user_style,
                ai_critique=payload.ai_critique,
                refresh=payload.refresh,
            ),
        )

    @app.post("/api/projects/{project_id}/critique")
    def critique(project_id: str, payload: CritiqueRequest):
        return state_after(
            project_id,
            lambda project_dir: record_critique_action(
                project_dir,
                project_id,
                critique_id=payload.critique_id,
                target=payload.target,
                author=payload.author,
                findings=payload.findings,
                recommendations=payload.recommendations,
                identity_score=payload.identity_score,
                style_score=payload.style_score,
                apply_to_style=payload.apply_to_style,
            ),
        )

    @app.post("/api/projects/{project_id}/feedback")
    def feedback(project_id: str, payload: FeedbackRequest):
        return state_after(
            project_id,
            lambda project_dir: record_feedback_action(
                project_dir,
                project_id,
                target=payload.target,
                text=payload.text,
                author=payload.author,
                branch_id=payload.branch_id,
                parent=payload.parent,
                create_branch=payload.create_branch,
            ),
        )

    @app.post("/api/projects/{project_id}/rows/plan")
    def plan_rows(project_id: str, payload: PlanRowsRequest):
        return state_after(
            project_id,
            lambda project_dir: plan_rows_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                provider=payload.provider,
                model_alias=payload.model_alias,
                character_reference=payload.character_reference,
            ),
        )

    @app.post("/api/projects/{project_id}/generation/handoff")
    def generation_handoff(project_id: str, payload: GenerateHandoffRequest):
        return state_after(project_id, lambda project_dir: generate_handoff_action(project_dir, project_id, payload.run_id, all_jobs=payload.all_jobs, job_ids=payload.job_ids))

    @app.post("/api/projects/{project_id}/generation/import")
    def generation_import(project_id: str, payload: ImportGeneratedRequest):
        return state_after(project_id, lambda project_dir: import_generated_action(project_dir, project_id, payload.run_id, payload.mapping))

    @app.post("/api/projects/{project_id}/review/build")
    def review_build(project_id: str, payload: BuildReviewRequest):
        return state_after(project_id, lambda project_dir: build_review_action(project_dir, project_id, payload.run_id, payload.row_provenance))

    @app.post("/api/projects/{project_id}/approval")
    def approval(project_id: str, payload: ApprovalRequest):
        return state_after(project_id, lambda project_dir: approve_action(project_dir, project_id, payload.run_id, payload.notes, artifact=payload.artifact, decision=payload.decision))

    @app.post("/api/projects/{project_id}/finish")
    def finish(project_id: str, payload: FinishRequest):
        install_root = Path(payload.install_root).expanduser().resolve() if payload.install_root else None
        return state_after(
            project_id,
            lambda project_dir: finish_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                approval_notes=payload.approval_notes,
                row_provenance=payload.row_provenance,
                install_root=install_root,
                override_reason=payload.override_reason,
            ),
        )

    @app.post("/api/projects/{project_id}/export")
    def export(project_id: str, payload: ExportRequest):
        output_dir = Path(payload.output_dir).expanduser().resolve() if payload.output_dir else None
        return state_after(project_id, lambda project_dir: export_action(project_dir, project_id, payload.kind, payload.run_id, output_dir=output_dir))

    @app.get("/api/projects/{project_id}/events")
    def events(project_id: str):
        state_after(project_id, lambda project_dir: project_state(project_dir, project_id))
        return {"events": []}

    return app
