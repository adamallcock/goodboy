import tempfile
import unittest
from pathlib import Path

from PIL import Image

from goodboy.jsonio import write_json
from goodboy.project import init_project
from goodboy.style import plan_row_generation_jobs, save_default_style_sheet
from goodboy.web.actions import (
    assign_source_roles_action,
    identity_confirm_action,
    ingest_source_images,
    plan_candidates_action,
    project_state,
    style_default_action,
)


class WebActionTests(unittest.TestCase):
    def test_ingest_source_images_returns_refreshed_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (16, 16), (255, 255, 255)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")

            state = ingest_source_images(project_dir, "project-001", [source], notes="front view")

            self.assertEqual(state["gate"]["stage"], "identity_review")
            self.assertEqual(len(state["sources"]), 1)
            self.assertEqual(state["sources"][0]["notes"], "front view")

    def test_plan_candidates_action_writes_contact_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (16, 16), (255, 255, 255)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            ingest_source_images(project_dir, "project-001", [source], notes="front view")
            identity_confirm_action(project_dir, "project-001", author="test")

            state = plan_candidates_action(
                project_dir,
                "project-001",
                provider="codex_builtin",
                model_alias="codex-imagegen",
                count=3,
                provider_consent=True,
            )

            self.assertEqual(len(state["candidates"]), 3)
            self.assertEqual(
                {item["evaluation_dimension"] for item in state["candidates"]},
                {"likeness"},
            )
            self.assertEqual(
                len({item["style_summary"] for item in state["candidates"]}),
                1,
            )
            self.assertEqual(
                len({item["character_delta"] for item in state["candidates"]}),
                3,
            )
            self.assertTrue((project_dir / "candidates" / "contact-sheet.png").is_file())
            self.assertTrue(any(item["kind"] == "candidate" for item in state["artifacts"]))

    def test_project_state_reports_initialized_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")

            state = project_state(project_dir, "project-001")

            self.assertEqual(state["manifest"]["id"], "demo")
            self.assertEqual(state["gate"]["stage"], "initialized")
            self.assertEqual(
                state["animation_contract"]["running-right"]["frame_durations_ms"],
                [120, 120, 120, 120, 120, 120, 120, 220],
            )

    def test_project_state_does_not_rewrite_stable_job_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            save_default_style_sheet(project_dir)
            plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
            )
            jobs_path = project_dir / "runs" / "run" / "generation-jobs.json"
            events_path = project_dir / "runs" / "run" / "events.jsonl"
            before_jobs = jobs_path.read_bytes()
            before_events = events_path.read_bytes()

            first = project_state(project_dir, "project-001")
            second = project_state(project_dir, "project-001")

            self.assertEqual(first["job_graph"], second["job_graph"])
            self.assertEqual(jobs_path.read_bytes(), before_jobs)
            self.assertEqual(events_path.read_bytes(), before_events)

    def test_project_state_exposes_saved_blind_direction_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            save_default_style_sheet(project_dir)
            plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
            )
            report = {"ok": True, "errors": [], "warnings": ["review-only endpoint ambiguity"]}
            write_json(project_dir / "runs" / "run" / "qa" / "direction-blind-validation.json", report)

            state = project_state(project_dir, "project-001")

            self.assertEqual(state["direction_blind"], report)

    def test_source_policy_and_style_mutations_return_real_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (32, 24), (180, 120, 80)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            state = ingest_source_images(project_dir, "project-001", [source], notes="front view")
            source_id = str(state["sources"][0]["id"])

            state = assign_source_roles_action(
                project_dir,
                "project-001",
                source_id=source_id,
                roles=["identity_front", "marking_detail"],
                provider_permissions={"openai_images": True},
            )
            self.assertEqual(
                state["sources"][0]["roles"],
                ["identity_front", "marking_detail"],
            )
            self.assertTrue(state["sources"][0]["provider_permissions"]["openai_images"])

            state = style_default_action(
                project_dir,
                "project-001",
                preset="anime",
                subject_kind="pet",
                ai_critique=["Keep the asymmetric marking."],
            )
            self.assertEqual(state["style_sheet"]["style_preset"], "anime")
            self.assertIn(
                "Keep the asymmetric marking.",
                state["style_sheet"]["ai_critique_overrides"],
            )
