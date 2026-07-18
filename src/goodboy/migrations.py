"""Versioned Goodboy project migrations."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from PIL import Image

from .contracts import V1_OUTPUT_CONTRACT, V2_OUTPUT_CONTRACT, contract_from_dict, get_output_contract
from .jsonio import read_json, write_json
from .schemas import GenerationJob, PetProject, utc_now


CURRENT_WORKSPACE_VERSION = "0.2.1"
CURRENT_WORKSPACE_SCHEMA_VERSION = "0.2"


def migrate_project_manifest(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return a current in-memory manifest without mutating the project."""

    migrated = dict(raw)
    changes: list[str] = []
    is_legacy_schema = migrated.get("workspace_schema_version") != CURRENT_WORKSPACE_SCHEMA_VERSION
    if is_legacy_schema:
        known_fields = {field.name for field in fields(PetProject)}
        unknown_fields = sorted(set(migrated) - known_fields)
        if unknown_fields:
            legacy_compat = (
                dict(migrated.get("legacy_compat", {}))
                if isinstance(migrated.get("legacy_compat"), dict)
                else {}
            )
            for key in unknown_fields:
                legacy_compat[key] = migrated.pop(key)
            migrated["legacy_compat"] = legacy_compat
            changes.append(
                "preserved unknown legacy fields in legacy_compat: "
                + ", ".join(unknown_fields)
            )
    embedded_contract = (
        migrated.get("output_contract")
        if isinstance(migrated.get("output_contract"), dict)
        else None
    )
    if embedded_contract is not None:
        contract = contract_from_dict(embedded_contract)
    elif isinstance(migrated.get("contract_id"), str):
        contract = get_output_contract(str(migrated["contract_id"]))
    else:
        contract = V1_OUTPUT_CONTRACT
    if migrated.get("workspace_schema_version") != CURRENT_WORKSPACE_SCHEMA_VERSION:
        migrated["workspace_schema_version"] = CURRENT_WORKSPACE_SCHEMA_VERSION
        changes.append(f"updated workspace_schema_version to {CURRENT_WORKSPACE_SCHEMA_VERSION}")
    if migrated.get("goodboy_version") != CURRENT_WORKSPACE_VERSION:
        migrated["goodboy_version"] = CURRENT_WORKSPACE_VERSION
        changes.append(f"updated goodboy_version to {CURRENT_WORKSPACE_VERSION}")
    if "contract_id" not in migrated:
        migrated["contract_id"] = contract.contract_id
        changes.append(f"detected {contract.contract_id}")
    if "contract_version" not in migrated:
        migrated["contract_version"] = contract.contract_version
        changes.append("added contract_version")
    if embedded_contract is None:
        migrated["output_contract"] = asdict(contract)
        changes.append(f"added {contract.contract_id} output_contract")
    if "backend_name" not in migrated:
        migrated["backend_name"] = "goodboy-v1" if contract == V1_OUTPUT_CONTRACT else "hatch-compatible"
        changes.append("added backend_name")
    if "backend_version" not in migrated:
        migrated["backend_version"] = "legacy" if contract == V1_OUTPUT_CONTRACT else "codex-bundled-2026-07-16"
        changes.append("added backend_version")
    if "privacy_policy" not in migrated:
        migrated["privacy_policy"] = {
            "sources_local_by_default": True,
            "strip_exif_for_provider": True,
            "include_sources_in_exports": False,
            "provider_consent_required": True,
        }
        changes.append("added privacy_policy")
    if "migration_state" not in migrated:
        migrated["migration_state"] = "legacy-v1" if contract == V1_OUTPUT_CONTRACT else "current"
        changes.append("added migration_state")
    if migrated.get("workspace_version") != CURRENT_WORKSPACE_VERSION:
        migrated["workspace_version"] = CURRENT_WORKSPACE_VERSION
        changes.append(f"updated workspace_version to {CURRENT_WORKSPACE_VERSION}")
    return migrated, changes


def upgrade_project_manifest(
    project_dir: Path,
    *,
    target_contract_id: str = V2_OUTPUT_CONTRACT.contract_id,
    provider: str = "codex_builtin",
    model_alias: str = "codex-imagegen",
    run_id: str | None = None,
) -> dict[str, Any]:
    manifest_path = project_dir / "goodboy.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing Goodboy project manifest: {manifest_path}")
    before = read_json(manifest_path)
    migrated, changes = migrate_project_manifest(before)
    previous_contract = contract_from_dict(
        before.get("output_contract") if isinstance(before.get("output_contract"), dict) else None
    )
    target = get_output_contract(target_contract_id)
    if (
        previous_contract.contract_id == target.contract_id
        and before.get("migration_state") in {"current", "awaiting-v2-look-rows"}
    ):
        existing_receipt = project_dir / "migration-receipt.json"
        if existing_receipt.is_file():
            receipt = read_json(existing_receipt)
            return {**receipt, "already_current": True}
        return {
            "migrated_at": utc_now(),
            "source_contract_id": previous_contract.contract_id,
            "target_contract_id": target.contract_id,
            "changes": [],
            "data_deleted": False,
            "requires_generation": before.get("migration_state") == "awaiting-v2-look-rows",
            "already_current": True,
        }
    timestamp = utc_now()
    archive_name = timestamp.replace(":", "").replace("+", "_")
    archive_dir = project_dir / "archives" / "migrations" / archive_name
    archive_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(manifest_path, archive_dir / "goodboy.json")

    migrated["contract_id"] = target.contract_id
    migrated["contract_version"] = target.contract_version
    migrated["output_contract"] = asdict(target)
    migrated["backend_name"] = "hatch-compatible"
    migrated["backend_version"] = "codex-bundled-2026-07-16"
    migrated["migration_state"] = (
        "awaiting-v2-look-rows"
        if previous_contract.contract_id == V1_OUTPUT_CONTRACT.contract_id
        and target.contract_id == V2_OUTPUT_CONTRACT.contract_id
        else "current"
    )
    migrated["updated_at"] = timestamp
    changes.append(f"targeted {target.contract_id}")
    migration_run: dict[str, Any] | None = None
    if (
        previous_contract.contract_id == V1_OUTPUT_CONTRACT.contract_id
        and target.contract_id == V2_OUTPUT_CONTRACT.contract_id
    ):
        source_atlas = find_latest_v1_atlas(project_dir, preferred_run_id=before.get("active_run_id"))
        if source_atlas is not None:
            migration_run = prepare_v1_upgrade_run(
                project_dir,
                source_atlas=source_atlas,
                provider=provider,
                model_alias=model_alias,
                run_id=run_id,
            )
            migrated["active_run_id"] = migration_run["run_id"]
    write_json(manifest_path, migrated)
    receipt = {
        "migrated_at": timestamp,
        "source_contract_id": previous_contract.contract_id,
        "target_contract_id": target.contract_id,
        "source_manifest": str((archive_dir / "goodboy.json").relative_to(project_dir)),
        "changes": changes,
        "data_deleted": False,
        "requires_generation": migrated["migration_state"] == "awaiting-v2-look-rows",
        "migration_run": migration_run,
        "missing_generation_jobs": (
            ["look-cardinals", "look-row-9", "look-row-10"]
            if migrated["migration_state"] == "awaiting-v2-look-rows"
            else []
        ),
        "preserved_v1_atlas_found": migration_run is not None,
    }
    write_json(archive_dir / "migration-receipt.json", receipt)
    write_json(project_dir / "migration-receipt.json", receipt)
    return receipt


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rgba_sha256(image: Image.Image) -> str:
    digest = hashlib.sha256()
    digest.update(f"{image.width}x{image.height}:RGBA".encode("ascii"))
    digest.update(image.convert("RGBA").tobytes())
    return digest.hexdigest()


def find_latest_v1_atlas(project_dir: Path, *, preferred_run_id: str | None = None) -> Path | None:
    runs_dir = project_dir / "runs"
    run_dirs: list[Path] = []
    if preferred_run_id and (runs_dir / str(preferred_run_id)).is_dir():
        run_dirs.append(runs_dir / str(preferred_run_id))
    if runs_dir.is_dir():
        run_dirs.extend(
            path
            for path in sorted(runs_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
            if path.is_dir() and path not in run_dirs
        )
    for run_dir in run_dirs:
        for relative in (
            "final/spritesheet.png",
            "final/spritesheet.webp",
            "final/spritesheet-standard.png",
            "final/spritesheet-standard.webp",
            "package/spritesheet.webp",
        ):
            candidate = run_dir / relative
            if not candidate.is_file():
                continue
            try:
                with Image.open(candidate) as image:
                    if image.size == (
                        V1_OUTPUT_CONTRACT.atlas_width,
                        V1_OUTPUT_CONTRACT.atlas_height,
                    ):
                        return candidate
            except OSError:
                continue
    return None


def prepare_v1_upgrade_run(
    project_dir: Path,
    *,
    source_atlas: Path,
    provider: str,
    model_alias: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a resumable three-job migration run around a preserved v1 atlas."""

    from .identity import (
        copy_identity_artifacts_for_run,
        identity_prompt_block,
        load_identity_profile,
        provider_reference_images,
    )
    from .jobs import initialize_run
    from .style import (
        LAYOUT_GUIDE_DIR,
        cardinal_prompt,
        choose_chroma_key,
        create_layout_guide,
        generation_inputs,
        load_style_sheet,
        look_row_prompt,
    )
    from .vendor.hatch_pet import BACKEND_VERSION

    timestamp = utc_now()
    resolved_run_id = run_id or f"v2-migration-{timestamp[:19].replace('-', '').replace(':', '').replace('T', '-')}"
    run_dir = project_dir / "runs" / resolved_run_id
    if (run_dir / "generation-jobs.json").is_file():
        raise FileExistsError(f"migration run already exists: {run_dir}")
    migration_input = run_dir / "migration-input"
    final_dir = run_dir / "final"
    neutral_dir = run_dir / "frames" / "idle"
    prompts_dir = run_dir / "prompts" / "rows"
    rows_dir = run_dir / "row-strips"
    for path in (migration_input, final_dir, neutral_dir, prompts_dir, rows_dir):
        path.mkdir(parents=True, exist_ok=True)

    archived_source = migration_input / f"v1-spritesheet{source_atlas.suffix.lower()}"
    shutil.copy2(source_atlas, archived_source)
    with Image.open(source_atlas) as opened:
        standard = opened.convert("RGBA")
    if standard.size != (V1_OUTPUT_CONTRACT.atlas_width, V1_OUTPUT_CONTRACT.atlas_height):
        raise ValueError(f"source v1 atlas has unsupported dimensions: {standard.size}")
    standard_png = final_dir / "spritesheet-standard.png"
    standard_webp = final_dir / "spritesheet-standard.webp"
    standard.save(standard_png)
    standard.save(standard_webp, format="WEBP", lossless=True)
    neutral = first_visible_idle_cell(standard)
    neutral_path = neutral_dir / "00.png"
    neutral.save(neutral_path)

    sheet = load_style_sheet(project_dir)
    identity = load_identity_profile(project_dir)
    identity_block = (
        identity_prompt_block(project_dir, require_confirmed=True)
        if identity is not None and identity.status == "confirmed"
        else "IDENTITY CONTRACT — preserve the exact character identity in the approved v1 atlas and baseline."
    )
    character_reference = (
        "character/selected-baseline.png"
        if (project_dir / "character" / "selected-baseline.png").is_file()
        else str(standard_png.relative_to(project_dir))
    )
    source_references = provider_reference_images(project_dir, provider=provider, max_sources=3)
    chroma_key = choose_chroma_key(project_dir, character_reference)
    guide_specs = [
        ("look-cardinals", 4),
        ("look-row-9", 8),
        ("look-row-10", 8),
    ]
    guides = {
        name: create_layout_guide(run_dir / LAYOUT_GUIDE_DIR / f"{name}.png", name, count)
        for name, count in guide_specs
    }
    cardinal_prompt_path = prompts_dir / "look-cardinals.md"
    cardinal_prompt_path.write_text(
        cardinal_prompt(sheet=sheet, chroma_key=chroma_key, identity_block=identity_block),
        encoding="utf-8",
    )
    row_9_prompt_path = prompts_dir / "look-row-9.md"
    row_9_prompt_path.write_text(
        look_row_prompt(state="look-000-to-157.5", sheet=sheet, chroma_key=chroma_key, identity_block=identity_block),
        encoding="utf-8",
    )
    row_10_prompt_path = prompts_dir / "look-row-10.md"
    row_10_prompt_path.write_text(
        look_row_prompt(state="look-180-to-337.5", sheet=sheet, chroma_key=chroma_key, identity_block=identity_block),
        encoding="utf-8",
    )

    def guide_path(name: str) -> str:
        return str((run_dir / LAYOUT_GUIDE_DIR / f"{name}.png").relative_to(project_dir))

    cardinal_inputs, cardinal_roles = generation_inputs(
        character_reference=character_reference,
        source_references=source_references,
        guide_path=guide_path("look-cardinals"),
        guide_role="four-cardinal layout guide only; do not copy guide lines or labels",
    )
    row_9_inputs, row_9_roles = generation_inputs(
        character_reference=character_reference,
        source_references=source_references,
        guide_path=guide_path("look-row-9"),
        guide_role="look-row layout guide only; deterministic registration owns exact cells",
        extra=[
            (
                str((run_dir / "decoded" / "look-anchors-row-9.png").relative_to(project_dir)),
                "approved row-9 anchors ordered back, screen-right, front; opposite turn excluded",
            )
        ],
    )
    row_10_inputs, row_10_roles = generation_inputs(
        character_reference=character_reference,
        source_references=source_references,
        guide_path=guide_path("look-row-10"),
        guide_role="look-row layout guide only; deterministic registration owns exact cells",
        extra=[
            (
                str((run_dir / "decoded" / "look-anchors-row-10.png").relative_to(project_dir)),
                "approved row-10 anchors ordered front, screen-left, back; opposite turn excluded",
            ),
        ],
    )
    common = {
        "provider": provider,
        "model_alias": model_alias,
        "retry_policy": {"max_attempts": 2, "use_retry_prompt": True},
        "identity_profile_version": identity.version if identity else None,
    }
    jobs = [
        GenerationJob(
            id="look-cardinals",
            kind="cardinal-strip",
            state="look-cardinals",
            status="planned",
            prompt_path=str(cardinal_prompt_path.relative_to(project_dir)),
            input_images=cardinal_inputs,
            input_image_roles=cardinal_roles,
            expected_output=str((rows_dir / "look-cardinals.png").relative_to(project_dir)),
            required_gates=["cardinal-extraction", "cardinal-semantics", "identity-consistency"],
            invalidates=["look-row-9", "look-row-10", "v2-atlas", "final-approval"],
            packaging_eligible=False,
            **common,
        ),
        GenerationJob(
            id="look-row-9",
            kind="look-row-strip",
            state="look-000-to-157.5",
            status="planned",
            prompt_path=str(row_9_prompt_path.relative_to(project_dir)),
            input_images=row_9_inputs,
            input_image_roles=row_9_roles,
            expected_output=str((rows_dir / "look-row-9.png").relative_to(project_dir)),
            depends_on=["look-cardinals"],
            required_gates=["row-registration", "direction-semantics", "continuity", "identity-consistency"],
            invalidates=["look-row-10", "v2-atlas", "final-approval"],
            **common,
        ),
        GenerationJob(
            id="look-row-10",
            kind="look-row-strip",
            state="look-180-to-337.5",
            status="planned",
            prompt_path=str(row_10_prompt_path.relative_to(project_dir)),
            input_images=row_10_inputs,
            input_image_roles=row_10_roles,
            expected_output=str((rows_dir / "look-row-10.png").relative_to(project_dir)),
            depends_on=["look-cardinals", "look-row-9"],
            required_gates=["row-registration", "direction-semantics", "continuity", "identity-consistency"],
            invalidates=["v2-atlas", "final-approval"],
            **common,
        ),
    ]
    initialize_run(
        project_dir,
        run_id=resolved_run_id,
        jobs=jobs,
        parent_run_id=source_atlas.parents[1].name if source_atlas.parents[1].parent == project_dir / "runs" else None,
        reason="v1-to-v2-preserve-standard-rows",
        identity_profile_version=identity.version if identity else None,
        contract_id=V2_OUTPUT_CONTRACT.contract_id,
        backend_version=BACKEND_VERSION,
    )
    write_json(
        run_dir / "run-metadata.json",
        {
            "run_id": resolved_run_id,
            "chroma_key": chroma_key,
            "layout_guides": guides,
            "canonical_reference": character_reference,
            "contract_id": V2_OUTPUT_CONTRACT.contract_id,
            "contract_version": V2_OUTPUT_CONTRACT.contract_version,
            "sprite_version_number": 2,
            "backend_version": BACKEND_VERSION,
            "identity_profile_version": identity.version if identity else None,
            "migration": {
                "source_contract_id": V1_OUTPUT_CONTRACT.contract_id,
                "source_atlas": str(archived_source.relative_to(project_dir)),
                "source_standard_atlas": str(standard_png.relative_to(project_dir)),
                "source_file_sha256": image_sha256(source_atlas),
                "standard_rgba_sha256": rgba_sha256(standard),
                "preservation_policy": "rows 0-8 are carried forward; only v2 look rows are generated",
            },
        },
    )
    if identity:
        copy_identity_artifacts_for_run(project_dir, resolved_run_id)
    return {
        "run_id": resolved_run_id,
        "source_atlas": str(source_atlas.relative_to(project_dir)),
        "archived_source": str(archived_source.relative_to(project_dir)),
        "standard_atlas": str(standard_png.relative_to(project_dir)),
        "source_file_sha256": image_sha256(source_atlas),
        "standard_rgba_sha256": rgba_sha256(standard),
        "jobs": [job.id for job in jobs],
    }


def first_visible_idle_cell(atlas: Image.Image) -> Image.Image:
    for column in range(V1_OUTPUT_CONTRACT.columns):
        left = column * V1_OUTPUT_CONTRACT.cell_width
        cell = atlas.crop(
            (
                left,
                0,
                left + V1_OUTPUT_CONTRACT.cell_width,
                V1_OUTPUT_CONTRACT.cell_height,
            )
        )
        if cell.getbbox() is not None:
            return cell
    raise ValueError("v1 atlas has no visible idle frame for v2 look-row registration")
