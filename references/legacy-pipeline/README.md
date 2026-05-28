# Legacy Pipeline References

This folder contains copied reference scripts and documentation from earlier one-off pet builds and the hatch-pet workflow. They are intentionally preserved as design evidence and implementation seed material.

These files should not be treated as a final Goodboy architecture. They represent the proven one-off mechanics that Goodboy will generalize.

## Copied Scripts

- `extract_strip_frames.py` - hatch-pet frame extractor with tighter chroma-key/despill behavior.
- `compose_atlas.py` - Codex pet atlas composer.
- `validate_atlas.py` - Codex pet atlas validator.
- `make_contact_sheet.py` - contact sheet generator.
- `render_animation_previews.py` - GIF preview renderer.
- `legacy_centered_row_builder.py` - row-strip builder that demonstrated component centering and chroma-edge trim.
- `companion_chroma_trim_row_builder.py` - row-strip builder that demonstrated tighter chroma-edge trim.

## Copied Reference Docs

- `references/centered_legacy_README.md`
- `references/companion_README.md`

## Lessons To Carry Forward

- Generated row strips can work well, but equal source-slot placement is not reliable enough by itself.
- Chroma-key cleanup needs both alpha extraction and RGB despill.
- Wispy fur makes chroma halos very visible on white backgrounds, so white edge previews are a required QA artifact.
- Animation drift is measurable and should be a hard QA gate.
- A pet is not complete until the install package, validation, contact sheet, previews, run summary, and rebuild notes all agree.
