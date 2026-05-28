import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from goodboy.cli import main
from goodboy.project import init_project
from goodboy.web.registry import ProjectRegistry


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None


class GoodboyWebCliTests(unittest.TestCase):
    def test_ui_help_command_is_registered(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            main(["ui", "--help"])
        self.assertEqual(caught.exception.code, 0)


class ProjectRegistryTests(unittest.TestCase):
    def test_register_project_returns_stable_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = ProjectRegistry()
            first = registry.register(Path(tmp))
            second = registry.register(Path(tmp))
            self.assertEqual(first, second)
            self.assertEqual(registry.resolve(first), Path(tmp).resolve())

    def test_unknown_project_id_raises_key_error(self) -> None:
        registry = ProjectRegistry()
        with self.assertRaises(KeyError):
            registry.resolve("missing")


@unittest.skipUnless(HAS_FASTAPI, "FastAPI UI dependencies are optional; install goodboy[ui] to run API contract tests.")
class ProjectStateApiTests(unittest.TestCase):
    def test_open_project_and_read_state(self) -> None:
        from fastapi.testclient import TestClient

        from goodboy.web.server import create_app

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            client = TestClient(create_app())

            opened = client.post("/api/projects/open", json={"project_dir": str(project_dir)})
            self.assertEqual(opened.status_code, 200)
            project_id = opened.json()["project_id"]

            state = client.get(f"/api/projects/{project_id}/state")
            self.assertEqual(state.status_code, 200)
            payload = state.json()
            self.assertEqual(payload["manifest"]["id"], "demo")
            self.assertEqual(payload["gate"]["stage"], "initialized")

    def test_artifact_route_serves_indexed_file(self) -> None:
        from fastapi.testclient import TestClient

        from goodboy.web.server import create_app

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            qa = project_dir / "runs" / "demo" / "qa"
            qa.mkdir(parents=True)
            Image.new("RGB", (18, 12), (255, 255, 255)).save(qa / "contact-sheet.png")
            client = TestClient(create_app())
            project_id = client.post("/api/projects/open", json={"project_dir": str(project_dir)}).json()["project_id"]

            artifact = client.get(f"/api/projects/{project_id}/artifacts/runs-demo-qa-contact-sheet-png")

            self.assertEqual(artifact.status_code, 200)
            self.assertEqual(artifact.headers["content-type"], "image/png")
