from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from goodboy.candidates import (
    IDENTITY_ANCHOR,
    build_candidate_contact_sheet,
    plan_baseline_candidates,
    record_candidate_review,
    select_baseline_candidate,
    store_candidate_image,
)
from goodboy.identity import analyze_reference_coverage, confirm_identity_profile, draft_identity_profile
from goodboy.ingest import draft_source_card, ingest_images
from goodboy.jsonio import read_json
from goodboy.project import init_project
from goodboy.validation import validate_project


class CandidateSourceFidelityTests(unittest.TestCase):
    def create_project(self, root: Path) -> tuple[Path, Path]:
        project_dir = root / "pet"
        source = root / "source.png"
        image = Image.new("RGB", (480, 360), (228, 224, 214))
        draw = ImageDraw.Draw(image)
        draw.ellipse((150, 55, 330, 315), fill=(45, 42, 38))
        image.save(source)
        init_project(project_dir, pet_id="source-fidelity", display_name="Source Fidelity", species="cat")
        ingest_images(project_dir, [source], role="primary_reference")
        draft_source_card(project_dir, user_notes="preserve the individual head and body gestalt")
        analyze_reference_coverage(project_dir)
        draft_identity_profile(project_dir)
        confirm_identity_profile(project_dir)
        plan_baseline_candidates(
            project_dir=project_dir,
            provider="codex_builtin",
            model_alias="codex-imagegen",
            count=3,
            provider_consent=True,
        )
        return project_dir, source

    def generated_candidate(self, path: Path, *, canvas: tuple[int, int], subject: tuple[int, int, int, int]) -> None:
        image = Image.new("RGB", canvas, (0, 255, 0))
        ImageDraw.Draw(image).ellipse(subject, fill=(55, 48, 42))
        image.save(path)

    def test_source_fidelity_candidates_are_balanced_gestalt_and_markings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir, _source = self.create_project(Path(tmp))
            index = read_json(project_dir / "candidates" / "baseline-candidates.json")
            self.assertEqual(
                [item["variation_id"] for item in index["candidates"]],
                ["identity-balanced", "identity-gestalt", "identity-markings"],
            )
            prompt = (project_dir / "candidates" / "baseline-002" / "prompt.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("holistic head mass", prompt)
            self.assertIn("occupying 72-78% of canvas height", prompt)
            self.assertIn("Do not enlarge the eyes", prompt)

    def test_review_tiles_normalize_different_provider_framing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir, _source = self.create_project(root)
            wide = root / "wide.png"
            tall = root / "tall.png"
            self.generated_candidate(wide, canvas=(900, 500), subject=(350, 90, 550, 440))
            self.generated_candidate(tall, canvas=(500, 900), subject=(155, 230, 345, 760))
            store_candidate_image(project_dir=project_dir, candidate_id="baseline-001", image_path=wide)
            store_candidate_image(project_dir=project_dir, candidate_id="baseline-002", image_path=tall)
            for candidate_id in ("baseline-001", "baseline-002"):
                review_path = (
                    project_dir
                    / "candidates"
                    / candidate_id
                    / "generated"
                    / "review-normalized.png"
                )
                with Image.open(review_path) as review:
                    self.assertEqual(review.size, (240, 200))
                    bbox = review.getchannel("A").getbbox()
                    self.assertIsNotNone(bbox)
                    assert bbox is not None
                    self.assertEqual(bbox[3], 184)
                    self.assertLessEqual(bbox[2] - bbox[0], 208)
                    self.assertLessEqual(bbox[3] - bbox[1], 164)
            self.assertTrue(build_candidate_contact_sheet(project_dir=project_dir).is_file())

    def test_selection_blocks_marking_win_that_loses_holistic_gestalt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir, _source = self.create_project(root)
            for index in range(1, 4):
                output = root / f"candidate-{index}.png"
                self.generated_candidate(output, canvas=(512, 512), subject=(150, 70, 362, 455))
                store_candidate_image(
                    project_dir=project_dir,
                    candidate_id=f"baseline-{index:03d}",
                    image_path=output,
                )
            record_candidate_review(
                project_dir=project_dir,
                candidate_id="baseline-001",
                holistic_gestalt_score=4,
                signature_trait_score=4,
                small_size_readability_score=4,
                notes="Balanced anatomy and markings.",
                reviewed_by="test",
            )
            record_candidate_review(
                project_dir=project_dir,
                candidate_id="baseline-002",
                holistic_gestalt_score=5,
                signature_trait_score=4,
                small_size_readability_score=4,
                notes="Strongest whole-animal resemblance.",
                reviewed_by="test",
            )
            record_candidate_review(
                project_dir=project_dir,
                candidate_id="baseline-003",
                holistic_gestalt_score=3,
                signature_trait_score=5,
                small_size_readability_score=5,
                notes="Best markings but materially weaker head and body gestalt.",
                reviewed_by="test",
            )
            with self.assertRaisesRegex(ValueError, "more than one point below"):
                select_baseline_candidate(
                    project_dir=project_dir,
                    candidate_id="baseline-003",
                    notes="markings-only winner",
                )
            character = select_baseline_candidate(
                project_dir=project_dir,
                candidate_id="baseline-002",
                notes="selected on holistic and trait evidence",
            )
            self.assertEqual(character.identity_anchor_image, IDENTITY_ANCHOR)
            self.assertEqual(character.identity_anchor_candidate_id, "baseline-002")
            self.assertTrue((project_dir / IDENTITY_ANCHOR).is_file())

    def test_style_candidates_derive_from_preserved_identity_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir, _source = self.create_project(root)
            generated = root / "identity.png"
            self.generated_candidate(generated, canvas=(512, 512), subject=(150, 70, 362, 455))
            select_baseline_candidate(
                project_dir=project_dir,
                candidate_id="baseline-001",
                image_path=generated,
                notes="best source likeness",
                holistic_gestalt_score=4.5,
                signature_trait_score=4.0,
                small_size_readability_score=4.0,
                review_notes="Preserves anatomy and defining coat layout.",
                reviewed_by="test",
            )
            styles = plan_baseline_candidates(
                project_dir=project_dir,
                provider="codex_builtin",
                model_alias="codex-imagegen",
                count=2,
                evaluation_dimension="style",
            )
            self.assertEqual([item.id for item in styles], ["style-001", "style-002"])
            self.assertEqual(styles[0].source_images[0], IDENTITY_ANCHOR)
            style_prompt = (project_dir / styles[0].prompt_path).read_text(encoding="utf-8")
            self.assertIn("Change rendering treatment only", style_prompt)
            index = read_json(project_dir / "candidates" / "baseline-candidates.json")
            self.assertEqual(len(index["candidates"]), 5)
            self.assertTrue(validate_project(project_dir, write_report=False).ok)

    def test_style_selection_blocks_identity_drift_after_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir, _source = self.create_project(root)
            identity = root / "identity.png"
            self.generated_candidate(identity, canvas=(512, 512), subject=(150, 70, 362, 455))
            select_baseline_candidate(
                project_dir=project_dir,
                candidate_id="baseline-001",
                image_path=identity,
                notes="identity anchor",
                holistic_gestalt_score=4.5,
                signature_trait_score=4.5,
                small_size_readability_score=4.0,
                review_notes="Faithful anchor.",
                reviewed_by="test",
            )
            styles = plan_baseline_candidates(
                project_dir=project_dir,
                provider="codex_builtin",
                model_alias="codex-imagegen",
                count=2,
                evaluation_dimension="style",
            )
            for index, style in enumerate(styles, start=1):
                output = root / f"style-{index}.png"
                self.generated_candidate(output, canvas=(512, 512), subject=(150, 70, 362, 455))
                store_candidate_image(
                    project_dir=project_dir,
                    candidate_id=style.id,
                    image_path=output,
                )
            record_candidate_review(
                project_dir=project_dir,
                candidate_id="style-001",
                holistic_gestalt_score=2.5,
                signature_trait_score=4.5,
                small_size_readability_score=5.0,
                notes="Attractive treatment but changed the head and body gestalt.",
                reviewed_by="test",
            )
            record_candidate_review(
                project_dir=project_dir,
                candidate_id="style-002",
                holistic_gestalt_score=4.0,
                signature_trait_score=4.0,
                small_size_readability_score=4.0,
                notes="Treatment changed while identity remained stable.",
                reviewed_by="test",
            )
            with self.assertRaisesRegex(ValueError, "holistic gestalt scored below"):
                select_baseline_candidate(
                    project_dir=project_dir,
                    candidate_id="style-001",
                    notes="style-only winner",
                )
            character = select_baseline_candidate(
                project_dir=project_dir,
                candidate_id="style-002",
                notes="identity-preserving style",
            )
            self.assertEqual(character.identity_anchor_image, IDENTITY_ANCHOR)
            self.assertEqual(character.identity_anchor_candidate_id, "baseline-001")


if __name__ == "__main__":
    unittest.main()
