"""High-level Goodboy build, review-package, and install pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .atlas import compose_atlas, make_contact_sheet, render_animation_previews, validate_atlas
from .contracts import STATE_ORDER, V1_OUTPUT_CONTRACT, V2_OUTPUT_CONTRACT, contract_from_dict
from .identity import (
    create_identity_pack,
    create_likeness_report,
    create_likeness_review_media,
    likeness_is_approved,
    load_identity_profile,
    write_likeness_receipt,
)
from .jsonio import read_json, write_json
from .migrations import rgba_sha256
from .project import init_project, load_project, save_project
from .qa import (
    animation_is_approved,
    audit_frames,
    evaluate_qa_policy,
    make_centering_overlay,
    make_white_edge_preview,
    write_animation_correctness_report,
    write_qa_report,
)
from .raster import build_frames_from_row_strips
from .safety import find_suspicious_renderer_scripts
from .schemas import RunSummary, utc_now
from .v2_backend import (
    backend_metadata,
    build_standard_rows,
    build_v2_backend,
    extract_and_compose_cardinals,
    normalize_run_json_paths,
    v2_review_gate,
    validate_v2_package,
    write_backend_snapshot,
)


V2_GENERATED_INPUTS = [
    *[f"{state}.png" for state in STATE_ORDER],
    "look-cardinals.png",
    "look-row-9.png",
    "look-row-10.png",
]


def parse_chroma_key(raw: dict[str, object] | None) -> tuple[int, int, int] | None:
    if not raw:
        return None
    rgb = raw.get("rgb")
    if isinstance(rgb, list) and len(rgb) == 3:
        return tuple(int(value) for value in rgb)
    hex_value = raw.get("hex")
    if isinstance(hex_value, str) and len(hex_value) == 7 and hex_value.startswith("#"):
        return tuple(int(hex_value[index : index + 2], 16) for index in (1, 3, 5))
    return None


def run_chroma_key_metadata(run_dir: Path) -> dict[str, object] | None:
    metadata_path = run_dir / "run-metadata.json"
    if not metadata_path.is_file():
        return None
    raw = read_json(metadata_path)
    chroma_key = raw.get("chroma_key")
    return chroma_key if isinstance(chroma_key, dict) else None


def copy_row_inputs(rows_dir: Path, target_dir: Path, filenames: list[str]) -> None:
    """Copy immutable provider outputs into the run without rewriting them."""

    rows_dir = rows_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source = rows_dir / filename
        if not source.is_file():
            raise FileNotFoundError(f"missing generated row input: {source}")
        target = target_dir / filename
        if source != target.resolve():
            shutil.copy2(source, target)


def _write_standard_goodboy_qa(run_dir: Path, final_atlas: Path) -> tuple[Any, Any]:
    frames_root = run_dir / "frames"
    qa_dir = run_dir / "qa"
    validation = validate_atlas(final_atlas)
    qa_report = audit_frames(frames_root)
    write_json(run_dir / "final" / "validation.json", validation.to_dict())
    make_contact_sheet(final_atlas, qa_dir / "contact-sheet.png")
    make_white_edge_preview(frames_root, qa_dir / "edge-preview-white.png")
    make_centering_overlay(frames_root, qa_dir / "centering-overlay.png")
    centering_report_path = frames_root / "centering-report.json"
    if centering_report_path.is_file():
        write_json(qa_dir / "centering-report.json", read_json(centering_report_path))
    else:
        from .raster import ANCHOR_POLICIES

        write_json(
            qa_dir / "centering-report.json",
            {
                "schema_version": "0.2",
                "advisory_only": True,
                "source": "post-extraction frame geometry",
                "states": {
                    state: {
                        "anchor_policy": ANCHOR_POLICIES[state],
                        "cx_range": details.get("cx_range", 0),
                        "cy_range": details.get("cy_range", 0),
                        "frames": [
                            {
                                "frame": frame.get("frame"),
                                "bbox": frame.get("bbox"),
                                "cx": frame.get("cx"),
                                "cy": frame.get("cy"),
                                "shift_y": 0,
                            }
                            for frame in details.get("frames", [])
                        ],
                    }
                    for state, details in qa_report.states.items()
                },
            },
        )
    write_qa_report(qa_dir / "duplicate-audit.json", qa_report)
    return validation, qa_report


def _write_package(
    *,
    package_dir: Path,
    atlas_path: Path,
    pet_id: str,
    display_name: str,
    sprite_version_number: int,
) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(atlas_path, package_dir / "spritesheet.webp")
    write_json(
        package_dir / "pet.json",
        {
            "id": pet_id,
            "displayName": display_name,
            "description": f"{display_name} Codex pet generated by Goodboy.",
            "spritesheetPath": "spritesheet.webp",
            "spriteVersionNumber": sprite_version_number,
        },
    )


def _legacy_v1_build(
    *,
    run_dir: Path,
    rows_dir: Path,
    extraction_method: str,
    force: bool,
) -> tuple[Path, Any, Any, dict[str, Any]]:
    transparent_dir = run_dir / "transparent-strips"
    frames_root = run_dir / "frames"
    final_dir = run_dir / "final"
    qa_dir = run_dir / "qa"
    chroma_metadata = run_chroma_key_metadata(run_dir)
    build_frames_from_row_strips(
        source_dir=rows_dir,
        transparent_dir=transparent_dir,
        frames_root=frames_root,
        chroma_key=parse_chroma_key(chroma_metadata),
        chroma_key_metadata=chroma_metadata,
        extraction_method=extraction_method,
        force=force,
    )
    final_atlas = final_dir / "spritesheet.webp"
    compose_atlas(
        frames_root,
        output_png=final_dir / "spritesheet.png",
        output_webp=final_atlas,
    )
    render_animation_previews(frames_root, qa_dir / "previews")
    validation, qa_report = _write_standard_goodboy_qa(run_dir, final_atlas)
    return final_atlas, validation, qa_report, {
        "contract_id": V1_OUTPUT_CONTRACT.contract_id,
        "sprite_version_number": 1,
        "compatibility_mode": "legacy-v1",
    }


def _v2_build(
    *,
    project_dir: Path,
    run_dir: Path,
    rows_dir: Path,
    extraction_method: str,
) -> tuple[Path, Any, Any, dict[str, Any]]:
    canonical_rows = run_dir / "row-strips"
    metadata_path = run_dir / "run-metadata.json"
    metadata = read_json(metadata_path) if metadata_path.is_file() else {}
    migration = metadata.get("migration") if isinstance(metadata.get("migration"), dict) else None
    copy_row_inputs(
        rows_dir,
        canonical_rows,
        ["look-cardinals.png", "look-row-9.png", "look-row-10.png"]
        if migration
        else V2_GENERATED_INPUTS,
    )
    write_backend_snapshot(run_dir / "backend-snapshot.json")
    if migration:
        standard_path = project_dir / str(migration["source_standard_atlas"])
        if not standard_path.is_file():
            raise FileNotFoundError(f"missing preserved v1 standard atlas: {standard_path}")
        standard = {
            "standard_png": str(standard_path),
            "migration": migration,
        }
    else:
        standard = build_standard_rows(run_dir, extraction_method=extraction_method)
    extract_and_compose_cardinals(run_dir)
    identity = load_identity_profile(project_dir)
    if identity is not None:
        create_identity_pack(project_dir, run_id=run_dir.name)
    neutral_cell = run_dir / "frames" / "idle" / "00.png"
    receipt = build_v2_backend(
        run_dir,
        standard_atlas=Path(standard["standard_png"]),
        neutral_cell=neutral_cell,
    )
    final_atlas = run_dir / "final" / "spritesheet-v2.webp"
    validation, qa_report = _write_standard_goodboy_qa(run_dir, final_atlas)
    write_animation_correctness_report(run_dir)
    if identity is not None:
        create_likeness_review_media(project_dir, run_id=run_dir.name)
        likeness_path = run_dir / "qa" / "likeness-report.json"
        if not likeness_path.is_file():
            create_likeness_report(project_dir, run_id=run_dir.name)
    migration_preservation: dict[str, Any] | None = None
    if migration:
        from PIL import Image

        with Image.open(Path(standard["standard_png"])) as opened:
            before_hash = rgba_sha256(opened.convert("RGBA"))
        with Image.open(final_atlas) as opened:
            after_standard = opened.convert("RGBA").crop(
                (0, 0, V1_OUTPUT_CONTRACT.atlas_width, V1_OUTPUT_CONTRACT.atlas_height)
            )
            after_hash = rgba_sha256(after_standard)
        migration_preservation = {
            "before_standard_rgba_sha256": before_hash,
            "after_standard_rgba_sha256": after_hash,
            "pixel_identical_after_final_despill": before_hash == after_hash,
            "note": (
                "The final one-pass chroma despill may clean edge pixels while preserving all v1 poses and layout."
                if before_hash != after_hash
                else "Rows 0-8 remained pixel-identical."
            ),
        }
        write_json(run_dir / "qa" / "migration-preservation.json", migration_preservation)
    return final_atlas, validation, qa_report, {
        "contract_id": V2_OUTPUT_CONTRACT.contract_id,
        "sprite_version_number": 2,
        "backend": backend_metadata(),
        "backend_receipt": receipt,
        "direction_gate": v2_review_gate(run_dir),
        "migration_preservation": migration_preservation,
    }


def build_from_row_strips(
    *,
    project_dir: Path,
    rows_dir: Path,
    run_id: str,
    pet_id: str | None = None,
    display_name: str | None = None,
    install: bool = False,
    install_root: Path | None = None,
    install_override_reason: str | None = None,
    row_provenance: str | None = None,
    visual_approval: str | None = None,
    extraction_method: str = "auto",
    force: bool = True,
) -> RunSummary:
    """Build the project's declared output contract from provider row strips.

    New workspaces always build v2. A migrated v1 workspace can still be
    inspected or rebuilt until ``goodboy upgrade`` explicitly targets v2.
    """

    project_dir = project_dir.resolve()
    rows_dir = rows_dir.resolve()
    if not (project_dir / "goodboy.json").exists():
        if pet_id is None or display_name is None:
            raise ValueError("pet_id and display_name are required when initializing a new project")
        project = init_project(project_dir, pet_id=pet_id, display_name=display_name)
    else:
        project = load_project(project_dir)
        if pet_id is not None:
            project.id = pet_id
        if display_name is not None:
            project.display_name = display_name

    run_dir = project_dir / "runs" / run_id
    qa_dir = run_dir / "qa"
    package_dir = run_dir / "package"
    contract = contract_from_dict(project.output_contract)
    if contract.contract_id == V2_OUTPUT_CONTRACT.contract_id:
        final_atlas, validation, qa_report, build_receipt = _v2_build(
            project_dir=project_dir,
            run_dir=run_dir,
            rows_dir=rows_dir,
            extraction_method=extraction_method,
        )
    else:
        final_atlas, validation, qa_report, build_receipt = _legacy_v1_build(
            run_dir=run_dir,
            rows_dir=rows_dir,
            extraction_method=extraction_method,
            force=force,
        )

    qa_policy = evaluate_qa_policy(
        validation,
        qa_report,
        override_reason=install_override_reason,
        install_requested=install,
        row_provenance=row_provenance,
        visual_approval=visual_approval,
    )
    write_json(qa_dir / "install-policy.json", qa_policy.to_dict())
    write_json(
        qa_dir / "review.json",
        {
            "ok": validation.ok and qa_report.ok,
            "errors": validation.errors + qa_report.errors,
            "warnings": validation.warnings + qa_report.warnings,
            "install_policy": qa_policy.to_dict(),
            "build": build_receipt,
        },
    )
    write_json(qa_dir / "human-review-checklist.json", human_review_checklist(run_id, v2=contract.sprite_version_number == 2))
    _write_package(
        package_dir=package_dir,
        atlas_path=final_atlas,
        pet_id=project.id,
        display_name=project.display_name,
        sprite_version_number=contract.sprite_version_number,
    )
    package_validation = (
        validate_v2_package(package_dir)
        if contract.sprite_version_number == 2
        else {"ok": True, "errors": []}
    )
    write_json(package_dir / "validation.json", package_validation)
    if not package_validation["ok"]:
        raise ValueError(f"invalid package: {'; '.join(package_validation['errors'])}")

    likeness_path = run_dir / "qa" / "likeness-receipt.json"
    summary = RunSummary(
        ok=validation.ok and qa_report.ok and package_validation["ok"],
        version=run_id,
        source_rows=str((run_dir / "row-strips").relative_to(project_dir)),
        spritesheet=str(final_atlas.relative_to(project_dir)),
        contact_sheet=str((qa_dir / "contact-sheet.png").relative_to(project_dir)),
        edge_preview=str((qa_dir / "edge-preview-white.png").relative_to(project_dir)),
        validation=str((run_dir / "final" / "validation.json").relative_to(project_dir)),
        review=str((qa_dir / "review.json").relative_to(project_dir)),
        duplicate_audit=str((qa_dir / "duplicate-audit.json").relative_to(project_dir)),
        package_dir=str(package_dir.relative_to(project_dir)),
        contract_id=contract.contract_id,
        sprite_version_number=contract.sprite_version_number,
        backend_version=project.backend_version,
        likeness_receipt=(
            str(likeness_path.relative_to(project_dir)) if likeness_path.is_file() else None
        ),
    )
    write_json(run_dir / "run-summary.json", summary.to_dict())

    project.active_run_id = run_id
    if (
        contract.sprite_version_number == 2
        and project.migration_state == "awaiting-v2-look-rows"
    ):
        project.migration_state = "current"
        migration_receipt_path = project_dir / "migration-receipt.json"
        if migration_receipt_path.is_file():
            migration_receipt = read_json(migration_receipt_path)
            migration_receipt["completed_run_id"] = run_id
            migration_receipt["completed_at"] = utc_now()
            migration_receipt["requires_generation"] = False
            write_json(migration_receipt_path, migration_receipt)
    save_project(project_dir, project)

    if install:
        _assert_installable(
            project_dir=project_dir,
            run_dir=run_dir,
            qa_policy=qa_policy.to_dict(),
            sprite_version_number=contract.sprite_version_number,
            allow_test_fixture=row_provenance == "test_fixture",
            override_reason=install_override_reason,
        )
        install_package(package_dir=package_dir, pet_id=project.id, install_root=install_root)
    normalize_run_json_paths(run_dir)
    return summary


def _assert_installable(
    *,
    project_dir: Path,
    run_dir: Path,
    qa_policy: dict[str, Any],
    sprite_version_number: int,
    allow_test_fixture: bool,
    override_reason: str | None,
) -> None:
    failures = list(qa_policy.get("hard_failures", []))
    if failures and not override_reason:
        raise ValueError(f"QA policy blocks install: {'; '.join(str(item) for item in failures)}")
    if sprite_version_number == 2:
        direction_gate = v2_review_gate(run_dir, allow_test_fixture=allow_test_fixture)
        if not direction_gate["ok"]:
            raise ValueError(f"v2 direction review blocks install: {'; '.join(direction_gate['hard_failures'])}")
        if not allow_test_fixture and not animation_is_approved(project_dir, run_dir.name):
            raise ValueError("approved state-by-state animation correctness review is required before install")
        if load_identity_profile(project_dir) is not None and not likeness_is_approved(project_dir, run_dir.name):
            raise ValueError("approved source-likeness review is required before install")
        if load_identity_profile(project_dir) is not None:
            write_likeness_receipt(project_dir, run_id=run_dir.name)
    suspicious = find_suspicious_renderer_scripts(project_dir)
    if suspicious:
        raise ValueError(f"suspicious renderer scripts block install: {', '.join(suspicious)}")


def assert_run_installable(
    *,
    project_dir: Path,
    run_id: str,
    row_provenance: str,
    override_reason: str | None = None,
) -> None:
    """Recompute install gates from source artifacts instead of trusting stale state."""

    run_dir = project_dir / "runs" / run_id
    project = load_project(project_dir)
    policy_path = run_dir / "qa" / "install-policy.json"
    policy = read_json(policy_path) if policy_path.is_file() else {"hard_failures": ["missing install policy"]}
    _assert_installable(
        project_dir=project_dir,
        run_dir=run_dir,
        qa_policy=policy,
        sprite_version_number=contract_from_dict(project.output_contract).sprite_version_number,
        allow_test_fixture=row_provenance == "test_fixture",
        override_reason=override_reason,
    )


def human_review_checklist(run_id: str, *, v2: bool = True) -> dict[str, object]:
    required = [
        "Open qa/contact-sheet.png and confirm every animation state is recognizable.",
        "Open qa/previews/*.gif and confirm loops do not drift, clip, or duplicate unnaturally.",
        "Complete qa/animation-review.json with state semantics, motion continuity, and cross-state identity evidence for every standard row.",
        "Open qa/edge-preview-white.png and confirm there is no visible chroma-key halo or colored residue.",
        "Open qa/centering-overlay.png and confirm frame centers are stable enough for idle/waiting/review.",
        "Read qa/review.json and qa/install-policy.json; approve only if hard failures are absent or intentionally overridden.",
        "Confirm the approved identity traits remain recognizable at the final small display size.",
    ]
    if v2:
        required.extend(
            [
                "Open qa/look-directions.png and confirm all 16 clockwise directions are semantically correct.",
                "Complete the independent blind direction review and verify qa/direction-blind-validation.json passes.",
                "Complete qa/likeness-report.json for every locked signature and important identity trait.",
            ]
        )
    return {
        "run_id": run_id,
        "required_before_approval": required,
        "approval_command": (
            "goodboy approve <project-dir> --notes "
            '"User approved animation, direction, identity, and likeness review"'
        ),
    }


def install_package(*, package_dir: Path, pet_id: str, install_root: Path | None = None) -> Path:
    install_root = install_root or Path.home() / ".codex" / "pets"
    target = install_root / pet_id
    archive_existing_install(target)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package_dir / "pet.json", target / "pet.json")
    shutil.copy2(package_dir / "spritesheet.webp", target / "spritesheet.webp")
    return target


def archive_existing_install(target: Path) -> None:
    if not target.exists():
        return
    archive_root = target.parent / ".goodboy-archives" / target.name
    archive_root.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        archive_dir = archive_root / f"archive-{index:03d}"
        if not archive_dir.exists():
            break
        index += 1
    archive_dir.mkdir(parents=True)
    for filename in ("pet.json", "spritesheet.webp"):
        source = target / filename
        if source.exists():
            shutil.copy2(source, archive_dir / filename)
