import unittest

from goodboy.web.models import artifact_id_for, artifact_url_for, severity_for_stage


class WebModelTests(unittest.TestCase):
    def test_artifact_id_is_stable_for_relative_paths(self) -> None:
        self.assertEqual(artifact_id_for("runs/demo/qa/contact-sheet.png"), "runs-demo-qa-contact-sheet-png")

    def test_artifact_url_is_project_scoped(self) -> None:
        self.assertEqual(
            artifact_url_for("project-001", "runs-demo-qa-contact-sheet-png"),
            "/api/projects/project-001/artifacts/runs-demo-qa-contact-sheet-png",
        )

    def test_severity_for_stage_defaults_to_info(self) -> None:
        self.assertEqual(severity_for_stage("sources"), "info")
