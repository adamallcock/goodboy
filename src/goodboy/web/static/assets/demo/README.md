# Demo Assets

The `companion/` folder contains a generic completed legacy v1 pet example used by the Review Room demo.

These assets are included so the UI can be explored without source photos, provider credentials, generated images, or a local Goodboy project. They are display fixtures for the app, not training data and not a required input for new projects.

Asset notes:

- The demo is intentionally labeled generically as "Companion Demo" in public UI and tests.
- The source, baseline, row, and QA preview assets are optimized WebP derivatives to keep the package small.
- `spritesheet.webp` keeps the full 8x9 v1 Codex pet atlas dimensions so the animated state viewer can exercise backward-compatible contract handling. Real v2 projects expose the two additional direction rows and their review gates.
- These demo assets are covered by the repository license unless a future asset-specific notice says otherwise.
