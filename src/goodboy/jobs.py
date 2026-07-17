"""Dependency-aware, event-sourced Goodboy generation jobs."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, Iterable

from .jsonio import append_jsonl, read_json, read_jsonl, write_json
from .locking import project_lock
from .schemas import GenerationJob, JobEvent, utc_now


JOB_STATUSES = {
    "planned",
    "blocked",
    "ready",
    "running",
    "generated",
    "processing",
    "qa_failed",
    "awaiting_approval",
    "approved",
    "complete",
    "superseded",
    "cancelled",
    "failed",  # legacy alias retained for migrations and provider failures
}

TERMINAL_JOB_STATUSES = {"complete", "superseded", "cancelled"}
DEPENDENCY_COMPLETE_STATUSES = {"complete", "approved"}

ALLOWED_TRANSITIONS = {
    "planned": {"ready", "blocked", "cancelled", "superseded"},
    "blocked": {"planned", "ready", "cancelled", "superseded"},
    "ready": {"running", "failed", "blocked", "cancelled", "superseded"},
    "running": {"generated", "failed", "blocked", "cancelled"},
    "generated": {"processing", "qa_failed", "awaiting_approval", "complete", "superseded"},
    "processing": {"qa_failed", "awaiting_approval", "complete", "failed"},
    "qa_failed": {"ready", "superseded", "cancelled"},
    "awaiting_approval": {"approved", "qa_failed", "superseded"},
    "approved": {"complete", "superseded"},
    "failed": {"ready", "blocked", "cancelled", "superseded"},
    "complete": {"superseded"},
    "superseded": set(),
    "cancelled": set(),
}


def jobs_path(project_dir: Path, run_id: str) -> Path:
    return project_dir / "runs" / run_id / "generation-jobs.json"


def events_path(project_dir: Path, run_id: str) -> Path:
    return project_dir / "runs" / run_id / "events.jsonl"


def run_manifest_path(project_dir: Path, run_id: str) -> Path:
    return project_dir / "runs" / run_id / "run.json"


def load_jobs(project_dir: Path, run_id: str) -> list[GenerationJob]:
    path = jobs_path(project_dir, run_id)
    if not path.is_file():
        return []
    raw = read_json(path)
    items = raw.get("jobs", []) if isinstance(raw, dict) else []
    return [GenerationJob(**item) for item in items]


def save_jobs(project_dir: Path, run_id: str, jobs: list[GenerationJob]) -> None:
    write_json(
        jobs_path(project_dir, run_id),
        {
            "schema_version": "0.2",
            "run_id": run_id,
            "jobs": [job.to_dict() for job in jobs],
            "updated_at": utc_now(),
        },
    )


def append_job_event(
    project_dir: Path,
    run_id: str,
    *,
    job_id: str,
    event: str,
    from_status: str | None,
    to_status: str | None,
    details: dict[str, Any] | None = None,
) -> JobEvent:
    item = JobEvent(
        id=str(uuid.uuid4()),
        run_id=run_id,
        job_id=job_id,
        event=event,
        from_status=from_status,
        to_status=to_status,
        details=details or {},
    )
    append_jsonl(events_path(project_dir, run_id), item.to_dict())
    return item


def initialize_run(
    project_dir: Path,
    *,
    run_id: str,
    jobs: list[GenerationJob],
    parent_run_id: str | None = None,
    reason: str = "new-generation",
    identity_profile_version: str | None = None,
    contract_id: str = "codex-pet-v2",
    backend_version: str = "codex-bundled-2026-07-16",
) -> list[GenerationJob]:
    run_dir = project_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if jobs_path(project_dir, run_id).is_file():
        return load_jobs(project_dir, run_id)
    now = utc_now()
    write_json(
        run_manifest_path(project_dir, run_id),
        {
            "run_id": run_id,
            "parent_run_id": parent_run_id,
            "reason": reason,
            "identity_profile_version": identity_profile_version,
            "contract_id": contract_id,
            "backend_version": backend_version,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    )
    refreshed = _refresh_readiness(jobs)
    save_jobs(project_dir, run_id, refreshed)
    for job in refreshed:
        append_job_event(
            project_dir,
            run_id,
            job_id=job.id,
            event="job-created",
            from_status=None,
            to_status=job.status,
            details={"depends_on": job.depends_on, "kind": job.kind},
        )
    return refreshed


def transition_job(
    project_dir: Path,
    run_id: str,
    job_id: str,
    to_status: str,
    *,
    event: str | None = None,
    details: dict[str, Any] | None = None,
    updates: dict[str, Any] | None = None,
    allow_same: bool = True,
) -> GenerationJob:
    if to_status not in JOB_STATUSES:
        raise ValueError(f"invalid job status `{to_status}`")
    with project_lock(project_dir):
        jobs = load_jobs(project_dir, run_id)
        job = next((item for item in jobs if item.id == job_id), None)
        if job is None:
            raise ValueError(f"unknown job `{job_id}` in run `{run_id}`")
        from_status = job.status
        if from_status == to_status and allow_same:
            return job
        allowed = ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise ValueError(f"invalid job transition `{from_status}` -> `{to_status}` for `{job_id}`")
        if to_status in {"running", "generated", "processing", "awaiting_approval", "approved", "complete"}:
            unresolved = unresolved_dependencies(jobs, job)
            if unresolved:
                raise ValueError(f"job `{job_id}` has unresolved dependencies: {', '.join(unresolved)}")
        job.status = to_status
        now = utc_now()
        if to_status == "ready":
            job.ready_at = now
            job.blocked_reason = None
        elif to_status == "running":
            job.started_at = now
            job.attempt += 1
        elif to_status == "complete":
            job.completed_at = now
        elif to_status == "blocked":
            job.blocked_reason = str((details or {}).get("reason", "blocked"))
        for key, value in (updates or {}).items():
            if not hasattr(job, key):
                raise ValueError(f"unknown GenerationJob field `{key}`")
            setattr(job, key, value)
        job.updated_at = now
        refreshed = _refresh_readiness(jobs)
        save_jobs(project_dir, run_id, refreshed)
        append_job_event(
            project_dir,
            run_id,
            job_id=job_id,
            event=event or f"job-{to_status}",
            from_status=from_status,
            to_status=to_status,
            details=details,
        )
        return next(item for item in refreshed if item.id == job_id)


def unresolved_dependencies(jobs: list[GenerationJob], job: GenerationJob) -> list[str]:
    by_id = {item.id: item for item in jobs}
    unresolved: list[str] = []
    for dependency in job.depends_on:
        candidate = by_id.get(dependency)
        if candidate is None or candidate.status not in DEPENDENCY_COMPLETE_STATUSES:
            unresolved.append(dependency)
    return unresolved


def _refresh_readiness(jobs: list[GenerationJob]) -> list[GenerationJob]:
    for job in jobs:
        if job.status not in {"planned", "blocked"}:
            continue
        if (
            job.status == "blocked"
            and job.blocked_reason
            and not job.blocked_reason.startswith("waiting for:")
        ):
            continue
        before = (job.status, job.blocked_reason, job.ready_at)
        unresolved = unresolved_dependencies(jobs, job)
        if unresolved:
            job.status = "blocked"
            job.blocked_reason = f"waiting for: {', '.join(unresolved)}"
        else:
            job.status = "ready"
            job.ready_at = job.ready_at or utc_now()
            job.blocked_reason = None
        if (job.status, job.blocked_reason, job.ready_at) != before:
            job.updated_at = utc_now()
    return jobs


def refresh_readiness(project_dir: Path, run_id: str) -> list[GenerationJob]:
    with project_lock(project_dir):
        jobs = load_jobs(project_dir, run_id)
        before_payload = [job.to_dict() for job in jobs]
        before = {job.id: job.status for job in jobs}
        jobs = _refresh_readiness(jobs)
        if [job.to_dict() for job in jobs] != before_payload:
            save_jobs(project_dir, run_id, jobs)
        for job in jobs:
            if before.get(job.id) != job.status:
                append_job_event(
                    project_dir,
                    run_id,
                    job_id=job.id,
                    event="dependency-readiness",
                    from_status=before.get(job.id),
                    to_status=job.status,
                    details={"blocked_reason": job.blocked_reason},
                )
        return jobs


def ready_jobs(project_dir: Path, run_id: str) -> list[GenerationJob]:
    return [job for job in refresh_readiness(project_dir, run_id) if job.status == "ready"]


def complete_job(
    project_dir: Path,
    run_id: str,
    job_id: str,
    *,
    selected_output_path: str,
    provider_invocation_id: str | None = None,
    qa_notes: str = "",
) -> GenerationJob:
    jobs = load_jobs(project_dir, run_id)
    current = next((job for job in jobs if job.id == job_id), None)
    if current is None:
        raise ValueError(f"unknown job `{job_id}`")
    if current.status == "ready":
        transition_job(project_dir, run_id, job_id, "running", event="output-import-started")
        transition_job(project_dir, run_id, job_id, "generated", event="output-imported")
    elif current.status == "running":
        transition_job(project_dir, run_id, job_id, "generated", event="output-imported")
    elif current.status in {"failed", "qa_failed"}:
        transition_job(project_dir, run_id, job_id, "ready", event="retry-ready")
        transition_job(project_dir, run_id, job_id, "running", event="retry-started")
        transition_job(project_dir, run_id, job_id, "generated", event="output-imported")
    current = next(job for job in load_jobs(project_dir, run_id) if job.id == job_id)
    if current.status == "generated":
        transition_job(project_dir, run_id, job_id, "processing", event="deterministic-processing")
    return transition_job(
        project_dir,
        run_id,
        job_id,
        "complete",
        event="job-complete",
        updates={
            "selected_output_path": selected_output_path,
            "provider_invocation_id": provider_invocation_id,
            "qa_notes": qa_notes,
        },
    )


def fail_job(
    project_dir: Path,
    run_id: str,
    job_id: str,
    *,
    reason: str,
    qa_failure: bool = False,
) -> GenerationJob:
    jobs = load_jobs(project_dir, run_id)
    job = next((item for item in jobs if item.id == job_id), None)
    if job is None:
        raise ValueError(f"unknown job `{job_id}`")
    target = "qa_failed" if qa_failure and job.status in {"generated", "processing", "awaiting_approval"} else "failed"
    retry_policy = dict(job.retry_policy)
    recorded_attempts = int(retry_policy.get("attempts", 0))
    attempts = max(recorded_attempts + 1, job.attempt, 1)
    retry_policy["attempts"] = attempts
    retry_policy["last_error"] = reason
    retry_policy["retry_available"] = attempts < int(retry_policy.get("max_attempts", 1))
    return transition_job(
        project_dir,
        run_id,
        job_id,
        target,
        event="job-failed",
        details={"reason": reason},
        updates={"qa_notes": reason, "retry_policy": retry_policy},
    )


def dependency_closure(jobs: list[GenerationJob], seed_ids: Iterable[str]) -> set[str]:
    affected = set(seed_ids)
    changed = True
    while changed:
        changed = False
        for job in jobs:
            if job.id in affected:
                continue
            if affected.intersection(job.depends_on):
                affected.add(job.id)
                changed = True
    return affected


def invalidate_jobs(
    project_dir: Path,
    run_id: str,
    *,
    job_ids: list[str] | None = None,
    identity_changed: bool = False,
    reason: str,
) -> list[str]:
    with project_lock(project_dir):
        jobs = load_jobs(project_dir, run_id)
        seeds = {
            job.id
            for job in jobs
            if identity_changed or job.id in set(job_ids or [])
        }
        affected = dependency_closure(jobs, seeds)
        for job in jobs:
            if job.id not in affected or job.status in {"cancelled", "superseded"}:
                continue
            before = job.status
            job.status = "planned"
            job.selected_output_path = None
            job.completed_at = None
            job.blocked_reason = None
            job.qa_notes = f"Invalidated: {reason}"
            job.updated_at = utc_now()
            append_job_event(
                project_dir,
                run_id,
                job_id=job.id,
                event="job-invalidated",
                from_status=before,
                to_status="planned",
                details={"reason": reason},
            )
        jobs = _refresh_readiness(jobs)
        save_jobs(project_dir, run_id, jobs)
        return sorted(affected)


def recover_run(project_dir: Path, run_id: str) -> dict[str, Any]:
    recovered: list[str] = []
    blocked: list[str] = []
    with project_lock(project_dir):
        jobs = load_jobs(project_dir, run_id)
        for job in jobs:
            if job.status == "running":
                job.status = "blocked"
                job.blocked_reason = "provider outcome unknown after interruption; attach the existing output or retry explicitly"
                job.updated_at = utc_now()
                blocked.append(job.id)
                append_job_event(
                    project_dir,
                    run_id,
                    job_id=job.id,
                    event="recovery-provider-unknown",
                    from_status="running",
                    to_status="blocked",
                    details={"reason": job.blocked_reason},
                )
            elif job.status == "processing":
                job.status = "generated"
                job.updated_at = utc_now()
                recovered.append(job.id)
                append_job_event(
                    project_dir,
                    run_id,
                    job_id=job.id,
                    event="recovery-processing-reset",
                    from_status="processing",
                    to_status="generated",
                    details={"reason": "deterministic processing is safe to rerun"},
                )
        jobs = _refresh_readiness(jobs)
        save_jobs(project_dir, run_id, jobs)
    return {
        "run_id": run_id,
        "recovered_jobs": recovered,
        "blocked_unknown_provider_jobs": blocked,
        "events": len(read_jsonl(events_path(project_dir, run_id))),
    }


def job_graph(project_dir: Path, run_id: str) -> dict[str, Any]:
    jobs = refresh_readiness(project_dir, run_id)
    return {
        "run_id": run_id,
        "jobs": [job.to_dict() for job in jobs],
        "ready": [job.id for job in jobs if job.status == "ready"],
        "blocked": [
            {"job_id": job.id, "reason": job.blocked_reason}
            for job in jobs
            if job.status == "blocked"
        ],
        "complete": [job.id for job in jobs if job.status == "complete"],
        "event_count": len(read_jsonl(events_path(project_dir, run_id))),
    }


def create_repair_attempt(
    project_dir: Path,
    run_id: str,
    *,
    job_ids: list[str],
    reason: str,
    author: str = "human",
    identity_changed: bool = False,
) -> dict[str, Any]:
    """Archive affected outputs, invalidate their dependency closure, and retry."""

    if not reason.strip():
        raise ValueError("repair reason is required")
    jobs = load_jobs(project_dir, run_id)
    known = {job.id for job in jobs}
    unknown = sorted(set(job_ids) - known)
    if unknown:
        raise ValueError(f"unknown repair jobs: {', '.join(unknown)}")
    seeds = known if identity_changed else set(job_ids)
    affected = dependency_closure(jobs, seeds)
    stamp = utc_now().replace(":", "").replace("+", "_")
    run_dir = project_dir / "runs" / run_id
    archive_dir = run_dir / "superseded" / stamp
    archived: list[dict[str, str]] = []
    archived_handoffs: list[dict[str, str]] = []
    for job in jobs:
        if job.id not in affected:
            continue
        source = project_dir / job.expected_output
        if not source.is_file():
            continue
        target = archive_dir / job.id / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        archived.append(
            {
                "job_id": job.id,
                "source": str(source.relative_to(project_dir)),
                "archive": str(target.relative_to(project_dir)),
            }
        )
    for job_id in sorted(affected):
        source = run_dir / "provider-invocations" / f"handoff-{job_id}.json"
        if not source.is_file():
            continue
        target = archive_dir / "provider-invocations" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        archived_handoffs.append(
            {
                "job_id": job_id,
                "source": str(source.relative_to(project_dir)),
                "archive": str(target.relative_to(project_dir)),
            }
        )
    invalidated = invalidate_jobs(
        project_dir,
        run_id,
        job_ids=job_ids,
        identity_changed=identity_changed,
        reason=reason,
    )
    authoritative_identity = ""
    identity_version: str | None = None
    if identity_changed:
        from .identity import (
            copy_identity_artifacts_for_run,
            create_identity_pack,
            identity_prompt_block,
            load_identity_profile,
        )

        identity = load_identity_profile(project_dir, required=True)
        assert identity is not None
        identity_version = identity.version
        authoritative_identity = identity_prompt_block(project_dir)
        create_identity_pack(project_dir, run_id=run_id)
        copy_identity_artifacts_for_run(project_dir, run_id)
        for manifest_path in (
            run_manifest_path(project_dir, run_id),
            run_dir / "run-metadata.json",
        ):
            if manifest_path.is_file():
                manifest = read_json(manifest_path)
                manifest["identity_profile_version"] = identity.version
                manifest["updated_at"] = utc_now()
                write_json(manifest_path, manifest)
    repair_prompts: dict[str, str] = {}
    refreshed_jobs = load_jobs(project_dir, run_id)
    by_id = {job.id: job for job in refreshed_jobs}
    prompt_job_ids = sorted(affected if identity_changed else set(job_ids))
    for job_id in prompt_job_ids:
        job = by_id[job_id]
        if identity_version is not None:
            job.identity_profile_version = identity_version
        original_prompt = project_dir / job.prompt_path
        if not original_prompt.is_file():
            continue
        repair_prompt = run_dir / "prompts" / "repairs" / f"{job.id}-{stamp}.md"
        repair_prompt.parent.mkdir(parents=True, exist_ok=True)
        repair_prompt.write_text(
            original_prompt.read_text(encoding="utf-8").rstrip()
            + "\n\n---\n\n"
            + "REPAIR ATTEMPT — the previous provider output failed visual QA.\n\n"
            + f"Failure evidence: {reason.strip()}\n\n"
            + (
                "UPDATED IDENTITY CONTRACT — authoritative and supersedes any earlier identity "
                "wording in this prompt:\n\n"
                + authoritative_identity
                + "\n\n"
                if authoritative_identity
                else ""
            )
            + "Correct this specific failure while preserving every requirement and every aspect that already passed. "
            + "Return a complete replacement artifact; do not annotate, explain, or reproduce this repair note in the image.\n",
            encoding="utf-8",
        )
        job.prompt_path = str(repair_prompt.relative_to(project_dir))
        retry_policy = dict(job.retry_policy)
        retry_policy["repair_attempts"] = int(retry_policy.get("repair_attempts", 0)) + 1
        retry_policy["last_repair_reason"] = reason.strip()
        job.retry_policy = retry_policy
        job.qa_notes = f"Repair requested: {reason.strip()}"
        job.updated_at = utc_now()
        repair_prompts[job_id] = job.prompt_path
        append_job_event(
            project_dir,
            run_id,
            job_id=job_id,
            event="repair-prompt-created",
            from_status=job.status,
            to_status=job.status,
            details={"reason": reason.strip(), "prompt_path": job.prompt_path},
        )
    if identity_version is not None:
        for job in refreshed_jobs:
            if job.id in affected:
                job.identity_profile_version = identity_version
    save_jobs(project_dir, run_id, refreshed_jobs)
    derived_paths = [
        run_dir / "run-summary.json",
        run_dir / "handoff-summary.json",
        run_dir / "package",
        run_dir / "final" / "spritesheet-v2.png",
        run_dir / "final" / "spritesheet-v2.webp",
        run_dir / "final" / "spritesheet-v2.json",
        run_dir / "final" / "validation-v2.json",
        run_dir / "qa" / "review-summary.json",
        run_dir / "qa" / "likeness-report.json",
        run_dir / "qa" / "likeness-receipt.json",
    ]
    if any(job_id.startswith("row-") for job_id in affected):
        derived_paths.extend(
            [
                run_dir / "final" / "spritesheet-standard.png",
                run_dir / "final" / "spritesheet-standard.webp",
            ]
        )
    archived_derived: list[str] = []
    for source in derived_paths:
        if not source.exists():
            continue
        target = archive_dir / "derived" / source.relative_to(run_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        archived_derived.append(str(target.relative_to(project_dir)))
    receipt = {
        "run_id": run_id,
        "reason": reason,
        "author": author,
        "identity_changed": identity_changed,
        "seed_jobs": sorted(job_ids),
        "invalidated_jobs": invalidated,
        "archived_outputs": archived,
        "archived_handoffs": archived_handoffs,
        "repair_prompts": repair_prompts,
        "archived_derived": archived_derived,
        "created_at": utc_now(),
    }
    write_json(archive_dir / "repair.json", receipt)
    write_json(run_dir / "latest-repair.json", receipt)
    refresh_readiness(project_dir, run_id)
    return receipt
