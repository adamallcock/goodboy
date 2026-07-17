"""Strict manifest validation for Goodboy projects."""

from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from typing import Any

from .adapters import CAPABILITY_REGISTRY
from .contracts import (
    ROW_FRAME_COUNTS,
    STATE_ORDER,
    V2_OUTPUT_CONTRACT,
    V2_STATE_ORDER,
    contract_from_dict,
    get_output_contract,
)
from .identity import IDENTITY_PROFILE, REFERENCE_COVERAGE
from .ingest import SOURCE_CARD, SOURCE_MANIFEST
from .jobs import JOB_STATUSES
from .jsonio import read_json, read_jsonl, write_json
from .schemas import (
    BranchManifest,
    CharacterCard,
    CritiqueReport,
    EmotionStyleSheet,
    FeedbackEvent,
    GenerationJob,
    IdentityProfile,
    JobEvent,
    LikenessReport,
    ManifestValidationIssue,
    ManifestValidationReport,
    PetProject,
    ProviderInvocation,
    RunSummary,
    ReferenceCoverage,
    SourceCard,
    SourceImage,
    StyleCandidate,
)
from .style import STYLE_PATH


def validate_project(project_dir: Path, *, write_report: bool = True) -> ManifestValidationReport:
    issues: list[ManifestValidationIssue] = []
    checked_files: list[str] = []
    validate_project_manifest(project_dir, issues, checked_files)
    validate_source_images(project_dir, issues, checked_files)
    validate_source_card(project_dir, issues, checked_files)
    validate_identity(project_dir, issues, checked_files)
    validate_candidates(project_dir, issues, checked_files)
    validate_character(project_dir, issues, checked_files)
    validate_style_sheet(project_dir, issues, checked_files)
    validate_feedback(project_dir, issues, checked_files)
    validate_critiques(project_dir, issues, checked_files)
    validate_branches(project_dir, issues, checked_files)
    validate_runs(project_dir, issues, checked_files)
    report = ManifestValidationReport(
        ok=not any(issue.severity == "error" for issue in issues),
        checked_files=checked_files,
        issues=issues,
    )
    if write_report:
        write_json(project_dir / "validation" / "manifest-validation.json", report.to_dict())
    return report


def validate_project_manifest(
    project_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    rel = Path("goodboy.json")
    raw = validate_json_dataclass(project_dir, rel, PetProject, issues, checked_files)
    if raw is None:
        return
    try:
        declared = get_output_contract(str(raw.get("contract_id", "")))
    except ValueError as exc:
        add_error(issues, rel, str(exc))
        return
    embedded = contract_from_dict(
        raw.get("output_contract") if isinstance(raw.get("output_contract"), dict) else None
    )
    if embedded.contract_id != declared.contract_id:
        add_error(
            issues,
            rel,
            f"output_contract `{embedded.contract_id}` disagrees with contract_id `{declared.contract_id}`",
        )
    if raw.get("contract_version") != declared.contract_version:
        add_error(issues, rel, f"contract_version must be `{declared.contract_version}`")
    embedded_raw = raw.get("output_contract", {})
    for key, expected in (
        ("rows", declared.rows),
        ("columns", declared.columns),
        ("atlas_width", declared.atlas_width),
        ("atlas_height", declared.atlas_height),
        ("sprite_version_number", declared.sprite_version_number),
    ):
        if embedded_raw.get(key) != expected:
            add_error(issues, rel, f"output_contract.{key} must be {expected}")
    privacy = raw.get("privacy_policy")
    if not isinstance(privacy, dict):
        add_error(issues, rel, "privacy_policy must be an object")
    else:
        for key in (
            "sources_local_by_default",
            "strip_exif_for_provider",
            "include_sources_in_exports",
            "provider_consent_required",
        ):
            if not isinstance(privacy.get(key), bool):
                add_error(issues, rel, f"privacy_policy.{key} must be boolean")
    active_run = raw.get("active_run_id")
    if active_run and not (project_dir / "runs" / str(active_run)).is_dir():
        add_error(issues, rel, f"active_run_id does not exist: {active_run}")


def validate_json_dataclass(
    project_dir: Path,
    relative_path: Path,
    cls: type[Any],
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> dict[str, Any] | None:
    path = project_dir / relative_path
    if not path.is_file():
        add_error(issues, relative_path, "missing manifest")
        return None
    checked_files.append(str(relative_path))
    try:
        raw = read_json(path)
    except Exception as exc:
        add_error(issues, relative_path, f"invalid JSON: {exc}")
        return None
    if not isinstance(raw, dict):
        add_error(issues, relative_path, "manifest must be a JSON object")
        return None
    check_unknown_and_required(raw, cls, relative_path, issues)
    try:
        cls.from_dict(raw) if hasattr(cls, "from_dict") else cls(**raw)
    except Exception as exc:
        add_error(issues, relative_path, f"cannot load as {cls.__name__}: {exc}")
    return raw


def check_unknown_and_required(
    raw: dict[str, Any],
    cls: type[Any],
    path: Path,
    issues: list[ManifestValidationIssue],
) -> None:
    if not is_dataclass(cls):
        return
    cls_fields = {field.name: field for field in fields(cls)}
    for key in sorted(set(raw) - set(cls_fields)):
        add_error(issues, path, f"unknown field `{key}`")
    missing = []
    for name, field_info in cls_fields.items():
        has_default = field_info.default is not MISSING
        has_factory = field_info.default_factory is not MISSING
        if name not in raw and not has_default and not has_factory:
            missing.append(name)
    for name in missing:
        add_error(issues, path, f"missing required field `{name}`")


def validate_source_images(
    project_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    path = project_dir / SOURCE_MANIFEST
    if not path.exists():
        return
    rel = Path(SOURCE_MANIFEST)
    checked_files.append(str(rel))
    raw = read_json(path)
    images = raw.get("images")
    if not isinstance(images, list):
        add_error(issues, rel, "`images` must be a list")
        return
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for index, item in enumerate(images):
        item_path = Path(f"{SOURCE_MANIFEST}:images[{index}]")
        if not isinstance(item, dict):
            add_error(issues, item_path, "source image entry must be an object")
            continue
        check_unknown_and_required(item, SourceImage, item_path, issues)
        try:
            image = SourceImage.from_dict(item)
        except Exception as exc:
            add_error(issues, item_path, f"cannot load SourceImage: {exc}")
            continue
        if image.id in seen_ids:
            add_error(issues, item_path, f"duplicate source id `{image.id}`")
        seen_ids.add(image.id)
        if image.sha256 in seen_hashes:
            add_warning(issues, item_path, f"duplicate source hash `{image.sha256}`")
        seen_hashes.add(image.sha256)
        require_relative_existing(project_dir, image.path, item_path, issues, "source image")
        if image.thumbnail_path:
            require_relative_existing(project_dir, image.thumbnail_path, item_path, issues, "thumbnail")
        if image.provider_derivative_path:
            if not image.provider_derivative_path.startswith("sources/provider-derivatives/"):
                add_error(issues, item_path, "provider derivative must live under sources/provider-derivatives")
            require_relative_existing(
                project_dir,
                image.provider_derivative_path,
                item_path,
                issues,
                "provider derivative",
            )
        for provider, permitted in image.provider_permissions.items():
            if provider not in CAPABILITY_REGISTRY:
                add_error(issues, item_path, f"unknown provider permission `{provider}`")
            if not isinstance(permitted, bool):
                add_error(issues, item_path, f"provider permission `{provider}` must be boolean")
            if permitted:
                receipt = project_dir / "decisions" / "provider-consent" / f"{provider}.json"
                if not receipt.is_file():
                    add_error(issues, item_path, f"provider `{provider}` permission has no consent receipt")
        if image.width <= 0 or image.height <= 0:
            add_error(issues, item_path, "width and height must be positive")


def validate_source_card(
    project_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    if not (project_dir / SOURCE_CARD).exists():
        return
    raw = validate_json_dataclass(project_dir, Path(SOURCE_CARD), SourceCard, issues, checked_files)
    if raw is None:
        return
    for field_name in ("must_keep", "avoid", "uncertainties", "source_image_ids", "source_image_paths"):
        if not isinstance(raw.get(field_name, []), list):
            add_error(issues, Path(SOURCE_CARD), f"`{field_name}` must be a list")
    for source_path in raw.get("source_image_paths", []):
        require_relative_existing(project_dir, source_path, Path(SOURCE_CARD), issues, "source image path")


def validate_identity(
    project_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    profile_path = project_dir / IDENTITY_PROFILE
    if profile_path.is_file():
        rel = Path(IDENTITY_PROFILE)
        checked_files.append(str(rel))
        raw = read_json(profile_path)
        if not isinstance(raw, dict):
            add_error(issues, rel, "identity profile must be an object")
        else:
            check_unknown_and_required(raw, IdentityProfile, rel, issues)
            try:
                profile = IdentityProfile.from_dict(raw)
            except Exception as exc:
                add_error(issues, rel, f"cannot load IdentityProfile: {exc}")
            else:
                seen: set[str] = set()
                source_ids = {image.id for image in load_source_image_objects(project_dir)}
                for trait in profile.traits:
                    if trait.id in seen:
                        add_error(issues, rel, f"duplicate identity trait id `{trait.id}`")
                    seen.add(trait.id)
                    if trait.importance not in {"signature", "important", "supporting", "uncertain", "ignore"}:
                        add_error(issues, rel, f"invalid importance `{trait.importance}` for `{trait.id}`")
                    if not 0 <= trait.confidence <= 1:
                        add_error(issues, rel, f"confidence for `{trait.id}` must be between 0 and 1")
                    for evidence in trait.evidence:
                        if evidence.source_id not in source_ids:
                            add_error(issues, rel, f"trait `{trait.id}` cites unknown source `{evidence.source_id}`")
                if profile.status == "confirmed":
                    unlocked = [
                        trait.id
                        for trait in profile.traits
                        if trait.importance == "signature" and (not trait.locked or not trait.user_confirmed)
                    ]
                    if unlocked:
                        add_error(issues, rel, f"confirmed profile has unlocked signature traits: {unlocked}")
    coverage_path = project_dir / REFERENCE_COVERAGE
    if coverage_path.is_file():
        validate_json_dataclass(
            project_dir,
            Path(REFERENCE_COVERAGE),
            ReferenceCoverage,
            issues,
            checked_files,
        )


def load_source_image_objects(project_dir: Path) -> list[SourceImage]:
    path = project_dir / SOURCE_MANIFEST
    if not path.is_file():
        return []
    raw = read_json(path)
    return [SourceImage.from_dict(item) for item in raw.get("images", []) if isinstance(item, dict)]


def validate_candidates(
    project_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    index_path = project_dir / "candidates" / "baseline-candidates.json"
    if not index_path.exists():
        return
    rel = Path("candidates/baseline-candidates.json")
    checked_files.append(str(rel))
    raw = read_json(index_path)
    candidates = raw.get("candidates")
    if not isinstance(candidates, list):
        add_error(issues, rel, "`candidates` must be a list")
        return
    selected_by_dimension: dict[str, int] = {}
    for index, item in enumerate(candidates):
        item_path = Path(f"candidates/baseline-candidates.json:candidates[{index}]")
        validate_candidate_object(project_dir, item, item_path, issues)
        if isinstance(item, dict) and item.get("selected"):
            dimension = str(item.get("evaluation_dimension", "likeness"))
            selected_by_dimension[dimension] = selected_by_dimension.get(dimension, 0) + 1
    for dimension, selected in selected_by_dimension.items():
        if selected > 1:
            add_error(
                issues,
                rel,
                f"only one baseline candidate may be selected for evaluation dimension `{dimension}`",
            )
    for candidate_file in sorted((project_dir / "candidates").glob("*/candidate.json")):
        rel_candidate = candidate_file.relative_to(project_dir)
        checked_files.append(str(rel_candidate))
        validate_candidate_object(project_dir, read_json(candidate_file), rel_candidate, issues)


def validate_candidate_object(
    project_dir: Path,
    item: Any,
    path: Path,
    issues: list[ManifestValidationIssue],
) -> None:
    if not isinstance(item, dict):
        add_error(issues, path, "candidate must be an object")
        return
    check_unknown_and_required(item, StyleCandidate, path, issues)
    try:
        candidate = StyleCandidate(**item)
    except Exception as exc:
        add_error(issues, path, f"cannot load StyleCandidate: {exc}")
        return
    require_relative_existing(project_dir, candidate.prompt_path, path, issues, "candidate prompt")
    if candidate.image_path:
        require_relative_existing(project_dir, candidate.image_path, path, issues, "candidate image")
    if candidate.review_image_path:
        require_relative_existing(
            project_dir,
            candidate.review_image_path,
            path,
            issues,
            "normalized candidate review image",
        )
    for label in (
        "holistic_gestalt_score",
        "signature_trait_score",
        "small_size_readability_score",
        "overall_identity_score",
    ):
        score = getattr(candidate, label)
        if score is not None and not 1.0 <= float(score) <= 5.0:
            add_error(issues, path, f"{label} must be between 1 and 5")
    for source_path in candidate.source_images:
        require_relative_existing(project_dir, source_path, path, issues, "candidate source image")
        if Path(source_path).as_posix().startswith("sources/originals/"):
            add_error(issues, path, "candidate provider inputs must not reference original source photos")
    if candidate.provider not in CAPABILITY_REGISTRY:
        add_error(issues, path, f"unknown provider `{candidate.provider}`")


def validate_character(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    if not (project_dir / "character" / "character-card.json").exists():
        return
    raw = validate_json_dataclass(project_dir, Path("character/character-card.json"), CharacterCard, issues, checked_files)
    if raw and raw.get("selected_baseline_image"):
        require_relative_existing(project_dir, raw["selected_baseline_image"], Path("character/character-card.json"), issues, "selected baseline image")
    if raw and raw.get("identity_anchor_image"):
        require_relative_existing(project_dir, raw["identity_anchor_image"], Path("character/character-card.json"), issues, "identity anchor image")


def validate_style_sheet(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    path = project_dir / STYLE_PATH
    if not path.exists():
        return
    rel = Path(STYLE_PATH)
    checked_files.append(str(rel))
    raw = read_json(path)
    if not isinstance(raw, dict):
        add_error(issues, rel, "style sheet must be an object")
        return
    check_unknown_and_required(raw, EmotionStyleSheet, rel, issues)
    try:
        sheet = EmotionStyleSheet.from_dict(raw)
    except Exception as exc:
        add_error(issues, rel, f"cannot load EmotionStyleSheet: {exc}")
        return
    states = [spec.state for spec in sheet.state_specs]
    if states != STATE_ORDER:
        add_error(issues, rel, f"state order must be {STATE_ORDER}; got {states}")
    for spec in sheet.state_specs:
        expected = ROW_FRAME_COUNTS.get(spec.state)
        if expected is None:
            add_error(issues, rel, f"unknown state `{spec.state}`")
        elif spec.frame_count != expected:
            add_error(issues, rel, f"{spec.state} frame_count is {spec.frame_count}, expected {expected}")


def validate_feedback(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    path = project_dir / "feedback" / "events.json"
    if not path.exists():
        return
    rel = Path("feedback/events.json")
    checked_files.append(str(rel))
    raw = read_json(path)
    events = raw.get("events")
    if not isinstance(events, list):
        add_error(issues, rel, "`events` must be a list")
        return
    seen: set[str] = set()
    for index, item in enumerate(events):
        item_path = Path(f"feedback/events.json:events[{index}]")
        if not isinstance(item, dict):
            add_error(issues, item_path, "feedback event must be an object")
            continue
        check_unknown_and_required(item, FeedbackEvent, item_path, issues)
        try:
            event = FeedbackEvent.from_dict(item)
        except Exception as exc:
            add_error(issues, item_path, f"cannot load FeedbackEvent: {exc}")
            continue
        if event.id in seen:
            add_error(issues, item_path, f"duplicate feedback event id `{event.id}`")
        seen.add(event.id)
        if event.author not in {"human", "vision_critic", "system"}:
            add_error(issues, item_path, f"unknown feedback author `{event.author}`")
        if not event.target:
            add_error(issues, item_path, "target is required")
        if not event.text.strip():
            add_error(issues, item_path, "text is required")


def validate_branches(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    for branch_file in sorted((project_dir / "branches").glob("*/branch.json")):
        rel = branch_file.relative_to(project_dir)
        checked_files.append(str(rel))
        raw = read_json(branch_file)
        if not isinstance(raw, dict):
            add_error(issues, rel, "branch manifest must be an object")
            continue
        check_unknown_and_required(raw, BranchManifest, rel, issues)
        try:
            branch = BranchManifest.from_dict(raw)
        except Exception as exc:
            add_error(issues, rel, f"cannot load BranchManifest: {exc}")
            continue
        if branch.id != branch_file.parent.name:
            add_error(issues, rel, f"branch id `{branch.id}` must match folder `{branch_file.parent.name}`")


def validate_critiques(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    for critique_file in sorted((project_dir / "critiques").glob("*.json")):
        rel = critique_file.relative_to(project_dir)
        checked_files.append(str(rel))
        raw = read_json(critique_file)
        if not isinstance(raw, dict):
            add_error(issues, rel, "critique report must be an object")
            continue
        check_unknown_and_required(raw, CritiqueReport, rel, issues)
        try:
            report = CritiqueReport.from_dict(raw)
        except Exception as exc:
            add_error(issues, rel, f"cannot load CritiqueReport: {exc}")
            continue
        if report.id != critique_file.stem:
            add_error(issues, rel, f"critique id `{report.id}` must match file `{critique_file.stem}`")
        if report.author not in {"human", "vision_critic", "system"}:
            add_error(issues, rel, f"unknown critique author `{report.author}`")
        for label, score in {"identity_score": report.identity_score, "style_score": report.style_score}.items():
            if score is not None and not 0 <= score <= 1:
                add_error(issues, rel, f"{label} must be between 0 and 1")


def validate_runs(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    for run_dir in sorted((project_dir / "runs").glob("*")):
        if not run_dir.is_dir():
            continue
        validate_generation_jobs(project_dir, run_dir, issues, checked_files)
        validate_job_events(project_dir, run_dir, issues, checked_files)
        validate_provider_invocations(project_dir, run_dir, issues, checked_files)
        validate_run_summary(project_dir, run_dir, issues, checked_files)
        validate_likeness_report(project_dir, run_dir, issues, checked_files)
        validate_v2_package_artifacts(project_dir, run_dir, issues, checked_files)


def validate_generation_jobs(
    project_dir: Path,
    run_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    path = run_dir / "generation-jobs.json"
    if not path.exists():
        return
    rel = path.relative_to(project_dir)
    checked_files.append(str(rel))
    raw = read_json(path)
    jobs = raw.get("jobs")
    if not isinstance(jobs, list):
        add_error(issues, rel, "`jobs` must be a list")
        return
    seen: set[str] = set()
    expected_outputs = {
        str(item.get("expected_output"))
        for item in jobs
        if isinstance(item, dict) and item.get("expected_output")
    }
    if len(expected_outputs) != len(
        [item for item in jobs if isinstance(item, dict) and item.get("expected_output")]
    ):
        add_error(issues, rel, "generation jobs must have unique expected_output paths")
    job_statuses = {
        str(item.get("id")): str(item.get("status"))
        for item in jobs
        if isinstance(item, dict)
    }
    for index, item in enumerate(jobs):
        item_path = Path(f"{rel}:jobs[{index}]")
        if not isinstance(item, dict):
            add_error(issues, item_path, "generation job must be an object")
            continue
        check_unknown_and_required(item, GenerationJob, item_path, issues)
        try:
            job = GenerationJob(**item)
        except Exception as exc:
            add_error(issues, item_path, f"cannot load GenerationJob: {exc}")
            continue
        if job.id in seen:
            add_error(issues, item_path, f"duplicate generation job id `{job.id}`")
        seen.add(job.id)
        if job.provider not in CAPABILITY_REGISTRY:
            add_error(issues, item_path, f"unknown provider `{job.provider}`")
        if job.status not in JOB_STATUSES:
            add_error(issues, item_path, f"invalid job status `{job.status}`")
        require_relative_existing(project_dir, job.prompt_path, item_path, issues, "job prompt")
        for input_image in job.input_images:
            if Path(input_image).as_posix().startswith("sources/originals/"):
                add_error(issues, item_path, "provider job input must not reference original source photos")
            if job.status in {"planned", "blocked"} and input_image in expected_outputs:
                continue
            if job.status in {"planned", "blocked"} and (
                "look-anchors-" in input_image or "look-row-9.png" in input_image
            ):
                continue
            require_relative_existing(project_dir, input_image, item_path, issues, "job input image")
        if job.state and job.state not in {*V2_STATE_ORDER, "look-cardinals"}:
            add_error(issues, item_path, f"unknown state `{job.state}`")
        for dep in job.depends_on:
            if dep not in seen and not any(isinstance(other, dict) and other.get("id") == dep for other in jobs):
                add_error(issues, item_path, f"unknown dependency `{dep}`")
        unresolved = [
            dep
            for dep in job.depends_on
            if job_statuses.get(dep) not in {"complete", "approved"}
        ]
        if job.status == "ready" and unresolved:
            add_error(issues, item_path, f"ready job has unresolved dependencies: {unresolved}")
        if job.status == "blocked" and not unresolved:
            add_error(issues, item_path, "blocked job has no unresolved dependency")
        if job.status in {"complete", "approved"}:
            require_relative_existing(
                project_dir,
                job.selected_output_path or job.expected_output,
                item_path,
                issues,
                "completed job output",
            )
    validate_job_dag(jobs, rel, issues)


def validate_job_dag(
    jobs: list[Any],
    path: Path,
    issues: list[ManifestValidationIssue],
) -> None:
    graph = {
        str(item.get("id")): [str(dep) for dep in item.get("depends_on", [])]
        for item in jobs
        if isinstance(item, dict)
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            add_error(issues, path, f"generation job dependency cycle includes `{node}`")
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def validate_job_events(
    project_dir: Path,
    run_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return
    rel = path.relative_to(project_dir)
    checked_files.append(str(rel))
    try:
        events = read_jsonl(path)
    except ValueError as exc:
        add_error(issues, rel, str(exc))
        return
    jobs_path = run_dir / "generation-jobs.json"
    known_jobs = {
        str(item.get("id"))
        for item in read_json(jobs_path).get("jobs", [])
        if isinstance(item, dict)
    } if jobs_path.is_file() else set()
    seen: set[str] = set()
    previous_at = ""
    for index, raw in enumerate(events):
        item_path = Path(f"{rel}:line[{index + 1}]")
        if not isinstance(raw, dict):
            add_error(issues, item_path, "job event must be an object")
            continue
        check_unknown_and_required(raw, JobEvent, item_path, issues)
        try:
            event = JobEvent(**raw)
        except Exception as exc:
            add_error(issues, item_path, f"cannot load JobEvent: {exc}")
            continue
        if event.id in seen:
            add_error(issues, item_path, f"duplicate event id `{event.id}`")
        seen.add(event.id)
        if event.run_id != run_dir.name:
            add_error(issues, item_path, f"event run_id `{event.run_id}` must match `{run_dir.name}`")
        if event.job_id not in known_jobs:
            add_error(issues, item_path, f"event cites unknown job `{event.job_id}`")
        for status in (event.from_status, event.to_status):
            if status is not None and status not in JOB_STATUSES:
                add_error(issues, item_path, f"event has invalid status `{status}`")
        if previous_at and event.created_at < previous_at:
            add_warning(issues, item_path, "event timestamp is earlier than the previous event")
        previous_at = event.created_at


def validate_provider_invocations(
    project_dir: Path,
    run_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    for invocation_file in sorted((run_dir / "provider-invocations").glob("*.json")):
        rel = invocation_file.relative_to(project_dir)
        checked_files.append(str(rel))
        raw = read_json(invocation_file)
        if not isinstance(raw, dict):
            add_error(issues, rel, "provider invocation must be an object")
            continue
        check_unknown_and_required(raw, ProviderInvocation, rel, issues)
        try:
            invocation = ProviderInvocation(**raw)
        except Exception as exc:
            add_error(issues, rel, f"cannot load ProviderInvocation: {exc}")
            continue
        if invocation.adapter not in CAPABILITY_REGISTRY:
            add_error(issues, rel, f"unknown adapter `{invocation.adapter}`")
        if invocation.status not in {"prepared", "running", "complete", "failed"}:
            add_error(issues, rel, f"invalid invocation status `{invocation.status}`")
        for output in invocation.output_paths:
            require_relative_existing(project_dir, output, rel, issues, "provider output")


def validate_run_summary(project_dir: Path, run_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    path = run_dir / "run-summary.json"
    if not path.exists():
        return
    rel = path.relative_to(project_dir)
    raw = validate_json_dataclass(project_dir, rel, RunSummary, issues, checked_files)
    if raw is None:
        return
    for key in ("spritesheet", "contact_sheet", "edge_preview", "validation", "review", "duplicate_audit"):
        require_existing_any_path(project_dir, raw.get(key), rel, issues, key)
    if raw.get("package_dir"):
        require_existing_any_path(project_dir, raw.get("package_dir"), rel, issues, "package_dir")
    if raw.get("sprite_version_number") == 2 and raw.get("contract_id") != V2_OUTPUT_CONTRACT.contract_id:
        add_error(issues, rel, "v2 run summary must declare contract_id codex-pet-v2")


def validate_likeness_report(
    project_dir: Path,
    run_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    path = run_dir / "qa" / "likeness-report.json"
    if not path.is_file():
        return
    rel = path.relative_to(project_dir)
    checked_files.append(str(rel))
    raw = read_json(path)
    if not isinstance(raw, dict):
        add_error(issues, rel, "likeness report must be an object")
        return
    check_unknown_and_required(raw, LikenessReport, rel, issues)
    try:
        report = LikenessReport.from_dict(raw)
    except Exception as exc:
        add_error(issues, rel, f"cannot load LikenessReport: {exc}")
        return
    if report.run_id != run_dir.name:
        add_error(issues, rel, "likeness report run_id must match its run folder")
    if report.status == "approved" and report.signature_failures:
        add_error(issues, rel, "approved likeness report cannot contain signature failures")
    if report.status == "approved" and (not report.reviewed_by or not report.reviewed_at):
        add_error(issues, rel, "approved likeness report requires reviewer and timestamp")
    if report.advisory_metrics and not report.advisory_metrics.get("advisory_only", False):
        add_error(issues, rel, "automated identity metrics must be explicitly marked advisory_only")


def validate_v2_package_artifacts(
    project_dir: Path,
    run_dir: Path,
    issues: list[ManifestValidationIssue],
    checked_files: list[str],
) -> None:
    package_dir = run_dir / "package"
    if not package_dir.is_dir():
        return
    manifest_path = package_dir / "pet.json"
    if not manifest_path.is_file() or read_json(manifest_path).get("spriteVersionNumber") != 2:
        return
    from .v2_backend import validate_v2_package

    result = validate_v2_package(package_dir)
    rel = package_dir.relative_to(project_dir)
    checked_files.extend(
        str(path.relative_to(project_dir))
        for path in (package_dir / "pet.json", package_dir / "spritesheet.webp")
        if path.is_file()
    )
    if not result["ok"]:
        for message in result["errors"]:
            add_error(issues, rel, str(message))
    unexpected = [
        path.name
        for path in package_dir.iterdir()
        if path.name not in {"pet.json", "spritesheet.webp", "validation.json"}
    ]
    if unexpected:
        add_error(issues, rel, f"install package contains unexpected files: {sorted(unexpected)}")


def require_relative_existing(
    project_dir: Path,
    value: Any,
    path: Path,
    issues: list[ManifestValidationIssue],
    label: str,
) -> None:
    if not isinstance(value, str) or not value:
        add_error(issues, path, f"{label} path must be a non-empty string")
        return
    candidate = Path(value)
    if candidate.is_absolute():
        add_error(issues, path, f"{label} path must be project-relative: {value}")
        return
    if ".." in candidate.parts:
        add_error(issues, path, f"{label} path must not escape the project: {value}")
        return
    if not (project_dir / candidate).exists():
        add_error(issues, path, f"{label} path does not exist: {value}")


def require_existing_any_path(
    project_dir: Path,
    value: Any,
    path: Path,
    issues: list[ManifestValidationIssue],
    label: str,
) -> None:
    if not isinstance(value, str) or not value:
        add_error(issues, path, f"{label} must be a non-empty path string")
        return
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = project_dir / candidate
    if not candidate.exists():
        add_error(issues, path, f"{label} does not exist: {value}")


def add_error(issues: list[ManifestValidationIssue], path: Path, message: str) -> None:
    issues.append(ManifestValidationIssue(severity="error", path=str(path), message=message))


def add_warning(issues: list[ManifestValidationIssue], path: Path, message: str) -> None:
    issues.append(ManifestValidationIssue(severity="warning", path=str(path), message=message))
