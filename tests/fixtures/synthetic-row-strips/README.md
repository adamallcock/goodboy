# Synthetic Row Strips Fixture

Small deterministic chroma-key row strips used by the regression tests.

These are intentionally simple generated pet-like sprites. They exercise the
Goodboy raster pipeline, atlas composer, QA policy, and manifest validator
without depending on local private pet project assets.

The three `look-*` files exercise the v2 cardinal-anchor and 16-direction
assembly path. Regenerate them with:

```bash
python scripts/generate_v2_test_fixtures.py
```

They are geometric fixtures only. Goodboy never uses them as generated pet art.
