import importlib.util
import re
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from goodboy.cli import main
from goodboy.project import init_project
from goodboy.web.registry import ProjectRegistry


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None


class GoodboyWebCliTests(unittest.TestCase):
    def test_version_is_registered(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            main(["--version"])
        self.assertEqual(caught.exception.code, 0)

    def test_ui_help_command_is_registered(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            main(["ui", "--help"])
        self.assertEqual(caught.exception.code, 0)

    def test_ui_refuses_non_loopback_binding(self) -> None:
        self.assertEqual(main(["ui", "--host", "0.0.0.0", "--no-open"]), 1)


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


class PackagedReviewRoomTests(unittest.TestCase):
    def test_compiled_review_room_assets_are_packaged(self) -> None:
        static = files("goodboy.web").joinpath("static")
        index = static.joinpath("index.html")
        self.assertTrue(index.is_file())
        source = index.read_text(encoding="utf-8")
        script_match = re.search(r'src="/([^"]+\.js)"', source)
        style_match = re.search(r'href="/([^"]+\.css)"', source)
        self.assertIsNotNone(script_match)
        self.assertIsNotNone(style_match)
        self.assertTrue(static.joinpath(*str(script_match.group(1)).split("/")).is_file())
        self.assertTrue(static.joinpath(*str(style_match.group(1)).split("/")).is_file())


@unittest.skipUnless(HAS_FASTAPI, "FastAPI UI dependencies are optional; install goodboy[ui] to run API contract tests.")
class ProjectStateApiTests(unittest.TestCase):
    def test_packaged_review_room_and_launch_context_are_served(self) -> None:
        from fastapi.testclient import TestClient

        from goodboy.web.registry import ProjectRegistry
        from goodboy.web.server import create_app

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            registry = ProjectRegistry()
            project_id = registry.register(project_dir)
            client = TestClient(create_app(registry, launch_project_id=project_id))

            index = client.get("/")
            self.assertEqual(index.status_code, 200)
            self.assertIn("text/html", index.headers["content-type"])
            self.assertIn('<div id="root"></div>', index.text)
            script_match = re.search(r'src="([^"]+\.js)"', index.text)
            self.assertIsNotNone(script_match)
            script = client.get(str(script_match.group(1)))
            self.assertEqual(script.status_code, 200)
            self.assertIn("javascript", script.headers["content-type"])

            context = client.get("/api/launch-context")
            self.assertEqual(
                context.json(),
                {"project_id": project_id, "project_dir": str(project_dir.resolve())},
            )

    def test_ui_launcher_runs_uvicorn_with_registered_project(self) -> None:
        from fastapi.testclient import TestClient

        from goodboy.web.dev import launch_dev_server

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            with patch("uvicorn.run") as run:
                result = launch_dev_server(
                    project_dir=project_dir,
                    host="127.0.0.1",
                    port=8787,
                    open_browser=False,
                )

            run.assert_called_once()
            app = run.call_args.args[0]
            client = TestClient(app)
            context = client.get("/api/launch-context").json()
            self.assertEqual(context["project_dir"], str(project_dir.resolve()))
            self.assertEqual(result["status"], "stopped")

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

    def test_source_policy_and_style_routes_mutate_the_registered_project(self) -> None:
        from fastapi.testclient import TestClient

        from goodboy.web.actions import ingest_source_images
        from goodboy.web.server import create_app

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (24, 18), (180, 120, 80)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            seeded = ingest_source_images(project_dir, "seed", [source], notes="front")
            source_id = seeded["sources"][0]["id"]
            client = TestClient(create_app())
            project_id = client.post(
                "/api/projects/open",
                json={"project_dir": str(project_dir)},
            ).json()["project_id"]

            roles = client.post(
                f"/api/projects/{project_id}/sources/{source_id}/roles",
                json={
                    "roles": ["identity_front", "marking_detail"],
                    "provider_permissions": {"openai_images": True},
                },
            )
            self.assertEqual(roles.status_code, 200)
            self.assertEqual(
                roles.json()["sources"][0]["roles"],
                ["identity_front", "marking_detail"],
            )

            style = client.post(
                f"/api/projects/{project_id}/style/default",
                json={
                    "preset": "anime",
                    "subject_kind": "pet",
                    "ai_critique": ["Keep the asymmetric marking."],
                },
            )
            self.assertEqual(style.status_code, 200)
            self.assertEqual(style.json()["style_sheet"]["style_preset"], "anime")

            invalid_dimension = client.post(
                f"/api/projects/{project_id}/candidates/plan",
                json={
                    "provider": "codex_builtin",
                    "model_alias": "codex-imagegen",
                    "count": 2,
                    "evaluation_dimension": "novelty",
                },
            )
            self.assertEqual(invalid_dimension.status_code, 400)
            self.assertIn(
                "evaluation_dimension",
                invalid_dimension.json()["detail"],
            )
