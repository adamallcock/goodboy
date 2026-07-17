from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from goodboy.contracts import (
    CELL_HEIGHT,
    CELL_WIDTH,
    LOOK_DIRECTIONS,
    STATE_ORDER,
    V2_OUTPUT_CONTRACT,
)
from goodboy.project import init_project
from goodboy.style import plan_row_generation_jobs, save_default_style_sheet
from goodboy.v2_backend import VENDOR_ROOT, backend_metadata


EXPECTED_HATCH_DEPENDENCIES = {
    "base": [],
    "idle": ["base"],
    "running-right": ["base"],
    "running-left": ["base", "running-right"],
    "waving": ["base"],
    "jumping": ["base"],
    "failed": ["base"],
    "waiting": ["base"],
    "running": ["base"],
    "review": ["base"],
    "look-cardinals": list(STATE_ORDER),
    "look-row-9": ["look-cardinals"],
    "look-row-10": ["look-cardinals", "look-row-9"],
}


class HatchSnapshotConformanceTests(unittest.TestCase):
    def test_vendored_snapshot_matches_every_pinned_hash(self) -> None:
        snapshot = json.loads((VENDOR_ROOT / "SNAPSHOT.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["license"], "Apache-2.0")
        self.assertTrue(snapshot["source_skill_sha256"])
        self.assertGreaterEqual(len(snapshot["files"]), 20)
        for relative_path, expected_hash in snapshot["files"].items():
            path = VENDOR_ROOT / relative_path
            self.assertTrue(path.is_file(), relative_path)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                expected_hash,
                relative_path,
            )

        metadata = backend_metadata()
        self.assertEqual(metadata["name"], "hatch-pet")
        self.assertEqual(metadata["contract_id"], "codex-pet-v2")
        self.assertEqual(metadata["sprite_version_number"], 2)
        self.assertNotIn("vendor_root", metadata)

    def test_pinned_hatch_preparer_emits_the_exact_v2_contract_and_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory) / "run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(VENDOR_ROOT / "scripts" / "prepare_pet_run.py"),
                    "--pet-name",
                    "Conformance Pet",
                    "--output-dir",
                    str(run_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(json.loads(completed.stdout)["ok"])
            request = json.loads((run_dir / "pet_request.json").read_text(encoding="utf-8"))
            jobs = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))[
                "jobs"
            ]

            self.assertEqual(request["sprite_version_number"], 2)
            self.assertEqual(
                request["atlas"],
                {
                    "columns": 8,
                    "rows": 11,
                    "cell_width": CELL_WIDTH,
                    "cell_height": CELL_HEIGHT,
                    "width": V2_OUTPUT_CONTRACT.atlas_width,
                    "height": V2_OUTPUT_CONTRACT.atlas_height,
                },
            )
            self.assertEqual(
                [(row["state"], row["row"], row["frames"]) for row in request["rows"]],
                [
                    ("idle", 0, 6),
                    ("running-right", 1, 8),
                    ("running-left", 2, 8),
                    ("waving", 3, 4),
                    ("jumping", 4, 5),
                    ("failed", 5, 8),
                    ("waiting", 6, 6),
                    ("running", 7, 6),
                    ("review", 8, 6),
                    ("look-row-9", 9, 8),
                    ("look-row-10", 10, 8),
                ],
            )
            self.assertEqual(len(jobs), 13)
            self.assertEqual(
                {job["id"]: job.get("depends_on", []) for job in jobs},
                EXPECTED_HATCH_DEPENDENCIES,
            )
            self.assertEqual(
                request["rows"][9]["directions"] + request["rows"][10]["directions"],
                LOOK_DIRECTIONS,
            )

    def test_goodboy_job_graph_preserves_hatch_dependency_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_dir = Path(temporary_directory) / "project"
            init_project(project_dir, pet_id="graph-pet", display_name="Graph Pet")
            save_default_style_sheet(project_dir)
            jobs = plan_row_generation_jobs(
                project_dir=project_dir,
                run_id="run",
                provider="codex_builtin",
                model_alias="codex-imagegen",
            )
            graph = {job.id: job.depends_on for job in jobs}

            self.assertEqual(len(jobs), 12)
            self.assertEqual(graph["row-running-left"], ["row-running-right"])
            standard_jobs = [f"row-{state}" for state in STATE_ORDER]
            self.assertEqual(graph["look-cardinals"], standard_jobs)
            self.assertEqual(graph["look-row-9"], ["look-cardinals"])
            self.assertEqual(graph["look-row-10"], ["look-cardinals", "look-row-9"])


if __name__ == "__main__":
    unittest.main()
