from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageSequence

from goodboy.adapters import execute_gemini_image_job, execute_openai_image_job, get_capabilities, prepare_handoff
from goodboy.atlas import compose_atlas, render_animation_previews, validate_atlas
from goodboy.candidates import build_candidate_contact_sheet, plan_baseline_candidates, select_baseline_candidate, store_candidate_image
from goodboy.cli import main as cli_main
from goodboy.contracts import CELL_HEIGHT, CELL_WIDTH, ROW_FRAME_COUNTS, ROW_FRAME_DURATIONS_MS, STATE_ORDER
from goodboy.exports import export_petdex_package, export_project_bundle
from goodboy.feedback import create_feedback_event
from goodboy.ingest import draft_source_card, ingest_images, load_source_images, write_provenance_report
from goodboy.jsonio import read_json, write_json
from goodboy.pipeline import build_from_row_strips
from goodboy.project import init_project, load_project
from goodboy.qa import audit_frames, evaluate_qa_policy
from goodboy.raster import remove_chroma_background
from goodboy.style import choose_chroma_key, plan_row_generation_jobs, save_default_style_sheet
from goodboy.validation import validate_project


class GoodboyCoreTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = cli_main(argv)
            except SystemExit as exc:
                code = int(exc.code) if isinstance(exc.code, int) else 1
        return code, stdout.getvalue(), stderr.getvalue()

    def test_project_init_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            project = init_project(root, pet_id="test_pet", display_name="Test Pet", species="dog")
            loaded = load_project(root)
            self.assertEqual(project.id, loaded.id)
            self.assertEqual(loaded.display_name, "Test Pet")
            self.assertTrue((root / "sources" / "originals").is_dir())
            self.assertTrue((root / "runs").is_dir())

    def test_webp_validation_preserves_transparent_rgb_invariant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames_root = root / "frames"
            for state in STATE_ORDER:
                state_dir = frames_root / state
                state_dir.mkdir(parents=True)
                for index in range(ROW_FRAME_COUNTS[state]):
                    frame = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(frame)
                    draw.ellipse((50, 60, 140, 160), fill=(245, 240, 225, 255))
                    draw.text((80, 96), str(index), fill=(0, 0, 0, 255))
                    frame.save(state_dir / f"{index:02d}.png")
            compose_atlas(
                frames_root,
                output_png=root / "spritesheet.png",
                output_webp=root / "spritesheet.webp",
            )
            report = validate_atlas(root / "spritesheet.webp")
            self.assertTrue(report.ok, report.errors)
            self.assertEqual(report.transparent_rgb_residue_pixels, 0)

    def test_animation_previews_use_pipeline_state_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames_root = root / "frames"
            for state in STATE_ORDER:
                state_dir = frames_root / state
                state_dir.mkdir(parents=True)
                for index in range(ROW_FRAME_COUNTS[state]):
                    frame = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(frame)
                    draw.rectangle((40 + index, 50, 140 + index, 150), fill=(240, 235, 220, 255))
                    frame.save(state_dir / f"{index:02d}.png")
            output_dir = root / "previews"
            render_animation_previews(frames_root, output_dir)

            for state in STATE_ORDER:
                with Image.open(output_dir / f"{state}.gif") as image:
                    durations = [int(frame.info.get("duration", 0)) for frame in ImageSequence.Iterator(image)]
                self.assertEqual(durations, ROW_FRAME_DURATIONS_MS[state])

    def test_ingest_source_card_style_and_handoff_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="companion", display_name="Companion", species="dog")
            source = Path(tmp) / "source.png"
            image = Image.new("RGB", (64, 48), (240, 236, 220))
            draw = ImageDraw.Draw(image)
            draw.ellipse((18, 10, 46, 38), fill=(255, 255, 255))
            image.save(source)

            added = ingest_images(root, [source], role="face_reference", notes="tiny white dog")
            self.assertEqual(len(added), 1)
            self.assertEqual(added[0].role, "face_reference")
            self.assertTrue((root / added[0].path).is_file())
            self.assertTrue((root / added[0].thumbnail_path).is_file())
            self.assertEqual(len(load_source_images(root)), 1)

            duplicate = ingest_images(root, [source], role="body_reference")
            self.assertEqual(duplicate[0].id, added[0].id)
            self.assertEqual(len(load_source_images(root)), 1)

            card = draft_source_card(root, user_notes="friendly and fluffy")
            self.assertEqual(card.species, "dog")
            self.assertEqual(card.source_image_ids, [added[0].id])
            self.assertIn("friendly", card.user_notes)

            candidates = plan_baseline_candidates(
                project_dir=root,
                provider="codex_builtin",
                model_alias="codex-imagegen",
                count=3,
            )
            self.assertEqual(len(candidates), 3)
            self.assertTrue((root / candidates[0].prompt_path).is_file())
            planned_sheet = build_candidate_contact_sheet(project_dir=root)
            self.assertTrue(planned_sheet.is_file())

            character = select_baseline_candidate(
                project_dir=root,
                candidate_id="baseline-001",
                image_path=source,
                notes="best balance of faithful and friendly",
            )
            self.assertEqual(character.selected_baseline_image, "character/selected-baseline.png")
            self.assertTrue((root / "character" / "character-card.json").is_file())
            selected = read_json(root / "candidates" / "baseline-candidates.json")["candidates"][0]
            self.assertTrue(selected["selected"])
            self.assertIn("faithful", selected["selection_notes"])

            sheet = save_default_style_sheet(root)
            self.assertEqual(len(sheet.state_specs), len(STATE_ORDER))

            jobs = plan_row_generation_jobs(
                project_dir=root,
                run_id="planned",
                provider="codex_builtin",
                model_alias="codex-imagegen",
                character_reference=added[0].path,
            )
            self.assertEqual(len(jobs), len(STATE_ORDER))
            self.assertEqual(jobs[0].status, "planned")
            self.assertTrue((root / jobs[0].prompt_path).is_file())
            self.assertTrue((root / "runs" / "planned" / "layout-guides" / "idle.png").is_file())
            self.assertIn("runs/planned/layout-guides/idle.png", jobs[0].input_images)
            self.assertEqual(
                jobs[0].input_image_roles["runs/planned/layout-guides/idle.png"],
                "layout guide only; use for spacing, do not copy guide lines",
            )
            prompt_text = (root / jobs[0].prompt_path).read_text(encoding="utf-8")
            self.assertIn("canonical base", prompt_text)
            self.assertIn("invisible equal-width slots", prompt_text)
            self.assertIn("safe padding", prompt_text)
            self.assertIn("Idle plays continuously", prompt_text)
            self.assertIn("near-still pose", prompt_text)
            self.assertIn("avoid vertical bobbing", prompt_text)
            metadata = read_json(root / "runs" / "planned" / "run-metadata.json")
            self.assertEqual(metadata["chroma_key"]["selection"], "auto")
            self.assertNotEqual(metadata["chroma_key"]["hex"].lower(), "#00ff00")

            invocation = prepare_handoff(root, "planned", jobs[0].id)
            self.assertEqual(invocation.adapter, "codex_builtin")
            self.assertEqual(invocation.status, "prepared")
            self.assertIn("input_image_roles", invocation.request_metadata)
            self.assertTrue((root / "runs" / "planned" / "provider-invocations" / f"{invocation.id}.json").is_file())

            event = create_feedback_event(
                project_dir=root,
                target="baseline-001",
                text="make the expression happier and trim chroma edges closer",
            )
            self.assertEqual(event.author, "human")
            self.assertTrue((root / "branches" / event.branch_id / "branch.json").is_file())

            validation = validate_project(root)
            self.assertTrue(validation.ok, [issue.to_dict() for issue in validation.issues])
            self.assertTrue((root / "validation" / "manifest-validation.json").is_file())

    def test_ingest_captures_exif_and_provenance_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="camera-pet", display_name="Camera Pet", species="object")
            source = Path(tmp) / "source.jpg"
            image = Image.new("RGB", (64, 48), (240, 236, 220))
            exif = Image.Exif()
            exif[274] = 1
            image.save(source, exif=exif)

            added = ingest_images(root, [source], role="style_reference", notes="with exif")
            self.assertEqual(added[0].exif.get("Orientation"), 1)
            report = write_provenance_report(root)
            self.assertEqual(report["source_count"], 1)
            self.assertTrue(report["images"][0]["exif_present"])
            self.assertEqual(report["images"][0]["sha256"], added[0].sha256)

    def test_candidate_image_is_stored_separately_from_selected_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            init_project(root, pet_id="pet", display_name="Pet", species="dog")
            ingest_images(root, [source])
            draft_source_card(root)
            plan_baseline_candidates(project_dir=root, provider="codex_builtin", model_alias="codex-imagegen", count=1)
            generated = Path(tmp) / "generated.png"
            Image.new("RGBA", (80, 80), (255, 255, 255, 255)).save(generated)

            stored = store_candidate_image(project_dir=root, candidate_id="baseline-001", image_path=generated)
            self.assertEqual(stored, "candidates/baseline-001/generated/candidate.png")
            selected = select_baseline_candidate(project_dir=root, candidate_id="baseline-001", image_path=generated)
            self.assertEqual(selected.selected_baseline_image, "character/selected-baseline.png")
            candidate = read_json(root / "candidates" / "baseline-001" / "candidate.json")
            self.assertEqual(candidate["image_path"], "candidates/baseline-001/generated/candidate.png")

    def test_style_customization_supports_subjects_and_ai_critique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "object-pet"
            init_project(root, pet_id="lamp", display_name="Lamp", species="object")
            sheet = save_default_style_sheet(
                root,
                style_id="anime-lamp",
                style_preset="clay",
                subject_kind="inanimate_object",
                user_style_overrides=["make the lamp look cozy and magical"],
                ai_critique_overrides=["increase silhouette readability around the shade"],
            )
            self.assertEqual(sheet.style_preset, "clay")
            self.assertEqual(sheet.subject_kind, "inanimate_object")
            jobs = plan_row_generation_jobs(project_dir=root, run_id="rows", provider="codex_builtin", model_alias="codex-imagegen")
            prompt = (root / jobs[0].prompt_path).read_text(encoding="utf-8")
            self.assertIn("handmade clay", prompt)
            self.assertIn("inanimate object", prompt)
            self.assertIn("squash/stretch", prompt)
            self.assertIn("make the lamp look cozy", prompt)
            self.assertIn("increase silhouette readability", prompt)

            code, stdout, stderr = self.run_cli(
                [
                    "critique",
                    str(root),
                    "--critique-id",
                    "vision-001",
                    "--target",
                    "style",
                    "--finding",
                    "object reads too flat",
                    "--recommendation",
                    "add subtle bounce and tilt while preserving lamp identity",
                    "--style-score",
                    "0.82",
                    "--apply-to-style",
                ]
            )
            self.assertEqual(code, 0, stderr)
            report = json.loads(stdout)
            self.assertTrue(report["apply_to_style"])
            updated = read_json(root / "style" / "emotion-style-sheet.json")
            self.assertIn("add subtle bounce", " ".join(updated["ai_critique_overrides"]))
            validation = validate_project(root)
            self.assertTrue(validation.ok, [issue.to_dict() for issue in validation.issues])

    def test_provider_failure_updates_retry_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="pet", display_name="Pet", species="dog")
            save_default_style_sheet(root)
            jobs = plan_row_generation_jobs(project_dir=root, run_id="rows", provider="openai_images", model_alias="gpt-image-2")
            old_key = os.environ.pop("OPENAI_API_KEY", None)
            try:
                invocation = execute_openai_image_job(root, run_id="rows", job_id=jobs[0].id)
            finally:
                if old_key is not None:
                    os.environ["OPENAI_API_KEY"] = old_key
            self.assertEqual(invocation.status, "failed")
            raw = read_json(root / "runs" / "rows" / "generation-jobs.json")
            job = raw["jobs"][0]
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["retry_policy"]["attempts"], 1)
            self.assertIn("OPENAI_API_KEY", job["retry_policy"]["last_error"])

            capabilities = get_capabilities("gemini_nano_banana_pro")
            self.assertTrue(capabilities.image_to_image)
            self.assertEqual(capabilities.default_model_alias, "gemini-3-pro-image-preview")

    def test_agent_make_next_and_agent_mode_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kitten"
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            code, stdout, stderr = self.run_cli(
                [
                    "make",
                    str(root),
                    "--pet-id",
                    "sample-kitten",
                    "--display-name",
                    "Sample Kitten",
                    "--species",
                    "cat",
                    "--source",
                    str(source),
                ]
            )
            self.assertEqual(code, 0, stderr)
            result = read_json(root / "workflow-state.json")
            self.assertEqual(result["stage"], "baselines_planned")
            self.assertEqual(result["next_action"], "generate_baselines")
            self.assertIn("do_not", result)
            self.assertIn("renderer", " ".join(result["do_not"]))
            self.assertIn("generate_baselines", stdout)

            code, stdout, stderr = self.run_cli(["next", str(root), "--agent-mode"])
            self.assertEqual(code, 0, stderr)
            next_payload = __import__("json").loads(stdout)
            self.assertEqual(next_payload["stage"], "baselines_planned")
            self.assertIn("goodboy advance", " ".join(next_payload["allowed_commands"]))
            self.assertIn("creating local renderer scripts", " ".join(next_payload["blocked_actions"]))

    def test_start_and_plan_candidates_render_candidate_sheet_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kitten"
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            code, stdout, stderr = self.run_cli(
                [
                    "start",
                    str(root),
                    "--pet-id",
                    "kitten",
                    "--display-name",
                    "Kitten",
                    "--species",
                    "cat",
                    "--source",
                    str(source),
                    "--count",
                    "2",
                ]
            )
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["stage"], "baselines_planned")
            self.assertTrue((root / "candidates" / "contact-sheet.png").is_file())
            self.assertIn("candidates/contact-sheet.png", payload["artifacts_to_show_user"])

            second = Path(tmp) / "second"
            init_project(second, pet_id="second", display_name="Second", species="dog")
            ingest_images(second, [source])
            draft_source_card(second)
            code, stdout, stderr = self.run_cli(
                [
                    "plan-candidates",
                    str(second),
                    "--provider",
                    "codex_builtin",
                    "--model-alias",
                    "codex-imagegen",
                    "--count",
                    "2",
                ]
            )
            self.assertEqual(code, 0, stderr)
            planned = json.loads(stdout)
            self.assertTrue((second / "candidates" / "contact-sheet.png").is_file())
            self.assertEqual(planned["contact_sheet"], str(second.resolve() / "candidates" / "contact-sheet.png"))

    def test_doctor_reports_next_stage_without_provider_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kitten"
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            code, _, stderr = self.run_cli(
                [
                    "make",
                    str(root),
                    "--pet-id",
                    "kitten",
                    "--display-name",
                    "Kitten",
                    "--species",
                    "cat",
                    "--source",
                    str(source),
                ]
            )
            self.assertEqual(code, 0, stderr)
            code, stdout, stderr = self.run_cli(["doctor", str(root), "--agent-mode"])
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertTrue(payload["validation"]["ok"])
            self.assertEqual(payload["workflow"]["stage"], "baselines_planned")
            self.assertEqual(payload["providers"], {"codex_builtin": {"required": "codex interactive image generation"}})
            self.assertFalse(payload["missing_generated_outputs"])
            self.assertFalse(payload["suspicious_renderer_scripts"])
            self.assertFalse(payload["tests_needed_for_project_artifacts_only"])
            self.assertIn("api_accelerators", payload)
            self.assertEqual(payload["api_accelerators"]["openai_images"]["status"], "optional_not_configured")

    def test_next_agent_mode_uses_executable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            self.run_cli(["make", str(root), "--pet-id", "pet", "--display-name", "Pet", "--source", str(source)])
            select_image = root / "candidate.png"
            Image.new("RGB", (64, 64), (255, 255, 255)).save(select_image)
            self.run_cli(["select-candidate", str(root), "--candidate-id", "baseline-001", "--image-path", str(select_image)])
            self.run_cli(["plan-rows", str(root), "--run-id", "rows", "--provider", "codex_builtin", "--model-alias", "codex-imagegen", "--character-reference", "character/selected-baseline.png"])
            code, stdout, stderr = self.run_cli(["next", str(root), "--agent-mode"])
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["stage"], "rows_planned")
            self.assertEqual(payload["recommended_command"], f"goodboy advance {root.resolve()} --agent-mode --run-id rows")
            self.assertIn("goodboy advance", payload["after_provider_generation"])
            self.assertIn("--generated-map", payload["after_provider_generation"])
            self.assertIn("custom metadata python", payload["do_not_run"])
            self.assertNotIn("<project-dir>", payload["recommended_command"])
            self.assertIn("style-default", " ".join(payload["already_done"]))

    def test_plan_commands_are_idempotent_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            self.run_cli(["make", str(root), "--pet-id", "pet", "--display-name", "Pet", "--source", str(source)])
            prompt = root / "candidates" / "baseline-001" / "prompt.md"
            before = prompt.read_text(encoding="utf-8")
            code, stdout, stderr = self.run_cli(["plan-candidates", str(root), "--provider", "codex_builtin", "--model-alias", "codex-imagegen", "--count", "6"])
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertTrue(payload["already_exists"])
            self.assertEqual(prompt.read_text(encoding="utf-8"), before)

            selected = root / "selected.png"
            Image.new("RGB", (64, 64), (255, 255, 255)).save(selected)
            self.run_cli(["select-candidate", str(root), "--candidate-id", "baseline-001", "--image-path", str(selected)])
            self.run_cli(["style-default", str(root)])
            code, stdout, stderr = self.run_cli(["style-default", str(root)])
            self.assertEqual(code, 0, stderr)
            self.assertTrue(json.loads(stdout)["already_exists"])
            self.run_cli(["plan-rows", str(root), "--run-id", "rows", "--provider", "codex_builtin", "--model-alias", "codex-imagegen", "--character-reference", "character/selected-baseline.png"])
            code, stdout, stderr = self.run_cli(["plan-rows", str(root), "--run-id", "rows", "--provider", "codex_builtin", "--model-alias", "codex-imagegen", "--character-reference", "character/selected-baseline.png"])
            self.assertEqual(code, 0, stderr)
            self.assertTrue(json.loads(stdout)["already_exists"])

    def test_simplified_handoff_import_build_review_finish_flow(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            source = Path(tmp) / "source.png"
            install_root = Path(tmp) / "pets"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            self.run_cli(["make", str(root), "--pet-id", "pet", "--display-name", "Pet", "--source", str(source)])
            self.run_cli(["select-candidate", str(root), "--candidate-id", "baseline-001", "--image-path", str(source)])
            self.run_cli(["style-default", str(root)])
            self.run_cli(["plan-rows", str(root), "--run-id", "rows", "--provider", "codex_builtin", "--model-alias", "codex-imagegen", "--character-reference", "character/selected-baseline.png"])

            code, stdout, stderr = self.run_cli(["generate-handoff", str(root), "--run-id", "rows", "--all"])
            self.assertEqual(code, 0, stderr)
            handoff = json.loads(stdout)
            self.assertEqual(handoff["prepared_count"], len(STATE_ORDER))
            self.assertEqual(handoff["next_action"], "await_provider_outputs")
            self.assertTrue((root / "runs" / "rows" / "handoff-summary.json").is_file())

            output_map = {state: str(rows / f"{state}.png") for state in STATE_ORDER}
            map_path = Path(tmp) / "generated-map.json"
            map_path.write_text(json.dumps(output_map), encoding="utf-8")
            code, stdout, stderr = self.run_cli(["import-generated", str(root), "--run-id", "rows", "--map", str(map_path)])
            self.assertEqual(code, 0, stderr)
            imported = json.loads(stdout)
            self.assertFalse(imported["missing_states"])
            self.assertEqual(len(imported["imported"]), len(STATE_ORDER))
            jobs = read_json(root / "runs" / "rows" / "generation-jobs.json")["jobs"]
            self.assertTrue(all(job["status"] == "complete" for job in jobs))

            code, stdout, stderr = self.run_cli(["build-review", str(root), "--run-id", "rows", "--row-provenance", "test_fixture", "--extraction-method", "stable-slots"])
            self.assertEqual(code, 0, stderr)
            review = json.loads(stdout)
            self.assertTrue(review["validation"]["ok"])
            self.assertIn("runs/rows/qa/contact-sheet.png", review["review_artifacts"])
            self.assertIn("runs/rows/qa/centering-overlay.png", review["review_artifacts"])
            self.assertIn("runs/rows/qa/centering-report.json", review["review_artifacts"])
            self.assertTrue((root / "runs" / "rows" / "qa" / "review-summary.json").is_file())
            manifest = read_json(root / "runs" / "rows" / "frames" / "frames-manifest.json")
            self.assertEqual({row["method"] for row in manifest["rows"]}, {"stable-slots"})

            code, stdout, stderr = self.run_cli(["finish", str(root), "--run-id", "rows", "--row-provenance", "test_fixture", "--install-root", str(install_root), "--approval-notes", "Approved simplified flow"])
            self.assertEqual(code, 0, stderr)
            finished = json.loads(stdout)
            self.assertTrue(finished["validation"]["ok"])
            self.assertTrue((install_root / "pet" / "pet.json").is_file())
            self.assertTrue((root / "runs" / "rows" / "finish-summary.json").is_file())

    def test_advance_collapses_deterministic_flow_between_gates(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            source = Path(tmp) / "source.png"
            install_root = Path(tmp) / "pets"
            Image.new("RGB", (64, 48), (240, 236, 220)).save(source)
            self.run_cli(["start", str(root), "--pet-id", "pet", "--display-name", "Pet", "--source", str(source)])

            code, stdout, stderr = self.run_cli(
                [
                    "advance",
                    str(root),
                    "--agent-mode",
                    "--candidate-id",
                    "baseline-001",
                    "--baseline-image",
                    str(source),
                    "--run-id",
                    "rows",
                    "--selection-notes",
                    "fixture selected",
                ]
            )
            self.assertEqual(code, 0, stderr)
            selected = json.loads(stdout)
            self.assertEqual(selected["gate"], "row_generation")
            self.assertIn("select-candidate", selected["actions"])
            self.assertIn("generate-handoff", selected["actions"])
            self.assertTrue((root / "runs" / "rows" / "handoff-summary.json").is_file())

            output_map = {state: str(rows / f"{state}.png") for state in STATE_ORDER}
            map_path = Path(tmp) / "generated-map.json"
            map_path.write_text(json.dumps(output_map), encoding="utf-8")
            code, stdout, stderr = self.run_cli(
                [
                    "advance",
                    str(root),
                    "--agent-mode",
                    "--run-id",
                    "rows",
                    "--generated-map",
                    str(map_path),
                    "--row-provenance",
                    "test_fixture",
                ]
            )
            self.assertEqual(code, 0, stderr)
            built = json.loads(stdout)
            self.assertEqual(built["gate"], "visual_approval")
            self.assertIn("build-review", built["actions"])
            self.assertIn("runs/rows/qa/contact-sheet.png", built["artifacts_to_show_user"])

            code, stdout, stderr = self.run_cli(
                [
                    "advance",
                    str(root),
                    "--agent-mode",
                    "--run-id",
                    "rows",
                    "--row-provenance",
                    "test_fixture",
                    "--install-root",
                    str(install_root),
                    "--approval-notes",
                    "Approved advance flow",
                ]
            )
            self.assertEqual(code, 0, stderr)
            finished = json.loads(stdout)
            self.assertEqual(finished["gate"], "done")
            self.assertIn("finish", finished["actions"])
            self.assertTrue((install_root / "pet" / "pet.json").is_file())

    def test_openai_execution_adapter_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="demo", display_name="Demo", species="dog")
            save_default_style_sheet(root)
            jobs = plan_row_generation_jobs(
                project_dir=root,
                run_id="openai-plan",
                provider="openai_images",
                model_alias="gpt-image-2",
            )
            invocation = execute_openai_image_job(
                root,
                "openai-plan",
                jobs[0].id,
                dry_run=True,
            )
            self.assertEqual(invocation.adapter, "openai_images")
            self.assertEqual(invocation.status, "prepared")
            self.assertEqual(invocation.request_metadata["endpoint"], "/v1/images/edits")
            self.assertGreaterEqual(invocation.request_metadata["input_image_count"], 1)

            reference = root / "character" / "selected-baseline.png"
            reference.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (32, 32), (255, 255, 255)).save(reference)
            edit_jobs = plan_row_generation_jobs(
                project_dir=root,
                run_id="openai-edit-plan",
                provider="openai_images",
                model_alias="gpt-image-2",
                character_reference="character/selected-baseline.png",
            )
            edit_invocation = execute_openai_image_job(
                root,
                "openai-edit-plan",
                edit_jobs[0].id,
                dry_run=True,
            )
            self.assertEqual(edit_invocation.status, "prepared")
            self.assertEqual(edit_invocation.request_metadata["endpoint"], "/v1/images/edits")

    def test_gemini_execution_adapter_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="demo", display_name="Demo", species="dog")
            save_default_style_sheet(root)
            jobs = plan_row_generation_jobs(
                project_dir=root,
                run_id="gemini-plan",
                provider="gemini_nano_banana_2",
                model_alias="gemini-3.1-flash-image-preview",
            )
            invocation = execute_gemini_image_job(
                root,
                "gemini-plan",
                jobs[0].id,
                dry_run=True,
            )
            self.assertEqual(invocation.adapter, "gemini_nano_banana_2")
            self.assertEqual(invocation.status, "prepared")
            self.assertIn(":generateContent", invocation.request_metadata["endpoint"])

    def test_manifest_validation_catches_named_manifest_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="demo", display_name="Demo", species="dog")
            project = read_json(root / "goodboy.json")
            project["unexpected"] = True
            write_json(root / "goodboy.json", project)
            write_json(
                root / "sources" / "source-images.json",
                {
                    "images": [
                        {
                            "id": "source-001",
                            "path": "sources/originals/missing.png",
                            "sha256": "abc",
                            "original_filename": "missing.png",
                            "mime_type": "image/png",
                            "width": 0,
                            "height": 64,
                        }
                    ]
                },
            )
            write_json(root / "sources" / "source-card.json", {"must_keep": "not-a-list"})
            write_json(
                root / "candidates" / "baseline-candidates.json",
                {
                    "candidates": [
                        {
                            "id": "baseline-001",
                            "image_path": None,
                            "prompt_path": "candidates/baseline-001/missing.md",
                            "provider": "bogus",
                            "model": "none",
                            "source_images": [],
                            "style_summary": "bad",
                            "character_delta": "bad",
                            "selected": True,
                        },
                        {
                            "id": "baseline-002",
                            "image_path": None,
                            "prompt_path": "candidates/baseline-002/missing.md",
                            "provider": "bogus",
                            "model": "none",
                            "source_images": [],
                            "style_summary": "bad",
                            "character_delta": "bad",
                            "selected": True,
                        },
                    ]
                },
            )
            write_json(
                root / "character" / "character-card.json",
                {
                    "canonical_name": "Demo",
                    "one_sentence_identity": "Bad",
                    "selected_baseline_image": "character/missing.png",
                },
            )
            sheet = save_default_style_sheet(root).to_dict()
            sheet["state_specs"][0]["frame_count"] = 99
            write_json(root / "style" / "emotion-style-sheet.json", sheet)
            write_json(
                root / "feedback" / "events.json",
                {"events": [{"id": "feedback-001", "author": "ghost", "target": "", "text": ""}]},
            )
            write_json(
                root / "branches" / "actual-id" / "branch.json",
                {
                    "id": "wrong-id",
                    "parent": "main",
                    "target": "baseline-001",
                    "reason": "bad",
                    "author": "human",
                    "source_event_id": "feedback-001",
                },
            )
            write_json(
                root / "runs" / "bad" / "generation-jobs.json",
                {
                    "jobs": [
                        {
                            "id": "job-001",
                            "kind": "row-strip",
                            "status": "nonsense",
                            "provider": "bogus",
                            "model_alias": "none",
                            "prompt_path": "runs/bad/prompts/missing.md",
                            "input_images": ["missing-input.png"],
                            "expected_output": "runs/bad/out.png",
                            "state": "not-a-state",
                            "depends_on": ["missing-job"],
                        }
                    ]
                },
            )
            write_json(
                root / "runs" / "bad" / "provider-invocations" / "bad.json",
                {
                    "id": "bad",
                    "adapter": "bogus",
                    "model": "none",
                    "status": "nonsense",
                    "prompt_hash": "abc",
                    "input_image_hashes": [],
                    "output_paths": ["runs/bad/missing-output.png"],
                    "started_at": "now",
                },
            )
            write_json(
                root / "runs" / "bad" / "run-summary.json",
                {
                    "ok": True,
                    "version": "bad",
                    "source_rows": "missing",
                    "spritesheet": "runs/bad/missing.webp",
                    "contact_sheet": "runs/bad/missing-contact.png",
                    "edge_preview": "runs/bad/missing-edge.png",
                    "validation": "runs/bad/missing-validation.json",
                    "review": "runs/bad/missing-review.json",
                    "duplicate_audit": "runs/bad/missing-audit.json",
                },
            )
            report = validate_project(root, write_report=False)
            messages = "\n".join(issue.message for issue in report.issues)
            self.assertFalse(report.ok)
            for expected in [
                "unknown field `unexpected`",
                "source image path does not exist",
                "`must_keep` must be a list",
                "only one baseline candidate may be selected",
                "unknown provider `bogus`",
                "selected baseline image path does not exist",
                "idle frame_count is 99",
                "unknown feedback author `ghost`",
                "branch id `wrong-id` must match folder `actual-id`",
                "invalid job status `nonsense`",
                "unknown dependency `missing-job`",
                "invalid invocation status `nonsense`",
                "spritesheet does not exist",
            ]:
                self.assertIn(expected, messages)

    def test_synthetic_row_fixture_builds_and_validates(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            summary = build_from_row_strips(
                project_dir=root,
                rows_dir=rows,
                run_id="synthetic-fixture",
                pet_id="synthetic",
                display_name="Synthetic",
            )
            self.assertTrue(summary.ok)
            policy = read_json(root / "runs" / "synthetic-fixture" / "qa" / "install-policy.json")
            self.assertTrue(policy["ok_to_install"], policy)
            validation = validate_project(root)
            self.assertTrue(validation.ok, [issue.to_dict() for issue in validation.issues])

    def test_install_blocks_rows_without_provenance_and_visual_approval(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            install_root = Path(tmp) / "pets"
            with self.assertRaisesRegex(ValueError, "row strip provenance"):
                build_from_row_strips(
                    project_dir=root,
                    rows_dir=rows,
                    run_id="synthetic-fixture",
                    pet_id="synthetic",
                    display_name="Synthetic",
                    install=True,
                    install_root=install_root,
                )
            self.assertFalse((install_root / "synthetic").exists())

    def test_cli_install_policy_block_prints_clean_error(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = cli_main(
                    [
                        "build-from-rows",
                        str(Path(tmp) / "synthetic"),
                        "--rows-dir",
                        str(rows),
                        "--run-id",
                        "synthetic-fixture",
                        "--pet-id",
                        "synthetic",
                        "--display-name",
                        "Synthetic",
                        "--install",
                        "--install-root",
                        str(Path(tmp) / "pets"),
                    ]
                )
            self.assertEqual(exit_code, 1)
            self.assertIn("row strip provenance is required", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_install_allows_approved_test_fixture_rows(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            install_root = Path(tmp) / "pets"
            build_from_row_strips(
                project_dir=root,
                rows_dir=rows,
                run_id="synthetic-fixture",
                pet_id="synthetic",
                display_name="Synthetic",
                install=True,
                install_root=install_root,
                row_provenance="test_fixture",
                visual_approval="fixture approved for install gate coverage",
            )
            self.assertTrue((install_root / "synthetic" / "pet.json").is_file())
            policy = read_json(root / "runs" / "synthetic-fixture" / "qa" / "install-policy.json")
            self.assertTrue(policy["ok_to_install"], policy)
            self.assertEqual(policy["row_provenance"], "test_fixture")
            self.assertEqual(policy["visual_approval"], "fixture approved for install gate coverage")
            self.assertTrue((root / "runs" / "synthetic-fixture" / "qa" / "human-review-checklist.json").is_file())

    def test_exports_project_and_petdex_packages(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            build_from_row_strips(
                project_dir=root,
                rows_dir=rows,
                run_id="synthetic-fixture",
                pet_id="synthetic",
                display_name="Synthetic",
                row_provenance="test_fixture",
            )
            project_export = export_project_bundle(root, run_id="synthetic-fixture", zip_output=True)
            self.assertTrue(Path(project_export["export_dir"]).is_dir())
            self.assertTrue(Path(project_export["zip"]).is_file())
            self.assertTrue((Path(project_export["export_dir"]) / "runs" / "synthetic-fixture" / "run-summary.json").is_file())

            petdex_export = export_petdex_package(root, run_id="synthetic-fixture", zip_output=True)
            self.assertTrue(Path(petdex_export["export_dir"]).is_dir())
            self.assertTrue(Path(petdex_export["zip"]).is_file())
            self.assertTrue((Path(petdex_export["export_dir"]) / "pet.json").is_file())
            self.assertTrue((Path(petdex_export["export_dir"]) / "spritesheet.webp").is_file())

    def test_approve_review_status_and_install_command(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            install_root = Path(tmp) / "pets"
            build_from_row_strips(
                project_dir=root,
                rows_dir=rows,
                run_id="synthetic-fixture",
                pet_id="synthetic",
                display_name="Synthetic",
            )
            blocked, _, blocked_stderr = self.run_cli(
                [
                    "install",
                    str(root),
                    "--run-id",
                    "synthetic-fixture",
                    "--install-root",
                    str(install_root),
                    "--row-provenance",
                    "test_fixture",
                ]
            )
            self.assertEqual(blocked, 1)
            self.assertIn("visual approval", blocked_stderr)

            code, stdout, stderr = self.run_cli(
                [
                    "approve",
                    str(root),
                    "--run-id",
                    "synthetic-fixture",
                    "--artifact",
                    "contact-sheet",
                    "--decision",
                    "approved",
                    "--notes",
                    "Fixture contact sheet approved for install",
                ]
            )
            self.assertEqual(code, 0, stderr)
            self.assertTrue((root / "runs" / "synthetic-fixture" / "approvals" / "contact-sheet.json").is_file())
            self.assertIn("approved", stdout)

            code, stdout, stderr = self.run_cli(["review-status", str(root), "--run-id", "synthetic-fixture", "--agent-mode"])
            self.assertEqual(code, 0, stderr)
            status = __import__("json").loads(stdout)
            self.assertTrue(status["has_visual_approval"])
            self.assertIn("runs/synthetic-fixture/qa/contact-sheet.png", status["review_artifacts"])

            code, stdout, stderr = self.run_cli(
                [
                    "install",
                    str(root),
                    "--run-id",
                    "synthetic-fixture",
                    "--install-root",
                    str(install_root),
                    "--row-provenance",
                    "test_fixture",
                ]
            )
            self.assertEqual(code, 0, stderr)
            self.assertTrue((install_root / "synthetic" / "pet.json").is_file())
            self.assertIn("installed", stdout)

    def test_approve_short_form_defaults_to_latest_contact_sheet(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            build_from_row_strips(
                project_dir=root,
                rows_dir=rows,
                run_id="synthetic-fixture",
                pet_id="synthetic",
                display_name="Synthetic",
            )
            code, stdout, stderr = self.run_cli(["approve", str(root), "--notes", "Short approval"])
            self.assertEqual(code, 0, stderr)
            approval = json.loads(stdout)
            self.assertEqual(approval["run_id"], "synthetic-fixture")
            self.assertEqual(approval["artifact"], "contact-sheet")
            self.assertEqual(approval["decision"], "approved")
            self.assertTrue((root / "runs" / "synthetic-fixture" / "approvals" / "contact-sheet.json").is_file())

    def test_install_blocks_suspicious_renderer_scripts(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            build_from_row_strips(
                project_dir=root,
                rows_dir=rows,
                run_id="synthetic-fixture",
                pet_id="synthetic",
                display_name="Synthetic",
            )
            code, _, stderr = self.run_cli(
                [
                    "approve",
                    str(root),
                    "--run-id",
                    "synthetic-fixture",
                    "--artifact",
                    "contact-sheet",
                    "--decision",
                    "approved",
                    "--notes",
                    "Fixture contact sheet approved for install",
                ]
            )
            self.assertEqual(code, 0, stderr)
            tools = root / "tools"
            tools.mkdir()
            (tools / "render_synthetic.py").write_text("from PIL import ImageDraw\n", encoding="utf-8")
            code, _, stderr = self.run_cli(
                [
                    "install",
                    str(root),
                    "--run-id",
                    "synthetic-fixture",
                    "--row-provenance",
                    "test_fixture",
                    "--install-root",
                    str(Path(tmp) / "pets"),
                ]
            )
            self.assertEqual(code, 1)
            self.assertIn("suspicious renderer", stderr)

    def test_variable_height_idle_is_stabilized_and_reported(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            rows_copy = Path(tmp) / "rows"
            shutil.copytree(rows, rows_copy)
            strip = Image.new("RGB", (1200, 260), (0, 255, 0))
            draw = ImageDraw.Draw(strip)
            heights = [110, 150, 95, 170, 120, 145]
            slot = strip.width // len(heights)
            for index, height in enumerate(heights):
                cx = index * slot + slot // 2
                bottom = 230
                draw.ellipse((cx - 45, bottom - height, cx + 45, bottom), fill=(245, 240, 225))
            strip.save(rows_copy / "idle.png")
            root = Path(tmp) / "pet"
            summary = build_from_row_strips(
                project_dir=root,
                rows_dir=rows_copy,
                run_id="centered",
                pet_id="centered",
                display_name="Centered",
            )
            self.assertTrue(summary.ok)
            audit = read_json(root / "runs" / "centered" / "qa" / "duplicate-audit.json")
            self.assertLessEqual(audit["states"]["idle"]["cy_range"], 4.0)
            centering = read_json(root / "runs" / "centered" / "qa" / "centering-report.json")
            self.assertEqual(centering["states"]["idle"]["anchor_policy"], "stable_center")
            self.assertTrue(any(frame["shift_y"] != 0 for frame in centering["states"]["idle"]["frames"]))
            self.assertTrue((root / "runs" / "centered" / "qa" / "centering-overlay.png").is_file())

    def test_stable_slots_extraction_is_explicit_and_reported(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stable"
            code, stdout, stderr = self.run_cli(
                [
                    "build-from-rows",
                    str(root),
                    "--rows-dir",
                    str(rows),
                    "--run-id",
                    "stable-slots",
                    "--pet-id",
                    "stable",
                    "--display-name",
                    "Stable",
                    "--extraction-method",
                    "stable-slots",
                ]
            )
            self.assertEqual(code, 0, stderr)
            summary = json.loads(stdout)
            self.assertTrue(summary["ok"])
            manifest = read_json(root / "runs" / "stable-slots" / "frames" / "frames-manifest.json")
            methods = {row["state"]: row["method"] for row in manifest["rows"]}
            self.assertEqual(methods["idle"], "stable-slots")
            review = read_json(root / "runs" / "stable-slots" / "qa" / "review.json")
            self.assertIn("stable-slots extraction", " ".join(review["warnings"]))

    def test_chroma_key_selection_and_explicit_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pet"
            init_project(root, pet_id="pet", display_name="Pet", species="object")
            source = Path(tmp) / "source.png"
            Image.new("RGB", (64, 64), (255, 0, 255)).save(source)
            ingest_images(root, [source], role="primary_reference", notes="magenta subject")

            chroma = choose_chroma_key(root)
            self.assertNotEqual(chroma["hex"].lower(), "#ff00ff")

            strip = Image.new("RGB", (40, 40), tuple(chroma["rgb"]))
            draw = ImageDraw.Draw(strip)
            draw.rectangle((12, 12, 28, 28), fill=(230, 220, 200))
            cleaned = remove_chroma_background(strip, tuple(chroma["rgb"]))
            self.assertEqual(cleaned.getpixel((0, 0))[3], 0)
            self.assertEqual(cleaned.getpixel((20, 20))[3], 255)

    def test_qa_policy_blocks_hard_failures_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp) / "frames"
            for state in STATE_ORDER:
                (frames / state).mkdir(parents=True)
            report = audit_frames(frames)
            validation = type(
                "ValidationLike",
                (),
                {"errors": [], "warnings": []},
            )()
            decision = evaluate_qa_policy(validation, report)
            self.assertFalse(decision.ok_to_install)
            self.assertTrue(decision.hard_failures)
            override = evaluate_qa_policy(validation, report, override_reason="manual visual approval")
            self.assertTrue(override.ok_to_install)

    def test_codex_plugin_package_and_marketplace_are_wired(self) -> None:
        plugin_root = Path("plugins/goodboy")
        manifest = read_json(plugin_root / ".codex-plugin" / "plugin.json")
        self.assertEqual(manifest["name"], "goodboy")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["interface"]["displayName"], "Goodboy")
        self.assertIn("start a Codex pet", " ".join(manifest["interface"]["defaultPrompt"]))
        self.assertTrue((plugin_root / "skills" / "goodboy" / "SKILL.md").is_file())

        marketplace = read_json(Path(".agents/plugins/marketplace.json"))
        self.assertEqual(marketplace["name"], "goodboy-local")
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn("goodboy", entries)
        entry = entries["goodboy"]
        self.assertEqual(entry["source"]["source"], "local")
        self.assertEqual(entry["source"]["path"], "./plugins/goodboy")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_existing_legacy_rows_regression_if_available(self) -> None:
        row_dir = os.environ.get("GOODBOY_LEGACY_ROW_STRIPS")
        if not row_dir:
            self.skipTest("GOODBOY_LEGACY_ROW_STRIPS is not set to a legacy row-strip folder")
        rows = Path(row_dir)
        if not rows.is_dir():
            self.skipTest("GOODBOY_LEGACY_ROW_STRIPS is not set to a legacy row-strip folder")
        with tempfile.TemporaryDirectory() as tmp:
            summary = build_from_row_strips(
                project_dir=Path(tmp) / "legacy",
                rows_dir=rows,
                run_id="legacy-regression",
                pet_id="legacy",
                display_name="Legacy",
            )
            self.assertTrue(summary.ok)
            validation = Path(summary.validation)
            audit = Path(summary.duplicate_audit)
            self.assertTrue(validation.is_file())
            self.assertTrue(audit.is_file())


if __name__ == "__main__":
    unittest.main()
