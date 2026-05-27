# Legacy Pipeline References

This folder contains copied reference scripts and documentation from the Millie, Napoleon, and hatch-pet work. They are intentionally preserved as design evidence and implementation seed material.

These files should not be treated as a final Goodboy architecture. They represent the proven one-off mechanics that Goodboy will generalize.

## Copied Scripts

- `extract_strip_frames.py` - hatch-pet frame extractor with tighter chroma-key/despill behavior.
- `compose_atlas.py` - Codex pet atlas composer.
- `validate_atlas.py` - Codex pet atlas validator.
- `make_contact_sheet.py` - contact sheet generator.
- `render_animation_previews.py` - GIF preview renderer.
- `napoleon_centered_row_builder.py` - Napoleon-specific row-strip builder with component centering and green-edge trim.
- `millie_green_trim_row_builder.py` - Millie-specific row-strip builder with green-edge trim.

## Copied Reference Docs

- `references/napoleon_README.md`
- `references/millie_README.md`

## Lessons To Carry Forward

- Generated row strips can work well, but equal source-slot placement is not reliable enough by itself.
- Chroma-key cleanup needs both alpha extraction and RGB despill.
- Wispy fur makes green halos very visible on white backgrounds, so white edge previews are a required QA artifact.
- Animation drift is measurable and should be a hard QA gate.
- A pet is not complete until the install package, validation, contact sheet, previews, run summary, and rebuild notes all agree.

