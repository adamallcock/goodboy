---
name: goodboy
description: Create, migrate, continue, recover, visually review, repair, validate, export, and install source-faithful Codex pet v2 projects from pet or mascot reference images.
---

# Goodboy

## Purpose

Use Goodboy when the user wants a Codex pet based on source images and values likeness, durable project state, privacy controls, targeted repair, provider choice, or a visual review workflow.

Goodboy v2 wraps a pinned Hatch-compatible deterministic backend. It must meet the same Codex v2 geometry and direction-quality floor; its additional value is evidence-linked source identity, recoverable orchestration, review, repair lineage, and export.

For the shortest one-task hatch without durable identity or project needs, `$hatch-pet` may be simpler. Do not claim Goodboy produces better source likeness unless a completed Goodboy benchmark report explicitly allows that claim.

## Runtime Preflight

The command blocks below show raw Goodboy CLI syntax for readability. Before the
first Goodboy command in a task, verify that the skill and Python runtime are the
same version. A request to create or review a pet is not, by itself, permission
to install or replace software.

### Plugin Mode

When this skill is loaded from a plugin, derive `<plugin-root>` from this
`SKILL.md` path by removing `/skills/goodboy/SKILL.md`. Use the plugin's
version-pinned runner:

```bash
node "<plugin-root>/scripts/goodboy-runtime.mjs" check
```

The runner returns a JSON status and distinct nonzero exit codes for
`missing`, `mismatch`, and `invalid` runtimes. It also checks uv's tool bin
directly, so a newly installed runtime does not require a shell restart.

- If status is `ready`, run every command shown below through the runner.
  For example, translate `goodboy start ...` to:

  ```bash
  node "<plugin-root>/scripts/goodboy-runtime.mjs" run -- start ...
  ```

- If status is `missing` or `mismatch`, tell the user the expected version,
  the discovered version if any, and the exact package
  `goodboy-codex[ui]==0.2.1`. Ask for explicit permission to install it with
  uv. A mismatch prompt must say that the existing Goodboy runtime will be
  replaced or updated.
- Only after the user approves that installation or replacement, run:

  ```bash
  node "<plugin-root>/scripts/goodboy-runtime.mjs" install --user-approved
  ```

  Then rerun `check` and continue the original pet task without making the user
  repeat it.
- If status is `uv_missing`, stop at that setup gate. Explain that uv is the
  isolated runtime installer, and ask separately before installing uv or using
  another package manager. Never download or execute a uv installer merely
  because the user approved the Goodboy runtime.
- `check` and `run` never install software. Never call `install` before
  direct user approval, never add `--force`, and never bypass a mismatch by
  running an arbitrary Goodboy executable.

### Standalone Skill Mode

If there is no plugin root and runner, perform the equivalent read-only check:

```bash
goodboy --version
```

Require `goodboy 0.2.1`. If it is missing or mismatched, use the same explicit
approval wording. Only after approval, install the exact isolated runtime:

```bash
uv tool install "goodboy-codex[ui]==0.2.1"
```

Recheck the version and continue. Do not silently fall back to an unversioned
`pip install`, and do not install uv without separate permission.

## Canonical Rail

Prefer:

```bash
goodboy start <project-dir> \
  --pet-id <id> \
  --display-name "<name>" \
  --species dog \
  --source <image>...

goodboy advance <project-dir> --agent-mode
```

`start` is local. It ingests source images, assesses reference coverage, drafts an evidence-linked identity profile, creates a source contact sheet, and stops at identity confirmation. It must not send source images to a provider.

Use `advance --agent-mode` repeatedly. It performs safe deterministic work and stops at real gates:

- identity confirmation;
- explicit provider consent;
- baseline image generation and likeness selection;
- dependency-ready animation or direction generation;
- direction semantics and blind-direction review;
- trait-level source-likeness review;
- visual approval;
- QA failure or user override;
- install review.

## My Pet Workflow

### 1. Inspect And Confirm Identity

```bash
goodboy identity-show <project-dir>
```

If needed:

```bash
goodboy source-role <project-dir> \
  --source-id <source-id> \
  --role identity_left \
  --role marking_detail \
  --provider-permission codex_builtin=true

goodboy identity-patch <project-dir> \
  --trait-id <trait-id> \
  --value "<correct description>" \
  --reason "<source evidence>"
```

Confirm and consent:

```bash
goodboy advance <project-dir> \
  --agent-mode \
  --confirm-identity \
  --provider-consent
```

Provider consent authorizes only current, hash-checked, EXIF-stripped PNG derivatives for that provider. Never attach `sources/originals/*` to a provider call.

### 2. Generate And Choose A Baseline

Generate all three source-fidelity candidates from `candidates/<id>/prompt.md`
using the listed consented inputs. They deliberately hold treatment, lighting,
pose, and stylization constant and Goodboy normalizes their review framing;
compare identity evidence rather than visual novelty. Register and score every
provider result:

```bash
goodboy candidate-image <project-dir> \
  --candidate-id baseline-001 \
  --image-path <generated.png>

goodboy candidate-review <project-dir> \
  --candidate-id baseline-001 \
  --holistic-gestalt-score <1-5> \
  --signature-trait-score <1-5> \
  --small-size-readability-score <1-5> \
  --notes "<visible source-linked evidence>" \
  --reviewed-by <name>
```

Repeat for every generated candidate, then choose by source likeness, not
merely attractive style. Goodboy preserves this winner as an identity anchor;
any later style candidate must retain its anatomy and defining traits:

For every side-specific marking, verify and record both anatomical side and
viewer/screen side in at least one named source view before confirmation. A
front-facing pet's anatomical right appears on viewer-left. If orientation is
not provable, record the trait as uncertain instead of guessing.

```bash
goodboy select-candidate <project-dir> \
  --candidate-id baseline-001 \
  --notes "<why it best preserves defining traits>"
```

Then:

```bash
goodboy advance <project-dir> \
  --agent-mode \
  --run-id <run-id>
```

### 3. Generate Dependency Waves

The post-baseline v2 graph contains nine standard animation rows, a four-cardinal strip, look row 9, and look row 10.

Important dependencies:

- `running-left` follows `running-right`;
- cardinals wait for all nine standard rows;
- row 9 waits for cardinals;
- row 10 waits for cardinals and row 9.

Treat every standard row as an ordered physical loop. A valid extraction is
not enough: reject paw-side swaps, sit/stand resets, random head scans,
uneven recovery jumps, or a final pose that cannot flow into frame 0. Repair
the whole affected row and preserve unaffected work.

Inspect or prepare ready work:

```bash
goodboy job-graph <project-dir> --run-id <run-id>
goodboy generate-handoff <project-dir> --run-id <run-id> --all
```

`--all` does not bypass dependencies. Generate only `ready` jobs.

Use `expected_outputs[].input_images` from the generated handoff summary (or
the matching invocation's `request_metadata.input_images`) as the exact
attachment list. It is already packed to the provider's hard reference limit;
do not attach the larger raw job list when the two differ.
The matching `input_image_roles` map is filtered to exactly that attachment
list. Look-row handoffs use row-specific three-anchor references; do not
replace them with the full cardinal strip or the opposite half-turn.

Every provider job must use:

- the exact prompt named in the job;
- the canonical selected baseline;
- only listed consented source derivatives;
- the layout guide as spacing guidance only;
- the requested flat chroma background;
- no copied guide lines, labels, borders, shadows, or detached effects.

Do not hand-make missing output with Pillow, SVG, canvas, local renderers, or one-off sprite scripts.

### 4. Import Provider Results

```bash
goodboy import-generated <project-dir> \
  --run-id <run-id> \
  --map <generated-output-map.json>
```

The map may include multiple dependency waves. Goodboy resolves ready jobs in order.

Use `--extraction-method stable-slots` only for an intentional fixture or a diagnosed recovery case. Production defaults to `auto`.

### 5. Build And Review

```bash
goodboy build-review <project-dir> \
  --run-id <run-id> \
  --row-provenance provider_generated

goodboy review-status <project-dir> \
  --run-id <run-id> \
  --agent-mode
```

Inspect at minimum:

- v2 contact sheet and animation previews;
- `animation-correctness.json`, including exact playback timing and all nine structured state verdicts;
- all sixteen look directions;
- blind direction pairs and consensus;
- continuity report;
- white edge preview;
- centering overlay/report;
- duplicate audit;
- source/baseline/state/direction likeness sheet;
- trait-level likeness report;
- install policy;
- package validation.

### 6. Record Animation Correctness

Machine timing and duplicate checks cannot prove that a state means the right
thing. Play every standard loop and submit exactly one `pass`, `warning`, or
`fail` verdict for each of the nine states. Every verdict must include nonempty
`state_semantics`, `motion_continuity`, and `identity_consistency` evidence:

```bash
goodboy animation-review <project-dir> \
  --run-id <run-id> \
  --verdicts <animation-verdicts.json> \
  --reviewer <name>
```

`running` means active task progress, not foot-running; `review` must read as
inspection; `waiting` must visibly request input. Any failed state blocks
approval and should be repaired narrowly.

### 7. Record Direction Review

Direction semantics require all sixteen direction entries with `pass`, `warning`, or `fail`:

```bash
goodboy direction-review <project-dir> \
  --run-id <run-id> \
  --verdicts <direction-verdicts.json> \
  --reviewer <name>
```

Blind validation requires exactly three isolated reviewer files:

```bash
goodboy direction-blind-import <project-dir> \
  --run-id <run-id> \
  --verdict <reviewer-1.json> \
  --verdict <reviewer-2.json> \
  --verdict <reviewer-3.json>
```

Do not let a reviewer inspect the blind answer key before submitting.

### 8. Record Source Likeness

Submit one evidence-bearing verdict for every locked signature and important trait:

```bash
goodboy likeness-review <project-dir> \
  --run-id <run-id> \
  --verdicts <likeness-verdicts.json> \
  --reviewer <name>
```

Valid verdicts are `pass`, `warning`, `fail`, `not_visible`, and `uncertain`.

A signature trait marked `fail`, `not_visible`, or `uncertain` blocks approval. Automated drift metrics are advisory only and cannot overrule a reviewer.

### 9. Repair Narrowly

```bash
goodboy repair <project-dir> \
  --run-id <run-id> \
  --job-id <job-id> \
  --reason "<visible failure and correction>"
```

Repair archives superseded artifacts and invalidates the dependency closure. Do not restart the full project when a narrow repair is sufficient.

If the identity definition itself is wrong, use `identity-patch` with the run ID. That versions the profile, invalidates all identity-dependent output, refreshes the run snapshot and job versions, and appends the authoritative replacement contract to every new repair prompt. Reattach prior provider output only when review proves its pixels already match the corrected source truth; otherwise regenerate complete artifacts.

### 10. Finish

```bash
goodboy finish <project-dir> \
  --run-id <run-id> \
  --row-provenance provider_generated \
  --approval-notes "<what the human reviewed and approved>"
```

Never fabricate approval notes. Installation requires a valid v2 package,
clean hard gates or an explicit permitted override, approved animation,
direction, and likeness reviews, approved provenance, and no suspicious
renderer scripts.

Confirm that `qa/likeness-receipt.json` and
`qa/likeness-receipt.md` record the baseline decision, trait evidence,
identity pack, provider snapshots, repair/run lineage, and final visual
approval.

## Interruption Recovery

```bash
goodboy recover <project-dir> --run-id <run-id>
```

Deterministic processing may be replayed. An interrupted provider job becomes blocked with an unknown-outcome reason; attach an existing output or retry explicitly. Do not silently issue a duplicate provider request.

Use these orientation commands before improvising:

```bash
goodboy next <project-dir> --agent-mode
goodboy doctor <project-dir> --agent-mode
goodboy job-graph <project-dir> --run-id <run-id>
goodboy validate <project-dir>
```

## V1 Upgrade

```bash
goodboy upgrade <project-dir> \
  --run-id <migration-run-id> \
  --provider codex_builtin \
  --model-alias codex-imagegen
```

The migration must:

- archive the original manifest and v1 atlas;
- preserve the 8 × 9 standard rows;
- generate only cardinals and look rows 9–10;
- record source and RGBA hashes;
- assemble a new 8 × 11 package;
- retain the original artifacts and migration receipt.

Do not regenerate approved v1 rows unless the user asks for a redesign or those rows fail validation.

## Privacy And Exports

Safe defaults:

```bash
goodboy export project <project-dir> --run-id <run-id>
goodboy export petdex <project-dir> --run-id <run-id>
goodboy export diagnostic <project-dir> --run-id <run-id>
```

Project exports exclude source pixels and source-bearing QA sheets by default. Petdex contains only the package and export metadata. Diagnostic exports omit all images, prompts, raw provider responses, request IDs, input hashes, and credential-like values.

Use `--include-sources` only after the user explicitly asks for a source-bearing project export.

Never write provider keys into manifests, prompts, docs, logs, memory, or output. Direct execution reads `OPENAI_API_KEY` or `GEMINI_API_KEY` from the environment.

## Hard Guardrails

- Do not create local renderer, drawing, sprite-maker, SVG, canvas, or Pillow scripts during a pet run.
- Do not synthesize missing provider art from textual traits.
- Do not bypass dependency, direction, likeness, visual approval, provenance, privacy, or install gates.
- Do not mutate Goodboy source code during a pet run unless the user asks to improve Goodboy itself.
- Do not treat `test_fixture` or `stable-slots` as production evidence.
- Do not install `mock_renderer`, `local_renderer`, `programmatic_renderer`, or `ad_hoc_renderer` output.
- Do not claim a pet resembles the source without a completed trait-level likeness review.
- Do not claim Goodboy is better than Hatch Pet without a benchmark report whose `better_likeness_claim_allowed` value is true.

## Development Validation

When changing Goodboy itself:

```bash
python -m unittest discover -s tests -v
python scripts/validate_skills.py \
  codex-skill/goodboy \
  plugins/goodboy/skills/goodboy

cd ui
npm run typecheck
npm run build:package
npm run check:package
npm run test:e2e
```

Keep the two Goodboy skill copies byte-identical. Keep private pet projects, generated source identity art, local installs, credentials, and provider responses out of the public repository.
