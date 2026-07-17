---
title: Goodboy V2 Implementation Audit
date: 2026-07-16
updated: 2026-07-17
type: audit
status: current
---

# Goodboy V2 Implementation Audit

## Decision

The source-faithful Goodboy v2 release path is code-complete and
release-candidate ready. It creates exact Codex pet v2 workspaces, preserves or
upgrades v1 work, runs the pinned Hatch-compatible backend, records a durable
job graph, enforces direction and likeness review, supports targeted repair,
serves the operational Review Room, and produces installable and source-safe
packages.

The plugin-first installation path is also code-complete: the public marketplace
selector is `goodboy@goodboy`, the plugin and runtime are pinned to the same
version, installation is an explicit consent gate, and every run revalidates
the executable. This remains a release candidate rather than a public 0.2.0
release until the matching PyPI distribution, Git tag, and GitHub release are
published in that order.

Goodboy is not yet entitled to claim empirically better source likeness or
animation than Hatch Pet. A real public-domain Socks pilot and independent
reviews now exist, but both frozen arms failed different direction gates before
a valid matched package existed. The later successful Goodboy package is an
explicitly out-of-budget mechanism diagnostic, not comparative evidence. A
licensed or consented multi-identity cohort must still be collected rather than
simulated.

## Plan Alignment

- [x] Milestone 0 — v1 is an import/maintenance surface; the exact v2 contract,
  pinned Hatch snapshot, license, hashes, fixtures, and capability comparison
  are recorded.
- [x] Milestone 1 — v1 and v2 contracts are registered; new workspaces default
  to v2; legacy fields migrate in memory; unknown legacy fields are preserved
  under `legacy_compat`; upgrades archive originals and write receipts.
- [x] Milestone 2 — the vendored Hatch-compatible backend owns extraction,
  cardinal anchors, registered look rows, extended assembly, direction QA,
  one-pass despill, and exact package validation.
- [x] Milestone 3 — generation uses validated states, dependencies, per-job
  timestamps, an append-only event log, atomic writes, project locking,
  idempotent readiness, interruption recovery, and dependency-scoped repair.
- [x] Milestone 4 — sources have roles, coverage, quality, and permissions;
  identity traits link to evidence and require confirmation; likeness
  candidates hold style constant; style is selected separately; prompts and
  reference packs carry the locked identity into every job.
- [x] Milestone 5 — source/baseline/state review media, advisory cross-state
  drift signals, trait-level verdicts, signature-trait vetoes, identity
  patches, job-scoped repair, JSON and Markdown likeness receipts, approvals,
  repair history, and run lineage are implemented.
- [ ] Milestone 6 — **partially implemented**. Protocol freezing,
  randomization, identity-clustered analysis, package validation, confidence
  intervals, unacceptable-output vetoes, and claim withholding are complete.
  The Socks pilot exercised the protocol with real licensed/public-domain
  sources and isolated reviewers, correctly produced no winner when both arms
  failed, and demonstrated Goodboy's repair mechanism out of budget. A real
  multi-identity release cohort remains external.
- [ ] Milestone 7 — **partially implemented beyond the release path**. The My
  Pet Review Room is operational for project/source/identity/candidate/style/
  generation/recovery/repair/QA/approval/install/export actions and has
  keyboard plus browser tests. A persistent cross-project Pet Library,
  arbitrary existing-v2-package import, and dedicated old-versus-repaired run
  comparison remain later product work.
- [ ] Milestone 8 — **partially implemented**. Codex, OpenAI, and Gemini
  capabilities, reference budgets, immutable snapshots, dry runs, direct
  execution, request IDs, latency, usage, failures, and routing-profile
  primitives exist. Official-SDK multi-turn editing, a local provider, and
  credentialed live conformance runs remain deferred.
- [ ] Milestone 9 — **partially implemented pending publication**. Skills,
  docs, privacy guidance, migration guidance, release checks, wheel/sdist/npm
  packaging, a sanitized diagnostic bundle, and a three-version Python CI
  matrix are present. Publishing artifacts and publishing empirical benchmark
  results require explicit release authority and real evidence.

## Release-Critical Backlog

- [x] Versioned 11-row v2 contract and `spriteVersionNumber: 2`.
- [x] Canonical v2 backend, cardinals, look rows, direction and continuity QA.
- [x] Dependency-aware workflow, recovery, and v1 migration.
- [x] Evidence-linked identity, controlled likeness choice, separate style
  choice, identity pack, trait gates, receipt, and targeted repair.
- [x] Operational source-safe Review Room and shared CLI/backend actions.
- [x] Privacy-safe exports, explicit provider consent, and install review.
- [ ] Better-likeness release claim — blocked only on the predeclared real
  multi-identity benchmark evidence.

## Logical Completeness

- Core source contains no `TODO`, `FIXME`, `HACK`, `NotImplemented`, or
  provider-image placeholder implementation.
- Missing generated images remain explicit provider gates. Contact-sheet
  placeholder cards indicate “not generated”; they are not accepted as pet art.
- No Pillow drawing fallback, SVG/canvas renderer, or individual final-cell
  patch path was introduced.
- Read-only Review Room state retrieval is byte-stable and does not rewrite job
  timestamps or append events.
- Provider ambiguity after interruption blocks for user resolution instead of
  silently repeating potentially billable work.
- Final installation recomputes package, direction, likeness, provenance,
  visual-approval, and suspicious-renderer gates from source artifacts.

## Pathway Coverage

Covered:

- new source-led My Pet projects;
- manual or multimodal identity-analysis import;
- controlled likeness candidates and independent style choice;
- Codex handoff plus optional OpenAI and Gemini direct adapters;
- dependency-wave output import and deterministic v2 assembly;
- interrupted runs and targeted row/identity repair;
- non-destructive v1 atlas upgrade preserving rows 0 through 8;
- direction, blind-direction, likeness, visual, and install gates;
- Review Room and CLI actions over the same application functions;
- Petdex, source-free project, explicit private project, and sanitized
  diagnostic exports;
- frozen blinded benchmark preparation, rating import, analysis, and claim
  vetoes.

Intentionally deferred:

- a separate Quick Hatch renderer or workflow; users wanting the shortest
  non-identity path should use Hatch Pet directly;
- persistent Pet Library/uninstall management across arbitrary install roots;
- arbitrary third-party v2 package adoption without a Goodboy project;
- local image generation, provider SDK multi-turn sessions, and heavyweight
  learned likeness metrics;
- multi-identity benchmark recruitment and live credentialed provider smokes.

## Contract And Interface Completeness

- Python, CLI, web request models, TypeScript API calls, packaged static UI,
  Codex skill copies, plugin metadata, npm launcher, and public docs identify
  version `0.2.0`.
- The plugin runtime contract independently identifies `goodboy-codex[ui]`,
  refuses missing or mismatched versions, requires an explicit approval marker
  before uv installation, verifies the post-install executable, and routes all
  CLI arguments without a shell.
- New workspace and job fields have defaults and migration behavior.
- Candidate evaluation dimension is validated and available through Python,
  CLI, and web interfaces.
- The Review Room is bundled into the wheel and served only on loopback with
  trusted-host enforcement.
- UI dependencies are locked; the dependency audit is clean.
- The Python UI extra uses `httpx2`, matching the current FastAPI/Starlette test
  client contract.
- The Apache-2.0 Hatch snapshot and license are present alongside Goodboy's MIT
  license in the source and wheel distributions.

## Verification Evidence

- Python discovers 84 tests. In the base environment, 78 pass and six skip:
  five require the optional UI dependency set and one requires a user-supplied
  legacy row fixture. The five UI API tests independently pass in the UI
  environment, leaving only the intentional external-fixture skip unexercised.
- The pinned Hatch snapshot passes hash, exact-contract, official-preparer, and
  Goodboy dependency-order conformance tests. Identity-version repair,
  animation evidence, candidate fidelity, provider failure, recovery, export,
  migration, and saved blind-review state all have focused passing tests.
- Fourteen Node regression tests cover exact, missing, mismatched, invalid,
  denied, uv-missing, successfully installed, replaced, failed,
  post-install-unverified, and guarded plugin-runtime states, plus exact-version
  npm discovery and mismatch refusal.
- The Review Room passes TypeScript checking, deterministic production build,
  packaged-static freshness, and 12 Playwright flows. Those flows include exact
  duration-boundary playback for every state, reduced motion, active-run asset
  selection, saved animation/direction/likeness evidence, saved blind-review
  validation, shared backend actions, and approval gating.
- A clean dependency audit reports zero UI vulnerabilities. `compileall` passes
  for source and tests.
- Final source and wheel CLI validation report zero issues for the Socks
  project. A clean wheel installed into a fresh Python 3.14 environment, reported
  `goodboy 0.2.0`, and validated 74 persisted project files with zero issues.
- Fresh wheel and sdist builds contain the vendored Hatch license and integrity
  manifest plus the packaged Review Room; the sdist also contains the Codex
  skill, plugin runtime contract, runner, and runner tests. Both repository
  skill copies and the active standalone install validate and are byte-identical.
  The npm dry-run contains only its README, package manifest, and executable
  launcher.
- An empty temporary Codex home added the local marketplace, installed
  `goodboy@goodboy` 0.2.0 into its plugin cache, and ran only that cached
  runner. With the global Goodboy bin deliberately absent from `PATH`, the
  runner discovered a fresh 0.2.0 wheel in isolated uv tool/bin directories,
  reported the exact match, created a synthetic project, stopped at the
  identity/provider-consent gate, and imported the packaged UI dependencies.
- The real local Codex installation now has `goodboy@goodboy` 0.2.0 enabled;
  its cached runner verifies and executes `goodboy 0.2.0`. A public-registry
  bootstrap remains a release gate because 0.2.0 has not yet been published.
- The packaged Review Room was opened against the actual Socks project. The
  repaired spritesheet returned HTTP 200; Waiting traversed all six frames,
  Active task all six, and Failed all eight with exact contract durations; the
  browser console had zero messages, warnings, or errors.
- The Socks continuation produces an exact 1536 × 2288, 8 × 11 v2 package.
  Three isolated animation reviews finish at four pass, five warning, zero
  fail; direction review finishes at 12 pass, four warning, zero fail; and
  likeness finishes at 10 pass, three warning, zero fail. Human final visual
  approval and installation remain blocked by design.
- Explicit ignore rules cover private project workspaces, benchmark cohorts,
  credentials, build output, and browser-test artifacts.

## Summary

- Milestones fully implemented: 6
- Milestones partially implemented: 4
- Release-critical engineering items implemented: 6 of 6
- External comparative claim gate implemented: yes
- Single-identity real mechanism evidence collected: yes
- Valid matched comparative evidence collected: no
- Risk level for v2 compatibility and the local release path: low
- Risk level for any “better than Hatch Pet” claim: high until a valid
  multi-identity frozen comparison passes
