"""Strict manifest validation for Goodboy projects."""

from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from typing import Any

from .adapters import CAPABILITY_REGISTRY
from .contracts import ROW_FRAME_COUNTS, STATE_ORDER
from .ingest import SOURCE_CARD, SOURCE_MANIFEST
from .jsonio import read_json, write_json
from .schemas import (
    BranchManifest,
    CharacterCard,
    CritiqueReport,
    EmotionStyleSheet,
    FeedbackEvent,
    GenerationJob,
    ManifestValidationIssue,
    ManifestValidationReport,
    PetProject,
    ProviderInvocation,
    RunSummary,
    SourceCard,
    SourceImage,
    StyleCandidate,
)
from .style import STYLE_PATH


def validate_project(project_dir: Path, *, write_report: bool = True) -> ManifestValidationReport:
    issues: list[ManifestValidationIssue] = []
    checked_files: list[str] = []
    validate_json_dataclass(project_dir, Path("goodboy.json"), PetProject, issues, checked_files)
    validate_source_images(project_dir, issues, checked_files)
    validate_source_card(project_dir, issues, checked_files)
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
    selected = 0
    for index, item in enumerate(candidates):
        item_path = Path(f"candidates/baseline-candidates.json:candidates[{index}]")
        validate_candidate_object(project_dir, item, item_path, issues)
        if isinstance(item, dict) and item.get("selected"):
            selected += 1
    if selected > 1:
        add_error(issues, rel, "only one baseline candidate may be selected")
    for candidate_file in sorted((project_dir / "candidates").glob("baseline-*/candidate.json")):
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
    for source_path in candidate.source_images:
        require_relative_existing(project_dir, source_path, path, issues, "candidate source image")
    if candidate.provider not in CAPABILITY_REGISTRY:
        add_error(issues, path, f"unknown provider `{candidate.provider}`")


def validate_character(project_dir: Path, issues: list[ManifestValidationIssue], checked_files: list[str]) -> None:
    if not (project_dir / "character" / "character-card.json").exists():
        return
    raw = validate_json_dataclass(project_dir, Path("character/character-card.json"), CharacterCard, issues, checked_files)
    if raw and raw.get("selected_baseline_image"):
        require_relative_existing(project_dir, raw["selected_baseline_image"], Path("character/character-card.json"), issues, "selected baseline image")


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
        validate_provider_invocations(project_dir, run_dir, issues, checked_files)
        validate_run_summary(project_dir, run_dir, issues, checked_files)


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
        if job.status not in {"planned", "prepared", "running", "complete", "failed", "skipped"}:
            add_error(issues, item_path, f"invalid job status `{job.status}`")
        require_relative_existing(project_dir, job.prompt_path, item_path, issues, "job prompt")
        for input_image in job.input_images:
            require_relative_existing(project_dir, input_image, item_path, issues, "job input image")
        if job.state and job.state not in STATE_ORDER:
            add_error(issues, item_path, f"unknown state `{job.state}`")
        for dep in job.depends_on:
            if dep not in seen and not any(isinstance(other, dict) and other.get("id") == dep for other in jobs):
                add_error(issues, item_path, f"unknown dependency `{dep}`")


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
