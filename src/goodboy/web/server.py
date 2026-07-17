"""FastAPI server for the Goodboy local Review Room UI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .actions import (
    advance_action,
    animation_review_action,
    approve_action,
    assign_source_roles_action,
    artifact_index,
    build_review_action,
    create_project_action,
    export_action,
    finish_action,
    generate_handoff_action,
    import_generated_action,
    ingest_source_images,
    identity_confirm_action,
    identity_handoff_action,
    identity_import_action,
    identity_patch_action,
    likeness_review_action,
    plan_candidates_action,
    plan_rows_action,
    project_state,
    record_critique_action,
    record_feedback_action,
    recover_action,
    register_candidate_image_action,
    review_candidate_action,
    repair_action,
    select_candidate_action,
    style_default_action,
    direction_blind_action,
    direction_blind_payloads_action,
    direction_review_action,
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
    count: int = 3
    provider_consent: bool = False
    evaluation_dimension: str = "likeness"


class CandidateImageRequest(BaseModel):
    image_path: str


class CandidateSelectRequest(BaseModel):
    image_path: Optional[str] = None
    notes: str = ""
    holistic_gestalt_score: Optional[float] = None
    signature_trait_score: Optional[float] = None
    small_size_readability_score: Optional[float] = None
    review_notes: str = ""
    reviewed_by: str = "human"


class CandidateReviewRequest(BaseModel):
    holistic_gestalt_score: float
    signature_trait_score: float
    small_size_readability_score: float
    notes: str
    reviewed_by: str = "human"


class AnimationReviewRequest(BaseModel):
    run_id: str
    verdicts: list[dict[str, Any]] = Field(default_factory=list)
    reviewed_by: str = "human"


class StyleDefaultRequest(BaseModel):
    preset: str = "soft-lifelike"
    subject_kind: str = "pet"
    user_style: list[str] = Field(default_factory=list)
    ai_critique: list[str] = Field(default_factory=list)
    refresh: bool = True


class CritiqueRequest(BaseModel):
    critique_id: str
    target: str
    author: str = "vision_critic"
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
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
    extraction_method: str = "auto"
    chroma_key_hex: Optional[str] = None


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
    include_sources: bool = False


class SourceRolesRequest(BaseModel):
    roles: list[str]
    provider_permissions: Optional[dict[str, bool]] = None


class IdentityHandoffRequest(BaseModel):
    provider: str = "codex_builtin"
    provider_consent: bool = False


class IdentityImportRequest(BaseModel):
    analysis: dict[str, Any]


class IdentityConfirmRequest(BaseModel):
    author: str = "human"


class IdentityPatchRequest(BaseModel):
    trait_id: str
    value: str
    reason: str
    author: str = "human"
    run_id: Optional[str] = None


class LikenessReviewRequest(BaseModel):
    run_id: str
    verdicts: list[dict[str, Any]]
    reviewer: str = "human"
    advisory_metrics: dict[str, Any] = Field(default_factory=dict)


class DirectionReviewRequest(BaseModel):
    run_id: str
    directions: list[dict[str, Any]]
    reviewer: str = "human"


class DirectionBlindRequest(BaseModel):
    run_id: str
    verdict_paths: list[str]


class DirectionBlindPayloadsRequest(BaseModel):
    run_id: str
    reviews: list[dict[str, Any]]


class RepairRequest(BaseModel):
    run_id: str
    job_ids: list[str]
    reason: str
    author: str = "human"


class RecoverRequest(BaseModel):
    run_id: str


class AdvanceRequest(BaseModel):
    run_id: Optional[str] = None
    provider: str = "codex_builtin"
    model_alias: str = "codex-imagegen"
    candidate_id: Optional[str] = None
    baseline_image: Optional[str] = None
    selection_notes: str = ""
    generated_map: Optional[dict[str, str]] = None
    row_provenance: str = "provider_generated"
    approval_notes: Optional[str] = None
    install_root: Optional[str] = None
    override_reason: Optional[str] = None
    confirm_identity: bool = False
    provider_consent: bool = False


def packaged_ui_dir() -> Path:
    return Path(__file__).with_name("static")


def create_app(
    registry: ProjectRegistry | None = None,
    *,
    launch_project_id: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Goodboy Review Room")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "::1", "testserver"],
    )
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

    @app.get("/api/launch-context")
    def launch_context() -> dict[str, str | None]:
        if launch_project_id is None:
            return {"project_id": None, "project_dir": None}
        try:
            project_dir = projects.resolve(launch_project_id)
        except KeyError:
            return {"project_id": None, "project_dir": None}
        return {
            "project_id": launch_project_id,
            "project_dir": str(project_dir),
        }

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

    @app.post("/api/projects/{project_id}/advance")
    def advance(project_id: str, payload: AdvanceRequest):
        return state_after(
            project_id,
            lambda project_dir: advance_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                provider=payload.provider,
                model_alias=payload.model_alias,
                candidate_id=payload.candidate_id,
                baseline_image=Path(payload.baseline_image).expanduser().resolve() if payload.baseline_image else None,
                selection_notes=payload.selection_notes,
                generated_map=payload.generated_map,
                row_provenance=payload.row_provenance,
                approval_notes=payload.approval_notes,
                install_root=Path(payload.install_root).expanduser().resolve() if payload.install_root else None,
                override_reason=payload.override_reason,
                confirm_identity=payload.confirm_identity,
                provider_consent=payload.provider_consent,
            ),
        )

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

    @app.post("/api/projects/{project_id}/sources/upload")
    async def upload_sources(
        project_id: str,
        files: list[UploadFile] = File(...),
        notes: str = Form(""),
    ):
        project_dir = resolve_project(project_id)
        try:
            with tempfile.TemporaryDirectory(prefix="goodboy-upload-") as temporary:
                paths: list[Path] = []
                for index, upload in enumerate(files):
                    filename = Path(upload.filename or f"source-{index + 1}.png").name
                    path = Path(temporary) / filename
                    path.write_bytes(await upload.read())
                    paths.append(path)
                return ingest_source_images(
                    project_dir,
                    project_id,
                    paths,
                    notes=notes,
                )
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/source-card")
    def update_source_card(project_id: str, payload: dict[str, Any]):
        return state_after(project_id, lambda project_dir: update_source_card_action(project_dir, project_id, payload))

    @app.post("/api/projects/{project_id}/sources/{source_id}/roles")
    def source_roles(project_id: str, source_id: str, payload: SourceRolesRequest):
        return state_after(
            project_id,
            lambda project_dir: assign_source_roles_action(
                project_dir,
                project_id,
                source_id=source_id,
                roles=payload.roles,
                provider_permissions=payload.provider_permissions,
            ),
        )

    @app.post("/api/projects/{project_id}/identity/handoff")
    def identity_handoff(project_id: str, payload: IdentityHandoffRequest):
        return state_after(
            project_id,
            lambda project_dir: identity_handoff_action(
                project_dir,
                project_id,
                provider=payload.provider,
                provider_consent=payload.provider_consent,
            ),
        )

    @app.post("/api/projects/{project_id}/identity/import")
    def identity_import(project_id: str, payload: IdentityImportRequest):
        return state_after(
            project_id,
            lambda project_dir: identity_import_action(
                project_dir,
                project_id,
                analysis=payload.analysis,
            ),
        )

    @app.post("/api/projects/{project_id}/identity/confirm")
    def identity_confirm(project_id: str, payload: IdentityConfirmRequest):
        return state_after(
            project_id,
            lambda project_dir: identity_confirm_action(
                project_dir,
                project_id,
                author=payload.author,
            ),
        )

    @app.post("/api/projects/{project_id}/identity/patch")
    def identity_patch(project_id: str, payload: IdentityPatchRequest):
        return state_after(
            project_id,
            lambda project_dir: identity_patch_action(
                project_dir,
                project_id,
                trait_id=payload.trait_id,
                value=payload.value,
                reason=payload.reason,
                author=payload.author,
                run_id=payload.run_id,
            ),
        )

    @app.post("/api/projects/{project_id}/candidates/plan")
    def plan_candidates(project_id: str, payload: CandidatePlanRequest):
        return state_after(
            project_id,
            lambda project_dir: plan_candidates_action(
                project_dir,
                project_id,
                payload.provider,
                payload.model_alias,
                payload.count,
                provider_consent=payload.provider_consent,
                evaluation_dimension=payload.evaluation_dimension,
            ),
        )

    @app.post("/api/projects/{project_id}/candidates/{candidate_id}/image")
    def candidate_image(project_id: str, candidate_id: str, payload: CandidateImageRequest):
        return state_after(project_id, lambda project_dir: register_candidate_image_action(project_dir, project_id, candidate_id, Path(payload.image_path).expanduser().resolve()))

    @app.post("/api/projects/{project_id}/candidates/{candidate_id}/select")
    def select_candidate(project_id: str, candidate_id: str, payload: CandidateSelectRequest):
        image_path = Path(payload.image_path).expanduser().resolve() if payload.image_path else None
        return state_after(
            project_id,
            lambda project_dir: select_candidate_action(
                project_dir,
                project_id,
                candidate_id,
                image_path,
                payload.notes,
                holistic_gestalt_score=payload.holistic_gestalt_score,
                signature_trait_score=payload.signature_trait_score,
                small_size_readability_score=payload.small_size_readability_score,
                review_notes=payload.review_notes,
                reviewed_by=payload.reviewed_by,
            ),
        )

    @app.post("/api/projects/{project_id}/candidates/{candidate_id}/review")
    def review_candidate(project_id: str, candidate_id: str, payload: CandidateReviewRequest):
        return state_after(
            project_id,
            lambda project_dir: review_candidate_action(
                project_dir,
                project_id,
                candidate_id,
                holistic_gestalt_score=payload.holistic_gestalt_score,
                signature_trait_score=payload.signature_trait_score,
                small_size_readability_score=payload.small_size_readability_score,
                notes=payload.notes,
                reviewed_by=payload.reviewed_by,
            ),
        )

    @app.post("/api/projects/{project_id}/animation/review")
    def animation_review(project_id: str, payload: AnimationReviewRequest):
        return state_after(
            project_id,
            lambda project_dir: animation_review_action(
                project_dir,
                project_id,
                payload.run_id,
                payload.verdicts,
                payload.reviewed_by,
            ),
        )

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
        return state_after(
            project_id,
            lambda project_dir: import_generated_action(
                project_dir,
                project_id,
                payload.run_id,
                payload.mapping,
                extraction_method=payload.extraction_method,
                chroma_key_hex=payload.chroma_key_hex,
            ),
        )

    @app.post("/api/projects/{project_id}/review/build")
    def review_build(project_id: str, payload: BuildReviewRequest):
        return state_after(project_id, lambda project_dir: build_review_action(project_dir, project_id, payload.run_id, payload.row_provenance))

    @app.post("/api/projects/{project_id}/approval")
    def approval(project_id: str, payload: ApprovalRequest):
        return state_after(project_id, lambda project_dir: approve_action(project_dir, project_id, payload.run_id, payload.notes, artifact=payload.artifact, decision=payload.decision))

    @app.post("/api/projects/{project_id}/review/likeness")
    def likeness_review(project_id: str, payload: LikenessReviewRequest):
        return state_after(
            project_id,
            lambda project_dir: likeness_review_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                verdicts=payload.verdicts,
                reviewer=payload.reviewer,
                advisory_metrics=payload.advisory_metrics,
            ),
        )

    @app.post("/api/projects/{project_id}/review/directions")
    def direction_review(project_id: str, payload: DirectionReviewRequest):
        return state_after(
            project_id,
            lambda project_dir: direction_review_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                directions=payload.directions,
                reviewer=payload.reviewer,
            ),
        )

    @app.post("/api/projects/{project_id}/review/directions/blind")
    def direction_blind(project_id: str, payload: DirectionBlindRequest):
        return state_after(
            project_id,
            lambda project_dir: direction_blind_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                verdict_paths=[Path(item).expanduser().resolve() for item in payload.verdict_paths],
            ),
        )

    @app.post("/api/projects/{project_id}/review/directions/blind-payloads")
    def direction_blind_payloads(project_id: str, payload: DirectionBlindPayloadsRequest):
        return state_after(
            project_id,
            lambda project_dir: direction_blind_payloads_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                reviews=payload.reviews,
            ),
        )

    @app.post("/api/projects/{project_id}/repair")
    def repair(project_id: str, payload: RepairRequest):
        return state_after(
            project_id,
            lambda project_dir: repair_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
                job_ids=payload.job_ids,
                reason=payload.reason,
                author=payload.author,
            ),
        )

    @app.post("/api/projects/{project_id}/recover")
    def recover(project_id: str, payload: RecoverRequest):
        return state_after(
            project_id,
            lambda project_dir: recover_action(
                project_dir,
                project_id,
                run_id=payload.run_id,
            ),
        )

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
        return state_after(
            project_id,
            lambda project_dir: export_action(
                project_dir,
                project_id,
                payload.kind,
                payload.run_id,
                output_dir=output_dir,
                include_sources=payload.include_sources,
            ),
        )

    @app.get("/api/projects/{project_id}/events")
    def events(project_id: str):
        state = state_after(project_id, lambda project_dir: project_state(project_dir, project_id))
        return {"events": state["events"]}

    ui_dir = packaged_ui_dir()
    if (ui_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="review-room")

    return app
