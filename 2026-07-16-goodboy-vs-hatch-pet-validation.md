---
title: Goodboy vs Hatch Pet Capability Validation
date: 2026-07-16
type: research
status: complete
---

# Goodboy vs Hatch Pet Capability Validation

> Historical pre-v2 audit: this report records the decision boundary before
> Goodboy 0.2 implemented the v2 backend and product layer. For current
> behavior, see `README.md` and `2026-07-16-goodboy-v2-next-level-plan.md`.

## Executive Decision

**Decision: use Hatch Pet now; continue Goodboy only as a v2 orchestration and product layer around the official pet-building machinery. Do not continue Goodboy as an independent v1 visual pipeline.**

For the immediate job of creating one current, high-quality Codex pet, the bundled `hatch-pet` skill is better:

- it implements the current v2 package contract;
- it has substantially deeper look-direction generation and QA;
- it is already bundled with Codex;
- its installed local copy is byte-for-byte identical to the skill inside the current Codex app bundle;
- its deterministic scripts and tests cover the hardest visual failure modes that Goodboy does not yet address.

Goodboy's defensible advantage is not better sprite generation. Its advantage is the reusable production system around sprite generation:

- durable projects rather than one task-local run;
- source provenance and reusable character/style records;
- candidate selection, feedback, approval, and recovery state;
- provider-neutral execution;
- a CLI workflow that can resume safely at real gates;
- exports, install governance, and an emerging visual review product;
- operation outside one Codex session or one built-in image provider.

That is a real product distinction, but it is currently weakened by a decisive problem: Goodboy still produces legacy v1 pets. Its present renderer and package path should therefore be treated as obsolete for newly created pets, even if Codex continues to recognize the resulting package as a legacy v1 pet.

The best strategy is **wrap/adopt**, not duplicate:

1. Make the official v2 contract the canonical Goodboy output target.
2. Reuse or faithfully port Hatch Pet's dependency graph, deterministic assembly, look-direction QA, and package validation.
3. Keep Goodboy's project model, provider abstraction, workflow engine, approvals, exports, and Review Room.
4. Retire Goodboy-specific visual logic wherever it is weaker or redundant.
5. Use a narrow v2 vertical slice as a continuation gate before doing broader product work.

If there is no appetite to maintain v2 conformance, finish the Review Room, and prove that users need provider portability or durable projects, the correct decision is to stop Goodboy and use Hatch Pet.

## Direct Answer: What Is the Advantage of Goodboy?

The simplest distinction is:

> **Hatch Pet is the current expert recipe for making a pet correctly inside Codex. Goodboy can be the durable studio and production manager for making, revising, approving, and exporting pets across sessions and providers.**

Goodboy has five plausible advantages.

### 1. A Durable Project, Not Just a Successful Run

Goodboy creates a persistent workspace containing:

- copied source images;
- SHA-256 hashes, MIME types, dimensions, notes, roles, thumbnails, and sanitized EXIF;
- a source card;
- baseline candidate definitions and prompts;
- the selected character and character card;
- style and critique records;
- generation jobs and provider invocation records;
- feedback events and branch manifests;
- run artifacts, approvals, QA, install policy, and exports.

This is useful when a pet is revised over days, handed between people or agents, regenerated through another provider, audited later, or used as the source for multiple deliverables.

Hatch Pet creates substantial run artifacts and QA evidence, but it does not present a general project lifecycle with the same source/candidate/feedback/export model.

### 2. Provider Portability

Goodboy has explicit capability records and adapters for:

- Codex built-in image generation handoffs;
- OpenAI Images API execution;
- Gemini image generation aliases.

Hatch Pet deliberately requires Codex's built-in `$imagegen` visual layer. That is a good default for a bundled skill, but it makes the workflow Codex-bound.

Provider portability matters if the product goal includes:

- running outside Codex;
- choosing providers by cost, quality, privacy, or availability;
- replaying the same job manifest against another provider;
- operating a hosted or team workflow;
- recording comparable provider invocation evidence.

It does not matter if the only goal is to create a pet in an already-open Codex task.

### 3. Repeatable Workflow and Recovery

Goodboy's `start` and `advance --agent-mode` commands form a persistent state machine. Safe deterministic work can progress automatically, while the pipeline stops at provider, baseline-selection, visual-approval, QA, or override gates.

That is a cleaner product primitive than asking every agent to re-interpret a long skill document and coordinate shell commands correctly. It offers a potential recovery advantage after:

- an interrupted task;
- a failed provider call;
- a new agent or user taking over;
- a revised source or style decision;
- a partially completed generation run.

Hatch Pet also records a run manifest and job dependencies, so it is not ephemeral. The distinction is degree: Hatch Pet is a carefully scripted agent workflow; Goodboy is trying to make the workflow itself a reusable application.

### 4. Human Review, Approval, and Governance

Goodboy has explicit structures for:

- candidate selection;
- feedback events;
- visual approval and rejection;
- QA overrides with reasons;
- provenance requirements;
- install readiness;
- suspicious ad hoc renderer-script detection;
- archiving an existing installed pet;
- project and Petdex exports.

The Review Room is intended to make those decisions visually accessible. Hatch Pet has stronger visual QA today, but its review experience is primarily generated artifacts plus agent/user inspection.

This could become Goodboy's most visible advantage if the UI is completed and connected to real projects. It is not yet a fully realized advantage: the current README correctly describes the UI as a strong demo/review surface, with full live project mutation and one-command launch still incomplete.

### 5. A Reusable Public Product Surface

Goodboy is packaged as:

- a Python CLI on PyPI;
- an npm launcher;
- a Codex skill;
- a repo-scoped plugin;
- a local web application foundation.

Hatch Pet is bundled functionality inside Codex. That is superior distribution for Codex users, but it is not a provider-neutral standalone product.

This distinction only becomes commercially or practically meaningful if Goodboy offers an experience materially easier than invoking Hatch Pet directly.

## What “V2” Actually Means

There is not a separate mysterious “v2 builder” alongside the installed skill. The current bundled `hatch-pet` skill implements the **Codex v2 pet format**.

The official local contract requires newly hatched pets to use:

| Property | V1 / Goodboy today | Current v2 |
| --- | ---: | ---: |
| Columns | 8 | 8 |
| Rows | 9 | 11 |
| Cell size | 192 × 208 | 192 × 208 |
| Atlas size | 1536 × 1872 | 1536 × 2288 |
| Standard animation rows | 9 | 9 |
| Look-direction rows | 0 | 2 |
| Look directions | None | 16 clockwise directions |
| Manifest version field | Omitted | `"spriteVersionNumber": 2` |

Rows 9 and 10 encode sixteen fixed clockwise directions. The app uses `spriteVersionNumber: 2` to select the 11-row layout and look behavior. Omitting the field selects the legacy v1 interpretation.

The bundled contract is explicit that the 8 × 9 atlas is only an intermediate artifact for a newly hatched v2 pet and must not be packaged as the new final output.

### Verification of the Official Surface

The current Codex app contains:

```text
/Applications/ChatGPT.app/Contents/Resources/skills/skills/.curated/hatch-pet/
```

The installed user copy is under the current user's Codex skills directory:

```text
~/.codex/skills/hatch-pet/
```

The two `SKILL.md` files have the same SHA-256:

```text
ccfabd5d761faa721586f8793dd93bdd735e2a2c07099a5d593a7e31286e58f3
```

A recursive comparison found no substantive difference between the installed skill and the current app-bundled skill. This is therefore current local Codex behavior, not an abandoned draft or an unrelated third-party implementation.

## Current Goodboy Reality

Goodboy is still v1 in executable code, not merely in old documentation.

### Hard-Coded Output Contract

`src/goodboy/contracts.py` defines:

```python
ATLAS_COLUMNS = 8
ATLAS_ROWS = 9
ATLAS_WIDTH = 1536
ATLAS_HEIGHT = 1872
```

It defines only the nine standard animation states.

### Job Planning

A local smoke run showed that Goodboy plans:

- two initial baseline candidates;
- then nine independent `row-strip` jobs;
- no cardinal-anchor job;
- no look-row jobs;
- no dependency edges between row jobs.

The states are:

1. `idle`
2. `running-right`
3. `running-left`
4. `waving`
5. `jumping`
6. `failed`
7. `waiting`
8. `running`
9. `review`

### Packaging

`src/goodboy/pipeline.py` writes a `pet.json` containing:

- `id`;
- `displayName`;
- `description`;
- `spritesheetPath`.

It does not write `spriteVersionNumber`.

The result is a legacy v1 package. It does not contain the current directional behavior.

### Public Release State

As checked on 2026-07-16:

- the latest [GitHub release](https://github.com/adamallcock/goodboy/releases) is `0.1.2`, published in May 2026;
- [PyPI](https://pypi.org/project/goodboy-codex/) also serves `0.1.2`;
- the npm launcher is also at `0.1.2`;
- current public `main` still contains the v1 contract despite a later June commit;
- the [GitHub repository](https://github.com/adamallcock/goodboy) showed one star, no forks, and no open issues or pull requests at the time of inspection;
- npm showed no dependents.

Those adoption numbers are weak market evidence, not proof that the idea is bad. They do mean there is no current external pull strong enough to justify maintaining a parallel renderer by default.

## Capability Comparison

Scores are directional judgments from the inspected code, tests, and local smokes, not quantitative benchmarks.

| Dimension | Goodboy today | Hatch Pet today | Winner |
| --- | ---: | ---: | --- |
| Current Codex package compatibility | 1/5 | 5/5 | Hatch Pet |
| Look-direction quality and QA | 0/5 | 5/5 | Hatch Pet |
| Standard-row generation guidance | 3/5 | 5/5 | Hatch Pet |
| Deterministic raster processing | 3/5 | 5/5 | Hatch Pet |
| Durable project and provenance model | 5/5 | 3/5 | Goodboy |
| Candidate and style decision history | 5/5 | 2/5 | Goodboy |
| Provider flexibility | 5/5 | 1/5 | Goodboy |
| Resume/recovery as a product primitive | 4/5 | 3/5 | Goodboy |
| Human review product | 3/5 | 2/5 | Goodboy, provisionally |
| Current visual QA rigor | 3/5 | 5/5 | Hatch Pet |
| One-task simplicity inside Codex | 2/5 | 5/5 | Hatch Pet |
| Standalone/outside-Codex portability | 5/5 | 1/5 | Goodboy |
| Maintenance and format-drift risk | 2/5 | 5/5 | Hatch Pet |
| Distribution to existing Codex users | 2/5 | 5/5 | Hatch Pet |

## Where Hatch Pet Is Materially Better

### 1. It Is the Canonical Current Implementation

The skill is bundled with Codex and implements the app's current package contract. Goodboy would have to detect and follow format changes; Hatch Pet moves with the product that consumes the output.

This is a structural advantage, not just a temporary feature gap.

### 2. The V2 Visual Job Graph Is More Sophisticated

A prepared Hatch Pet run contains thirteen visual jobs:

- one base identity job;
- nine standard animation-row jobs;
- one four-pose cardinal-anchor job;
- one coherent row-9 direction job;
- one coherent row-10 direction job.

The jobs form a dependency graph:

- standard rows depend on the canonical base;
- cardinals wait for the standard pet identity to stabilize;
- row 9 depends on approved cardinals;
- row 10 depends on approved cardinals and a registered, reviewed row 9.

Goodboy's nine row jobs are independent and have no concept of this directional dependency chain.

### 3. It Uses a Stronger Identity-Preservation Policy

Hatch Pet requires generated rows to use:

- the canonical base identity;
- the relevant layout guide;
- explicit input-role labels;
- coherent full-row generation rather than packaging individually invented cells.

It allows derivation of `running-left` only under a controlled approval path. It repairs the smallest packaging-eligible scope: a complete standard row or a complete coherent look row.

This reduces identity drift and inconsistent per-frame edits.

### 4. Its Directional QA Is Deep

Hatch Pet verifies more than atlas geometry. Its v2 pipeline includes:

- four explicit cardinal anchors;
- pet-specific look mechanics;
- exact semantic checks for all sixteen directions;
- a focused full-body and head/upper-body QA sheet;
- continuity measurements for holes, center movement, area movement, and local visual outliers;
- registered-row edge checks;
- randomized blind A/B direction challenges;
- three isolated reviewers;
- strict-majority consensus;
- an independent reviewer or explicit user inspection for repaired directions.

Goodboy has no equivalent look-direction system.

### 5. Its Extended Atlas Registration Is Safer

Hatch Pet's extended assembler:

- recovers pose groups from the original-resolution generated row;
- establishes a shared lower-body anchor and practical body scale;
- accounts for asymmetric left and right pose extents;
- resizes original crops only once;
- checks post-registration near-edge clipping;
- compares the result against a neutral cell.

This is much more robust than simply appending two rows or resizing sixteen independent cells.

### 6. Its Chroma Cleanup Has a Stricter Contract

Hatch Pet uses a single final, deterministic, linear-light, edge-local chroma despill pass and tests that it is applied only once. This avoids repeated color damage and green/magenta halos.

Goodboy has useful transparency, residue, chroma, clipping, centering, and duplicate-frame checks, but it does not implement the same v2 edge-treatment contract.

### 7. It Has Focused Regression Tests for the Hard Parts

The local Hatch Pet suite has 28 passing tests covering:

- extended-atlas assembly;
- shared scale and asymmetric safe fitting;
- post-registration edge failure;
- chroma matte decontamination;
- the single-final-despill rule;
- direction-blind consensus and acceptance;
- look-row prompt constraints.

These tests target exactly the v2-specific risks Goodboy lacks.

## Where Goodboy Is Materially Better

### 1. Source Ingest and Provenance

Goodboy treats source images as durable inputs rather than incidental attachments. It records enough information to identify, deduplicate, inspect, and later audit the inputs.

This is valuable for repeatable production and team workflows. It is excessive for a one-off pet.

### 2. Baseline Alternatives and Character Selection

Goodboy explicitly plans multiple baseline candidates, records provider and style intent, builds a candidate contact sheet, and saves the selected identity as a character card.

Hatch Pet creates or selects a base identity, but it does not expose the same reusable candidate-management product.

### 3. Feedback and Decision Records

Goodboy records feedback as structured events and can create branch manifests associated with a target and parent.

This is a useful start for non-destructive iteration. It should not be overstated: current “branches” are metadata records, not a complete copy-on-write asset graph or replay engine.

### 4. Provider Invocation Evidence

Goodboy records:

- adapter/provider;
- model alias;
- prompt and input image hashes;
- input roles;
- request metadata;
- status and error state;
- output paths;
- retry metadata;
- optional raw response location and cost slot.

This is a strong foundation for reproducibility and provider comparison.

The direct adapters are still thin and were not live-smoked against real provider credentials in this audit. Their existence is verified; production reliability across providers is not.

### 5. A Higher-Level Workflow API

`goodboy start` and `goodboy advance --agent-mode` are better product APIs than a long sequence of implementation commands.

This abstraction is worth keeping. A future Goodboy should make the underlying v2 graph easier to operate, not replace it with a simpler but weaker graph.

### 6. Review, Install, and Export Governance

Goodboy has explicit approval state, install policy, archive behavior, and export formats. This makes it a more plausible foundation for:

- a local pet studio;
- a team production tool;
- a batch or hosted workflow;
- a provider comparison harness;
- a Petdex/library manager.

## Important Goodboy Limitations

Goodboy's advantages are partly architectural intent rather than fully delivered product advantage.

### V1 Is a Release-Blocking Gap

Any new release that still presents Goodboy as a current Codex pet builder would be misleading. The CLI, skill, docs, examples, exports, and Review Room all need a v2-compatible path.

### The Review Room Is Not Yet the Primary Workflow

The frontend has useful screens and passing tests, but opening real projects and mutating the backend are not fully wired. The CLI remains the source of truth.

Until the UI can operate a real v2 run, “better human review UX” is a promising advantage, not a proven one.

### Provider Breadth Creates Maintenance Burden

Every provider adds:

- request format drift;
- model-name drift;
- image input/output differences;
- authentication and retry behavior;
- quality variance;
- safety and policy variation.

Provider neutrality is only an advantage if it is tested and actively maintained.

### Parallel Visual Logic Is a Liability

Goodboy and Hatch Pet both contain machinery for:

- prompt/job preparation;
- strip extraction;
- atlas composition;
- transparency cleanup;
- previews;
- visual QA;
- package validation.

Maintaining a weaker independent implementation creates duplicated bugs and continuous format drift. Goodboy should own orchestration and durable state while sharing or conforming to the canonical visual backend.

### Public Demand Is Not Yet Proven

Current package and repository adoption is minimal. The project should not assume a broad standalone-tool market without testing whether users value:

- provider choice;
- project history;
- a visual studio;
- team review;
- exporting and managing multiple pets.

## Migration Is More Than Adding Two Rows

A correct v2 migration requires all of the following.

### Contract and Schema

- Introduce an explicit, versioned output-contract model.
- Make v2 the default for new projects.
- Retain v1 only for legacy import and upgrade.
- Add 11-row dimensions and sixteen fixed look directions.
- Add `spriteVersionNumber: 2` to package manifests.
- Validate that atlas size and manifest version agree.

### Job Graph

- Add a canonical base job.
- Preserve the nine standard-row jobs.
- Add the four-pose cardinal job.
- Add coherent row-9 and row-10 jobs.
- Represent dependencies and readiness explicitly.
- Prevent row 10 from starting before row 9 clears the required gates.

### Visual Processing

- Add cardinal extraction and approval.
- Add row-level look registration.
- Add shared-scale and lower-body anchoring.
- Add post-registration edge checks.
- Add extended-atlas assembly.
- Replace or reconcile Goodboy's chroma cleanup with the one-final-pass rule.
- Prevent individual generated look-cell mosaics for new pets.

### QA

- Add a look-mechanics artifact.
- Add semantic evidence for all directions.
- Add focused look-direction contact sheets.
- Add continuity measurements.
- Add blind direction challenges and consensus.
- Add independent review requirements for repairs.
- Gate installation on v2-specific QA.

### Product and UI

- Update the Review Room viewer from nine rows to eleven.
- Add an interactive sixteen-direction preview.
- Surface cardinal, semantic, continuity, and blind-review status.
- Show job dependencies and next-ready work.
- Update approvals, exports, demos, screenshots, and documentation.

### Existing Project Migration

Hatch Pet already supports upgrading an approved 8 × 9 atlas by preserving rows 0–8 and adding rows 9–10. Goodboy should use that bounded path:

1. classify an existing run as legacy v1;
2. preserve and revalidate the original nine rows;
3. derive a canonical neutral/base reference;
4. generate and approve the cardinal anchors;
5. generate, register, and validate rows 9 and 10;
6. emit a new v2 run and package without mutating the original v1 artifacts;
7. retain provenance linking the v2 run to its v1 source.

## Recommended Architecture

Goodboy should become a **contract-aware pet production shell**:

```mermaid
flowchart LR
    A["Goodboy project, sources, candidates, style"] --> B["Versioned pet contract"]
    B --> C["Canonical v2 visual job graph"]
    C --> D["Codex imagegen or provider adapter"]
    D --> E["Canonical deterministic assembly and QA"]
    E --> F["Goodboy Review Room and approvals"]
    F --> G["Install, export, archive, Petdex"]
```

The ownership boundary should be:

### Goodboy Owns

- project lifecycle;
- source and identity records;
- candidate selection;
- provider adapters and invocation evidence;
- durable job state and recovery;
- feedback, approvals, and review UX;
- exports, installation, archiving, and library management.

### Canonical V2 Backend Owns

- animation and direction contract;
- visual job dependencies;
- row prompt constraints;
- extraction and registration;
- chroma treatment;
- direction semantics and continuity;
- atlas validation;
- package conformance.

Goodboy should not hard-depend on the absolute application bundle path. Viable integration approaches, in preference order, are:

1. extract or contribute a shared versioned library/contract that both workflows can call;
2. vendor a clearly identified, tested snapshot of the canonical deterministic scripts with an automated conformance/drift check;
3. add a discoverable Hatch backend adapter when running inside Codex, with a standalone tested fallback.

Copying pieces informally without a sync strategy would reproduce the current drift.

## Next Validation Slice

Do not begin with a broad rewrite. Build one end-to-end vertical slice:

1. Add a versioned `v2` output contract and package manifest.
2. Import one completed Goodboy v1 demo project.
3. Preserve and validate its nine existing rows.
4. Use the canonical v2 flow to add cardinal anchors and two coherent look rows.
5. Assemble and validate a `1536 × 2288` atlas.
6. Pass the official v2 deterministic tests and package checks.
7. Display all sixteen directions in the Review Room.
8. Record the upgrade, provider inputs, QA evidence, approval, and export in the Goodboy project.

### Success Criteria

Continue Goodboy if the slice proves that it:

- produces a package accepted under the official v2 contract;
- does not weaken Hatch Pet's visual QA;
- preserves a meaningfully better audit and recovery trail;
- reduces the manual coordination required to resume or revise a run;
- exposes a useful visual review experience;
- keeps providers replaceable without corrupting the contract.

### Stop Criteria

Stop or archive Goodboy if:

- v2 parity requires maintaining a permanently divergent renderer;
- the Review Room remains a demo rather than the real workflow;
- provider portability is not used or requested;
- Goodboy adds more setup and failure modes than the durable state saves;
- the only demonstrated user need is “make me a Codex pet.”

## Validation Performed

### Goodboy

Python:

```text
python -m unittest discover -s tests -v
45 passed, 3 skipped
```

The skips were environmental/optional:

- one absent optional legacy fixture;
- two FastAPI tests skipped because the selected local runtime did not include the optional FastAPI dependency.

Skill validation:

```text
scripts/validate_skills.py codex-skill/goodboy plugins/goodboy/skills/goodboy
Skills are valid.
```

UI:

```text
npm run typecheck
passed

npm run build
passed

npm run test:e2e
5 passed
```

The tests cover project initialization, ingest/provenance, candidates, style, feedback records, workflow progression, provider invocation metadata, imports, raster processing, QA/install policy, approvals, exports, plugin wiring, and the Review Room demo.

### Hatch Pet

```text
python -m unittest discover -s ~/.codex/skills/hatch-pet/tests -v
28 passed
```

The tests cover the v2 extended atlas, safe pose fitting, registration edges, chroma decontamination, one-pass cleanup, look-row prompts, and blind direction consensus.

### Comparative Smoke

Using the same public Goodboy demo source:

- Goodboy prepared an 8 × 9 project and nine independent row jobs.
- Hatch Pet prepared an 8 × 11 v2 project and thirteen dependency-aware visual jobs.
- Goodboy had no look-direction artifacts.
- Hatch Pet emitted `sprite_version_number: 2`, cardinal and look-row prompts, dependency metadata, and v2 assembly/QA expectations.

## Final Recommendation

| Question | Answer |
| --- | --- |
| What should create a pet today? | Use the bundled Hatch Pet skill. |
| Does Goodboy have an advantage today as a renderer? | No. It is behind the current contract and visual QA. |
| Does Goodboy have a defensible product advantage? | Yes: durable projects, provider portability, workflow recovery, approvals, exports, and a potential visual studio. |
| Should Goodboy implement its own alternative v2 renderer? | No. Adopt or share the canonical v2 machinery. |
| Should Goodboy continue? | Only through a narrow v2 wrapper/orchestration slice with explicit success and stop criteria. |
| Hard strategic verdict | **Wrap/adopt Hatch v2; freeze the independent v1 path. Stop entirely if the orchestration and Review Room advantage cannot be proven.** |
