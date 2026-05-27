import tempfile
import unittest
from pathlib import Path

from PIL import Image

from goodboy.web.artifacts import build_artifact_index, safe_artifact_path


class ArtifactIndexTests(unittest.TestCase):
    def test_build_index_finds_known_qa_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "runs" / "demo" / "qa"
            qa.mkdir(parents=True)
            image_path = qa / "contact-sheet.png"
            Image.new("RGBA", (20, 10), (255, 255, 255, 255)).save(image_path)

            index = build_artifact_index(root, project_id="project-001")

            self.assertIn("runs-demo-qa-contact-sheet-png", index.by_id)
            ref = index.by_id["runs-demo-qa-contact-sheet-png"]
            self.assertEqual(ref["width"], 20)
            self.assertEqual(ref["height"], 10)
            self.assertEqual(ref["kind"], "qa")

    def test_safe_artifact_path_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                safe_artifact_path(root, "../outside.png")
