# Goodboy Milestones

Progress legend:

- `[ ]` not started
- `[~]` in progress
- `[x]` complete

## M0: Project Charter And Reference Import

Status: `[x]`

- `[x]` Create `/Users/adamallcock/Documents/Coding/goodboy`.
- `[x]` Copy legacy hatch-pet, Millie, and Napoleon scripts as references.
- `[x]` Add master plan, tracking, decision, and risk documents.
- `[x]` Decide initial implementation language packaging details.
- `[x]` Create first typed schema files.

## M1: Manifest And Artifact Model

Status: `[x]`

- `[x]` Define `PetProject`.
- `[x]` Define `SourceImage`.
- `[x]` Define `SourceCard`.
- `[x]` Define `CharacterCard`.
- `[x]` Define `StyleCandidate`.
- `[x]` Define `EmotionStyleSheet`.
- `[x]` Define `GenerationJob`.
- `[x]` Define `ProviderInvocation`.
- `[x]` Define `FeedbackEvent`.
- `[x]` Define `BranchManifest`.
- `[x]` Define `ManifestValidationReport`.
- `[x]` Define `QAPolicyDecision`.
- `[x]` Define `QAReport`.
- `[x]` Define `RunSummary`.
- `[x]` Add schema validation tests for the current dataclass roundtrips and pipeline invariants.

Exit criteria:

- A project can be initialized and validated without generating images.
- All paths are relative where possible and portable inside the project folder.

## M2: Ingest And Source Analysis

Status: `[x]`

- `[x]` Copy source images into project artifact store.
- `[x]` Hash and fingerprint source images.
- `[x]` Generate thumbnails.
- `[x]` Capture EXIF where available.
- `[x]` Produce a source-card draft.
- `[x]` Support manual source-card edits through JSON artifact edits and source-card refresh.
- `[x]` Add provenance report.

Exit criteria:

- A user can ingest images and get a structured description of the pet identity before generation.

## M3: Baseline Candidate Generation

Status: `[x]`

- `[x]` Plan multiple style candidates; actual image submission remains adapter-dependent.
- `[x]` Store each candidate image.
- `[x]` Store exact prompt and provider metadata.
- `[x]` Store candidate character-card deltas.
- `[x]` Produce candidate contact sheet with generated images or placeholders.
- `[x]` Let user select a canonical candidate.
- `[x]` Save selected baseline as canonical visual reference when an image is supplied.

Exit criteria:

- A selected baseline can be used repeatedly as the identity source for future rows.

## M4: Generation Adapters

Status: `[x]`

- `[x]` Define provider adapter interface.
- `[x]` Implement `codex_builtin` handoff adapter.
- `[x]` Implement `openai_images` adapter for text-to-image and image-input edit jobs.
- `[x]` Implement `gemini_nano_banana_2` adapter.
- `[x]` Implement `gemini_nano_banana_pro` adapter.
- `[x]` Normalize output capture for OpenAI text-to-image and image-input edit jobs.
- `[x]` Add adapter capability registry.
- `[x]` Add provider-level retry and failure reporting through planned job metadata.

Exit criteria:

- Goodboy can run the same generation plan through at least two provider adapters.

## M5: Emotion Style Sheet And Row Planning

Status: `[x]`

- `[x]` Define default Codex pet state sheet.
- `[x]` Define frame counts and row prompts per state.
- `[x]` Define state-level avoid rules.
- `[x]` Support user style overrides.
- `[x]` Support AI critique overrides.
- `[x]` Support human feedback forks.
- `[x]` Generate row job manifests.

Exit criteria:

- A selected baseline can produce a full set of row-generation jobs with consistent identity rules.

## M6: Deterministic Raster Pipeline

Status: `[x]`

- `[x]` Generalize chroma-key cleanup from legacy scripts.
- `[x]` Generalize component extraction.
- `[x]` Generalize centering and baseline policies.
- `[x]` Add state-specific anchor policies and idle stabilization.
- `[x]` Write `frames/centering-report.json`.
- `[x]` Compose Codex atlas.
- `[x]` Validate atlas contract.
- `[x]` Generate contact sheet.
- `[x]` Generate animation previews.

Exit criteria:

- Existing Millie/Napoleon row strips can be rebuilt through Goodboy with matching or better QA metrics.

## M7: QA Engine

Status: `[x]`

- `[x]` Transparent RGB residue check.
- `[x]` Green-edge metric.
- `[x]` Edge clipping check.
- `[x]` Horizontal and vertical drift measurement.
- `[x]` State-specific vertical drift thresholds.
- `[x]` Centering overlay and copied QA centering report.
- `[x]` Duplicate and near-duplicate audit.
- `[x]` Component count sanity check.
- `[x]` State-specific motion sanity checks.
- `[x]` QA severity and fail/pass policy.
- `[x]` Human visual review checklist.
- `[x]` Record human visual approval as a run artifact.
- `[x]` Block install when suspicious local renderer scripts are present.

Exit criteria:

- Bad sheets fail before installation.
- QA reports explain exactly what to fix.

## M8: Installer And Exporters

Status: `[x]`

- `[x]` Generate `pet.json`.
- `[x]` Install to `~/.codex/pets/<id>`.
- `[x]` Create archive snapshots before overwrites.
- `[x]` Split final installation into review, approval, and install commands.
- `[x]` Export project package.
- `[x]` Export Petdex-ready folder or zip.
- `[x]` Validate installed package through atlas/package generation tests and an installed-target smoke check.

Exit criteria:

- A validated pet can be installed and archived safely.

## M9: Codex Integration

Status: `[x]`

- `[x]` Create Goodboy Codex skill wrapper draft under `codex-skill/goodboy`.
- `[x]` Install Goodboy Codex skill wrapper to `/Users/adamallcock/.codex/skills/goodboy`.
- `[x]` Validate repo and installed skill wrappers with the official skill validator.
- `[x]` Define Codex commands and prompts.
- `[x]` Support Codex built-in image generation handoff through existing manifests.
- `[x]` Preserve generated output paths through candidate/job/provider manifests.
- `[x]` Add Agent Rail commands: `make`, `next`, `approve`, `review-status`, and `install`.
- `[x]` Add Agent Rail v2 commands: `doctor`, `generate-handoff`, `import-generated`, `build-review`, and `finish`.
- `[x]` Add Agent Rail v3 fast-pass commands: `start` and `advance`.
- `[x]` Render candidate sheets by default when baselines are planned.
- `[x]` Report OpenAI/Gemini API keys as optional accelerators.
- `[x]` Add executable `next --agent-mode` fields and planning idempotence.
- `[x]` Persist `workflow-state.json` so agents can follow the next safe action instead of guessing.
- `[x]` Add Codex plugin feasibility spike.
- `[x]` If viable, define plugin commands/UI flow.
- `[x]` Add repo-scoped Codex plugin package under `plugins/goodboy`.
- `[x]` Add repo marketplace at `.agents/plugins/marketplace.json`.
- `[x]` Consider bundled Goodboy MCP tools after the plugin package proves useful; deferred until plugin usage proves the added surface is worthwhile.
- `[x]` Consider a richer visual review UI through a local web UI or future app surface; deferred to M10.

Exit criteria:

- A Codex user can run Goodboy end-to-end with guided review points.

## M10: Local Web UI

Status: `[~]`

- `[x]` Create comprehensive UI functional and technical requirements.
- `[x]` Scan off-the-shelf component options and define initial design directions.
- `[x]` Choose Review Room as the primary M10 design direction.
- `[x]` Create complete Review Room implementation plan.
- `[ ]` Candidate browser.
- `[ ]` Source-image comparison view.
- `[ ]` Baseline selection view.
- `[ ]` Row and contact-sheet review view.
- `[ ]` Animation preview view.
- `[ ]` QA report view.
- `[ ]` Feedback/fork controls.

Exit criteria:

- The visually heavy parts of the workflow are easier than inspecting files manually.
- UI implementation and verification evidence are linked from this tracker.

## M11: Documentation And Examples

Status: `[x]`

- `[x]` Create quickstart.
- `[x]` Create architecture docs.
- `[x]` Create adapter docs.
- `[x]` Create QA docs.
- `[x]` Create portable synthetic fixture and keep Millie/Napoleon references.
- `[x]` Create troubleshooting guide.

Exit criteria:

- A new user can understand the system without reading the source code.
