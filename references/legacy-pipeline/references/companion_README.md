# Legacy Companion Reference

This file summarizes the first one-off companion-pet build that informed Goodboy.

The original build proved that row-specific image generation can produce a charming Codex pet, but also showed why a reusable system needs durable manifests, provenance, visual approvals, edge cleanup, duplicate checks, and package validation.

Public notes are intentionally generic. Private source photos, generated project folders, and installed packages are not tracked in this repository.

## Lessons Preserved

- Generate each Codex state row separately instead of reusing a small pose set too heavily.
- Preserve the approved creative row strips as the source of truth.
- Use chroma-key removal plus despill, not only alpha thresholding.
- Always inspect a white-background edge preview before install.
- Keep final `pet.json`, `spritesheet.webp`, validation, contact sheet, previews, QA reports, and rebuild notes together.

## Relevant Reference Script

```text
references/legacy-pipeline/companion_chroma_trim_row_builder.py
```

The modern Goodboy implementation generalizes this into `src/goodboy/raster.py`, `src/goodboy/qa.py`, and the higher-level `build-review` workflow.
