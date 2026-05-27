# Millie Codex Pet

This folder is the reference archive for Millie, a custom Codex digital pet based on a tiny friendly white Maltese dog with a teal bandana.

The final package was built from row-specific generated animation strips. Earlier versions reused a smaller set of poses too heavily; the final v5 pass generated each Codex animation row separately, then split those rows into individual frames and composed the required Codex atlas. The current installed build is `v5-green-trim`, regenerated from the same v5 rows with tighter green-screen edge cleanup.

## Final Installed Pet

The installed Codex pet package is:

```text
~/.codex/pets/millie
```

It contains:

```text
pet.json
spritesheet.webp
```

To use it in Codex:

1. Restart Codex if it was already open.
2. Open Codex Settings.
3. Go to Appearance / Pets.
4. Select Millie.
5. Use `/pet` to wake her.

## Key Artifacts

- `package/` - copy of the installed Codex pet package.
- `final/spritesheet.webp` - final Codex-compatible spritesheet.
- `final/spritesheet.png` - PNG version of the final atlas for inspection.
- `final/validation.json` - hatch-pet atlas validation output.
- `qa/contact-sheet.png` - final visual contact sheet.
- `qa/previews/` - animated GIF previews for each Codex state.
- `qa/review.json` - frame inspection output.
- `qa/run-summary.json` - machine-readable summary of the current final pass.
- `qa/duplicate-audit-v5-green-trim.json` - duplicate, frame-count, and green-edge audit for the final sheet.
- `qa/edge-preview-white-v5-green-trim.png` - white-background preview for checking residual green halos.
- `generated/v5-row-strips/` - final generated source rows, before frame slicing.
- `generated/v5-transparent-strips/` - v5 source rows after green-screen removal.
- `frames/` - final per-state extracted frames used to compose the atlas.
- `source-images/` - original reference photo and canonical generated base image.
- `backups/` - earlier spritesheet/contact-sheet iterations for rollback and comparison.
- `backups/20260525-120016-before-green-trim/` - installed/package snapshot before the tighter green-edge cleanup.
- `scripts/` - local scripts used to build frames and atlas inputs.
- `prompts/` - hatch-pet prompts generated during the original run.
- `2026-05-24-millie-pet-project-plan.md` - project plan, intentions, and decision notes.

## Final State Contract

The final spritesheet follows the Codex pet contract:

- Atlas size: `1536x1872`
- Cell size: `192x208`
- Columns: `8`
- Rows: `9`
- States: `idle`, `running-right`, `running-left`, `waving`, `jumping`, `failed`, `waiting`, `running`, `review`

Final validation passed with no errors and no warnings. The final green-trim pass reuses the approved v5 source rows and only changes matte cleanup around the dog edges.

## Iteration Notes

- `v5` remains the creative source of truth for Millie.
- `v5-green-trim` was rebuilt from the same v5 rows after the shared green-screen cleanup was tightened for Napoleon.
- The shared hatch-pet extractor at `~/.codex/skills/hatch-pet/scripts/extract_strip_frames.py` was also updated with the tighter chroma-key/despill behavior for future pet runs.

## Rebuild Notes

The final v5 source rows are the important creative source. To rebuild from them, run the row-strip builder with:

```bash
MILLIE_ROW_STRIP_VERSION=v5 python3 scripts/build_millie_frames_from_row_strips.py
```

Then compose, validate, and regenerate QA media with the hatch-pet scripts:

```bash
python ~/.codex/skills/hatch-pet/scripts/compose_atlas.py \
  --frames-root frames \
  --output final/spritesheet.png \
  --webp-output final/spritesheet.webp

python ~/.codex/skills/hatch-pet/scripts/validate_atlas.py \
  final/spritesheet.webp \
  --json-out final/validation.json

python ~/.codex/skills/hatch-pet/scripts/make_contact_sheet.py \
  final/spritesheet.webp \
  --output qa/contact-sheet.png

python ~/.codex/skills/hatch-pet/scripts/render_animation_previews.py \
  --frames-root frames \
  --output-dir qa/previews
```
