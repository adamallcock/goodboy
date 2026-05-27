# Goodboy Module Catalog

This catalog breaks Goodboy into clear modules with ownership boundaries, inputs, outputs, and acceptance criteria.

## Module 01: Project Workspace

Purpose: create and manage the filesystem shape for a Goodboy pet project.

Responsibilities:

- initialize project folders
- write `goodboy.json`
- assign project id and display name
- maintain active run pointer
- validate path references
- create archive folders before destructive output updates

Inputs:

- pet id
- display name
- output directory
- optional template

Outputs:

- project directory
- project manifest
- initial tracking files

Acceptance criteria:

- project can be initialized without images
- project manifest can be loaded and validated
- no absolute paths are required inside portable project manifests except install targets

## Module 02: Source Ingest

Purpose: preserve source images and describe what was provided.

Responsibilities:

- copy source images into immutable storage
- hash originals
- generate thumbnails
- store file metadata
- classify image roles
- preserve user notes

Inputs:

- user-provided image paths
- optional role labels
- optional notes

Outputs:

- `sources/originals/*`
- `sources/thumbnails/*`
- `sources/source-images.json`

Acceptance criteria:

- duplicate files are detected by hash
- thumbnails are created
- missing source paths produce actionable errors

## Module 03: Source Analysis

Purpose: transform source images and user notes into a semantic source card.

Responsibilities:

- describe visible pet identity
- distinguish directly observed traits from inferred traits
- capture uncertainty
- create editable source card
- optionally use a vision model for analysis

Inputs:

- source image manifest
- user notes
- optional vision adapter

Outputs:

- `sources/source-card.json`
- optional `sources/source-analysis.md`

Acceptance criteria:

- source-card covers species, breed/type, face, fur, eyes, nose, ears, tail, markings, props, personality, must-keep traits, avoidances
- user can edit source-card before generation

## Module 04: Baseline Candidate Planner

Purpose: plan multiple baseline visual directions for user choice.

Responsibilities:

- create candidate prompts
- produce style variation descriptions
- record candidate intent before generation
- ensure variations are meaningfully different but identity-safe

Inputs:

- source-card
- user style preferences
- provider capability registry

Outputs:

- candidate job manifests
- candidate prompt files
- `candidates/baseline-candidates.json`

Acceptance criteria:

- each candidate has a distinct style summary
- each candidate has a regenerable character-card delta
- prompts avoid unapproved logos/text/backgrounds

## Module 05: Generation Adapter Layer

Purpose: normalize image generation providers behind one interface.

Responsibilities:

- prepare provider-specific requests
- submit jobs
- collect outputs
- normalize outputs into Goodboy artifacts
- record provider metadata
- handle retries

Initial adapters:

- `codex_builtin`
- `openai_images`
- `gemini_nano_banana_2`
- `gemini_nano_banana_pro`

Inputs:

- generation job manifest
- provider config
- credential references

Outputs:

- generated image artifacts
- provider invocation records

Acceptance criteria:

- no raw API keys written to disk
- output artifacts are copied into the project
- failed jobs are resumable

## Module 06: Candidate Review

Purpose: help the user choose the pet's canonical baseline look.

Responsibilities:

- build candidate contact sheet
- display candidate summaries
- record user selection
- store selected baseline image
- create character card from selected candidate

Inputs:

- candidate artifacts
- user selection

Outputs:

- `character/selected-baseline.png`
- `character/selected-candidate.json`
- `character/character-card.json`
- selection event

Acceptance criteria:

- every candidate remains traceable
- selected baseline is immutable
- rejected candidates remain available for comparison
- aggregate candidate index reflects the selected candidate

## Module 07: Visual Critic

Purpose: optionally compare source images, baseline candidates, and generated rows.

Responsibilities:

- run vision-model comparison
- produce structured identity/style feedback
- suggest prompt changes
- create AI-feedback branch when needed

Inputs:

- source images
- generated images
- source-card
- character-card

Outputs:

- critique reports
- suggested feedback events

Acceptance criteria:

- critique never silently mutates selected artifacts
- AI feedback and human feedback use the same branch model

## Module 08: Feedback And Branching

Purpose: preserve user and AI feedback as explicit project history.

Responsibilities:

- create feedback events
- create branches
- link branch to parent artifact
- record acceptance/rejection
- compare branches

Inputs:

- feedback text
- target artifact
- author

Outputs:

- branch manifest
- feedback event

Acceptance criteria:

- a branch can be traced to its parent and reason
- installing from a branch records that branch in run summary

## Module 09: Emotion Style Sheet

Purpose: define animation state behavior before generating rows.

Responsibilities:

- provide default Codex pet state sheet
- support mood overrides
- support state-level prompt overrides
- define frame counts
- define avoid rules
- define centering policy

Inputs:

- character-card
- user mood preferences
- optional style preset
- subject kind such as pet, object, inanimate_object, or fantasy_creature
- optional human and AI critique overrides

Outputs:

- `style/emotion-style-sheet.json`
- style preset, subject-kind, user override, and AI critique override fields

Acceptance criteria:

- every required Codex state is covered
- frame counts match output contract
- user overrides are preserved
- pets, object mascots, and alternate styles can be expressed without changing code

## Module 10: Row Job Planner

Purpose: convert character card and emotion style sheet into generation jobs.

Responsibilities:

- create one row job per state
- attach selected baseline image
- attach layout guide when needed
- write retry prompts
- order jobs by dependencies

Inputs:

- character-card
- emotion-style-sheet
- selected provider

Outputs:

- `generation-jobs.json`
- prompt files

Acceptance criteria:

- all required states are planned
- every row job has identity lock and avoid rules
- jobs can be resumed after partial completion
- row prompts include style preset, subject-kind guidance, user overrides, and critique overrides

## Module 11: Alpha Cleanup

Purpose: turn generated rows into clean transparent rows.

Responsibilities:

- detect chroma key
- remove background
- despill green/magenta edge pixels
- trim low-alpha matte residue
- normalize transparent RGB

Inputs:

- generated row strip
- background policy
- cleanup thresholds

Outputs:

- transparent row strip
- cleanup metrics

Acceptance criteria:

- transparent RGB residue is zero
- edge preview shows acceptable halo
- cleanup is deterministic

## Module 12: Frame Extraction And Centering

Purpose: extract animation frames and keep the pet stable.

Responsibilities:

- split rows by components or slots
- keep main component
- remove tiny detached artifacts
- center horizontally
- apply state-specific vertical anchor policies
- stabilize idle/waiting/review/task-style states while preserving directional and jump motion
- avoid edge clipping

Inputs:

- transparent row strips
- state specs
- centering policy

Outputs:

- per-state frame PNGs
- frame manifest
- `frames/centering-report.json`
- drift metrics

Acceptance criteria:

- frame count matches state spec
- horizontal drift under threshold
- idle vertical center drift is within the strict state threshold after stabilization
- edge clearance over threshold
- no primary frame is cut off

## Module 13: Atlas Composer

Purpose: compose Codex-compatible atlas.

Responsibilities:

- place frames into 8x9 grid
- leave unused cells transparent
- export PNG and WebP
- preserve transparent RGB invariant

Inputs:

- extracted frames
- output contract

Outputs:

- `final/spritesheet.png`
- `final/spritesheet.webp`

Acceptance criteria:

- atlas size exactly matches contract
- unused cells are transparent

## Module 14: QA Engine

Purpose: determine whether a pet is ready to install.

Responsibilities:

- validate atlas
- inspect frames
- detect duplicates
- measure drift
- apply state-specific vertical drift thresholds
- measure edge clearance
- measure green-edge pixels
- produce centering report and overlay for visual inspection
- produce QA report

Inputs:

- frames
- atlas
- style sheet
- thresholds

Outputs:

- `qa/review.json`
- `qa/duplicate-audit.json`
- `qa/centering-report.json`
- `qa/centering-overlay.png`
- `qa/green-edge-report.json`
- `qa/run-summary.json`

Acceptance criteria:

- hard failures block install
- warnings are actionable
- user overrides are explicit

## Module 15: Preview Generator

Purpose: make visual review easy.

Responsibilities:

- contact sheet generation
- GIF preview generation
- white-background edge preview
- centering overlay generation
- optional side-by-side before/after previews

Inputs:

- atlas
- frames

Outputs:

- `qa/contact-sheet.png`
- `qa/previews/*.gif`
- `qa/edge-preview-white.png`
- `qa/centering-overlay.png`

Acceptance criteria:

- previews are regenerated after each final build
- paths are included in run summary

## Module 16: Installer

Purpose: safely install Codex pets.

Responsibilities:

- generate `pet.json`
- copy `spritesheet.webp`
- archive previous install
- install to `~/.codex/pets/<pet-id>`
- validate installed files

Inputs:

- package metadata
- final spritesheet
- install target

Outputs:

- installed Codex pet package
- install record

Acceptance criteria:

- previous package is archived before overwrite
- installed `pet.json` and project `package/pet.json` match

## Module 17: Exporters

Purpose: prepare outputs for external distribution.

Responsibilities:

- export project bundle
- export Petdex-ready package
- export debug bundle

Inputs:

- final package
- run summary
- metadata

Outputs:

- export folder or zip

Acceptance criteria:

- exported package validates before release

## Module 18: Codex Skill

Purpose: make Goodboy usable inside Codex.

Responsibilities:

- guided workflow
- Codex built-in image generation handoff
- batch handoff/import/review/finish command flow
- progress checklist
- project-local artifact management
- final summary

Inputs:

- user request
- project path

Outputs:

- completed Goodboy project
- installed pet

Acceptance criteria:

- user can complete a pet without manually running individual scripts, shell copy loops, or manifest-edit snippets

## Module 19: Codex Plugin

Purpose: provide a deeper Codex integration.

Responsibilities:

- package Goodboy for Codex plugin distribution
- expose command workflows through the bundled Goodboy skill
- support resumable workflow through Goodboy manifests
- optionally add app or MCP surfaces

Inputs:

- Codex plugin surface capabilities
- existing Goodboy skill

Outputs:

- `docs/2026-05-27-goodboy-codex-plugin-feasibility.md`
- `plugins/goodboy/.codex-plugin/plugin.json`
- `plugins/goodboy/skills/goodboy/SKILL.md`
- `.agents/plugins/marketplace.json`

Acceptance criteria:

- bundled plugin installs and validates
- repo marketplace exposes the plugin
- plugin does not weaken provenance or QA

## Module 20: Local Web UI

Purpose: handle visual-heavy review steps.

Responsibilities:

- candidate gallery
- selected baseline review
- row review
- contact sheet review
- animation previews
- QA dashboard
- feedback/fork controls

Inputs:

- Goodboy project manifests and artifacts

Outputs:

- user selections
- feedback events
- approval records

Acceptance criteria:

- visual decisions are easier and safer than inspecting files manually
