from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from goodboy.contracts import STATE_ORDER
from goodboy.jsonio import read_json
from goodboy.pipeline import build_from_row_strips
from goodboy.qa import animation_is_approved, record_animation_review
from goodboy.workflow import review_gates
from goodboy.web.actions import project_state


class AnimationCorrectnessReviewTests(unittest.TestCase):
    def verdicts(self, failed_state: str | None = None) -> list[dict[str, str]]:
        return [
            {
                "state": state,
                "verdict": "fail" if state == failed_state else "pass",
                "state_semantics": f"{state} reads as its intended Codex behavior.",
                "motion_continuity": "The ordered frames form a continuous loop without popping or reversal.",
                "identity_consistency": "The same face, silhouette, palette, and proportions persist across the row.",
            }
            for state in STATE_ORDER
        ]

    def test_v2_build_writes_exact_temporal_contract_report(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            build_from_row_strips(
                project_dir=project_dir,
                rows_dir=rows,
                run_id="animation",
                pet_id="animation",
                display_name="Animation",
                row_provenance="provider_generated",
            )
            report = read_json(
                project_dir / "runs" / "animation" / "qa" / "animation-correctness.json"
            )
            self.assertTrue(report["technical_ok"], report["technical_failures"])
            self.assertFalse(report["review_complete"])
            self.assertFalse(report["ok"])
            self.assertEqual(len(report["rows"]), len(STATE_ORDER))
            self.assertTrue(all(row["temporal_contract_ok"] for row in report["rows"]))
            gates = review_gates(project_dir, "animation")
            self.assertIn(
                "state-by-state animation semantics, continuity, and identity review",
                gates["missing_reviews"],
            )

    def test_animation_review_requires_all_states_and_blocks_failed_state(self) -> None:
        rows = Path("tests/fixtures/synthetic-row-strips").resolve()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            build_from_row_strips(
                project_dir=project_dir,
                rows_dir=rows,
                run_id="animation",
                pet_id="animation",
                display_name="Animation",
                row_provenance="provider_generated",
            )
            with self.assertRaisesRegex(ValueError, "incomplete"):
                record_animation_review(
                    project_dir,
                    run_id="animation",
                    verdicts=self.verdicts()[:-1],
                    reviewed_by="test",
                )
            failed = record_animation_review(
                project_dir,
                run_id="animation",
                verdicts=self.verdicts(failed_state="running"),
                reviewed_by="test",
            )
            self.assertEqual(failed["status"], "failed")
            self.assertFalse(animation_is_approved(project_dir, "animation"))
            approved = record_animation_review(
                project_dir,
                run_id="animation",
                verdicts=self.verdicts(),
                reviewed_by="test",
            )
            self.assertEqual(approved["status"], "approved")
            self.assertTrue(animation_is_approved(project_dir, "animation"))
            correctness = read_json(
                project_dir / "runs" / "animation" / "qa" / "animation-correctness.json"
            )
            self.assertTrue(correctness["ok"], correctness)
            state = project_state(project_dir, "animation-project")
            self.assertEqual(state["animation_review"]["status"], "approved")
            self.assertTrue(state["animation_correctness"]["ok"])


if __name__ == "__main__":
    unittest.main()
