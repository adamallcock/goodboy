# Napoleon Codex Pet

This folder is the reference archive for Napoleon, a custom Codex digital pet based on the source photos in `source-images/`.

Napoleon is a senior white Maltese-style dog, age 17, with shaggy wispy off-white fur, a slightly longer snout than Millie, round dark senior eyes, a dark brown-black nose with softer/faded pigmentation, soft droopy ears, a curled fluffy tail, a red-and-black plaid bandana, and a small blue charm. The final `v7-happier-green-trim-centered` pass uses the selected bottom-left concept as the base identity, gives him the warmest expression set, uses tighter green-screen cleanup around the fur edges, and centers each extracted dog component to prevent animation drift.

## Final Installed Pet

The installed Codex pet package is:

```text
~/.codex/pets/napoleon
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
4. Select Napoleon.
5. Use `/pet` to wake him.

## Key Artifacts

- `package/` - copy of the installed Codex pet package.
- `final/spritesheet.webp` - final Codex-compatible spritesheet.
- `final/spritesheet.png` - PNG version of the final atlas for inspection.
- `final/validation.json` - hatch-pet atlas validation output.
- `qa/contact-sheet.png` - final visual contact sheet.
- `qa/previews/` - animated GIF previews for each Codex state.
- `qa/review.json` - frame inspection output.
- `qa/run-summary.json` - machine-readable summary of the current final pass.
- `generated/concepts/napoleon-selected-bottom-left-base.png` - selected base identity.
- `generated/v7-happier-row-strips/` - final generated source rows, before frame slicing.
- `generated/v7-happier-transparent-strips/` - final source rows after green-screen removal.
- `qa/duplicate-audit-v7-happier-green-trim-centered.json` - duplicate, frame-count, drift, and green-edge audit for the final sheet.
- `qa/edge-preview-white-v7-happier-green-trim-centered.png` - white-background preview for checking residual green halos.
- `frames/` - final per-state extracted frames used to compose the atlas.
- `source-images/` - original Napoleon reference photos and local preview JPEGs.
- `scripts/` - local script used to build frames and atlas inputs.
- `archive/20260525-115145-before-green-trim/` - package snapshot before the tighter green-edge cleanup.
- `archive/20260525-122829-before-centering-fix/` - package snapshot before the centered-frame rebuild.
- `2026-05-24-napoleon-pet-project-plan.md` - project plan, intentions, and decision notes.

## Final State Contract

The final spritesheet follows the Codex pet contract:

- Atlas size: `1536x1872`
- Cell size: `192x208`
- Columns: `8`
- Rows: `9`
- States: `idle`, `running-right`, `running-left`, `waving`, `jumping`, `failed`, `waiting`, `running`, `review`

Final validation passed with no errors and no warnings. Duplicate audit also found no exact or near-duplicate frames in any row. The final centered pass reduced horizontal drift to about half a pixel per row while preserving the wispy-fur silhouette, and every frame has at least 12px of edge clearance.

## Iteration Notes

- `v7-happier` generated a warmer expression set from the selected bottom-left Napoleon concept.
- `v7-happier-green-trim` rebuilt the same rows with tighter chroma-key cleanup to reduce green halos around wispy fur.
- `v7-happier-green-trim-centered` rebuilt again with component-based extraction and state-specific vertical baselines so Napoleon stays centered during loops and running frames are not cut off.
- The shared hatch-pet extractor at `~/.codex/skills/hatch-pet/scripts/extract_strip_frames.py` was also updated with the tighter chroma-key/despill behavior for future pet runs.

## Rebuild Notes

The final source rows are in `generated/v7-happier-row-strips/`. To rebuild frames from those rows:

```bash
NAPOLEON_ROW_STRIP_VERSION=v7-happier python3 scripts/build_napoleon_frames_from_row_strips.py
```

Then compose and validate with the hatch-pet scripts:

```bash
python ~/.codex/skills/hatch-pet/scripts/compose_atlas.py \
  --frames-root frames \
  --output final/spritesheet.png \
  --webp-output final/spritesheet.webp

python ~/.codex/skills/hatch-pet/scripts/validate_atlas.py \
  final/spritesheet.webp \
  --json-out final/validation.json
```

Regenerate QA media after composing:

```bash
python ~/.codex/skills/hatch-pet/scripts/make_contact_sheet.py \
  final/spritesheet.webp \
  --output qa/contact-sheet.png

python ~/.codex/skills/hatch-pet/scripts/render_animation_previews.py \
  --frames-root frames \
  --output-dir qa/previews
```
