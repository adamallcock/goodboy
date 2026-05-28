"""Agent-facing Goodboy workflow rails."""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from .adapters import prepare_handoff
from .candidates import CANDIDATE_INDEX, SELECTED_CANDIDATE, build_candidate_contact_sheet, plan_baseline_candidates, select_baseline_candidate
from .contracts import STATE_ORDER
from .ingest import SOURCE_CARD, SOURCE_MANIFEST, draft_source_card, ingest_images, load_source_images
from .jsonio import read_json, write_json
from .pipeline import build_from_row_strips, install_package
from .project import init_project, load_project, save_project
from .safety import find_suspicious_renderer_scripts
from .schemas import ApprovalRecord, utc_now
from .style import STYLE_PATH, plan_row_generation_jobs, save_default_style_sheet
from .validation import validate_project


WORKFLOW_STATE = "workflow-state.json"
APPROVED_PROVENANCE = {"provider_generated", "user_supplied", "test_fixture"}


def default_do_not() -> list[str]:
    return [
        "do not write renderer, drawing, sprite-maker, or row-strip generator scripts",
        "do not synthesize pet art with Pillow, SVG, canvas, or handwritten image code",
        "do not install without approved provenance and a recorded visual approval",
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
    init_project(project_dir, pet_id=pet_id, display_name=display_name, species=species)
    ingest_images(project_dir, sources, role="primary_reference", notes=notes)
    draft_source_card(project_dir, user_notes=notes)
    plan_baseline_candidates(
        project_dir=project_dir,
        provider=provider,
        model_alias=model_alias,
        count=candidate_count,
    )
    status = next_status(project_dir)
    write_workflow_state(project_dir, status)
    return status


def next_status(project_dir: Path) -> WorkflowStatus:
    project_dir = project_dir.resolve()
    if not (project_dir / "goodboy.json").is_file():
        return WorkflowStatus(
            stage="missing_project",
            next_action="start_project",
            allowed_commands=["goodboy start <project-dir> --pet-id <id> --display-name <name> --source <image>..."],
            blocked_actions=["all build and install commands"],
            recommended_command=f"goodboy start {project_dir} --pet-id <id> --display-name <name> --source <image>",
            missing_inputs=["source images", "pet id", "display name"],
            do_not_run=["build-from-rows", "install"],
            required_user_input=["source images", "pet id", "display name"],
        )

    run_id = latest_run_id(project_dir)
    stage = infer_stage(project_dir, run_id)
    if stage == "initialized":
        status = WorkflowStatus(
            stage=stage,
            next_action="ingest_sources",
            allowed_commands=["goodboy ingest <project-dir> <image>...", "goodboy source-card <project-dir>"],
            blocked_actions=["planning rows", "building rows", "installing"],
            recommended_command=f"goodboy ingest {project_dir} <image>",
            acceptable_commands=[f"goodboy source-card {project_dir}"],
            missing_inputs=["source images"],
            do_not_run=["plan-rows", "build-review", "finish"],
            required_user_input=["source images"],
        )
    elif stage == "sources_ingested":
        status = WorkflowStatus(
            stage=stage,
            next_action="plan_baselines",
            allowed_commands=["goodboy advance <project-dir> --agent-mode", "goodboy source-card <project-dir>", "goodboy plan-candidates <project-dir> --provider codex_builtin --model-alias codex-imagegen"],
            blocked_actions=["creating local renderer scripts", "building rows", "installing"],
            recommended_command=f"goodboy advance {project_dir} --agent-mode",
            acceptable_commands=[f"goodboy plan-candidates {project_dir} --provider codex_builtin --model-alias codex-imagegen", f"goodboy source-card {project_dir}"],
            do_not_run=["build-review", "finish", "local renderer scripts"],
            already_done=["source images ingested"],
            artifacts_to_show_user=[SOURCE_CARD],
        )
    elif stage == "baselines_planned":
        status = WorkflowStatus(
            stage=stage,
            next_action="generate_baselines",
            allowed_commands=[
                "generate provider candidate images from candidates/*/prompt.md",
                "goodboy advance <project-dir> --agent-mode --candidate-id baseline-001 --baseline-image <generated.png>",
            ],
            blocked_actions=["creating local renderer scripts", "planning rows before baseline selection", "installing"],
            recommended_command=f"goodboy advance {project_dir} --agent-mode",
            acceptable_commands=[f"goodboy candidate-sheet {project_dir}", f"goodboy select-candidate {project_dir} --candidate-id baseline-001 --image-path /path/to/generated-baseline.png"],
            missing_inputs=["generated baseline image", "user baseline choice"],
            do_not_run=["plan-candidates", "plan-rows", "local renderer scripts", "custom metadata python"],
            required_user_input=["choose a generated baseline candidate"],
            artifacts_to_show_user=["candidates/contact-sheet.png", "candidates/baseline-candidates.json"],
            already_done=["source-card", "plan-candidates"],
        )
    elif stage == "baseline_selected":
        status = WorkflowStatus(
            stage=stage,
            next_action="plan_rows",
            allowed_commands=["goodboy advance <project-dir> --agent-mode", "goodboy style-default <project-dir>", "goodboy plan-rows <project-dir> --run-id <run-id> --provider codex_builtin --model-alias codex-imagegen --character-reference character/selected-baseline.png"],
            blocked_actions=["creating local renderer scripts", "building from missing row strips", "installing"],
            recommended_command=f"goodboy advance {project_dir} --agent-mode --run-id <run-id>",
            acceptable_commands=[f"goodboy plan-rows {project_dir} --run-id <run-id> --provider codex_builtin --model-alias codex-imagegen --character-reference character/selected-baseline.png", f"goodboy style-default {project_dir}"],
            do_not_run=["build-review before row strips exist", "finish", "local renderer scripts"],
            already_done=["select-candidate"],
        )
    elif stage == "rows_planned":
        status = WorkflowStatus(
            stage=stage,
            next_action="generate_rows",
            allowed_commands=["goodboy advance <project-dir> --agent-mode --run-id <run-id>", "goodboy handoff <project-dir> --run-id <run-id> --job-id <job-id>", "goodboy execute-openai ...", "goodboy execute-gemini ..."],
            blocked_actions=["creating local renderer scripts", "installing before build and approval"],
            recommended_command=f"goodboy advance {project_dir} --agent-mode --run-id {run_id}",
            acceptable_commands=[f"goodboy generate-handoff {project_dir} --run-id {run_id} --all", f"goodboy import-generated {project_dir} --run-id {run_id} --map /path/to/generated-output-map.json"],
            after_provider_generation=f"goodboy advance {project_dir} --agent-mode --run-id {run_id} --generated-map /path/to/generated-output-map.json --row-provenance provider_generated",
            missing_inputs=["provider-generated row strips"],
            do_not_run=["custom metadata python", "local shell cp loops", "build-review before row strips are imported"],
            already_done=["style-default", "plan-rows"],
            required_user_input=["provider-generated row strips"],
        )
    elif stage == "built_for_review":
        status = WorkflowStatus(
            stage=stage,
            next_action="visual_review",
            allowed_commands=["goodboy advance <project-dir> --agent-mode --run-id <run-id> --approval-notes <notes>", "goodboy review-status <project-dir> --run-id <run-id>", "goodboy approve <project-dir> --notes <notes>"],
            blocked_actions=["installing before approval"],
            recommended_command=f"goodboy advance {project_dir} --agent-mode --run-id {run_id} --approval-notes /quote/user-approval-notes/ --row-provenance provider_generated",
            acceptable_commands=[f"goodboy review-status {project_dir} --run-id {run_id}", f"goodboy approve {project_dir} --notes /quote/user-approval-notes/", f"goodboy finish {project_dir} --run-id {run_id} --approval-notes /quote/user-approval-notes/ --row-provenance provider_generated"],
            missing_inputs=["visual approval notes"],
            do_not_run=["install without approval"],
            already_done=["build-review"],
            required_user_input=["visual approval of contact sheet and previews"],
            artifacts_to_show_user=review_artifacts(project_dir, run_id),
        )
    elif stage == "visually_approved":
        status = WorkflowStatus(
            stage=stage,
            next_action="install",
            allowed_commands=["goodboy advance <project-dir> --agent-mode --run-id <run-id> --approval-notes <notes>", "goodboy install <project-dir> --run-id <run-id> --row-provenance provider_generated"],
            blocked_actions=["installing renderer/mock rows"],
            recommended_command=f"goodboy advance {project_dir} --agent-mode --run-id {run_id} --approval-notes /quote/user-approval-notes/ --row-provenance provider_generated",
            acceptable_commands=[f"goodboy install {project_dir} --run-id {run_id} --row-provenance provider_generated", f"goodboy finish {project_dir} --run-id {run_id} --approval-notes /quote/user-approval-notes/ --row-provenance provider_generated"],
            do_not_run=["installing renderer/mock rows"],
            already_done=["visual approval"],
            artifacts_to_show_user=review_artifacts(project_dir, run_id),
        )
    else:
        status = WorkflowStatus(
            stage=stage,
            next_action="done",
            allowed_commands=["goodboy validate <project-dir>"],
            blocked_actions=["creating local renderer scripts"],
            recommended_command=f"goodboy validate {project_dir}",
            acceptable_commands=[f"goodboy doctor {project_dir} --agent-mode"],
            do_not_run=["local renderer scripts", "custom metadata python"],
            already_done=["finish", "install"],
            artifacts_to_show_user=review_artifacts(project_dir, run_id),
        )
    write_workflow_state(project_dir, status)
    return status


def infer_stage(project_dir: Path, run_id: str | None) -> str:
    if not load_source_images(project_dir):
        return "initialized"
    if not (project_dir / CANDIDATE_INDEX).is_file():
        return "sources_ingested"
    if not (project_dir / SELECTED_CANDIDATE).is_file():
        return "baselines_planned"
    if run_id is None:
        return "baseline_selected"
    if not (project_dir / "runs" / run_id / "run-summary.json").is_file():
        return "rows_planned"
    if has_visual_approval(project_dir, run_id):
        project = load_project(project_dir)
        if project.active_run_id == run_id and (project_dir / "runs" / run_id / "install.json").is_file():
            return "installed"
        return "visually_approved"
    return "built_for_review"


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
        id=f"{artifact}-{decision}",
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
    records = []
    for path in sorted(approvals_dir.glob("*.json")):
        records.append(ApprovalRecord.from_dict(read_json(path)))
    return records


def has_visual_approval(project_dir: Path, run_id: str | None) -> bool:
    if not run_id:
        return False
    return any(record.decision == "approved" for record in load_approvals(project_dir, run_id))


def visual_approval_note(project_dir: Path, run_id: str) -> str | None:
    notes = [record.notes for record in load_approvals(project_dir, run_id) if record.decision == "approved"]
    return "; ".join(notes) if notes else None


def review_status(project_dir: Path, run_id: str) -> dict[str, Any]:
    run_dir = project_dir / "runs" / run_id
    artifacts = review_artifacts(project_dir, run_id)
    approvals = [record.to_dict() for record in load_approvals(project_dir, run_id)]
    policy_path = run_dir / "qa" / "install-policy.json"
    policy = read_json(policy_path) if policy_path.is_file() else None
    suspicious = find_suspicious_renderer_scripts(project_dir)
    return {
        "run_id": run_id,
        "stage": infer_stage(project_dir, run_id),
        "review_artifacts": artifacts,
        "approvals": approvals,
        "has_visual_approval": any(record["decision"] == "approved" for record in approvals),
        "install_policy": policy,
        "suspicious_renderer_scripts": suspicious,
        "install_ready": bool(artifacts) and any(record["decision"] == "approved" for record in approvals) and not suspicious,
    }


def doctor(project_dir: Path) -> dict[str, Any]:
    validation = validate_project(project_dir, write_report=False)
    workflow = next_status(project_dir)
    providers = provider_status(project_dir)
    missing = missing_generated_outputs(project_dir)
    suspicious = find_suspicious_renderer_scripts(project_dir)
    return {
        "validation": {
            "ok": validation.ok,
            "issues": [issue.to_dict() for issue in validation.issues],
            "checked_files": validation.checked_files,
        },
        "workflow": workflow.to_dict(),
        "providers": providers,
        "api_accelerators": api_accelerators(),
        "missing_generated_outputs": missing,
        "suspicious_renderer_scripts": suspicious,
        "tests_needed_for_project_artifacts_only": False,
    }


def api_accelerators() -> dict[str, dict[str, str | bool]]:
    return {
        "openai_images": {
            "status": "available" if os.environ.get("OPENAI_API_KEY") else "optional_not_configured",
            "env_var": "OPENAI_API_KEY",
            "note": "optional accelerator for direct API generation; Codex built-in handoff works without it",
        },
        "gemini_nano_banana_2": {
            "status": "available" if os.environ.get("GEMINI_API_KEY") else "optional_not_configured",
            "env_var": "GEMINI_API_KEY",
            "note": "optional accelerator for direct API generation; Codex built-in handoff works without it",
        },
        "gemini_nano_banana_pro": {
            "status": "available" if os.environ.get("GEMINI_API_KEY") else "optional_not_configured",
            "env_var": "GEMINI_API_KEY",
            "note": "optional accelerator for direct API generation; Codex built-in handoff works without it",
        },
    }


def provider_status(project_dir: Path) -> dict[str, dict[str, str | bool]]:
    providers = used_providers(project_dir)
    status: dict[str, dict[str, str | bool]] = {}
    for provider in sorted(providers):
        if provider == "codex_builtin":
            status[provider] = {"required": "codex interactive image generation"}
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
        for item in read_json(candidate_path).get("candidates", []):
            provider = item.get("provider")
            if provider:
                providers.add(provider)
    for jobs_path in sorted((project_dir / "runs").glob("*/generation-jobs.json")):
        for item in read_json(jobs_path).get("jobs", []):
            provider = item.get("provider")
            if provider:
                providers.add(provider)
    return providers


def missing_generated_outputs(project_dir: Path) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for jobs_path in sorted((project_dir / "runs").glob("*/generation-jobs.json")):
        run_id = jobs_path.parent.name
        for job in read_json(jobs_path).get("jobs", []):
            expected = job.get("expected_output")
            if expected and not (project_dir / expected).is_file():
                missing.append({"run_id": run_id, "job_id": job.get("id", ""), "state": job.get("state", ""), "expected_output": expected})
    return missing


def default_run_id() -> str:
    return f"row-gen-{utc_now()[:10].replace('-', '')}"


def advance_project(
    *,
    project_dir: Path,
    run_id: str | None = None,
    provider: str = "codex_builtin",
    model_alias: str = "codex-imagegen",
    candidate_id: str | None = None,
    baseline_image: Path | None = None,
    selection_notes: str = "",
    generated_map: dict[str, str] | None = None,
    row_provenance: str = "provider_generated",
    approval_notes: str | None = None,
    install_root: Path | None = None,
    override_reason: str | None = None,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    before = next_status(project_dir)
    actions: list[str] = []
    outputs: dict[str, Any] = {}
    stage = before.stage

    if stage == "initialized":
        return advance_payload(project_dir, before, actions, "source_images", "Add source images, then run goodboy advance again.", outputs)

    if stage == "sources_ingested":
        if not (project_dir / SOURCE_CARD).is_file():
            draft_source_card(project_dir)
            actions.append("source-card")
        if not (project_dir / CANDIDATE_INDEX).is_file():
            plan_baseline_candidates(project_dir=project_dir, provider=provider, model_alias=model_alias)
            actions.append("plan-candidates")
        else:
            build_candidate_contact_sheet(project_dir=project_dir)
            actions.append("candidate-sheet")
        after = next_status(project_dir)
        return advance_payload(
            project_dir,
            after,
            actions,
            "baseline_generation_or_selection",
            "Generate baseline candidates through the chosen provider, then select one.",
            outputs,
        )

    if stage == "baselines_planned":
        build_candidate_contact_sheet(project_dir=project_dir)
        if candidate_id and baseline_image:
            select_baseline_candidate(
                project_dir=project_dir,
                candidate_id=candidate_id,
                image_path=baseline_image,
                notes=selection_notes,
            )
            actions.extend(["candidate-sheet", "select-candidate"])
            stage = "baseline_selected"
        else:
            after = next_status(project_dir)
            return advance_payload(
                project_dir,
                after,
                actions + ["candidate-sheet"],
                "baseline_generation_or_selection",
                "Review candidates/contact-sheet.png, generate missing baselines, and choose one.",
                outputs,
            )

    if stage == "baseline_selected":
        if not (project_dir / STYLE_PATH).is_file():
            save_default_style_sheet(project_dir)
            actions.append("style-default")
        resolved_run_id = run_id or latest_run_id(project_dir) or default_run_id()
        jobs_path = project_dir / "runs" / resolved_run_id / "generation-jobs.json"
        if not jobs_path.is_file():
            plan_row_generation_jobs(
                project_dir=project_dir,
                run_id=resolved_run_id,
                provider=provider,
                model_alias=model_alias,
                character_reference="character/selected-baseline.png",
            )
            actions.append("plan-rows")
        outputs["handoff"] = generate_handoffs(project_dir, run_id=resolved_run_id, all_jobs=True)
        actions.append("generate-handoff")
        after = next_status(project_dir)
        return advance_payload(
            project_dir,
            after,
            actions,
            "row_generation",
            "Generate row strips from the handoff prompts, then run advance with --generated-map.",
            outputs,
        )

    if stage == "rows_planned":
        resolved_run_id = run_id or latest_run_id(project_dir)
        if not resolved_run_id:
            raise ValueError("run id is required to advance planned rows")
        if generated_map:
            outputs["import"] = import_generated_outputs(project_dir, run_id=resolved_run_id, mapping=generated_map)
            actions.append("import-generated")
            if outputs["import"]["missing_states"]:
                after = next_status(project_dir)
                return advance_payload(
                    project_dir,
                    after,
                    actions,
                    "row_generation",
                    "Import the remaining generated row strips, then run advance again.",
                    outputs,
                )
            outputs["build_review"] = build_review(project_dir, run_id=resolved_run_id, row_provenance=row_provenance)
            actions.append("build-review")
            after = next_status(project_dir)
            return advance_payload(
                project_dir,
                after,
                actions,
                "visual_approval",
                "Review the contact sheet, GIF previews, edge preview, and centering overlay; approve if acceptable.",
                outputs,
            )
        outputs["handoff"] = generate_handoffs(project_dir, run_id=resolved_run_id, all_jobs=True)
        actions.append("generate-handoff")
        after = next_status(project_dir)
        return advance_payload(
            project_dir,
            after,
            actions,
            "row_generation",
            "Generate row strips from the handoff prompts, then run advance with --generated-map.",
            outputs,
        )

    if stage == "built_for_review":
        resolved_run_id = run_id or latest_run_id(project_dir)
        if not resolved_run_id:
            raise ValueError("run id is required to finish a review build")
        if approval_notes:
            outputs["finish"] = finish_run(
                project_dir=project_dir,
                run_id=resolved_run_id,
                approval_notes=approval_notes,
                row_provenance=row_provenance,
                install_root=install_root,
                override_reason=override_reason,
            )
            actions.append("finish")
            after = next_status(project_dir)
            return advance_payload(project_dir, after, actions, "done", "Installed and validated.", outputs)
        after = next_status(project_dir)
        return advance_payload(
            project_dir,
            after,
            actions,
            "visual_approval",
            "Review the contact sheet, GIF previews, edge preview, and centering overlay; approve if acceptable.",
            outputs,
        )

    if stage == "visually_approved":
        resolved_run_id = run_id or latest_run_id(project_dir)
        if not resolved_run_id:
            raise ValueError("run id is required to install an approved run")
        target = install_approved_run(
            project_dir=project_dir,
            run_id=resolved_run_id,
            row_provenance=row_provenance,
            install_root=install_root,
            override_reason=override_reason,
        )
        actions.append("install")
        outputs["installed"] = str(target)
        after = next_status(project_dir)
        return advance_payload(project_dir, after, actions, "done", "Installed and validated.", outputs)

    after = next_status(project_dir)
    return advance_payload(project_dir, after, actions, "done", "No further deterministic action is required.", outputs)


def advance_payload(
    project_dir: Path,
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
        Path("runs") / run_id / "qa" / "edge-preview-white.png",
        Path("runs") / run_id / "qa" / "centering-overlay.png",
        Path("runs") / run_id / "qa" / "centering-report.json",
        Path("runs") / run_id / "qa" / "duplicate-audit.json",
        Path("runs") / run_id / "qa" / "review.json",
        Path("runs") / run_id / "qa" / "human-review-checklist.json",
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
    suspicious = find_suspicious_renderer_scripts(project_dir)
    if suspicious:
        raise ValueError(f"suspicious renderer scripts block install: {', '.join(suspicious)}")
    approval_note = visual_approval_note(project_dir, run_id)
    if not approval_note:
        raise ValueError("visual approval is required before install")
    run_dir = project_dir / "runs" / run_id
    package_dir = run_dir / "package"
    if not (package_dir / "pet.json").is_file() or not (package_dir / "spritesheet.webp").is_file():
        raise FileNotFoundError(f"missing package artifacts for run: {run_id}")
    policy_path = run_dir / "qa" / "install-policy.json"
    if policy_path.is_file():
        policy = read_json(policy_path)
        hard_failures = policy.get("hard_failures", [])
        if hard_failures and not override_reason:
            raise ValueError(f"QA policy blocks install: {'; '.join(hard_failures)}")
        policy["install_requested"] = True
        policy["row_provenance"] = row_provenance
        policy["visual_approval"] = approval_note
        policy["override_reason"] = override_reason
        write_json(policy_path, policy)
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
        },
    )
    next_status(project_dir)
    return target


def generate_handoffs(project_dir: Path, *, run_id: str, all_jobs: bool = False, job_ids: list[str] | None = None) -> dict[str, Any]:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    jobs = read_json(jobs_path).get("jobs", [])
    requested = {job["id"] for job in jobs} if all_jobs else set(job_ids or [])
    if not requested:
        raise ValueError("provide --all or at least one --job-id")
    prepared = []
    skipped = []
    for job in jobs:
        if job["id"] not in requested:
            continue
        invocation_path = project_dir / "runs" / run_id / "provider-invocations" / f"handoff-{job['id']}.json"
        if invocation_path.is_file():
            invocation = read_json(invocation_path)
            skipped.append(job["id"])
        else:
            invocation = prepare_handoff(project_dir, run_id, job["id"]).to_dict()
            prepared.append(job["id"])
        invocation["job_id"] = job["id"]
    summary = {
        "run_id": run_id,
        "prepared_count": len(prepared) + len(skipped),
        "newly_prepared": prepared,
        "already_prepared": skipped,
        "next_action": "await_provider_outputs",
        "expected_outputs": [
            {"job_id": job["id"], "state": job.get("state"), "prompt_path": job["prompt_path"], "expected_output": job["expected_output"]}
            for job in jobs
            if job["id"] in requested
        ],
    }
    write_json(project_dir / "runs" / run_id / "handoff-summary.json", summary)
    next_status(project_dir)
    return summary


def import_generated_outputs(project_dir: Path, *, run_id: str, mapping: dict[str, str]) -> dict[str, Any]:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    raw = read_json(jobs_path)
    jobs = raw.get("jobs", [])
    by_state = {job.get("state"): (index, job) for index, job in enumerate(jobs) if job.get("state")}
    imported = []
    for state, source_text in mapping.items():
        if state not in by_state:
            raise ValueError(f"unknown generated-output state: {state}")
        source = Path(source_text).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"generated output does not exist: {source}")
        with Image.open(source) as image:
            image.verify()
        index, job = by_state[state]
        output = project_dir / job["expected_output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
        job["status"] = "complete"
        job["selected_output_path"] = job["expected_output"]
        job["provider_invocation_id"] = job.get("provider_invocation_id") or f"handoff-{job['id']}"
        job["qa_notes"] = "Provider-generated output imported by goodboy import-generated."
        jobs[index] = job
        update_invocation_for_import(project_dir, run_id, job, source)
        imported.append({"state": state, "source": str(source), "output": job["expected_output"]})
    write_json(jobs_path, {"jobs": jobs})
    missing = [
        job["state"]
        for job in jobs
        if job.get("state") in STATE_ORDER and not (project_dir / job["expected_output"]).is_file()
    ]
    result = {"run_id": run_id, "imported": imported, "missing_states": missing, "next_action": "build-review" if not missing else "import_remaining_outputs"}
    write_json(project_dir / "runs" / run_id / "import-summary.json", result)
    next_status(project_dir)
    return result


def update_invocation_for_import(project_dir: Path, run_id: str, job: dict[str, Any], source: Path) -> None:
    invocation_id = job.get("provider_invocation_id") or f"handoff-{job['id']}"
    path = project_dir / "runs" / run_id / "provider-invocations" / f"{invocation_id}.json"
    if path.is_file():
        invocation = read_json(path)
    else:
        invocation = {
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


def build_review(
    project_dir: Path,
    *,
    run_id: str,
    row_provenance: str,
    extraction_method: str = "auto",
    force: bool = True,
) -> dict[str, Any]:
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
        "install_ready": status["install_ready"],
        "next_action": "finish_after_visual_approval",
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
    approval = approve_artifact(
        project_dir=project_dir,
        run_id=run_id,
        artifact="contact-sheet",
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
