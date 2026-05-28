import tempfile
import unittest
from pathlib import Path

from PIL import Image

from goodboy.project import init_project
from goodboy.web.actions import ingest_source_images, plan_candidates_action, project_state


class WebActionTests(unittest.TestCase):
    def test_ingest_source_images_returns_refreshed_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (16, 16), (255, 255, 255)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")

            state = ingest_source_images(project_dir, "project-001", [source], notes="front view")

            self.assertEqual(state["gate"]["stage"], "sources_ingested")
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

            state = plan_candidates_action(project_dir, "project-001", provider="codex_builtin", model_alias="codex-imagegen", count=3)

            self.assertEqual(len(state["candidates"]), 3)
            self.assertTrue((project_dir / "candidates" / "contact-sheet.png").is_file())
            self.assertTrue(any(item["kind"] == "candidate" for item in state["artifacts"]))

    def test_project_state_reports_initialized_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")

            state = project_state(project_dir, "project-001")

            self.assertEqual(state["manifest"]["id"], "demo")
            self.assertEqual(state["gate"]["stage"], "initialized")
