# Legacy Centering Reference

This file summarizes the second one-off pet build that informed Goodboy’s centering and QA policies.

The original run exposed two important failure modes: chroma residue around wispy fur and animation drift caused by inconsistent extraction/cropping across frames. Goodboy preserves those lessons in a generic, reusable pipeline instead of keeping the old private project as the operating source of truth.

Public notes are intentionally generic. Private source photos, generated project folders, and installed packages are not tracked in this repository.

## Lessons Preserved

- Component-based extraction can reduce animation drift when generated rows are not evenly spaced.
- State-specific vertical baselines matter; running, jumping, idle, waiting, review, and failure poses should not share one naive anchor.
- Idle needs stricter drift thresholds because it plays continuously.
- Edge cleanup must be inspected on white because chroma residue can look acceptable on transparent or dark backgrounds.
- Running frames need explicit clipping checks; a row can validate dimensionally while still losing a tail, paw, ear, or prop.

## Relevant Reference Script

```text
references/legacy-pipeline/legacy_centered_row_builder.py
```

The modern Goodboy implementation generalizes this into chroma-key selection, layout guides, `stable-slots` extraction, centering overlays, drift reports, and install-blocking QA.
