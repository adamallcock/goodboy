from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from goodboy.adapters import prepare_handoff
from goodboy.benchmark import (
    QUESTIONS,
    REQUIRED_ANIMATION_STATES,
    analyze_benchmark,
    import_ratings,
    initialize_benchmark,
    prepare_trials,
)
from goodboy.candidates import plan_baseline_candidates, select_baseline_candidate
from goodboy.contracts import V1_OUTPUT_CONTRACT, V2_OUTPUT_CONTRACT
from goodboy.exports import export_diagnostic_bundle, export_project_bundle
from goodboy.identity import (
    analyze_reference_coverage,
    apply_identity_trait_patch,
    confirm_identity_profile,
    create_likeness_report,
    draft_identity_profile,
    likeness_is_approved,
    prepare_identity_analysis_handoff,
    record_likeness_review,
    write_likeness_receipt,
)
from goodboy.ingest import draft_source_card, ingest_images, load_source_images
from goodboy.jobs import (
    complete_job,
    create_repair_attempt,
    load_jobs,
    recover_run,
    transition_job,
)
from goodboy.jsonio import read_json, read_jsonl, write_json
from goodboy.migrations import upgrade_project_manifest
from goodboy.pipeline import build_from_row_strips
from goodboy.project import init_project, load_project
from goodboy.style import plan_row_generation_jobs, save_default_style_sheet
from goodboy.validation import validate_project
from goodboy.v2_backend import extract_and_compose_cardinals, record_direction_semantics
from goodboy.workflow import build_review, import_generated_outputs


FIXTURE_ROWS = Path("tests/fixtures/synthetic-row-strips").resolve()


class GoodboyV2Tests(unittest.TestCase):
    def create_confirmed_identity(self, project_dir: Path, source: Path) -> None:
        ingest_images(project_dir, [source])
        draft_source_card(project_dir)
        analyze_reference_coverage(project_dir)
        draft_identity_profile(project_dir)
        confirm_identity_profile(project_dir, confirmed_by="test")

    def test_provider_privacy_requires_consent_and_never_hands_off_originals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.jpg"
            image = Image.new("RGB", (320, 240), (180, 120, 80))
            exif = Image.Exif()
            exif[274] = 6
            image.save(source, exif=exif)
            init_project(project_dir, pet_id="privacy-pet", display_name="Privacy Pet", species="dog")
            self.create_confirmed_identity(project_dir, source)

            with self.assertRaisesRegex(ValueError, "provider consent"):
                plan_baseline_candidates(
                    project_dir=project_dir,
                    provider="codex_builtin",
                    model_alias="codex-imagegen",
                    count=1,
                )

            identity_handoff = prepare_identity_analysis_handoff(
                project_dir,
                provider="codex_builtin",
                provider_consent=True,
            )
            identity_prompt = (project_dir / identity_handoff["prompt_path"]).read_text(encoding="utf-8")
            self.assertIn("pet's anatomical side", identity_prompt)
            self.assertIn("viewer/screen side", identity_prompt)
            self.assertIn("explicitly verify the orientation", identity_prompt)
            self.assertEqual(
                set(identity_handoff["input_images"]),
                set(identity_handoff["input_image_roles"]),
            )
            self.assertFalse(
                any(path.startswith("sources/originals/") for path in identity_handoff["input_images"])
            )

            candidates = plan_baseline_candidates(
                project_dir=project_dir,
                provider="codex_builtin",
                model_alias="codex-imagegen",
                count=1,
                provider_consent=True,
            )
            self.assertTrue(candidates[0].source_images)
            self.assertTrue(
                all(path.startswith("sources/provider-derivatives/") for path in candidates[0].source_images)
            )
            sources = load_source_images(project_dir)
            derivative = project_dir / str(sources[0].provider_derivative_path)
            self.assertTrue(derivative.is_file())
            with Image.open(derivative) as opened:
                self.assertFalse(opened.getexif())
            receipt = read_json(project_dir / "decisions" / "provider-consent" / "codex_builtin.json")
            self.assertEqual(receipt["source_handling"], "EXIF-transposed RGBA PNG derivatives only; originals remain local")

            baseline = root / "baseline.png"
            Image.new("RGBA", (256, 256), (210, 160, 110, 255)).save(baseline)
            select_baseline_candidate(
                project_dir=project_dir,
                candidate_id="baseline-001",
                image_path=baseline,
                holistic_gestalt_score=4,
                signature_trait_score=4,
                small_size_readability_score=4,
                review_notes="Synthetic candidate preserves the source fixture.",
                reviewed_by="test",
            )
            save_default_style_sheet(project_dir)
            jobs = plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="privacy-run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
                character_reference="character/selected-baseline.png",
            )
            self.assertEqual(len(jobs), 12)
            row_9_prompt = (
                project_dir / "runs" / "privacy-run" / "prompts" / "rows" / "look-000-to-157.5.md"
            ).read_text(encoding="utf-8")
            row_10_prompt = (
                project_dir / "runs" / "privacy-run" / "prompts" / "rows" / "look-180-to-337.5.md"
            ).read_text(encoding="utf-8")
            self.assertIn("000 is fully back-facing", row_9_prompt)
            self.assertIn("Do not include a front-facing 180 pose", row_9_prompt)
            self.assertIn("180 is fully front-facing", row_10_prompt)
            self.assertIn("Do not include a fully back-facing 000 pose", row_10_prompt)
            self.assertIn("cannot duplicate 000", row_10_prompt)
            self.assertIn("opposite-facing profile is intentionally absent", row_10_prompt)
            row_9_job = next(job for job in jobs if job.id == "look-row-9")
            row_10_job = next(job for job in jobs if job.id == "look-row-10")
            self.assertTrue(any(path.endswith("look-anchors-row-9.png") for path in row_9_job.input_images))
            self.assertTrue(any(path.endswith("look-anchors-row-10.png") for path in row_10_job.input_images))
            self.assertFalse(any(path.endswith("look-row-9.png") for path in row_10_job.input_images))
            self.assertFalse(
                any(
                    Path(path).as_posix().startswith("sources/originals/")
                    for job in jobs
                    for path in job.input_images
                )
            )
            invocation = prepare_handoff(project_dir, "privacy-run", jobs[0].id)
            self.assertTrue(invocation.input_image_hashes)
            report = validate_project(project_dir, write_report=False)
            self.assertTrue(report.ok, [issue.to_dict() for issue in report.issues])

    def test_recovery_preserves_unknown_provider_gate_and_repair_is_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="recover", display_name="Recover")
            save_default_style_sheet(project_dir)
            jobs = plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
            )
            first = jobs[0]
            raw_jobs = read_json(
                project_dir / "runs" / "run" / "generation-jobs.json"
            )
            raw_jobs["jobs"][0]["created_at"] = "2020-01-01T00:00:00+00:00"
            raw_jobs["jobs"][0]["updated_at"] = "2020-01-01T00:00:00+00:00"
            write_json(
                project_dir / "runs" / "run" / "generation-jobs.json",
                raw_jobs,
            )
            transition_job(project_dir, "run", first.id, "running")
            running = next(
                job
                for job in load_jobs(project_dir, "run")
                if job.id == first.id
            )
            self.assertEqual(running.created_at, "2020-01-01T00:00:00+00:00")
            self.assertNotEqual(running.updated_at, "2020-01-01T00:00:00+00:00")
            recovery = recover_run(project_dir, "run")
            self.assertIn(first.id, recovery["blocked_unknown_provider_jobs"])
            recovered = next(job for job in load_jobs(project_dir, "run") if job.id == first.id)
            self.assertEqual(recovered.status, "blocked")
            self.assertIn("outcome unknown", recovered.blocked_reason or "")

            transition_job(project_dir, "run", first.id, "ready", event="explicit-retry")
            output = project_dir / first.expected_output
            output.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (256, 256), (0, 255, 0)).save(output)
            complete_job(
                project_dir,
                "run",
                first.id,
                selected_output_path=first.expected_output,
            )
            repair = create_repair_attempt(
                project_dir,
                "run",
                job_ids=[first.id],
                reason="identity drift in idle",
                author="test",
            )
            self.assertIn(first.id, repair["invalidated_jobs"])
            self.assertIn("look-cardinals", repair["invalidated_jobs"])
            self.assertFalse(output.exists())
            refreshed = {job.id: job for job in load_jobs(project_dir, "run")}
            self.assertEqual(refreshed[first.id].status, "ready")
            self.assertIn("prompts/repairs/", refreshed[first.id].prompt_path)
            repair_prompt = project_dir / refreshed[first.id].prompt_path
            self.assertTrue(repair_prompt.is_file())
            self.assertIn("identity drift in idle", repair_prompt.read_text(encoding="utf-8"))
            self.assertEqual(repair["repair_prompts"][first.id], refreshed[first.id].prompt_path)
            self.assertEqual(refreshed["look-cardinals"].status, "blocked")
            self.assertGreater(len(read_jsonl(project_dir / "runs" / "run" / "events.jsonl")), len(jobs))

    def test_direction_only_repair_preserves_standard_atlas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="repair", display_name="Repair")
            save_default_style_sheet(project_dir)
            jobs = plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
            )
            for job in jobs:
                if job.id == "look-row-10":
                    job.status = "ready"
                    job.depends_on = []
                elif job.id.startswith("row-"):
                    job.status = "complete"
            write_json(
                project_dir / "runs" / "run" / "generation-jobs.json",
                {"jobs": [job.to_dict() for job in jobs]},
            )
            final_dir = project_dir / "runs" / "run" / "final"
            final_dir.mkdir(parents=True)
            Image.new("RGBA", (16, 16), "white").save(final_dir / "spritesheet-standard.png")
            Image.new("RGBA", (16, 16), "white").save(final_dir / "spritesheet-v2.png")

            create_repair_attempt(
                project_dir,
                "run",
                job_ids=["look-row-10"],
                reason="337.5 duplicated 000",
                author="test",
            )

            self.assertTrue((final_dir / "spritesheet-standard.png").is_file())
            self.assertFalse((final_dir / "spritesheet-v2.png").exists())

    def test_identity_repair_refreshes_run_snapshot_jobs_and_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (320, 240), (190, 150, 100)).save(source)
            init_project(project_dir, pet_id="identity-repair", display_name="Identity Repair", species="dog")
            self.create_confirmed_identity(project_dir, source)
            baseline = project_dir / "character" / "selected-baseline.png"
            baseline.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (256, 256), (180, 140, 100, 255)).save(baseline)
            save_default_style_sheet(project_dir)
            jobs = plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
                character_reference="character/selected-baseline.png",
            )
            old_version = jobs[0].identity_profile_version
            trait_id = read_json(project_dir / "identity" / "identity-profile.json")["traits"][0]["id"]
            profile = apply_identity_trait_patch(
                project_dir,
                trait_id=trait_id,
                value="anatomical right foreleg has the higher white marking",
                reason="source orientation correction",
                author="test",
            )
            self.assertNotEqual(profile.version, old_version)

            repair = create_repair_attempt(
                project_dir,
                "run",
                job_ids=[],
                reason="identity markings.primary changed after a source orientation audit",
                author="test",
                identity_changed=True,
            )

            refreshed = load_jobs(project_dir, "run")
            self.assertEqual(len(repair["repair_prompts"]), len(refreshed))
            self.assertTrue(all(job.identity_profile_version == profile.version for job in refreshed))
            self.assertEqual(
                read_json(project_dir / "runs" / "run" / "run.json")["identity_profile_version"],
                profile.version,
            )
            self.assertEqual(
                read_json(project_dir / "runs" / "run" / "run-metadata.json")["identity_profile_version"],
                profile.version,
            )
            self.assertEqual(
                read_json(project_dir / "runs" / "run" / "identity" / "identity-profile.json")["version"],
                profile.version,
            )
            self.assertEqual(
                read_json(project_dir / "runs" / "run" / "identity" / "identity-pack.json")
                ["identity_profile_version"],
                profile.version,
            )
            prompt = (project_dir / refreshed[0].prompt_path).read_text(encoding="utf-8")
            self.assertIn("UPDATED IDENTITY CONTRACT", prompt)
            self.assertIn("anatomical right foreleg", prompt)

    def test_signature_likeness_failure_blocks_receipt_until_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (320, 240), (190, 150, 100)).save(source)
            init_project(project_dir, pet_id="likeness", display_name="Likeness", species="dog")
            self.create_confirmed_identity(project_dir, source)
            (project_dir / "runs" / "run" / "qa").mkdir(parents=True)
            report = create_likeness_report(project_dir, run_id="run")
            signature = report.verdicts[0].trait_id
            verdicts = [
                {
                    "trait_id": verdict.trait_id,
                    "target": "final-atlas",
                    "verdict": "uncertain" if verdict.trait_id == signature else "pass",
                    "evidence": (
                        "The defining trait cannot be confirmed at pet size."
                        if verdict.trait_id == signature
                        else "The trait is preserved in the reviewed output."
                    ),
                }
                for verdict in report.verdicts
            ]
            failed = record_likeness_review(
                project_dir,
                run_id="run",
                verdicts=verdicts,
                reviewed_by="test",
            )
            self.assertEqual(failed.status, "failed")
            self.assertFalse(likeness_is_approved(project_dir, "run"))
            with self.assertRaisesRegex(ValueError, "approved likeness"):
                write_likeness_receipt(project_dir, run_id="run")

            passed = record_likeness_review(
                project_dir,
                run_id="run",
                verdicts=[
                    {
                        "trait_id": verdict.trait_id,
                        "target": "final-atlas",
                        "verdict": "pass",
                        "evidence": "The species-defining silhouette is clear in source and final output.",
                    }
                    for verdict in report.verdicts
                ],
                reviewed_by="test",
            )
            self.assertEqual(passed.status, "approved")
            write_json(
                project_dir / "character" / "selected-candidate.json",
                {
                    "id": "baseline-002",
                    "evaluation_dimension": "likeness",
                    "selection_notes": "Best ear shape and face proportions.",
                    "selected_at": "2026-07-16T12:00:00+00:00",
                },
            )
            write_json(
                project_dir / "runs" / "run" / "run.json",
                {
                    "run_id": "run",
                    "parent_run_id": None,
                    "reason": "new-generation",
                },
            )
            write_json(
                project_dir / "runs" / "run" / "run-summary.json",
                {"run_id": "run", "likeness_receipt": None},
            )
            write_json(
                project_dir / "runs" / "run" / "approvals" / "final-review.json",
                {
                    "id": "approval",
                    "run_id": "run",
                    "artifact": "final-review",
                    "decision": "approved",
                    "notes": "Compared source, baseline, animations, and directions.",
                    "created_at": "2026-07-16T12:30:00+00:00",
                    "author": "human",
                },
            )
            write_json(
                project_dir / "runs" / "run" / "superseded" / "repair-001" / "repair.json",
                {
                    "run_id": "run",
                    "reason": "Corrected the defining ear shape.",
                    "invalidated_jobs": ["row-waving"],
                },
            )
            receipt = write_likeness_receipt(project_dir, run_id="run")
            self.assertTrue(receipt["automated_metrics_are_advisory"])
            self.assertEqual(receipt["goodboy_version"], "0.2.1")
            self.assertEqual(receipt["baseline_decision"]["id"], "baseline-002")
            self.assertEqual(receipt["final_visual_approval"]["decision"], "approved")
            self.assertEqual(len(receipt["repairs"]), 1)
            self.assertTrue(
                (project_dir / "runs" / "run" / "qa" / "likeness-receipt.md").is_file()
            )
            self.assertEqual(
                read_json(project_dir / "runs" / "run" / "run-summary.json")[
                    "likeness_receipt"
                ],
                "runs/run/qa/likeness-receipt.json",
            )

    def test_legacy_unknown_manifest_fields_are_preserved_during_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "legacy"
            project_dir.mkdir()
            write_json(
                project_dir / "goodboy.json",
                {
                    "id": "legacy",
                    "display_name": "Legacy",
                    "species": "dog",
                    "workspace_version": "0.1.0",
                    "custom_old_setting": {"keep": True},
                },
            )

            loaded = load_project(project_dir)

            self.assertEqual(loaded.goodboy_version, "0.2.1")
            self.assertEqual(loaded.contract_id, "codex-pet-v1")
            self.assertEqual(loaded.output_contract["rows"], 9)
            self.assertEqual(
                loaded.legacy_compat["custom_old_setting"],
                {"keep": True},
            )

    def test_current_manifest_unknown_fields_remain_strict_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "current"
            init_project(project_dir, pet_id="current", display_name="Current")
            manifest = read_json(project_dir / "goodboy.json")
            manifest["unexpected_current_field"] = True
            write_json(project_dir / "goodboy.json", manifest)

            with self.assertRaisesRegex(TypeError, "unexpected_current_field"):
                load_project(project_dir)

    def test_direction_review_requires_unique_evidence_for_every_v2_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "qa").mkdir(parents=True)
            directions = [
                {
                    "direction": direction,
                    "verdict": "pass",
                    "observed": direction,
                    "reason": "The face and body orientation match this angle.",
                }
                for direction in V2_OUTPUT_CONTRACT.look_directions
            ]
            reviewed = record_direction_semantics(run_dir, directions, reviewer="test")
            self.assertEqual(reviewed["status"], "reviewed")
            missing_evidence = [dict(item) for item in directions]
            missing_evidence[0]["reason"] = ""
            with self.assertRaisesRegex(ValueError, "visible evidence"):
                record_direction_semantics(run_dir, missing_evidence, reviewer="test")
            duplicate = [dict(item) for item in directions]
            duplicate[-1]["direction"] = duplicate[0]["direction"]
            with self.assertRaisesRegex(ValueError, "duplicate"):
                record_direction_semantics(run_dir, duplicate, reviewer="test")

    def test_cardinal_import_registers_four_separated_components_when_slot_margins_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "row-strips").mkdir(parents=True)
            write_json(run_dir / "run-metadata.json", {"chroma_key": {"hex": "#FF00FF"}})
            strip = Image.new("RGB", (800, 320), "#FF00FF")
            for box, color in zip(
                [(20, 60, 230, 260), (240, 60, 430, 260), (440, 60, 630, 260), (640, 60, 790, 260)],
                ["black", "navy", "darkgreen", "maroon"],
                strict=True,
            ):
                strip.paste(color, box)
            strip.save(run_dir / "row-strips" / "look-cardinals.png")

            report = extract_and_compose_cardinals(run_dir)

            self.assertTrue(report["ok"])
            self.assertEqual(report["extraction_method"], "components")
            self.assertTrue(report["fallback_trigger"])
            self.assertTrue(report["warnings"])
            with Image.open(run_dir / "decoded" / "look-anchors-approved.png") as approved:
                self.assertEqual(approved.size, (192 * 4, 208))
            with Image.open(run_dir / "decoded" / "look-anchors-row-9.png") as row_9_reference:
                self.assertEqual(row_9_reference.size, (192 * 3, 208))
            with Image.open(run_dir / "decoded" / "look-anchors-row-10.png") as row_10_reference:
                self.assertEqual(row_10_reference.size, (192 * 3, 208))
            self.assertEqual(
                report["row_specific_references"]["look-row-10"]["directions"],
                ["180", "270", "000"],
            )
            for direction in ("000", "090", "180", "270"):
                with Image.open(run_dir / "decoded" / "look-anchors" / f"{direction}.png") as anchor:
                    bbox = anchor.convert("RGBA").getchannel("A").getbbox()
                    self.assertIsNotNone(bbox)
                    assert bbox is not None
                    self.assertGreaterEqual(bbox[0], 4)
                    self.assertGreaterEqual(bbox[1], 4)
                    self.assertLessEqual(bbox[2], 188)
                    self.assertLessEqual(bbox[3], 204)

    def test_v1_upgrade_preserves_standard_atlas_and_generates_only_look_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "legacy"
            init_project(project_dir, pet_id="legacy", display_name="Legacy")
            manifest = read_json(project_dir / "goodboy.json")
            manifest["contract_id"] = V1_OUTPUT_CONTRACT.contract_id
            manifest["contract_version"] = V1_OUTPUT_CONTRACT.contract_version
            manifest["output_contract"] = V1_OUTPUT_CONTRACT.to_dict()
            manifest["migration_state"] = "legacy-v1"
            write_json(project_dir / "goodboy.json", manifest)
            build_from_row_strips(
                project_dir=project_dir,
                rows_dir=FIXTURE_ROWS,
                run_id="legacy-v1",
                row_provenance="test_fixture",
                extraction_method="stable-slots",
            )

            receipt = upgrade_project_manifest(
                project_dir,
                provider="codex_builtin",
                model_alias="codex-imagegen",
                run_id="upgrade-v2",
            )
            self.assertTrue(receipt["preserved_v1_atlas_found"])
            self.assertEqual(
                receipt["migration_run"]["jobs"],
                ["look-cardinals", "look-row-9", "look-row-10"],
            )
            jobs = load_jobs(project_dir, "upgrade-v2")
            self.assertEqual(len(jobs), 3)
            self.assertEqual(jobs[0].status, "ready")
            self.assertTrue(all(job.created_at and job.updated_at for job in jobs))
            mapping = {
                "look-cardinals": str(FIXTURE_ROWS / "look-cardinals.png"),
                "look-row-9": str(FIXTURE_ROWS / "look-row-9.png"),
                "look-row-10": str(FIXTURE_ROWS / "look-row-10.png"),
            }
            imported = import_generated_outputs(
                project_dir,
                run_id="upgrade-v2",
                mapping=mapping,
                extraction_method="stable-slots",
                chroma_key_hex="#00FF00",
            )
            self.assertFalse(imported["remaining_jobs"])
            review = build_review(
                project_dir,
                run_id="upgrade-v2",
                row_provenance="test_fixture",
                extraction_method="stable-slots",
            )
            self.assertTrue(review["validation"]["ok"], review["validation"]["issues"])
            package = read_json(project_dir / "runs" / "upgrade-v2" / "package" / "pet.json")
            self.assertEqual(package["spriteVersionNumber"], 2)
            with Image.open(project_dir / "runs" / "upgrade-v2" / "package" / "spritesheet.webp") as atlas:
                self.assertEqual(atlas.size, (V2_OUTPUT_CONTRACT.atlas_width, V2_OUTPUT_CONTRACT.atlas_height))
            preservation = read_json(project_dir / "runs" / "upgrade-v2" / "qa" / "migration-preservation.json")
            self.assertIn("before_standard_rgba_sha256", preservation)
            self.assertIn("after_standard_rgba_sha256", preservation)
            self.assertEqual(load_project(project_dir).migration_state, "current")
            current_receipt = read_json(project_dir / "migration-receipt.json")
            self.assertFalse(current_receipt["requires_generation"])
            self.assertEqual(current_receipt["completed_run_id"], "upgrade-v2")

    def test_exports_exclude_source_pixels_by_default_and_diagnostics_are_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (64, 64), (120, 80, 60)).save(source)
            init_project(project_dir, pet_id="private", display_name="Private")
            ingest_images(project_dir, [source])
            run_dir = project_dir / "runs" / "run"
            (run_dir / "identity").mkdir(parents=True)
            (run_dir / "qa").mkdir(parents=True)
            (run_dir / "provider-invocations").mkdir(parents=True)
            Image.new("RGB", (32, 32), "red").save(run_dir / "identity" / "source-contact-sheet.png")
            Image.new("RGB", (32, 32), "blue").save(run_dir / "qa" / "likeness-qa-sheet.png")
            write_json(run_dir / "run.json", {"run_id": "run", "status": "active"})
            write_json(
                run_dir / "provider-invocations" / "handoff.json",
                {"request_metadata": {"generated_image_source": str(source.resolve())}},
            )

            default = export_project_bundle(
                project_dir,
                run_id="run",
                output_dir=root / "default-export",
            )
            default_root = Path(str(default["export_dir"]))
            self.assertFalse((default_root / "sources" / "originals").exists())
            self.assertFalse((default_root / "runs" / "run" / "identity" / "source-contact-sheet.png").exists())
            self.assertFalse((default_root / "runs" / "run" / "qa" / "likeness-qa-sheet.png").exists())
            exported_json = "\n".join(
                path.read_text(encoding="utf-8")
                for path in default_root.rglob("*.json")
            )
            self.assertNotIn(str(root), exported_json)
            explicit = export_project_bundle(
                project_dir,
                run_id="run",
                output_dir=root / "explicit-export",
                include_sources=True,
            )
            explicit_root = Path(str(explicit["export_dir"]))
            self.assertTrue(any((explicit_root / "sources" / "originals").iterdir()))
            self.assertTrue((explicit_root / "runs" / "run" / "qa" / "likeness-qa-sheet.png").is_file())
            diagnostic = export_diagnostic_bundle(
                project_dir,
                run_id="run",
                output_dir=root / "diagnostic",
                zip_output=False,
            )
            diagnostic_root = Path(str(diagnostic["export_dir"]))
            self.assertFalse(any(path.suffix.lower() in {".png", ".jpg", ".webp"} for path in diagnostic_root.rglob("*")))
            self.assertFalse(diagnostic["manifest"]["contains_source_images"])

    def test_blinded_benchmark_uses_identity_clusters_and_predeclared_claim_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            benchmark_dir = root / "benchmark"
            initialize_benchmark(
                benchmark_dir,
                benchmark_id="goodboy-v2-smoke",
                seed="frozen-test-seed",
                release_min_identities=4,
                min_raters_per_identity=3,
            )
            packages: dict[str, Path] = {}
            for method, color in (("goodboy", (180, 120, 80, 255)), ("hatch", (80, 120, 180, 255))):
                package = root / f"{method}-package"
                package.mkdir()
                write_json(
                    package / "pet.json",
                    {
                        "id": f"{method}-pet",
                        "displayName": f"{method.title()} Pet",
                        "spritesheet": "spritesheet.webp",
                        "spriteVersionNumber": 2,
                    },
                )
                Image.new(
                    "RGBA",
                    (V2_OUTPUT_CONTRACT.atlas_width, V2_OUTPUT_CONTRACT.atlas_height),
                    color,
                ).save(package / "spritesheet.webp", format="WEBP", lossless=True)
                packages[method] = package
            identities = []
            for index in range(4):
                goodboy = root / f"goodboy-{index}.png"
                hatch = root / f"hatch-{index}.png"
                Image.new("RGB", (32, 32), (180 + index, 120, 80)).save(goodboy)
                Image.new("RGB", (32, 32), (80, 120, 180 + index)).save(hatch)
                identities.append(
                    {
                        "identity_id": f"pet-{index}",
                        "goodboy_output": str(goodboy),
                        "hatch_output": str(hatch),
                        "goodboy_package": str(packages["goodboy"]),
                        "hatch_package": str(packages["hatch"]),
                        "goodboy_media": {
                            "contact_sheet": str(goodboy),
                            "directions": str(goodboy),
                            "animations": {
                                state: str(goodboy) for state in REQUIRED_ANIMATION_STATES
                            },
                        },
                        "hatch_media": {
                            "contact_sheet": str(hatch),
                            "directions": str(hatch),
                            "animations": {
                                state: str(hatch) for state in REQUIRED_ANIMATION_STATES
                            },
                        },
                        "cohort": {"coat": "synthetic"},
                    }
                )
            comparisons = root / "comparisons.json"
            write_json(comparisons, {"identities": identities})
            prepare_trials(benchmark_dir, comparisons)
            answer_key = read_json(benchmark_dir / "private" / "answer-key.json")
            goodboy_sides = {
                assignment["trial_id"]: next(
                    side
                    for side, output in assignment["outputs"].items()
                    if output["method"] == "goodboy"
                )
                for assignment in answer_key["assignments"]
            }
            review_packet = (benchmark_dir / "review-packet.json").read_text(encoding="utf-8")
            self.assertNotIn("goodboy_output", review_packet)
            self.assertNotIn("hatch_output", review_packet)
            for reviewer in range(3):
                ratings_path = root / f"ratings-{reviewer}.json"
                write_json(
                    ratings_path,
                    {
                        "reviewer_id": f"reviewer-{reviewer}",
                        "ratings": [
                            {
                                "trial_id": trial_id,
                                **{question: side for question in QUESTIONS},
                                "unacceptable": [],
                            }
                            for trial_id, side in goodboy_sides.items()
                        ],
                    },
                )
                import_ratings(benchmark_dir, ratings_path)
            result = analyze_benchmark(benchmark_dir)
            self.assertTrue(result["better_likeness_claim_allowed"], result["release_gates"])
            self.assertTrue(result["release_gates"]["technical_evidence_complete"])
            self.assertTrue(result["release_gates"]["animation_media_evidence_complete"])
            self.assertTrue(result["release_gates"]["unacceptable_failure_parity"])
            self.assertEqual(result["questions"]["likeness"]["identity_count"], 4)
            self.assertGreater(result["questions"]["likeness"]["wilson_95"][0], 0.5)
            report_files = list(benchmark_dir.glob("*-benchmark-report.md"))
            self.assertEqual(len(report_files), 1)
            self.assertIn("Claim status", report_files[0].read_text(encoding="utf-8"))
            manifest = read_json(benchmark_dir / "benchmark.json")
            manifest["release_win_rate"] = 0.5
            write_json(benchmark_dir / "benchmark.json", manifest)
            with self.assertRaisesRegex(ValueError, "changed after it was frozen"):
                analyze_benchmark(benchmark_dir)

    def test_benchmark_withholds_claim_for_self_reported_technical_validity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            benchmark_dir = root / "benchmark"
            initialize_benchmark(
                benchmark_dir,
                benchmark_id="unverified-technical-evidence",
                seed="frozen-test-seed",
                release_min_identities=1,
                min_raters_per_identity=3,
            )
            goodboy = root / "goodboy.png"
            hatch = root / "hatch.png"
            Image.new("RGB", (32, 32), (180, 120, 80)).save(goodboy)
            Image.new("RGB", (32, 32), (80, 120, 180)).save(hatch)
            comparisons = root / "comparisons.json"
            write_json(
                comparisons,
                {
                    "identities": [
                        {
                            "identity_id": "pet-001",
                            "goodboy_output": str(goodboy),
                            "hatch_output": str(hatch),
                            "goodboy_v2_valid": True,
                            "hatch_v2_valid": True,
                        }
                    ]
                },
            )
            prepare_trials(benchmark_dir, comparisons)
            assignment = read_json(benchmark_dir / "private" / "answer-key.json")[
                "assignments"
            ][0]
            goodboy_side = next(
                side
                for side, output in assignment["outputs"].items()
                if output["method"] == "goodboy"
            )
            for reviewer in range(3):
                ratings_path = root / f"ratings-{reviewer}.json"
                write_json(
                    ratings_path,
                    {
                        "reviewer_id": f"reviewer-{reviewer}",
                        "ratings": [
                            {
                                "trial_id": "trial-0001",
                                **{question: goodboy_side for question in QUESTIONS},
                                "unacceptable": [],
                            }
                        ],
                    },
                )
                import_ratings(benchmark_dir, ratings_path)
            result = analyze_benchmark(benchmark_dir)
            self.assertFalse(result["release_gates"]["technical_evidence_complete"])
            self.assertFalse(result["release_gates"]["animation_media_evidence_complete"])
            self.assertFalse(result["better_likeness_claim_allowed"])
            self.assertIn("WITHHELD", result["claim"])


if __name__ == "__main__":
    unittest.main()
