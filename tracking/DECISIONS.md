# Goodboy Decisions

## Accepted

### D001: Use A Manifest-First Pipeline

Every run must be driven by structured manifests rather than loose filenames and implicit prompts.

Reason: prior one-off pet runs were successful, but one-off state lived in chat, file timestamps, copied paths, and local judgment. Goodboy needs repeatability.

### D002: Copy Reference Assets, Do Not Move Them

Existing pet projects stay intact. Goodboy stores copied reference scripts and docs under `references/legacy-pipeline/`.

Reason: the original pet projects are working archives and should remain independently rebuildable.

### D003: Treat Image Generation As A Replaceable Adapter

Goodboy core must not assume a single image provider. Adapters will normalize job input and output into a common artifact contract.

Initial adapters:

- `codex_builtin`
- `openai_images` with configurable default alias `gpt-image-2`
- `gemini_nano_banana_2` with configurable default alias `gemini-3.1-flash-image-preview`
- `gemini_nano_banana_pro` with configurable default alias `gemini-3-pro-image-preview`

### D004: Selected Baseline Image Is Canonical

Prompt descriptions are required, but the selected baseline image itself becomes the strongest identity reference.

Reason: exact regeneration is not guaranteed across providers, especially when seeds are absent or model versions change.

### D005: QA Gates Are Product Features

Centering, clipping, duplicate detection, transparent RGB residue, chroma-edge detection, and visual previews are not optional polish. They are core output correctness.

### D006: Plan Candidate Intent Before Image Generation

Baseline candidates must store style summaries, character deltas, prompts, provider, and model alias before images are generated.

Reason: the user should be able to choose a character direction, regenerate it, or fork it without reverse-engineering intent from an image.

### D007: Feedback Creates Explicit Branch Artifacts

Human and AI feedback must be written to `feedback/events.json`; branch-worthy feedback also writes `branches/<branch-id>/branch.json`.

Reason: repeated pet iteration phrases such as "happier", "trim chroma edges closer", and "center subject" are product decisions and should not live only in chat or folder names.

### D008: Install Requires QA Policy Approval

Goodboy may package a failing run for inspection, but install is blocked unless QA passes or an explicit override reason is supplied and recorded.

Reason: installation is the user-visible state change; failures should not silently replace a working pet.

### D009: CLI First, Then Codex Skill, Then Plugin

Goodboy should keep the Python library and CLI as the deterministic core, wrap that core with a Codex skill, and expose a repo-scoped Codex plugin without making plugin UI the only product surface.

Reason: the deterministic pipeline should be usable outside Codex, while Codex remains a premium orchestration environment.

### D010: Local Web UI For Candidate Selection

Goodboy should provide a local web UI for browsing candidate baselines, comparing QA media, accepting/rejecting rows, recording style/critique decisions, and preparing a polished demo experience.

Reason: the repo-scoped Codex plugin is useful for agent steering, but the current plugin surface should not be treated as the image-heavy review UI. M10 needs a dedicated local visual surface over the existing manifests.

### D011: Review Room Is The Primary M10 UI Direction

Goodboy M10 should default to an artifact-first Review Room rather than a permanently dense Studio Console.

Reason: the most important Goodboy decisions are visual review decisions. A simpler Review Room better supports first-use clarity and hiring-manager demos, while Studio Console behaviors can still exist as advanced/debug drawers for logs, manifests, commands, and job tables.

## Open

- Should Goodboy store generated images in-project by default, or use an external artifact cache with project references?
- Should Goodboy use SQLite for run tracking, or keep everything as JSON/YAML manifests?
- Should image generation jobs be resumable through a queue system from the first release?
- Should Petdex export be MVP or a post-MVP feature?
