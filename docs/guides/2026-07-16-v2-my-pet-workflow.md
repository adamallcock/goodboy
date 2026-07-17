---
title: Goodboy V2 My Pet Workflow
date: 2026-07-16
type: guide
status: current
---

# Goodboy V2 My Pet Workflow

This is the canonical end-to-end workflow for creating a source-faithful Codex pet. The default rail is `start`, followed by repeated `advance --agent-mode` calls. Lower-level commands exist for inspection, explicit review, and recovery.

## 1. Start Locally

```bash
goodboy start <project-dir> \
  --pet-id <id> \
  --display-name "<name>" \
  --species dog \
  --source /absolute/path/front.jpg \
  --source /absolute/path/side.jpg
```

This step:

- creates a `codex-pet-v2` workspace;
- copies source images into the local project;
- records hashes, dimensions, filenames, MIME types, thumbnails, and EXIF;
- assigns initial reference roles;
- assesses reference coverage and basic quality;
- drafts an evidence-linked identity profile;
- creates a source contact sheet;
- stops at identity confirmation.

No provider receives an image during `start`.

## 2. Review Reference Coverage

```bash
goodboy identity-show <project-dir>
```

Recommended coverage includes:

- a clear face or three-quarter view;
- body proportions;
- at least one side or marking-detail view.

Missing coverage is a warning, not an excuse to invent details. Add images with `ingest`, or assign explicit roles:

```bash
goodboy source-role <project-dir> \
  --source-id source-001 \
  --role identity_left \
  --role marking_detail \
  --provider-permission codex_builtin=true
```

Relevant roles include `identity_front`, `identity_three_quarter`, `identity_left`, `identity_right`, `identity_back`, `body_proportions`, `face_detail`, `marking_detail`, `tail_detail`, `accessory_detail`, `style_only`, and `exclude_from_identity`.

## 3. Confirm The Identity Contract

The draft identity profile separates signature, important, supporting, uncertain, and ignored traits. Each observed trait links to source evidence and records whether it is symmetric or mirror-sensitive. For any side-specific marking, verify both the pet's anatomical side and its viewer/screen side in a named source view before confirmation. A front-facing pet's anatomical right appears on viewer-left; never copy a screen-side label into the anatomical contract without this check.

For richer visual analysis, prepare a consented provider handoff:

```bash
goodboy identity-handoff <project-dir> \
  --provider codex_builtin \
  --provider-consent
```

Import structured analysis:

```bash
goodboy identity-import <project-dir> \
  --analysis /absolute/path/identity-analysis.json
```

Confirm:

```bash
goodboy identity-confirm <project-dir> --author human
```

Or use the normal rail to confirm and immediately plan candidates:

```bash
goodboy advance <project-dir> \
  --agent-mode \
  --confirm-identity \
  --provider-consent
```

Provider consent creates a provider-specific receipt and EXIF-stripped PNG derivatives. Original source files are not job inputs.

## 4. Generate And Select A Likeness Baseline

Goodboy plans three controlled identity interpretations: balanced identity,
holistic gestalt, and exact markings. For the default
`likeness` dimension, every prompt holds treatment, lighting, pose, framing,
and stylization constant while emphasizing different confirmed identity
evidence. Generate each from its prompt and consented references, then register
every returned file. Goodboy also creates a 240 × 200 normalized review tile
with shared subject scale and baseline so provider framing does not bias the
choice:

```bash
goodboy candidate-image <project-dir> \
  --candidate-id baseline-001 \
  --image-path /absolute/path/baseline-001.png
```

Score every generated candidate from 1–5. Holistic gestalt deliberately has
the largest weight because a markings-perfect generic mascot is still the
wrong animal:

```bash
goodboy candidate-review <project-dir> \
  --candidate-id baseline-001 \
  --holistic-gestalt-score 4.5 \
  --signature-trait-score 4.0 \
  --small-size-readability-score 4.0 \
  --notes "Head mass, muzzle length, ear set, body depth, coat volume, and markings match" \
  --reviewed-by human
```

Repeat `candidate-image` and `candidate-review` for every planned candidate,
then choose primarily by source likeness:

```bash
goodboy select-candidate <project-dir> \
  --candidate-id baseline-001 \
  --notes "Best facial proportions and asymmetric marking"
```

The selected likeness becomes `character/identity-anchor.png`; later
stylization cannot overwrite it. Likeness and style are separate decisions. A
stylish candidate with the wrong defining traits is blocked from winning.

For an explicit rendering-treatment comparison after identity is fixed, the
lower-level planner also supports:

```bash
goodboy plan-candidates <project-dir> \
  --provider codex_builtin \
  --model-alias codex-imagegen \
  --evaluation-dimension style \
  --provider-consent \
  --refresh
```

## 5. Plan The V2 Job Graph

```bash
goodboy advance <project-dir> \
  --agent-mode \
  --run-id <run-id>
```

Goodboy compiles the confirmed identity contract into twelve post-baseline jobs:

```text
standard rows except running-left ─┐
running-right ──> running-left ────┼──> look-cardinals ──> look-row-9 ──> look-row-10
other standard rows ───────────────┘                       └──────────────^
```

The explicit job states are:

- `planned`
- `blocked`
- `ready`
- `running`
- `generated`
- `processing`
- `qa_failed`
- `awaiting_approval`
- `approved`
- `complete`
- `superseded`
- `cancelled`
- `failed`

Inspect the graph at any time:

```bash
goodboy job-graph <project-dir> --run-id <run-id>
```

## 6. Generate Dependency Waves

```bash
goodboy generate-handoff <project-dir> \
  --run-id <run-id> \
  --all
```

`--all` means “prepare every requested job that is currently ready.” Blocked jobs remain blocked and appear with their dependency reason.

Every handoff includes:

- the identity-locked prompt;
- the canonical selected baseline;
- up to three consented source derivatives;
- a layout guide used only for slots and safe margins;
- the provider and model alias;
- input hashes and roles;
- the expected output path;
- a provider snapshot.

The handoff summary lists the provider-packed input set and its matching role
map, not the larger logical job set. If a provider has a hard reference limit,
Goodboy keeps the canonical identity, direction-specific approved anchors,
and the layout guide first, then uses the remaining slots for the
highest-priority consented source derivatives. Look row 9 receives an ordered
back/right/front anchor reference; look row 10 receives an ordered
front/left/back anchor reference. The opposite profile is deliberately absent.

## 7. Import Provider Output

Standard-row prompts contain an exact state-specific storyboard and a
loop-closure lock. Treat each row as one ordered motion sequence: adjacent
frames must be plausible next steps and the last frame must return naturally
to frame 0. Single-paw gestures must keep the same anatomical limb on the same
screen side, and neutral loops must match their first and last posture. A
structurally valid strip can still fail the later animation
semantics review if it behaves like a random pose sampler.

`goodboy repair` archives both the failed output and any prepared handoff,
writes a versioned repair prompt containing the visual failure evidence, and
invalidates only the selected job plus its dependency closure. The next
`generate-handoff` is therefore a fresh request with the corrected prompt.

Import one wave:

```bash
goodboy import-generated <project-dir> \
  --run-id <run-id> \
  --state idle=/absolute/path/idle.png \
  --state running-right=/absolute/path/running-right.png
```

Or pass a JSON map containing any or all jobs:

```bash
goodboy import-generated <project-dir> \
  --run-id <run-id> \
  --map /absolute/path/generated-output-map.json
```

The importer repeatedly resolves newly ready jobs, verifies images, copies immutable provider outputs into the run, performs deterministic processing, writes events, and advances the dependency graph.

For four-cardinal strips, ordinary equal-slot extraction remains the first
path. If and only if the strip contains exactly four disconnected whole poses
in the correct left-to-right order, Goodboy can component-register those poses
with safe cell padding. Merged, ambiguous, missing, or reordered poses still
fail and require a whole-strip repair.

`stable-slots` is reserved for deliberate fixture or recovery use when component extraction would destabilize known slot geometry:

```bash
goodboy import-generated <project-dir> \
  --run-id <run-id> \
  --map /absolute/path/map.json \
  --extraction-method stable-slots \
  --chroma-key '#00FF00'
```

Do not use fixture settings to disguise a production extraction failure.

## 8. Build V2 Review Artifacts

```bash
goodboy build-review <project-dir> \
  --run-id <run-id> \
  --row-provenance provider_generated
```

The deterministic backend:

1. extracts and inspects standard frames;
2. composes the 8 × 9 intermediate;
3. extracts four cardinal anchors;
4. registers row 9 to the neutral reference using one shared scale;
5. registers row 10 using the row 9 scale and continuity context;
6. assembles the exact 1536 × 2288 atlas;
7. applies one final linear-light, edge-local chroma cleanup;
8. validates the v2 atlas and package;
9. creates animation, direction, blind-direction, edge, centering, duplicate, and likeness review surfaces.

## 9. Record Animation Correctness

Deterministic checks confirm the exact frame counts and GIF durations, but they
cannot prove that an animation means the right thing. Play every standard row
in order and record one evidence-bearing verdict per state:

```json
{
  "verdicts": [
    {
      "state": "running",
      "verdict": "pass",
      "state_semantics": "Focused desk-like checking reads as an active task, not foot-running.",
      "motion_continuity": "The six ordered poses advance smoothly and the last returns cleanly to the first.",
      "identity_consistency": "Face geometry, asymmetric marking, coat volume, and body proportions remain the same animal."
    }
  ]
}
```

The file must cover `idle`, `running-right`, `running-left`, `waving`,
`jumping`, `failed`, `waiting`, `running`, and `review` exactly once. Valid
verdicts are `pass`, `warning`, and `fail`.

```bash
goodboy animation-review <project-dir> \
  --run-id <run-id> \
  --verdicts /absolute/path/animation-verdicts.json \
  --reviewer human
```

Any failed state blocks approval and should enter targeted repair. The combined
machine and visual result is written to `qa/animation-correctness.json`.

## 10. Record Direction Semantics

Create a JSON file containing every direction:

```json
{
  "directions": [
    {
      "direction": "000",
      "observed": "up",
      "verdict": "pass",
      "reason": "Back of head and nose orientation read as upward."
    }
  ]
}
```

Valid directions are `000`, `022.5`, `045`, `067.5`, `090`, `112.5`, `135`, `157.5`, `180`, `202.5`, `225`, `247.5`, `270`, `292.5`, `315`, and `337.5`. Valid verdicts are `pass`, `warning`, and `fail`.

```bash
goodboy direction-review <project-dir> \
  --run-id <run-id> \
  --verdicts /absolute/path/direction-verdicts.json \
  --reviewer human
```

## 11. Record Three Blind Direction Reviews

Three reviewers inspect the blind pair sheet without the answer key. Each verdict file follows the Hatch blind-direction format and must cover every pair. Combine them:

```bash
goodboy direction-blind-import <project-dir> \
  --run-id <run-id> \
  --verdict /absolute/path/reviewer-1.json \
  --verdict /absolute/path/reviewer-2.json \
  --verdict /absolute/path/reviewer-3.json
```

Exactly three isolated reviews are required. A strict majority wins; ties become ambiguous. Hard cardinal/axis ambiguity blocks approval, while explicitly designated review-only pairs request human review.

## 12. Record Trait-Level Likeness

The generated `qa/likeness-report.json` names every required locked trait. Submit one verdict per required trait:

```json
{
  "verdicts": [
    {
      "trait_id": "markings.primary",
      "target": "final-atlas",
      "verdict": "pass",
      "evidence": "In the named front source, the higher sock is on viewer-left (the pet's anatomical right), and that mapping remains stable in front, running, and look views."
    }
  ]
}
```

Valid verdicts are `pass`, `warning`, `fail`, `not_visible`, and `uncertain`.

```bash
goodboy likeness-review <project-dir> \
  --run-id <run-id> \
  --verdicts /absolute/path/likeness-verdicts.json \
  --reviewer human
```

A signature trait marked `fail`, `not_visible`, or `uncertain` blocks the likeness receipt. Advisory drift metrics cannot override that result.

## 13. Repair Only What Failed

```bash
goodboy repair <project-dir> \
  --run-id <run-id> \
  --job-id row-running-left \
  --reason "Anatomical side marking was mirrored"
```

Goodboy archives the old output and all derived products, invalidates the dependency closure, records a repair receipt, and makes only the necessary jobs ready again.

For an identity-definition error:

```bash
goodboy identity-patch <project-dir> \
  --trait-id markings.primary \
  --value "<corrected description>" \
  --reason "<evidence>" \
  --run-id <run-id>
```

That versions the identity profile and invalidates all identity-dependent outputs. Goodboy also refreshes the run's identity snapshot, metadata, and job profile versions, then appends the authoritative updated contract to every replacement prompt. Reattach prior provider output only when visual review proves its pixels already match the corrected source truth; otherwise regenerate complete replacement artifacts.

## 14. Approve And Install

```bash
goodboy review-status <project-dir> --run-id <run-id> --agent-mode

goodboy finish <project-dir> \
  --run-id <run-id> \
  --row-provenance provider_generated \
  --approval-notes "Approved all identity, direction, animation, edge, and package review surfaces"
```

Installation requires:

- exact v2 geometry and package metadata;
- passing deterministic QA;
- exact animation preview timing plus approved nine-state semantics, motion continuity, and identity consistency;
- complete direction semantics;
- passing blind-direction validation;
- approved likeness when an identity profile exists;
- explicit visual approval;
- approved row provenance;
- no suspicious local renderer scripts.

The final approval refreshes:

- `runs/<run-id>/qa/likeness-receipt.json`;
- `runs/<run-id>/qa/likeness-receipt.md`.

The receipt records the baseline decision, identity pack, trait evidence,
provider snapshots, repair history, run lineage, and final visual approval.

## 15. Export

```bash
goodboy export petdex <project-dir> --run-id <run-id>
goodboy export project <project-dir> --run-id <run-id>
goodboy export diagnostic <project-dir> --run-id <run-id>
```

Project exports are source-free by default. Use `--include-sources` only after deliberately reviewing the privacy impact.
