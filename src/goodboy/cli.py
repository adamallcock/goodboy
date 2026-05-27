"""Goodboy command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import execute_gemini_image_job, execute_openai_image_job, list_capabilities, prepare_handoff
from .candidates import CANDIDATE_INDEX, build_candidate_contact_sheet, plan_baseline_candidates, select_baseline_candidate, store_candidate_image
from .critique import record_critique
from .exports import export_petdex_package, export_project_bundle
from .feedback import create_feedback_event
from .ingest import draft_source_card, ingest_images, load_source_images, write_provenance_report
from .jsonio import read_json
from .pipeline import build_from_row_strips
from .project import init_project, load_project
from .style import STYLE_PATH, plan_row_generation_jobs, save_default_style_sheet
from .validation import validate_project
from .workflow import (
    advance_project,
    approve_artifact,
    build_review,
    doctor,
    finish_run,
    generate_handoffs,
    import_generated_outputs,
    install_approved_run,
    latest_run_id,
    make_project,
    next_status,
    review_status,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="goodboy", description="Create and validate Codex pet spritesheets.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a Goodboy project workspace.")
    init_cmd.add_argument("project_dir")
    init_cmd.add_argument("--pet-id", required=True)
    init_cmd.add_argument("--display-name", required=True)
    init_cmd.add_argument("--species", default="pet")

    inspect_cmd = sub.add_parser("inspect", help="Print the Goodboy project manifest.")
    inspect_cmd.add_argument("project_dir")

    make_cmd = sub.add_parser("make", help="Create a project, ingest sources, plan baselines, and print the next safe action.")
    make_cmd.add_argument("project_dir")
    make_cmd.add_argument("--pet-id", required=True)
    make_cmd.add_argument("--display-name", required=True)
    make_cmd.add_argument("--species", default="pet")
    make_cmd.add_argument("--source", action="append", required=True)
    make_cmd.add_argument("--provider", default="codex_builtin")
    make_cmd.add_argument("--model-alias", default="codex-imagegen")
    make_cmd.add_argument("--count", type=int, default=6)
    make_cmd.add_argument("--notes", default="")

    start_cmd = sub.add_parser("start", help="Start a Goodboy project and stop at the first provider/user gate.")
    start_cmd.add_argument("project_dir")
    start_cmd.add_argument("--pet-id", required=True)
    start_cmd.add_argument("--display-name", required=True)
    start_cmd.add_argument("--species", default="pet")
    start_cmd.add_argument("--source", action="append", required=True)
    start_cmd.add_argument("--provider", default="codex_builtin")
    start_cmd.add_argument("--model-alias", default="codex-imagegen")
    start_cmd.add_argument("--count", type=int, default=6)
    start_cmd.add_argument("--notes", default="")

    advance_cmd = sub.add_parser("advance", help="Run safe deterministic workflow steps until the next provider/user gate.")
    advance_cmd.add_argument("project_dir")
    advance_cmd.add_argument("--agent-mode", action="store_true")
    advance_cmd.add_argument("--run-id")
    advance_cmd.add_argument("--provider", default="codex_builtin")
    advance_cmd.add_argument("--model-alias", default="codex-imagegen")
    advance_cmd.add_argument("--candidate-id")
    advance_cmd.add_argument("--baseline-image")
    advance_cmd.add_argument("--selection-notes", default="")
    advance_cmd.add_argument("--generated-map")
    advance_cmd.add_argument("--state", action="append", help="Generated row mapping in the form state=/absolute/path.png")
    advance_cmd.add_argument("--row-provenance", choices=["provider_generated", "user_supplied", "test_fixture"], default="provider_generated")
    advance_cmd.add_argument("--approval-notes")
    advance_cmd.add_argument("--install-root")
    advance_cmd.add_argument("--install-override-reason")

    next_cmd = sub.add_parser("next", help="Print the next safe action for a Goodboy project.")
    next_cmd.add_argument("project_dir")
    next_cmd.add_argument("--agent-mode", action="store_true")

    doctor_cmd = sub.add_parser("doctor", help="Report validation, workflow, provider, and artifact readiness.")
    doctor_cmd.add_argument("project_dir")
    doctor_cmd.add_argument("--agent-mode", action="store_true")

    ingest_cmd = sub.add_parser("ingest", help="Copy source images into the project and write source manifests.")
    ingest_cmd.add_argument("project_dir")
    ingest_cmd.add_argument("images", nargs="+")
    ingest_cmd.add_argument("--role", default="primary_reference")
    ingest_cmd.add_argument("--notes", default="")

    source_card_cmd = sub.add_parser("source-card", help="Create or refresh a manual-editable source-card scaffold.")
    source_card_cmd.add_argument("project_dir")
    source_card_cmd.add_argument("--notes", default="")

    style_cmd = sub.add_parser("style-default", help="Write the default happy Codex emotion style sheet.")
    style_cmd.add_argument("project_dir")
    style_cmd.add_argument("--style-id", default="happy-codex-default")
    style_cmd.add_argument("--preset", default="soft-lifelike")
    style_cmd.add_argument("--subject-kind", default="pet")
    style_cmd.add_argument("--user-style", action="append", default=[])
    style_cmd.add_argument("--ai-critique", action="append", default=[])
    style_cmd.add_argument("--refresh", action="store_true")

    plan_rows_cmd = sub.add_parser("plan-rows", help="Plan Codex state row generation jobs.")
    plan_rows_cmd.add_argument("project_dir")
    plan_rows_cmd.add_argument("--run-id", required=True)
    plan_rows_cmd.add_argument("--provider", required=True)
    plan_rows_cmd.add_argument("--model-alias", required=True)
    plan_rows_cmd.add_argument("--character-reference")
    plan_rows_cmd.add_argument("--refresh", action="store_true")

    candidates_cmd = sub.add_parser("plan-candidates", help="Plan baseline style candidates and prompts.")
    candidates_cmd.add_argument("project_dir")
    candidates_cmd.add_argument("--provider", required=True)
    candidates_cmd.add_argument("--model-alias", required=True)
    candidates_cmd.add_argument("--count", type=int, default=6)
    candidates_cmd.add_argument("--refresh", action="store_true")
    candidates_cmd.add_argument("--no-sheet", action="store_true")

    select_candidate_cmd = sub.add_parser("select-candidate", help="Select a baseline candidate and create a character card.")
    select_candidate_cmd.add_argument("project_dir")
    select_candidate_cmd.add_argument("--candidate-id", required=True)
    select_candidate_cmd.add_argument("--image-path")
    select_candidate_cmd.add_argument("--notes", default="")

    candidate_image_cmd = sub.add_parser("candidate-image", help="Store a provider-generated image for a baseline candidate.")
    candidate_image_cmd.add_argument("project_dir")
    candidate_image_cmd.add_argument("--candidate-id", required=True)
    candidate_image_cmd.add_argument("--image-path", required=True)

    candidate_sheet_cmd = sub.add_parser("candidate-sheet", help="Render a baseline candidate review contact sheet.")
    candidate_sheet_cmd.add_argument("project_dir")
    candidate_sheet_cmd.add_argument("--output")
    candidate_sheet_cmd.add_argument("--columns", type=int, default=3)

    feedback_cmd = sub.add_parser("feedback", help="Record human or AI feedback and optionally create a branch.")
    feedback_cmd.add_argument("project_dir")
    feedback_cmd.add_argument("--target", required=True)
    feedback_cmd.add_argument("--text", required=True)
    feedback_cmd.add_argument("--author", default="human")
    feedback_cmd.add_argument("--branch-id")
    feedback_cmd.add_argument("--parent", default="main")
    feedback_cmd.add_argument("--no-branch", action="store_true")

    critique_cmd = sub.add_parser("critique", help="Record structured human or AI critique and optionally apply it to the style sheet.")
    critique_cmd.add_argument("project_dir")
    critique_cmd.add_argument("--critique-id", required=True)
    critique_cmd.add_argument("--target", required=True)
    critique_cmd.add_argument("--author", default="vision_critic")
    critique_cmd.add_argument("--finding", action="append", default=[])
    critique_cmd.add_argument("--recommendation", action="append", default=[])
    critique_cmd.add_argument("--identity-score", type=float)
    critique_cmd.add_argument("--style-score", type=float)
    critique_cmd.add_argument("--apply-to-style", action="store_true")

    provenance_cmd = sub.add_parser("provenance", help="Write a source image provenance and EXIF report.")
    provenance_cmd.add_argument("project_dir")

    adapters_cmd = sub.add_parser("adapters", help="List generation adapter capabilities.")
    adapters_cmd.add_argument("--json", action="store_true")

    handoff_cmd = sub.add_parser("handoff", help="Prepare a provider handoff manifest for a planned generation job.")
    handoff_cmd.add_argument("project_dir")
    handoff_cmd.add_argument("--run-id", required=True)
    handoff_cmd.add_argument("--job-id", required=True)

    batch_handoff_cmd = sub.add_parser("generate-handoff", help="Prepare provider handoff manifests for one or more planned jobs.")
    batch_handoff_cmd.add_argument("project_dir")
    batch_handoff_cmd.add_argument("--run-id", required=True)
    batch_handoff_cmd.add_argument("--all", action="store_true")
    batch_handoff_cmd.add_argument("--job-id", action="append")

    import_cmd = sub.add_parser("import-generated", help="Import provider-generated outputs and update job/invocation manifests.")
    import_cmd.add_argument("project_dir")
    import_cmd.add_argument("--run-id", required=True)
    import_cmd.add_argument("--map")
    import_cmd.add_argument("--state", action="append", help="State mapping in the form state=/absolute/path.png")

    execute_openai_cmd = sub.add_parser("execute-openai", help="Execute a text-to-image OpenAI Images API job.")
    execute_openai_cmd.add_argument("project_dir")
    execute_openai_cmd.add_argument("--run-id", required=True)
    execute_openai_cmd.add_argument("--job-id", required=True)
    execute_openai_cmd.add_argument("--dry-run", action="store_true")
    execute_openai_cmd.add_argument("--size", default="1024x1024")
    execute_openai_cmd.add_argument("--quality", default="medium")
    execute_openai_cmd.add_argument("--output-format", default="png")

    execute_gemini_cmd = sub.add_parser("execute-gemini", help="Execute a Gemini/Nano Banana image generation job.")
    execute_gemini_cmd.add_argument("project_dir")
    execute_gemini_cmd.add_argument("--run-id", required=True)
    execute_gemini_cmd.add_argument("--job-id", required=True)
    execute_gemini_cmd.add_argument("--dry-run", action="store_true")

    build_cmd = sub.add_parser("build-from-rows", help="Build a Codex pet from existing generated row strips.")
    build_cmd.add_argument("project_dir")
    build_cmd.add_argument("--rows-dir", required=True)
    build_cmd.add_argument("--run-id", required=True)
    build_cmd.add_argument("--pet-id")
    build_cmd.add_argument("--display-name")
    build_cmd.add_argument("--install", action="store_true")
    build_cmd.add_argument("--install-root")
    build_cmd.add_argument("--install-override-reason")
    build_cmd.add_argument(
        "--row-provenance",
        choices=["provider_generated", "user_supplied", "test_fixture", "mock_renderer", "local_renderer", "programmatic_renderer", "ad_hoc_renderer"],
        help="Source class for row strips. Required for install; mock/local renderer values are never installable.",
    )
    build_cmd.add_argument("--visual-approval", help="Human visual approval note required before installing.")
    build_cmd.add_argument("--reuse-transparent", action="store_true")

    build_review_cmd = sub.add_parser("build-review", help="Build a run for review, run QA, validate, and summarize review artifacts.")
    build_review_cmd.add_argument("project_dir")
    build_review_cmd.add_argument("--run-id", required=True)
    build_review_cmd.add_argument("--row-provenance", choices=["provider_generated", "user_supplied", "test_fixture"], required=True)
    build_review_cmd.add_argument("--reuse-transparent", action="store_true")

    approve_cmd = sub.add_parser("approve", help="Record human visual approval or rejection for a run artifact.")
    approve_cmd.add_argument("project_dir")
    approve_cmd.add_argument("--run-id")
    approve_cmd.add_argument("--artifact", default="contact-sheet")
    approve_cmd.add_argument("--decision", choices=["approved", "rejected"], default="approved")
    approve_cmd.add_argument("--notes", required=True)
    approve_cmd.add_argument("--author", default="human")

    review_cmd = sub.add_parser("review-status", help="Report review artifacts, approvals, and install readiness.")
    review_cmd.add_argument("project_dir")
    review_cmd.add_argument("--run-id", required=True)
    review_cmd.add_argument("--agent-mode", action="store_true")

    install_cmd = sub.add_parser("install", help="Install an approved Goodboy run package.")
    install_cmd.add_argument("project_dir")
    install_cmd.add_argument("--run-id", required=True)
    install_cmd.add_argument("--row-provenance", choices=["provider_generated", "user_supplied", "test_fixture"], required=True)
    install_cmd.add_argument("--install-root")
    install_cmd.add_argument("--install-override-reason")

    finish_cmd = sub.add_parser("finish", help="Record approval, install an approved run, and validate the project.")
    finish_cmd.add_argument("project_dir")
    finish_cmd.add_argument("--run-id", required=True)
    finish_cmd.add_argument("--approval-notes", required=True)
    finish_cmd.add_argument("--row-provenance", choices=["provider_generated", "user_supplied", "test_fixture"], default="provider_generated")
    finish_cmd.add_argument("--install-root")
    finish_cmd.add_argument("--install-override-reason")

    export_cmd = sub.add_parser("export", help="Export a Goodboy project bundle or Petdex-ready package.")
    export_cmd.add_argument("kind", choices=["project", "petdex"])
    export_cmd.add_argument("project_dir")
    export_cmd.add_argument("--run-id", required=True)
    export_cmd.add_argument("--output-dir")
    export_cmd.add_argument("--no-zip", action="store_true")

    validate_cmd = sub.add_parser("validate", help="Validate Goodboy manifests and artifact references.")
    validate_cmd.add_argument("project_dir")
    validate_cmd.add_argument("--no-write", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "init":
        project = init_project(
            Path(args.project_dir).expanduser().resolve(),
            pet_id=args.pet_id,
            display_name=args.display_name,
            species=args.species,
        )
        print(json.dumps(project.to_dict(), indent=2))
        return 0
    if args.command == "inspect":
        project = load_project(Path(args.project_dir).expanduser().resolve())
        print(json.dumps(project.to_dict(), indent=2))
        return 0
    if args.command in {"make", "start"}:
        try:
            status = make_project(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                pet_id=args.pet_id,
                display_name=args.display_name,
                species=args.species,
                sources=[Path(item) for item in args.source],
                provider=args.provider,
                model_alias=args.model_alias,
                candidate_count=args.count,
                notes=args.notes,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(status.to_dict(), indent=2))
        return 0
    if args.command == "advance":
        try:
            mapping = load_generated_mapping(args.generated_map, args.state) if args.generated_map or args.state else None
            payload = advance_project(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                run_id=args.run_id,
                provider=args.provider,
                model_alias=args.model_alias,
                candidate_id=args.candidate_id,
                baseline_image=Path(args.baseline_image).expanduser().resolve() if args.baseline_image else None,
                selection_notes=args.selection_notes,
                generated_map=mapping,
                row_provenance=args.row_provenance,
                approval_notes=args.approval_notes,
                install_root=Path(args.install_root).expanduser().resolve() if args.install_root else None,
                override_reason=args.install_override_reason,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.agent_mode:
            print(json.dumps(payload, indent=2))
        else:
            print(f"stage: {payload['stage']}")
            print(f"gate: {payload['gate']}")
            print(f"next_human_action: {payload['next_human_action']}")
            print("actions:")
            for action in payload["actions"]:
                print(f"- {action}")
            if payload["artifacts_to_show_user"]:
                print("artifacts_to_show_user:")
                for artifact in payload["artifacts_to_show_user"]:
                    print(f"- {artifact}")
        return 0
    if args.command == "next":
        try:
            status = next_status(Path(args.project_dir).expanduser().resolve())
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.agent_mode:
            print(json.dumps(status.to_dict(), indent=2))
        else:
            print(f"stage: {status.stage}")
            print(f"next_action: {status.next_action}")
            print("allowed_commands:")
            for command in status.allowed_commands:
                print(f"- {command}")
            print("blocked_actions:")
            for action in status.blocked_actions:
                print(f"- {action}")
        return 0
    if args.command == "doctor":
        try:
            payload = doctor(Path(args.project_dir).expanduser().resolve())
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.agent_mode:
            print(json.dumps(payload, indent=2))
        else:
            print(f"validation_ok: {payload['validation']['ok']}")
            print(f"stage: {payload['workflow']['stage']}")
            print(f"next_action: {payload['workflow']['next_action']}")
            print(f"missing_generated_outputs: {len(payload['missing_generated_outputs'])}")
        return 0
    if args.command == "ingest":
        images = ingest_images(
            Path(args.project_dir).expanduser().resolve(),
            [Path(item) for item in args.images],
            role=args.role,
            notes=args.notes,
        )
        print(json.dumps({"images": [image.to_dict() for image in images]}, indent=2))
        return 0
    if args.command == "source-card":
        card = draft_source_card(Path(args.project_dir).expanduser().resolve(), user_notes=args.notes)
        print(json.dumps(card.to_dict(), indent=2))
        return 0
    if args.command == "style-default":
        project_dir = Path(args.project_dir).expanduser().resolve()
        if (project_dir / STYLE_PATH).is_file() and not args.refresh:
            sheet = read_json(project_dir / STYLE_PATH)
            print(json.dumps({"already_exists": True, "style_sheet": sheet}, indent=2))
            return 0
        sheet = save_default_style_sheet(
            project_dir,
            style_id=args.style_id,
            style_preset=args.preset,
            subject_kind=args.subject_kind,
            user_style_overrides=args.user_style,
            ai_critique_overrides=args.ai_critique,
        )
        print(json.dumps(sheet.to_dict(), indent=2))
        return 0
    if args.command == "plan-rows":
        project_dir = Path(args.project_dir).expanduser().resolve()
        jobs_path = project_dir / "runs" / args.run_id / "generation-jobs.json"
        if jobs_path.is_file() and not args.refresh:
            print(json.dumps({"already_exists": True, "jobs": read_json(jobs_path).get("jobs", [])}, indent=2))
            return 0
        jobs = plan_row_generation_jobs(
            project_dir=project_dir,
            run_id=args.run_id,
            provider=args.provider,
            model_alias=args.model_alias,
            character_reference=args.character_reference,
        )
        print(json.dumps({"jobs": [job.to_dict() for job in jobs]}, indent=2))
        return 0
    if args.command == "plan-candidates":
        project_dir = Path(args.project_dir).expanduser().resolve()
        index_path = project_dir / CANDIDATE_INDEX
        if index_path.is_file() and not args.refresh:
            contact_sheet = None
            if not args.no_sheet:
                contact_sheet = build_candidate_contact_sheet(project_dir=project_dir)
            print(json.dumps({"already_exists": True, "candidates": read_json(index_path).get("candidates", []), "contact_sheet": str(contact_sheet) if contact_sheet else None}, indent=2))
            return 0
        candidates = plan_baseline_candidates(
            project_dir=project_dir,
            provider=args.provider,
            model_alias=args.model_alias,
            count=args.count,
            render_sheet=not args.no_sheet,
        )
        contact_sheet = project_dir / "candidates" / "contact-sheet.png"
        print(json.dumps({"candidates": [candidate.to_dict() for candidate in candidates], "contact_sheet": str(contact_sheet) if contact_sheet.is_file() else None}, indent=2))
        return 0
    if args.command == "select-candidate":
        character = select_baseline_candidate(
            project_dir=Path(args.project_dir).expanduser().resolve(),
            candidate_id=args.candidate_id,
            image_path=Path(args.image_path) if args.image_path else None,
            notes=args.notes,
        )
        print(json.dumps(character.to_dict(), indent=2))
        return 0
    if args.command == "candidate-image":
        try:
            image = store_candidate_image(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                candidate_id=args.candidate_id,
                image_path=Path(args.image_path).expanduser().resolve(),
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"candidate_id": args.candidate_id, "image_path": image}, indent=2))
        return 0
    if args.command == "candidate-sheet":
        output = build_candidate_contact_sheet(
            project_dir=Path(args.project_dir).expanduser().resolve(),
            output_path=Path(args.output).expanduser().resolve() if args.output else None,
            columns=args.columns,
        )
        print(json.dumps({"contact_sheet": str(output)}, indent=2))
        return 0
    if args.command == "feedback":
        event = create_feedback_event(
            project_dir=Path(args.project_dir).expanduser().resolve(),
            target=args.target,
            text=args.text,
            author=args.author,
            create_branch=not args.no_branch,
            branch_id=args.branch_id,
            parent=args.parent,
        )
        print(json.dumps(event.to_dict(), indent=2))
        return 0
    if args.command == "critique":
        try:
            report = record_critique(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                critique_id=args.critique_id,
                target=args.target,
                author=args.author,
                findings=args.finding,
                recommendations=args.recommendation,
                identity_score=args.identity_score,
                style_score=args.style_score,
                apply_to_style=args.apply_to_style,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    if args.command == "provenance":
        try:
            report = write_provenance_report(Path(args.project_dir).expanduser().resolve())
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2))
        return 0
    if args.command == "adapters":
        capabilities = list_capabilities()
        if args.json:
            print(json.dumps({"adapters": capabilities}, indent=2))
        else:
            for capability in capabilities:
                print(f"{capability['id']}: {capability['display_name']} ({capability['default_model_alias']})")
        return 0
    if args.command == "handoff":
        invocation = prepare_handoff(
            Path(args.project_dir).expanduser().resolve(),
            run_id=args.run_id,
            job_id=args.job_id,
        )
        print(json.dumps(invocation.to_dict(), indent=2))
        return 0
    if args.command == "generate-handoff":
        try:
            summary = generate_handoffs(
                Path(args.project_dir).expanduser().resolve(),
                run_id=args.run_id,
                all_jobs=args.all,
                job_ids=args.job_id,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "import-generated":
        try:
            mapping = load_generated_mapping(args.map, args.state)
            summary = import_generated_outputs(
                Path(args.project_dir).expanduser().resolve(),
                run_id=args.run_id,
                mapping=mapping,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "execute-openai":
        invocation = execute_openai_image_job(
            Path(args.project_dir).expanduser().resolve(),
            run_id=args.run_id,
            job_id=args.job_id,
            dry_run=args.dry_run,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
        )
        print(json.dumps(invocation.to_dict(), indent=2))
        return 0 if invocation.status != "failed" else 1
    if args.command == "execute-gemini":
        invocation = execute_gemini_image_job(
            Path(args.project_dir).expanduser().resolve(),
            run_id=args.run_id,
            job_id=args.job_id,
            dry_run=args.dry_run,
        )
        print(json.dumps(invocation.to_dict(), indent=2))
        return 0 if invocation.status != "failed" else 1
    if args.command == "build-from-rows":
        try:
            summary = build_from_row_strips(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                rows_dir=Path(args.rows_dir).expanduser().resolve(),
                run_id=args.run_id,
                pet_id=args.pet_id,
                display_name=args.display_name,
                install=args.install,
                install_root=Path(args.install_root).expanduser().resolve() if args.install_root else None,
                install_override_reason=args.install_override_reason,
                row_provenance=args.row_provenance,
                visual_approval=args.visual_approval,
                force=not args.reuse_transparent,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary.to_dict(), indent=2))
        return 0
    if args.command == "build-review":
        try:
            summary = build_review(
                Path(args.project_dir).expanduser().resolve(),
                run_id=args.run_id,
                row_provenance=args.row_provenance,
                force=not args.reuse_transparent,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "approve":
        try:
            project_dir = Path(args.project_dir).expanduser().resolve()
            run_id = args.run_id or latest_run_id(project_dir)
            if not run_id:
                raise ValueError("run id is required because no latest run exists")
            approval = approve_artifact(
                project_dir=project_dir,
                run_id=run_id,
                artifact=args.artifact,
                decision=args.decision,
                notes=args.notes,
                author=args.author,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(approval.to_dict(), indent=2))
        return 0
    if args.command == "review-status":
        try:
            status = review_status(Path(args.project_dir).expanduser().resolve(), args.run_id)
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.agent_mode:
            print(json.dumps(status, indent=2))
        else:
            print(f"run_id: {status['run_id']}")
            print(f"stage: {status['stage']}")
            print(f"has_visual_approval: {status['has_visual_approval']}")
            print(f"install_ready: {status['install_ready']}")
            print("review_artifacts:")
            for artifact in status["review_artifacts"]:
                print(f"- {artifact}")
            if status["suspicious_renderer_scripts"]:
                print("suspicious_renderer_scripts:")
                for path in status["suspicious_renderer_scripts"]:
                    print(f"- {path}")
        return 0
    if args.command == "install":
        try:
            target = install_approved_run(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                run_id=args.run_id,
                row_provenance=args.row_provenance,
                install_root=Path(args.install_root).expanduser().resolve() if args.install_root else None,
                override_reason=args.install_override_reason,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"installed": str(target)}, indent=2))
        return 0
    if args.command == "finish":
        try:
            summary = finish_run(
                project_dir=Path(args.project_dir).expanduser().resolve(),
                run_id=args.run_id,
                approval_notes=args.approval_notes,
                row_provenance=args.row_provenance,
                install_root=Path(args.install_root).expanduser().resolve() if args.install_root else None,
                override_reason=args.install_override_reason,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "export":
        try:
            if args.kind == "project":
                summary = export_project_bundle(
                    Path(args.project_dir).expanduser().resolve(),
                    run_id=args.run_id,
                    output_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
                    zip_output=not args.no_zip,
                )
            else:
                summary = export_petdex_package(
                    Path(args.project_dir).expanduser().resolve(),
                    run_id=args.run_id,
                    output_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
                    zip_output=not args.no_zip,
                )
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "validate":
        report = validate_project(
            Path(args.project_dir).expanduser().resolve(),
            write_report=not args.no_write,
        )
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.ok else 1
    raise AssertionError(f"unhandled command: {args.command}")


def load_generated_mapping(map_path: str | None, state_items: list[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if map_path:
        raw = read_json(Path(map_path).expanduser().resolve())
        if "states" in raw and isinstance(raw["states"], dict):
            raw = raw["states"]
        if not isinstance(raw, dict):
            raise ValueError("generated output map must be a JSON object")
        mapping.update({str(key): str(value) for key, value in raw.items()})
    for item in state_items or []:
        if "=" not in item:
            raise ValueError("--state must use state=/path/to/generated.png")
        state, path = item.split("=", 1)
        mapping[state] = path
    if not mapping:
        raise ValueError("provide --map or at least one --state")
    return mapping


if __name__ == "__main__":
    raise SystemExit(main())
