# Goodboy Master Plan

For practical command-by-command usage, start with `docs/2026-05-26-goodboy-user-guide.md`. This document remains the architecture and product plan.

## 1. Purpose

Goodboy is a repeatable, provider-agnostic system for creating lifelike animated Codex pets from pet reference images.

It should transform an ad hoc, high-touch workflow into a systematic production pipeline:

1. Ingest pet source images.
2. Analyze and describe the pet identity.
3. Generate multiple baseline style candidates.
4. Preserve prompt, provider, and character-card provenance for every candidate.
5. Let the user choose a canonical baseline.
6. Optionally run visual critique against source images.
7. Accept human feedback and AI feedback as explicit branches.
8. Generate Codex pet animation rows from a standard emotion/state style sheet.
9. Apply deterministic alpha cleanup, frame extraction, centering, and atlas composition.
10. Run automatic QA gates.
11. Produce installable Codex pet materials.
12. Preserve enough artifacts to rebuild, explain, debug, submit, or publish the pet later.

The name Goodboy is intentionally warm. The product should feel like a careful studio assistant for making tiny companions, not like a brittle file converter.

## 2. Ethos

### Joyful But Exact

The output is playful, but the process should be rigorous. A pet can be cute and still have a proper run manifest, validation report, and rollback archive.

### Human Choice Is A First-Class Artifact

When a user chooses between baseline variants, gives feedback, or rejects a row, Goodboy should record that decision. The selected personality is not just a generated PNG; it is an authored character direction.

### Provider-Neutral, Artifact-Strict

Image providers can change. Goodboy should isolate provider-specific behavior behind adapters and normalize everything into stable local artifacts.

### Determinism After Generation

Generation is probabilistic. Everything after selected image output should be deterministic, auditable, and reproducible:

- alpha cleanup
- frame extraction
- centering
- atlas layout
- validation
- packaging

### No Hidden State

No critical state should live only in chat history, timestamps, or a person’s memory. Every meaningful prompt, selection, critique, metric, and output path should be stored.

### Make Failure Legible

If a pet fails QA, Goodboy should say why in concrete terms:

- frame 3 in `running-right` is clipped on the right edge
- `idle` has 4 near-duplicate pairs
- `review` has 22px horizontal drift
- transparent pixels contain nonzero RGB residue
- white-edge preview shows green halo above threshold

### Gentle Defaults, Deep Overrides

The default style sheet should produce happy, entertaining Codex pets. Advanced users should be able to override state prompts, frame counts, style, provider, QA thresholds, and package metadata.

## 3. Scope

### In Scope

- Local project creation.
- Source image ingestion.
- Source image metadata and thumbnails.
- LLM or vision-model source analysis.
- Baseline image candidate generation.
- Candidate selection and feedback.
- Character-card preservation.
- Emotion/style sheet generation.
- Codex state row generation.
- Multiple image generation adapters.
- Chroma-key and transparent-background processing.
- Frame extraction and centering.
- Atlas composition.
- QA gates and reports.
- Installable Codex package creation.
- Archive and rollback.
- Petdex-ready export.
- Codex skill wrapper.
- Codex plugin feasibility and repo-scoped plugin package.
- Optional local web UI.

### Out Of Scope For MVP

- Training or fine-tuning image models.
- Real-time animation playback inside Goodboy itself beyond previews.
- Marketplace hosting.
- Automatic public publishing without user review.
- Guaranteeing exact image regeneration when providers do not expose deterministic seeds.

## 4. External References

OpenAI currently documents image generation through the Image API for standalone generation/edit endpoints and through the Responses API image generation tool for conversational, multi-turn flows. Goodboy should treat the OpenAI Images API adapter as a direct API adapter and Codex built-in image generation as a Codex-context adapter. The current default OpenAI alias is `gpt-image-2`, but the adapter must keep model, endpoint, size, quality, format, and background configurable. See OpenAI image generation docs: https://platform.openai.com/docs/guides/image-generation

Google documents Nano Banana as Gemini native image generation. The current Goodboy defaults are `gemini-3.1-flash-image-preview` for the Nano Banana 2 adapter and `gemini-3-pro-image-preview` for the Nano Banana Pro adapter. Goodboy should keep these behind configurable model aliases so changes are easy to absorb. See Gemini image generation docs: https://ai.google.dev/gemini-api/docs/image-generation

Petdex is a valuable ecosystem target for discovery and installation, but it does not appear to be the creation pipeline itself. Goodboy should produce Petdex-ready packages rather than depending on Petdex to generate them.

## 5. System Principles

### 5.1 Manifest-First

Every project has structured manifests:

- project identity
- source images
- source analysis
- baseline candidates
- selected baseline
- character card
- emotion style sheet
- generation jobs
- provider invocations
- deterministic processing settings
- QA reports
- install/export records

### 5.2 Immutable Raw Inputs

Source images and raw generated outputs are immutable once imported. Edits and conversions create derived artifacts.

### 5.3 Branches Are Explicit

Human feedback and AI feedback can fork the run. A fork must name its parent and reason:

- `human-feedback-snouter-face`
- `vision-critic-closer-fur-color`
- `provider-comparison-openai`
- `provider-comparison-nano-banana-pro`

### 5.4 Selected Baseline Is The Canonical Identity

The selected baseline image should be attached to row-generation jobs as the canonical visual reference wherever the provider supports image input. The character card is the semantic identity; the selected baseline is the visual identity.

### 5.5 QA Before Install

Goodboy should not install a pet if required QA gates fail, unless the user explicitly overrides with a reason that is written into the install manifest.

### 5.6 Archive Before Overwrite

Any install or package overwrite should create an archive snapshot first.

## 6. User Workflow

### 6.1 Happy Path

1. User creates a Goodboy project.
2. User adds source images.
3. Goodboy ingests and analyzes source images.
4. Goodboy creates a source-card draft.
5. User edits or approves source card.
6. Goodboy generates baseline candidates.
7. Goodboy records candidate prompts and character-card deltas.
8. User selects a baseline.
9. Optional AI visual critic compares source images to selected baseline.
10. User accepts or forks suggested adjustments.
11. Goodboy creates an emotion style sheet.
12. User accepts or overrides the style sheet.
13. Goodboy generates row strips.
14. Goodboy processes row strips into frames.
15. Goodboy composes atlas.
16. Goodboy runs QA.
17. User reviews contact sheet, edge preview, and animation previews.
18. Goodboy installs Codex pet.
19. Goodboy writes final run summary.
20. Optional export to Petdex package.

### 6.2 Feedback Path

Feedback can happen at:

- source analysis stage
- baseline candidate stage
- selected baseline stage
- row generation stage
- deterministic assembly stage
- QA stage

Feedback must be attached to a branch and should not mutate the previous accepted artifact in place.

Examples:

```text
goodboy feedback baseline-03 "Make her look older, with softer eyes and less puppy-like proportions."
goodboy feedback row:waiting "Too sad; make this expectant and cheerful."
goodboy feedback qa:green-edge "Trim more aggressively around the ears."
```

## 7. Data Model

### 7.1 PetProject

Fields:

- `id`
- `display_name`
- `species`
- `created_at`
- `updated_at`
- `workspace_version`
- `output_contract`
- `active_run_id`
- `install_targets`

### 7.2 SourceImage

Fields:

- `id`
- `path`
- `sha256`
- `original_filename`
- `mime_type`
- `width`
- `height`
- `exif`
- `role`
- `notes`
- `thumbnail_path`

Roles:

- `primary_reference`
- `face_reference`
- `body_reference`
- `markings_reference`
- `personality_reference`
- `style_reference`

### 7.3 SourceCard

Fields:

- `species`
- `breed_or_type`
- `age_traits`
- `size_traits`
- `face_traits`
- `eyes`
- `nose`
- `ears`
- `fur`
- `tail`
- `markings`
- `props`
- `colors`
- `personality`
- `must_keep`
- `avoid`
- `uncertainties`
- `source_image_links`

### 7.4 CharacterCard

The character card is the reusable semantic contract for the pet after baseline selection.

Fields:

- `canonical_name`
- `one_sentence_identity`
- `stable_traits`
- `style`
- `material`
- `proportions`
- `facial_expression_range`
- `palette`
- `props`
- `animation_personality`
- `do_not_change`
- `provider_notes`
- `selected_baseline_image`

### 7.5 StyleCandidate

Fields:

- `id`
- `image_path`
- `prompt_path`
- `provider`
- `model`
- `provider_invocation_id`
- `source_images`
- `style_summary`
- `character_delta`
- `strengths`
- `risks`
- `selected`
- `selection_notes`
- `selected_at`

### 7.6 EmotionStyleSheet

Fields:

- `id`
- `base_mood`
- `state_specs`
- `global_avoid`
- `prop_policy`
- `effects_policy`
- `background_policy`
- `centering_policy`
- `qa_thresholds`

### 7.7 StateSpec

Fields:

- `state`
- `frame_count`
- `purpose`
- `mood`
- `allowed_motion`
- `forbidden_motion`
- `prompt_notes`
- `layout_notes`
- `centering_policy`
- `baseline_policy`
- `qa_overrides`

### 7.8 GenerationJob

Fields:

- `id`
- `kind`
- `state`
- `status`
- `provider`
- `model_alias`
- `prompt_path`
- `input_images`
- `expected_output`
- `retry_policy`
- `selected_output_path`
- `provider_invocation_id`
- `qa_notes`

### 7.9 ProviderInvocation

Fields:

- `id`
- `adapter`
- `model`
- `request_metadata`
- `prompt_hash`
- `input_image_hashes`
- `output_paths`
- `started_at`
- `finished_at`
- `status`
- `error`
- `cost_estimate`
- `raw_response_path`

No API keys may be written here.

### 7.10 QAReport

Fields:

- `ok`
- `errors`
- `warnings`
- `atlas_contract`
- `transparent_rgb_residue`
- `green_edge_pixels`
- `frame_counts`
- `edge_clearance`
- `drift`
- `duplicate_pairs`
- `component_counts`
- `visual_review`
- `override_reason`

## 8. Artifact Layout

Recommended project layout:

```text
<project>/
  goodboy.json
  README.md
  sources/
    originals/
    thumbnails/
    source-images.json
    source-card.json
  candidates/
    baseline-candidates.json
    contact-sheet.png
    baseline-001/
      prompt.md
      image.png
      candidate.json
    baseline-002/
  character/
    character-card.json
    selected-candidate.json
    selected-baseline.png
  style/
    emotion-style-sheet.json
  runs/
    <run-id>/
      generation-jobs.json
      provider-invocations/
      decoded/
      row-strips/
      transparent-strips/
      frames/
      final/
      qa/
      package/
      run-summary.json
  archives/
  exports/
```

## 9. Default Codex Pet Contract

Goodboy targets the Codex pet contract:

- cell width: `192`
- cell height: `208`
- columns: `8`
- rows: `9`
- atlas width: `1536`
- atlas height: `1872`
- output: `spritesheet.webp`
- metadata: `pet.json`

Default state order:

1. `idle`
2. `running-right`
3. `running-left`
4. `waving`
5. `jumping`
6. `failed`
7. `waiting`
8. `running`
9. `review`

Default frame counts:

```json
{
  "idle": 6,
  "running-right": 8,
  "running-left": 8,
  "waving": 4,
  "jumping": 5,
  "failed": 8,
  "waiting": 6,
  "running": 6,
  "review": 6
}
```

## 10. Default Emotion Style Sheet

The default pet should be generally happy, warm, entertaining, and unobtrusive.

### idle

Calm breathing, tiny blink, subtle head or tail motion. No large gestures.

### running-right

Directional drag movement facing right. Use body and limb posture only. No speed lines or shadows.

### running-left

Directional drag movement facing left. Same identity and cadence as running-right.

### waving

Friendly greeting through a paw or limb. No wave marks, sparkles, punctuation, or motion arcs.

### jumping

Happy hop through vertical body position. No floor, shadow, dust, or impact marks.

### failed

Disappointed but still adorable. Avoid red X marks, detached tears, smoke, symbols, or props.

### waiting

Expectant asking pose: bright eyes, paw raise, head tilt, patient stance.

### running

Active task work, thinking, processing, or focused helper energy. Not literal directional running.

### review

Focused inspection through lean, head tilt, blink, nose-down look, or pleased look-up. No extra props unless part of the pet identity.

## 11. Generation Adapters

### 11.1 Adapter Interface

Each adapter should implement:

```text
prepare(job, project) -> PreparedRequest
submit(prepared_request) -> ProviderInvocation
collect(provider_invocation) -> GeneratedOutputs
normalize(generated_outputs) -> GoodboyArtifact[]
```

All adapters must return local artifact paths and structured metadata.

### 11.2 Codex Built-In Adapter

Adapter id:

```text
codex_builtin
```

This adapter is only available inside a Codex conversation or skill context. It cannot be treated like a normal standalone API call.

Expected behavior:

- write prompt files and job manifests
- ask Codex/imagegen to generate one visual job at a time
- copy selected output from Codex generated image storage into the project
- record selected path and QA note
- resume from manifest status

### 11.3 OpenAI Images API Adapter

Adapter id:

```text
openai_images
```

Expected behavior:

- use OpenAI image generation/edit APIs
- support candidate generation
- support row-strip generation
- support image reference inputs where model/API supports them
- store model, quality, size, output format, and moderation settings
- never store `OPENAI_API_KEY`

Default model alias should be configurable. As of the checked docs, OpenAI describes GPT Image generation through the Image API and Responses API image generation tool; implementation should verify the chosen model and endpoint at build time.

### 11.4 Gemini Nano Banana 2 Adapter

Adapter id:

```text
gemini_nano_banana_2
```

Default model alias:

```text
gemini-3.1-flash-image-preview
```

Expected behavior:

- high-volume candidate and row-strip generation
- fast iteration
- configurable aspect ratio and image size
- use source images as multimodal inputs where supported
- record SynthID/provider metadata where exposed
- never store `GEMINI_API_KEY`

### 11.5 Gemini Nano Banana Pro Adapter

Adapter id:

```text
gemini_nano_banana_pro
```

Default model alias:

```text
gemini-3-pro-image-preview
```

Expected behavior:

- high-fidelity baseline candidates
- complex instruction following
- identity-preserving row generation
- production-quality visual variants
- configurable aspect ratio and image size

### 11.6 Adapter Capability Registry

Goodboy should track provider capabilities:

- text-to-image
- image-to-image
- multi-image input
- edit existing image
- transparent background
- seed support
- aspect ratio support
- output resolution support
- batch support
- cost metadata
- raw response storage

The pipeline should select prompts and fallback strategy based on capabilities.

## 12. Visual Critique

Goodboy may use a strong visual intake model, such as Gemini Flash/Pro-class vision, to compare:

- source images vs baseline candidates
- selected baseline vs generated rows
- contact sheet vs style sheet
- edge preview vs green-halo thresholds

Visual critique outputs should be structured:

```json
{
  "ok": true,
  "identity_match": 0.82,
  "style_match": 0.91,
  "concerns": [],
  "suggested_prompt_changes": [],
  "fork_recommended": false
}
```

AI critique should not silently overwrite human choice. It creates suggestions or branches.

## 13. Feedback And Forking

Goodboy should treat feedback as an event:

```json
{
  "id": "feedback-001",
  "author": "human",
  "target": "baseline-003",
  "text": "Make the snout longer and the eyes older.",
  "created_at": "...",
  "creates_branch": "human-feedback-longer-snout"
}
```

AI feedback follows the same structure with `author: "vision_critic"`.

## 14. Deterministic Raster Pipeline

Pipeline stages:

1. Normalize generated source image.
2. Remove chroma key or process alpha.
3. Despill RGB edge pixels.
4. Trim low-alpha matte fringe.
5. Extract components or equal slots.
6. Keep main subject component.
7. Apply state-specific centering.
8. Apply state-specific vertical baseline.
9. Save frames.
10. Compose atlas.
11. Validate atlas.

The legacy Napoleon centered builder proved the need for component-based extraction and state-specific baselines.

## 15. QA Gates

Required hard gates:

- atlas dimensions exactly match the contract
- transparent pixels have no RGB residue
- required frame counts are present
- no unexpected visible pixels in unused cells
- edge clearance above threshold
- no severe horizontal drift
- no exact duplicate frames
- no near-duplicate frames beyond state-specific tolerance
- no missing primary component
- no generated text, visible frame boxes, or obvious guide marks

Recommended soft gates:

- green-edge pixel threshold
- visual critic identity score
- visual critic style score
- row motion readability
- contact sheet human approval
- white-background edge preview human approval

## 16. Codex Integration

### 16.1 Codex Skill

The first Codex integration should be a skill that wraps the CLI and provides guided interactive generation.

Responsibilities:

- create project
- ingest references
- run source analysis
- produce candidate generation jobs
- use Codex built-in image generation when selected
- copy generated outputs into the project
- run deterministic build and QA
- install package
- summarize artifacts

### 16.2 Codex Plugin

Goodboy now ships a first Codex plugin slice after the CLI and skill became stable. The plugin is intentionally narrow: it packages the Goodboy skill and install-surface metadata, then exposes it through a repo marketplace. Rich visual review remains in Goodboy artifacts for now.

Potential plugin value:

- expose Goodboy commands directly in Codex
- provide a more persistent project-aware workflow
- manage provider credentials through approved Codex mechanisms
- integrate candidate selection and QA review into a richer flow if the plugin surface supports it

Plugin feasibility questions:

- Can the plugin present image grids or only textual command output?
- Can it call built-in image generation directly, or must it still rely on skill/chat context?
- Can it manage local files safely?
- Can it install into `~/.codex/pets` with user approval?
- Can it maintain resumable job state?

Decision summary:

- Feasible now: a repo-scoped plugin that bundles the Goodboy skill and steers agents through the CLI rails.
- Implemented now: `plugins/goodboy/.codex-plugin/plugin.json`, `plugins/goodboy/skills/goodboy/SKILL.md`, and `.agents/plugins/marketplace.json`.
- Deferred: MCP tools, hooks, app/connectors, and richer visual review.

If the plugin surface is not visually rich enough, Goodboy should use a local web UI for candidate selection and keep the Codex plugin focused on orchestration.

## 17. CLI Shape

Current and planned commands:

```bash
goodboy init <project-dir> --pet-id <id> --display-name <name>
goodboy start <project-dir> --pet-id <id> --display-name <name> --source path/to/image.png
goodboy advance <project-dir> --agent-mode
goodboy inspect <project-dir>
goodboy ingest <project-dir> path/to/images/* --role primary_reference
goodboy source-card <project-dir>
goodboy plan-candidates <project-dir> --provider codex_builtin --model-alias codex-imagegen --count 6 [--refresh] [--no-sheet]
goodboy select-candidate <project-dir> --candidate-id baseline-003 --image-path path/to/generated.png
goodboy candidate-sheet <project-dir>
goodboy feedback <project-dir> --target baseline-003 --text "make him happier"
goodboy provenance <project-dir>
goodboy style-default <project-dir> [--preset anime] [--subject-kind inanimate_object] [--user-style "..."] [--ai-critique "..."] [--refresh]
goodboy critique <project-dir> --critique-id vision-001 --target style --finding "..." --recommendation "..." [--apply-to-style]
goodboy plan-rows <project-dir> --run-id <run-id> --provider codex_builtin --model-alias codex-imagegen [--refresh]
goodboy adapters --json
goodboy doctor <project-dir> --agent-mode
goodboy next <project-dir> --agent-mode
goodboy generate-handoff <project-dir> --run-id <run-id> --all
goodboy import-generated <project-dir> --run-id <run-id> --map generated-output-map.json
goodboy build-review <project-dir> --run-id <run-id> --row-provenance provider_generated
goodboy finish <project-dir> --run-id <run-id> --row-provenance provider_generated --approval-notes "User approved ..."
goodboy approve <project-dir> --notes "User approved ..."
goodboy handoff <project-dir> --run-id <run-id> --job-id row-idle
goodboy execute-openai <project-dir> --run-id <run-id> --job-id row-idle --dry-run
goodboy execute-gemini <project-dir> --run-id <run-id> --job-id row-idle --dry-run
goodboy build-from-rows <project-dir> --run-id <run-id> --rows-dir path/to/rows
goodboy export project <project-dir> --run-id <run-id>
goodboy export petdex <project-dir> --run-id <run-id>
goodboy validate <project-dir>

# Planned commands after the current executable slice:
goodboy analyze <project-dir>
goodboy qa <project-dir>
```

## 18. MVP Definition

MVP should prove repeatability without requiring every provider.

MVP must include:

- project creation
- source image ingest
- manual source-card support
- baseline candidate manifest
- one generation adapter
- selected baseline
- default style sheet
- row job manifests
- deterministic raster pipeline
- QA reports and install policy
- feedback events and branches
- installable Codex package
- archive before overwrite
- clear docs

MVP should ideally include:

- Codex built-in adapter
- OpenAI Images API adapter
- local contact sheet and GIF preview generation

Post-MVP:

- live provider smoke tests
- visual critic
- local web UI
- Codex plugin
- Petdex export

## 19. Quality Bar

A Goodboy pet is not finished until:

- install package exists
- package validates
- contact sheet exists
- GIF previews exist
- edge preview exists
- centering overlay and report exist
- run summary exists
- generation prompts are saved
- source rows are saved
- selected baseline is saved
- QA reports pass or have explicit approved overrides
- feedback decisions and branches are recorded
- rebuild instructions are present

## 20. Immediate Next Steps

1. Run live OpenAI and Gemini image execution smoke tests when keys are available.
2. Harden provider execution error parsing and retry policy.
3. Add visual-critic source/baseline/row comparison reports.
4. Add EXIF/provenance reporting for source ingest.
5. Add bundled Goodboy MCP tools if plugin usage proves the extra structure is worthwhile.
6. Add Petdex-ready export validation.
