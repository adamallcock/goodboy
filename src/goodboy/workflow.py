"""Agent-safe, gate-driven Goodboy v2 workflow rails."""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from .adapters import prepare_handoff
from .candidates import (
    CANDIDATE_INDEX,
    SELECTED_CANDIDATE,
    build_candidate_contact_sheet,
    plan_baseline_candidates,
    select_baseline_candidate,
)
from .contracts import STATE_ORDER, V2_OUTPUT_CONTRACT
from .identity import (
    IDENTITY_PROFILE,
    REFERENCE_COVERAGE,
    analyze_reference_coverage,
    confirm_identity_profile,
    create_identity_pack,
    draft_identity_profile,
    has_provider_consent,
    likeness_is_approved,
    load_identity_profile,
    load_likeness_report,
    source_contact_sheet,
)
from .ingest import draft_source_card, ingest_images, load_source_images
from .jobs import (
    complete_job,
    fail_job,
    job_graph,
    load_jobs,
    recover_run,
    refresh_readiness,
)
from .jsonio import read_json, write_json
from .pipeline import (
    assert_run_installable,
    build_from_row_strips,
    install_package,
)
from .project import init_project, load_project, save_project
from .qa import animation_is_approved, write_animation_correctness_report
from .safety import find_suspicious_renderer_scripts
from .schemas import ApprovalRecord, GenerationJob, utc_now
from .style import STYLE_PATH, plan_row_generation_jobs, save_default_style_sheet
from .validation import validate_project
from .v2_backend import (
    extract_and_compose_cardinals,
    register_look_row_9,
    v2_review_gate,
    validate_v2_package,
)


WORKFLOW_STATE = "workflow-state.json"
APPROVED_PROVENANCE = {"provider_generated", "user_supplied", "test_fixture"}
STANDARD_JOB_IDS = [f"row-{state}" for state in STATE_ORDER]


def default_do_not() -> list[str]:
    return [
        "do not write renderer, drawing, sprite-maker, or row-strip generator scripts",
        "do not synthesize pet art with Pillow, SVG, canvas, or handwritten image code",
        "do not install without approved provenance and recorded direction, likeness, and visual approval",
    ]


@dataclass
class WorkflowStatus:
    stage: str
    next_action: str
    allowed_commands: list[str]
    blocked_actions: list[str]
    recommended_command: str | None = None
    acceptable_commands: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    do_not_run: list[str] = field(default_factory=list)
    already_done: list[str] = field(default_factory=list)
    after_provider_generation: str | None = None
    required_user_input: list[str] = field(default_factory=list)
    artifacts_to_show_user: list[str] = field(default_factory=list)
    do_not: list[str] = field(default_factory=default_do_not)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_project(
    *,
    project_dir: Path,
    pet_id: str,
    display_name: str,
    species: str,
    sources: list[Path],
    provider: str = "codex_builtin",
    model_alias: str = "codex-imagegen",
    candidate_count: int = 6,
    notes: str = "",
) -> WorkflowStatus:
    """Start a My Pet project and stop at the identity confirmation gate."""

    del provider, model_alias, candidate_count  # provider work starts only after explicit consent
    init_project(project_dir, pet_id=pet_id, display_name=display_name, species=species)
    ingest_images(project_dir, sources, role="primary_reference", notes=notes)
    draft_source_card(project_dir, user_notes=notes)
    analyze_reference_coverage(project_dir)
    draft_identity_profile(project_dir)
    source_contact_sheet(project_dir)
    status = next_status(project_dir)
    write_workflow_state(project_dir, status)
    return status


def infer_stage(project_dir: Path, run_id: str | None) -> str:
    if not load_source_images(project_dir):
        return "initialized"
    identity = load_identity_profile(project_dir)
    if identity is None or identity.status != "confirmed":
        return "identity_review"
    if not (project_dir / CANDIDATE_INDEX).is_file():
        return "identity_confirmed"
    if not (project_dir / SELECTED_CANDIDATE).is_file():
        return "baselines_planned"
    if run_id is None:
        return "baseline_selected"
    run_dir = project_dir / "runs" / run_id
    if not (run_dir / "run-summary.json").is_file():
        return "generation_in_progress"
    if (run_dir / "install.json").is_file():
        return "installed"
    if not review_gates(project_dir, run_id)["all_reviews_complete"]:
        return "quality_review"
    if has_visual_approval(project_dir, run_id):
        return "visually_approved"
    return "built_for_review"


def next_status(project_dir: Path) -> WorkflowStatus:
    project_dir = project_dir.resolve()
    if not (project_dir / "goodboy.json").is_file():
        status = WorkflowStatus(
            stage="missing_project",
            next_action="start_project",
            allowed_commands=["goodboy start <project-dir> --pet-id <id> --display-name <name> --source <image>..."],
            blocked_actions=["all build and install commands"],
            recommended_command=f"goodboy start {project_dir} --pet-id <id> --display-name <name> --source <image>",
            missing_inputs=["source images", "pet id", "display name"],
            required_user_input=["source images", "pet id", "display name"],
        )
        write_workflow_state(project_dir, status)
        return status

    run_id = latest_run_id(project_dir)
    stage = infer_stage(project_dir, run_id)
    command = f"goodboy advance {project_dir} --agent-mode"
    if stage == "initialized":
        status = WorkflowStatus(
            stage=stage,
            next_action="ingest_sources",
            allowed_commands=["goodboy ingest <project-dir> <image>..."],
            blocked_actions=["identity confirmation", "generation", "install"],
            recommended_command=f"goodboy ingest {project_dir} <image>",
            missing_inputs=["source images"],
            required_user_input=["source images"],
        )
    elif stage == "identity_review":
        status = WorkflowStatus(
            stage=stage,
            next_action="confirm_identity",
            allowed_commands=[
                "goodboy identity-show <project-dir>",
                "goodboy identity-handoff <project-dir>",
                "goodboy identity-import <project-dir> --analysis <json>",
                "goodboy identity-confirm <project-dir>",
                f"{command} --confirm-identity",
            ],
            blocked_actions=["baseline generation", "animation generation", "install"],
            recommended_command=f"goodboy identity-show {project_dir}",
            acceptable_commands=[f"{command} --confirm-identity --provider-consent"],
            required_user_input=[
                "confirm or correct defining pet traits",
                "consent to EXIF-stripped provider derivatives before likeness generation",
            ],
            artifacts_to_show_user=[
                REFERENCE_COVERAGE,
                IDENTITY_PROFILE,
                "identity/source-contact-sheet.png",
            ],
            already_done=["source ingest", "reference coverage", "identity draft"],
        )
    elif stage == "identity_confirmed":
        status = WorkflowStatus(
            stage=stage,
            next_action="plan_baselines",
            allowed_commands=[
                f"{command} --provider-consent",
                "goodboy plan-candidates <project-dir> --provider <provider> --model-alias <model> --provider-consent",
            ],
            blocked_actions=["animation rows before baseline selection", "install"],
            recommended_command=f"{command} --provider-consent",
            already_done=["identity confirmation"],
        )
    elif stage == "baselines_planned":
        status = WorkflowStatus(
            stage=stage,
            next_action="generate_and_select_likeness_baseline",
            allowed_commands=[
                command,
                "generate candidate images from candidates/*/prompt.md",
                "goodboy select-candidate <project-dir> --candidate-id <id> --image-path <image>",
            ],
            blocked_actions=["animation generation", "install"],
            recommended_command=command,
            missing_inputs=["provider-generated candidate images", "user likeness choice"],
            required_user_input=["choose the candidate that looks most like the source pet"],
            artifacts_to_show_user=["candidates/contact-sheet.png", CANDIDATE_INDEX],
            already_done=["identity confirmation", "baseline planning"],
        )
    elif stage == "baseline_selected":
        status = WorkflowStatus(
            stage=stage,
            next_action="plan_v2_generation",
            allowed_commands=[command, "goodboy plan-rows <project-dir> --run-id <id>"],
            blocked_actions=["build before provider outputs", "install"],
            recommended_command=f"{command} --run-id <run-id>",
            already_done=["likeness baseline selection"],
        )
    elif stage == "generation_in_progress":
        graph = job_graph(project_dir, run_id or "")
        ready = graph["ready"]
        status = WorkflowStatus(
            stage=stage,
            next_action="generate_ready_jobs",
            allowed_commands=[
                f"{command} --run-id {run_id}",
                f"goodboy generate-handoff {project_dir} --run-id {run_id} --all",
                f"goodboy import-generated {project_dir} --run-id {run_id} --map <json>",
            ],
            blocked_actions=["generating dependency-blocked look rows", "install"],
            recommended_command=f"{command} --run-id {run_id}",
            after_provider_generation=(
                f"{command} --run-id {run_id} --generated-map <json> "
                "--row-provenance provider_generated"
            ),
            missing_inputs=[job["state"] or job["id"] for job in missing_generated_outputs(project_dir) if job["run_id"] == run_id],
            required_user_input=["provider outputs for ready jobs"] if ready else [],
            artifacts_to_show_user=[f"runs/{run_id}/handoff-summary.json"],
            already_done=["style-default", "v2 job graph planned"],
        )
    elif stage in {"quality_review", "built_for_review"}:
        gates = review_gates(project_dir, run_id or "")
        status = WorkflowStatus(
            stage=stage,
            next_action="complete_v2_reviews" if stage == "quality_review" else "visual_approval",
            allowed_commands=[
                f"goodboy review-status {project_dir} --run-id {run_id}",
                f"goodboy direction-review {project_dir} --run-id {run_id} --verdicts <json>",
                f"goodboy direction-blind-import {project_dir} --run-id {run_id} --verdict <json> --verdict <json> --verdict <json>",
                f"goodboy likeness-review {project_dir} --run-id {run_id} --verdicts <json>",
                f"goodboy animation-review {project_dir} --run-id {run_id} --verdicts <json>",
                f"goodboy approve {project_dir} --run-id {run_id} --notes <notes>",
            ],
            blocked_actions=["install until every v2 review gate passes"],
            recommended_command=f"goodboy review-status {project_dir} --run-id {run_id} --agent-mode",
            missing_inputs=gates["missing_reviews"],
            required_user_input=gates["missing_reviews"],
            artifacts_to_show_user=review_artifacts(project_dir, run_id),
            already_done=["v2 atlas build", "deterministic validation"],
        )
    elif stage == "visually_approved":
        status = WorkflowStatus(
            stage=stage,
            next_action="install",
            allowed_commands=[
                f"{command} --run-id {run_id} --row-provenance provider_generated",
                f"goodboy install {project_dir} --run-id {run_id} --row-provenance provider_generated",
            ],
            blocked_actions=["install if any source artifact has changed since review"],
            recommended_command=f"{command} --run-id {run_id} --row-provenance provider_generated",
            artifacts_to_show_user=review_artifacts(project_dir, run_id),
            already_done=["direction review", "likeness review", "visual approval"],
        )
    else:
        status = WorkflowStatus(
            stage=stage,
            next_action="done",
            allowed_commands=["goodboy validate <project-dir>", "goodboy export petdex <project-dir> --run-id <id>"],
            blocked_actions=["creating local renderer scripts"],
            recommended_command=f"goodboy validate {project_dir}",
            artifacts_to_show_user=review_artifacts(project_dir, run_id),
            already_done=["v2 package", "reviews", "install"],
        )
    write_workflow_state(project_dir, status)
    return status


def latest_run_id(project_dir: Path) -> str | None:
    try:
        project = load_project(project_dir)
    except FileNotFoundError:
        return None
    if project.active_run_id:
        return project.active_run_id
    runs_dir = project_dir / "runs"
    if not runs_dir.is_dir():
        return None
    runs = sorted(path.name for path in runs_dir.iterdir() if path.is_dir())
    return runs[-1] if runs else None


def write_workflow_state(project_dir: Path, status: WorkflowStatus) -> None:
    if project_dir.exists():
        write_json(project_dir / WORKFLOW_STATE, status.to_dict())


def approve_artifact(
    *,
    project_dir: Path,
    run_id: str,
    artifact: str,
    decision: str,
    notes: str,
    author: str = "human",
) -> ApprovalRecord:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    if not notes.strip():
        raise ValueError("approval notes are required")
    run_dir = project_dir / "runs" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"missing run: {run_dir}")
    approval = ApprovalRecord(
        id=f"{artifact}-{decision}-{utc_now()}",
        run_id=run_id,
        artifact=artifact,
        decision=decision,
        notes=notes,
        author=author,
    )
    write_json(run_dir / "approvals" / f"{artifact}.json", approval.to_dict())
    next_status(project_dir)
    return approval


def load_approvals(project_dir: Path, run_id: str) -> list[ApprovalRecord]:
    approvals_dir = project_dir / "runs" / run_id / "approvals"
    if not approvals_dir.is_dir():
        return []
    return [
        ApprovalRecord.from_dict(read_json(path))
        for path in sorted(approvals_dir.glob("*.json"))
    ]


def has_visual_approval(project_dir: Path, run_id: str | None) -> bool:
    if not run_id:
        return False
    return any(
        record.decision == "approved" and record.artifact in {"contact-sheet", "final-review"}
        for record in load_approvals(project_dir, run_id)
    )


def visual_approval_note(project_dir: Path, run_id: str) -> str | None:
    notes = [
        record.notes
        for record in load_approvals(project_dir, run_id)
        if record.decision == "approved" and record.artifact in {"contact-sheet", "final-review"}
    ]
    return "; ".join(notes) if notes else None


def review_gates(project_dir: Path, run_id: str) -> dict[str, Any]:
    run_dir = project_dir / "runs" / run_id
    project = load_project(project_dir)
    is_v2 = project.contract_id == V2_OUTPUT_CONTRACT.contract_id
    policy_path = run_dir / "qa" / "install-policy.json"
    policy = read_json(policy_path) if policy_path.is_file() else {}
    direction = (
        v2_review_gate(
            run_dir,
            allow_test_fixture=policy.get("row_provenance") == "test_fixture",
        )
        if is_v2
        else {"ok": True, "hard_failures": [], "warnings": []}
    )
    likeness_required = load_identity_profile(project_dir) is not None
    likeness = load_likeness_report(project_dir, run_id) if likeness_required else None
    likeness_ok = not likeness_required or likeness_is_approved(project_dir, run_id)
    animation_required = is_v2 and policy.get("row_provenance") != "test_fixture"
    animation_ok = not animation_required or animation_is_approved(project_dir, run_id)
    if is_v2 and (run_dir / "qa" / "previews").is_dir():
        write_animation_correctness_report(run_dir)
    missing: list[str] = []
    if not direction["ok"]:
        missing.extend(direction["hard_failures"])
    if likeness_required and not likeness_ok:
        missing.append("source-likeness verdicts and approval")
    if animation_required and not animation_ok:
        missing.append("state-by-state animation semantics, continuity, and identity review")
    return {
        "direction": direction,
        "likeness_required": likeness_required,
        "likeness": likeness.to_dict() if likeness else None,
        "likeness_ok": likeness_ok,
        "animation_required": animation_required,
        "animation_ok": animation_ok,
        "missing_reviews": list(dict.fromkeys(missing)),
        "all_reviews_complete": direction["ok"] and likeness_ok and animation_ok,
    }


def review_status(project_dir: Path, run_id: str) -> dict[str, Any]:
    run_dir = project_dir / "runs" / run_id
    artifacts = review_artifacts(project_dir, run_id)
    approvals = [record.to_dict() for record in load_approvals(project_dir, run_id)]
    policy_path = run_dir / "qa" / "install-policy.json"
    policy = read_json(policy_path) if policy_path.is_file() else None
    suspicious = find_suspicious_renderer_scripts(project_dir)
    gates = review_gates(project_dir, run_id)
    policy_ok = bool(policy) and not policy.get("hard_failures", [])
    return {
        "run_id": run_id,
        "stage": infer_stage(project_dir, run_id),
        "review_artifacts": artifacts,
        "approvals": approvals,
        "has_visual_approval": has_visual_approval(project_dir, run_id),
        "review_gates": gates,
        "install_policy": policy,
        "suspicious_renderer_scripts": suspicious,
        "install_ready": (
            bool(artifacts)
            and has_visual_approval(project_dir, run_id)
            and gates["all_reviews_complete"]
            and policy_ok
            and not suspicious
        ),
    }


def doctor(project_dir: Path) -> dict[str, Any]:
    validation = validate_project(project_dir, write_report=False)
    workflow = next_status(project_dir)
    run_id = latest_run_id(project_dir)
    return {
        "validation": validation.to_dict(),
        "workflow": workflow.to_dict(),
        "providers": provider_status(project_dir),
        "api_accelerators": api_accelerators(),
        "missing_generated_outputs": missing_generated_outputs(project_dir),
        "job_graph": job_graph(project_dir, run_id) if run_id and (project_dir / "runs" / run_id / "generation-jobs.json").is_file() else None,
        "suspicious_renderer_scripts": find_suspicious_renderer_scripts(project_dir),
        "tests_needed_for_project_artifacts_only": False,
    }


def api_accelerators() -> dict[str, dict[str, str | bool]]:
    return {
        "openai_images": {
            "status": "available" if os.environ.get("OPENAI_API_KEY") else "optional_not_configured",
            "env_var": "OPENAI_API_KEY",
            "note": "optional direct API accelerator; Codex built-in handoff works without it",
        },
        "gemini_nano_banana_2": {
            "status": "available" if os.environ.get("GEMINI_API_KEY") else "optional_not_configured",
            "env_var": "GEMINI_API_KEY",
            "note": "optional direct API accelerator",
        },
        "gemini_nano_banana_pro": {
            "status": "available" if os.environ.get("GEMINI_API_KEY") else "optional_not_configured",
            "env_var": "GEMINI_API_KEY",
            "note": "optional high-fidelity direct API accelerator",
        },
    }


def provider_status(project_dir: Path) -> dict[str, dict[str, str | bool]]:
    status: dict[str, dict[str, str | bool]] = {}
    for provider in sorted(used_providers(project_dir)):
        if provider == "codex_builtin":
            status[provider] = {"required": "Codex interactive image generation"}
        elif provider == "openai_images":
            status[provider] = {"OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY"))}
        elif provider.startswith("gemini"):
            status[provider] = {"GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY"))}
        else:
            status[provider] = {"known": False}
    return status


def used_providers(project_dir: Path) -> set[str]:
    providers: set[str] = set()
    candidate_path = project_dir / CANDIDATE_INDEX
    if candidate_path.is_file():
        providers.update(
            str(item["provider"])
            for item in read_json(candidate_path).get("candidates", [])
            if item.get("provider")
        )
    for jobs_path in sorted((project_dir / "runs").glob("*/generation-jobs.json")):
        providers.update(
            str(item["provider"])
            for item in read_json(jobs_path).get("jobs", [])
            if item.get("provider")
        )
    return providers


def missing_generated_outputs(project_dir: Path) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for jobs_path in sorted((project_dir / "runs").glob("*/generation-jobs.json")):
        run_id = jobs_path.parent.name
        for job in read_json(jobs_path).get("jobs", []):
            expected = job.get("expected_output")
            if expected and not (project_dir / expected).is_file() and job.get("status") not in {"cancelled", "superseded"}:
                missing.append(
                    {
                        "run_id": run_id,
                        "job_id": str(job.get("id", "")),
                        "state": str(job.get("state", "")),
                        "expected_output": str(expected),
                    }
                )
    return missing


def default_run_id() -> str:
    return f"v2-{utc_now()[:10].replace('-', '')}"


def advance_project(
    *,
    project_dir: Path,
    run_id: str | None = None,
    provider: str = "codex_builtin",
    model_alias: str = "codex-imagegen",
    candidate_id: str | None = None,
    baseline_image: Path | None = None,
    selection_notes: str = "",
    holistic_gestalt_score: float | None = None,
    signature_trait_score: float | None = None,
    small_size_readability_score: float | None = None,
    candidate_review_notes: str = "",
    candidate_reviewed_by: str = "human",
    generated_map: dict[str, str] | None = None,
    row_provenance: str = "provider_generated",
    approval_notes: str | None = None,
    install_root: Path | None = None,
    override_reason: str | None = None,
    confirm_identity: bool = False,
    provider_consent: bool = False,
) -> dict[str, Any]:
    """Advance deterministic work until the next real provider or human gate."""

    project_dir = project_dir.resolve()
    before = next_status(project_dir)
    actions: list[str] = []
    outputs: dict[str, Any] = {}
    stage = before.stage

    if stage == "initialized":
        return advance_payload(before, actions, "source_images", "Add source images.", outputs)

    if stage == "identity_review":
        if not confirm_identity:
            return advance_payload(
                before,
                actions,
                "identity_confirmation",
                "Review the evidence-linked identity profile, correct it if needed, then confirm it.",
                outputs,
            )
        outputs["identity"] = confirm_identity_profile(project_dir).to_dict()
        actions.append("identity-confirm")
        stage = "identity_confirmed"

    if stage == "identity_confirmed":
        if not provider_consent and not has_provider_consent(project_dir, provider):
            return advance_payload(
                next_status(project_dir),
                actions,
                "provider_consent",
                (
                    f"Approve EXIF-stripped source derivatives for `{provider}` before likeness "
                    "candidate generation. Original photos remain local."
                ),
                outputs,
            )
        plan_baseline_candidates(
            project_dir=project_dir,
            provider=provider,
            model_alias=model_alias,
            provider_consent=provider_consent,
        )
        build_candidate_contact_sheet(project_dir=project_dir)
        actions.extend(["plan-candidates", "candidate-sheet"])
        return advance_payload(
            next_status(project_dir),
            actions,
            "baseline_generation_or_selection",
            "Generate the planned likeness candidates and choose the one that most resembles the source pet.",
            outputs,
        )

    if stage == "baselines_planned":
        build_candidate_contact_sheet(project_dir=project_dir)
        actions.append("candidate-sheet")
        if not (candidate_id and baseline_image):
            return advance_payload(
                next_status(project_dir),
                actions,
                "baseline_generation_or_selection",
                "Review candidates/contact-sheet.png and choose the strongest likeness baseline.",
                outputs,
            )
        outputs["selection"] = select_baseline_candidate(
            project_dir=project_dir,
            candidate_id=candidate_id,
            image_path=baseline_image,
            notes=selection_notes,
            holistic_gestalt_score=holistic_gestalt_score,
            signature_trait_score=signature_trait_score,
            small_size_readability_score=small_size_readability_score,
            review_notes=candidate_review_notes,
            reviewed_by=candidate_reviewed_by,
        ).to_dict()
        actions.append("select-candidate")
        stage = "baseline_selected"

    if stage == "baseline_selected":
        if not (project_dir / STYLE_PATH).is_file():
            save_default_style_sheet(project_dir)
            actions.append("style-default")
        resolved_run_id = run_id or default_run_id()
        plan_row_generation_jobs(
            project_dir=project_dir,
            run_id=resolved_run_id,
            provider=provider,
            model_alias=model_alias,
            character_reference="character/selected-baseline.png",
        )
        project = load_project(project_dir)
        project.active_run_id = resolved_run_id
        save_project(project_dir, project)
        create_identity_pack(project_dir, run_id=resolved_run_id)
        outputs["handoff"] = generate_handoffs(project_dir, run_id=resolved_run_id, all_jobs=True)
        actions.extend(["plan-v2-jobs", "generate-ready-handoffs"])
        return advance_payload(
            next_status(project_dir),
            actions,
            "provider_generation",
            "Generate only the ready standard animation rows, then import them.",
            outputs,
        )

    if stage == "generation_in_progress":
        resolved_run_id = run_id or latest_run_id(project_dir)
        if not resolved_run_id:
            raise ValueError("run id is required for generation")
        if generated_map:
            outputs["import"] = import_generated_outputs(
                project_dir,
                run_id=resolved_run_id,
                mapping=generated_map,
                extraction_method=(
                    "stable-slots" if row_provenance == "test_fixture" else "auto"
                ),
                chroma_key_hex="#00FF00" if row_provenance == "test_fixture" else None,
            )
            actions.append("import-generated")
        outputs["reconcile"] = reconcile_run(project_dir, resolved_run_id)
        if all_jobs_complete(project_dir, resolved_run_id):
            if not (project_dir / "runs" / resolved_run_id / "run-summary.json").is_file():
                outputs["build_review"] = build_review(
                    project_dir,
                    run_id=resolved_run_id,
                    row_provenance=row_provenance,
                )
                actions.append("build-v2-review")
            return advance_payload(
                next_status(project_dir),
                actions,
                "direction_and_likeness_review",
                "Review all 16 directions and every locked likeness trait before final approval.",
                outputs,
            )
        outputs["handoff"] = generate_handoffs(project_dir, run_id=resolved_run_id, all_jobs=True)
        actions.append("generate-ready-handoffs")
        return advance_payload(
            next_status(project_dir),
            actions,
            "provider_generation",
            "Generate the newly ready dependency wave and import its outputs.",
            outputs,
        )

    if stage in {"quality_review", "built_for_review"}:
        resolved_run_id = run_id or latest_run_id(project_dir)
        if not resolved_run_id:
            raise ValueError("run id is required for review")
        gates = review_gates(project_dir, resolved_run_id)
        if not gates["all_reviews_complete"]:
            return advance_payload(
                next_status(project_dir),
                actions,
                "direction_and_likeness_review",
                "Complete the direction, blind-direction, and likeness verdicts.",
                {"review_gates": gates},
            )
        if not approval_notes:
            return advance_payload(
                next_status(project_dir),
                actions,
                "visual_approval",
                "Approve the final contact sheet, animations, directions, and source likeness.",
                outputs,
            )
        outputs["finish"] = finish_run(
            project_dir=project_dir,
            run_id=resolved_run_id,
            approval_notes=approval_notes,
            row_provenance=row_provenance,
            install_root=install_root,
            override_reason=override_reason,
        )
        actions.append("finish")
        return advance_payload(next_status(project_dir), actions, "done", "Installed and validated.", outputs)

    if stage == "visually_approved":
        resolved_run_id = run_id or latest_run_id(project_dir)
        if not resolved_run_id:
            raise ValueError("run id is required for install")
        target = install_approved_run(
            project_dir=project_dir,
            run_id=resolved_run_id,
            row_provenance=row_provenance,
            install_root=install_root,
            override_reason=override_reason,
        )
        actions.append("install")
        outputs["installed"] = str(target)
        return advance_payload(next_status(project_dir), actions, "done", "Installed and validated.", outputs)

    return advance_payload(next_status(project_dir), actions, "done", "No further deterministic action is required.", outputs)


def advance_payload(
    status: WorkflowStatus,
    actions: list[str],
    gate: str,
    next_human_action: str,
    outputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "stage": status.stage,
        "next_action": status.next_action,
        "gate": gate,
        "actions": actions,
        "next_human_action": next_human_action,
        "workflow": status.to_dict(),
        "artifacts_to_show_user": status.artifacts_to_show_user,
        "api_accelerators": api_accelerators(),
        "outputs": outputs,
    }


def review_artifacts(project_dir: Path, run_id: str | None) -> list[str]:
    if not run_id:
        return []
    candidates = [
        Path("runs") / run_id / "qa" / "contact-sheet.png",
        Path("runs") / run_id / "qa" / "contact-sheet-v2.png",
        Path("runs") / run_id / "qa" / "look-directions.png",
        Path("runs") / run_id / "qa" / "direction-blind-pairs.png",
        Path("runs") / run_id / "qa" / "look-continuity.json",
        Path("runs") / run_id / "qa" / "direction-semantics.json",
        Path("runs") / run_id / "qa" / "likeness-report.json",
        Path("runs") / run_id / "qa" / "likeness-qa-sheet.png",
        Path("runs") / run_id / "qa" / "identity-drift.json",
        Path("runs") / run_id / "qa" / "edge-preview-white.png",
        Path("runs") / run_id / "qa" / "centering-overlay.png",
        Path("runs") / run_id / "qa" / "centering-report.json",
        Path("runs") / run_id / "qa" / "duplicate-audit.json",
        Path("runs") / run_id / "qa" / "animation-correctness.json",
        Path("runs") / run_id / "qa" / "animation-review.json",
        Path("runs") / run_id / "qa" / "review.json",
        Path("identity") / "identity-pack.json",
        Path("identity") / "small-size-preview.png",
    ]
    previews_dir = project_dir / "runs" / run_id / "qa" / "previews"
    if previews_dir.is_dir():
        candidates.extend(path.relative_to(project_dir) for path in sorted(previews_dir.glob("*.gif")))
    return [str(path) for path in candidates if (project_dir / path).exists()]


def install_approved_run(
    *,
    project_dir: Path,
    run_id: str,
    row_provenance: str,
    install_root: Path | None = None,
    override_reason: str | None = None,
) -> Path:
    if row_provenance not in APPROVED_PROVENANCE:
        raise ValueError("row provenance must be provider_generated, user_supplied, or test_fixture")
    approval_note = visual_approval_note(project_dir, run_id)
    if not approval_note:
        raise ValueError("visual approval is required before install")
    run_dir = project_dir / "runs" / run_id
    package_dir = run_dir / "package"
    package_validation = validate_v2_package(package_dir)
    if not package_validation["ok"]:
        raise ValueError(f"package validation blocks install: {'; '.join(package_validation['errors'])}")
    assert_run_installable(
        project_dir=project_dir,
        run_id=run_id,
        row_provenance=row_provenance,
        override_reason=override_reason,
    )
    project = load_project(project_dir)
    target = install_package(package_dir=package_dir, pet_id=project.id, install_root=install_root)
    project.active_run_id = run_id
    save_project(project_dir, project)
    write_json(
        run_dir / "install.json",
        {
            "installed_at": utc_now(),
            "install_root": str(target.parent),
            "target": str(target),
            "row_provenance": row_provenance,
            "visual_approval": approval_note,
            "override_reason": override_reason,
            "package_validation": package_validation,
        },
    )
    next_status(project_dir)
    return target


def generate_handoffs(
    project_dir: Path,
    *,
    run_id: str,
    all_jobs: bool = False,
    job_ids: list[str] | None = None,
) -> dict[str, Any]:
    jobs = refresh_readiness(project_dir, run_id)
    requested = {job.id for job in jobs} if all_jobs else set(job_ids or [])
    if not requested:
        raise ValueError("provide --all or at least one --job-id")
    ready = {job.id for job in jobs if job.status == "ready"}
    prepared: list[str] = []
    existing: list[str] = []
    blocked: list[dict[str, str]] = []
    expected: list[dict[str, Any]] = []
    for job in jobs:
        if job.id not in requested:
            continue
        if job.id not in ready:
            if job.status not in {"complete", "approved"}:
                blocked.append({"job_id": job.id, "reason": job.blocked_reason or f"status={job.status}"})
            continue
        invocation_path = project_dir / "runs" / run_id / "provider-invocations" / f"handoff-{job.id}.json"
        if invocation_path.is_file():
            existing.append(job.id)
        else:
            prepare_handoff(project_dir, run_id, job.id)
            prepared.append(job.id)
        invocation = read_json(invocation_path)
        request_metadata = invocation.get("request_metadata", {})
        packed_images = request_metadata.get("input_images", job.input_images)
        packed_roles = request_metadata.get("input_image_roles", job.input_image_roles)
        expected.append(
            {
                "job_id": job.id,
                "state": job.state,
                "prompt_path": job.prompt_path,
                "expected_output": job.expected_output,
                "input_images": packed_images,
                "input_image_roles": packed_roles,
            }
        )
    summary = {
        "run_id": run_id,
        "prepared_count": len(prepared) + len(existing),
        "newly_prepared": prepared,
        "already_prepared": existing,
        "dependency_blocked": blocked,
        "ready_job_ids": sorted(ready),
        "next_action": "await_provider_outputs" if expected else "advance_or_review",
        "expected_outputs": expected,
    }
    write_json(project_dir / "runs" / run_id / "handoff-summary.json", summary)
    next_status(project_dir)
    return summary


def _job_lookup(jobs: list[GenerationJob], key: str) -> GenerationJob | None:
    return next((job for job in jobs if job.id == key or job.state == key), None)


def _verify_generated_image(path: Path) -> None:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        if image.width < 128 or image.height < 128:
            raise ValueError(f"generated output is implausibly small: {path} ({image.width}x{image.height})")


def _process_imported_job(project_dir: Path, run_id: str, job: GenerationJob) -> None:
    run_dir = project_dir / "runs" / run_id
    if job.id == "look-cardinals":
        extract_and_compose_cardinals(run_dir)
        if load_identity_profile(project_dir) is not None and (
            project_dir / "character" / "selected-baseline.png"
        ).is_file():
            create_identity_pack(project_dir, run_id=run_id)
    elif job.id == "look-row-9":
        standard = run_dir / "final" / "spritesheet-standard.png"
        neutral = run_dir / "frames" / "idle" / "00.png"
        if not standard.is_file():
            raise FileNotFoundError("standard atlas must pass processing before look row 9")
        register_look_row_9(run_dir, standard_atlas=standard, neutral_cell=neutral)


def _build_standard_if_ready(
    project_dir: Path,
    run_id: str,
    *,
    extraction_method: str = "auto",
) -> dict[str, Any] | None:
    metadata_path = project_dir / "runs" / run_id / "run-metadata.json"
    metadata = read_json(metadata_path) if metadata_path.is_file() else {}
    if extraction_method == "auto" and metadata.get("extraction_method") in {
        "components",
        "slots",
        "stable-slots",
    }:
        extraction_method = str(metadata["extraction_method"])
    jobs = load_jobs(project_dir, run_id)
    if not all(next((job.status in {"complete", "approved"} for job in jobs if job.id == job_id), False) for job_id in STANDARD_JOB_IDS):
        return None
    standard = project_dir / "runs" / run_id / "final" / "spritesheet-standard.png"
    if standard.is_file():
        return {"status": "already-built", "standard_atlas": str(standard)}
    from .v2_backend import build_standard_rows

    result = build_standard_rows(
        project_dir / "runs" / run_id,
        extraction_method=extraction_method,
    )
    refresh_readiness(project_dir, run_id)
    return result


def import_generated_outputs(
    project_dir: Path,
    *,
    run_id: str,
    mapping: dict[str, str],
    extraction_method: str = "auto",
    chroma_key_hex: str | None = None,
) -> dict[str, Any]:
    """Import one dependency wave by job id or state, preserving job lineage."""

    metadata_path = project_dir / "runs" / run_id / "run-metadata.json"
    metadata = read_json(metadata_path) if metadata_path.is_file() else {}
    metadata["extraction_method"] = extraction_method
    if chroma_key_hex:
        from .style import parse_hex_color

        rgb = parse_hex_color(chroma_key_hex)
        metadata["chroma_key"] = {
            "hex": f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}",
            "rgb": list(rgb),
            "name": "explicit",
            "selection": "explicit-import",
        }
    write_json(metadata_path, metadata)
    pending = dict(mapping)
    imported: list[dict[str, str]] = []
    while pending:
        jobs = refresh_readiness(project_dir, run_id)
        progressed = False
        for key, source_text in list(pending.items()):
            job = _job_lookup(jobs, key)
            if job is None:
                raise ValueError(f"unknown generated-output job or state: {key}")
            if job.status in {"complete", "approved"}:
                pending.pop(key)
                progressed = True
                continue
            if job.status != "ready":
                continue
            source = Path(source_text).expanduser().resolve()
            if not source.is_file():
                raise FileNotFoundError(f"generated output does not exist: {source}")
            _verify_generated_image(source)
            output = project_dir / job.expected_output
            output.parent.mkdir(parents=True, exist_ok=True)
            if source != output.resolve():
                shutil.copy2(source, output)
            try:
                _process_imported_job(project_dir, run_id, job)
                completed = complete_job(
                    project_dir,
                    run_id,
                    job.id,
                    selected_output_path=job.expected_output,
                    provider_invocation_id=job.provider_invocation_id or f"handoff-{job.id}",
                    qa_notes="Provider-generated output imported and deterministic dependency processing passed.",
                )
            except Exception as exc:
                fail_job(project_dir, run_id, job.id, reason=str(exc))
                raise
            update_invocation_for_import(project_dir, run_id, completed.to_dict(), source)
            imported.append({"job_id": job.id, "state": job.state or "", "source": str(source), "output": job.expected_output})
            pending.pop(key)
            progressed = True
        _build_standard_if_ready(
            project_dir,
            run_id,
            extraction_method=extraction_method,
        )
        if not progressed:
            blocked = {
                key: (_job_lookup(refresh_readiness(project_dir, run_id), key).blocked_reason if _job_lookup(refresh_readiness(project_dir, run_id), key) else "unknown")
                for key in pending
            }
            raise ValueError(f"cannot import dependency-blocked outputs in this wave: {blocked}")
    graph = job_graph(project_dir, run_id)
    result = {
        "run_id": run_id,
        "imported": imported,
        "remaining_jobs": [
            job["id"]
            for job in graph["jobs"]
            if job["status"] not in {"complete", "approved", "cancelled", "superseded"}
        ],
        "ready_jobs": graph["ready"],
        "next_action": "build-review" if all_jobs_complete(project_dir, run_id) else "generate_next_ready_wave",
    }
    write_json(project_dir / "runs" / run_id / "import-summary.json", result)
    next_status(project_dir)
    return result


def update_invocation_for_import(project_dir: Path, run_id: str, job: dict[str, Any], source: Path) -> None:
    invocation_id = job.get("provider_invocation_id") or f"handoff-{job['id']}"
    path = project_dir / "runs" / run_id / "provider-invocations" / f"{invocation_id}.json"
    invocation = read_json(path) if path.is_file() else {
        "id": invocation_id,
        "adapter": job["provider"],
        "model": job["model_alias"],
        "status": "prepared",
        "prompt_hash": "",
        "input_image_hashes": [],
        "output_paths": [],
        "started_at": utc_now(),
        "request_metadata": {"job_id": job["id"], "state": job.get("state")},
    }
    invocation["status"] = "complete"
    invocation["finished_at"] = utc_now()
    invocation["output_paths"] = [job["expected_output"]]
    invocation.setdefault("request_metadata", {})["generated_image_source"] = str(source)
    write_json(path, invocation)


def all_jobs_complete(project_dir: Path, run_id: str) -> bool:
    jobs = load_jobs(project_dir, run_id)
    return bool(jobs) and all(job.status in {"complete", "approved"} for job in jobs)


def reconcile_run(project_dir: Path, run_id: str) -> dict[str, Any]:
    """Reconcile direct-provider outputs and deterministic dependency products."""

    reconciled: list[str] = []
    standard: dict[str, Any] | None = None
    while True:
        jobs = refresh_readiness(project_dir, run_id)
        progressed = False
        for job in jobs:
            output = project_dir / job.expected_output
            if not output.is_file() or job.status in {"complete", "approved"}:
                continue
            if job.status not in {"ready", "running", "generated", "processing"}:
                continue
            _verify_generated_image(output)
            _process_imported_job(project_dir, run_id, job)
            complete_job(
                project_dir,
                run_id,
                job.id,
                selected_output_path=job.expected_output,
                provider_invocation_id=job.provider_invocation_id,
                qa_notes="Existing provider output reconciled after interruption or direct execution.",
            )
            reconciled.append(job.id)
            progressed = True
        standard_result = _build_standard_if_ready(project_dir, run_id)
        if standard_result is not None:
            standard = standard_result
            if standard_result.get("status") != "already-built":
                progressed = True
        if not progressed:
            break
    return {
        "run_id": run_id,
        "reconciled": reconciled,
        "standard": standard,
        "graph": job_graph(project_dir, run_id),
    }


def build_review(
    project_dir: Path,
    *,
    run_id: str,
    row_provenance: str,
    extraction_method: str = "auto",
    force: bool = True,
) -> dict[str, Any]:
    if not all_jobs_complete(project_dir, run_id):
        raise ValueError("all v2 provider jobs must complete before the final review build")
    summary = build_from_row_strips(
        project_dir=project_dir,
        rows_dir=project_dir / "runs" / run_id / "row-strips",
        run_id=run_id,
        row_provenance=row_provenance,
        extraction_method=extraction_method,
        force=force,
    )
    validation = validate_project(project_dir, write_report=True)
    status = review_status(project_dir, run_id)
    result = {
        "run_id": run_id,
        "summary": summary.to_dict(),
        "validation": validation.to_dict(),
        "review_artifacts": status["review_artifacts"],
        "review_gates": status["review_gates"],
        "install_ready": status["install_ready"],
        "next_action": "complete_direction_and_likeness_reviews",
    }
    write_json(project_dir / "runs" / run_id / "qa" / "review-summary.json", result)
    next_status(project_dir)
    return result


def finish_run(
    *,
    project_dir: Path,
    run_id: str,
    approval_notes: str,
    row_provenance: str,
    install_root: Path | None = None,
    override_reason: str | None = None,
) -> dict[str, Any]:
    if not review_gates(project_dir, run_id)["all_reviews_complete"] and row_provenance != "test_fixture":
        raise ValueError("direction and likeness reviews must pass before final approval")
    approval = approve_artifact(
        project_dir=project_dir,
        run_id=run_id,
        artifact="final-review",
        decision="approved",
        notes=approval_notes,
    )
    target = install_approved_run(
        project_dir=project_dir,
        run_id=run_id,
        row_provenance=row_provenance,
        install_root=install_root,
        override_reason=override_reason,
    )
    validation = validate_project(project_dir, write_report=True)
    result = {
        "run_id": run_id,
        "approval": approval.to_dict(),
        "installed": str(target),
        "validation": validation.to_dict(),
    }
    write_json(project_dir / "runs" / run_id / "finish-summary.json", result)
    return result


def recover_project_run(project_dir: Path, run_id: str) -> dict[str, Any]:
    recovery = recover_run(project_dir, run_id)
    recovery["reconcile"] = reconcile_run(project_dir, run_id)
    next_status(project_dir)
    return recovery
