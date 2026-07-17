---
title: Goodboy V1 To V2 Migration
date: 2026-07-16
type: migration-guide
status: current
---

# Goodboy V1 To V2 Migration

Goodboy v1 produced an 8 × 9 atlas containing the nine standard animation states. Codex pet v2 requires an 8 × 11 atlas with two additional rows containing sixteen 22.5-degree look directions.

The migration policy is preservation first: do not regenerate an already approved v1 character merely to add the v2 direction rows.

## Preconditions

A migratable project needs:

- `goodboy.json`;
- a readable 1536 × 1872 v1 atlas in a prior run;
- an emotion style sheet;
- preferably the selected baseline and confirmed identity profile;
- provider consent if source derivatives will be reused.

Goodboy searches the active run first, then other runs from newest to oldest. Supported v1 atlas locations include standard final and package paths.

## Start The Upgrade

```bash
goodboy upgrade <project-dir> \
  --target-contract codex-pet-v2 \
  --provider codex_builtin \
  --model-alias codex-imagegen \
  --run-id <migration-run-id>
```

This action:

1. archives the original `goodboy.json`;
2. writes a migration receipt;
3. copies the selected v1 atlas into `runs/<run-id>/migration-input/`;
4. creates lossless standard PNG and WebP intermediates;
5. extracts the first visible idle cell as the registration reference;
6. records file and RGBA hashes;
7. plans only `look-cardinals`, `look-row-9`, and `look-row-10`;
8. marks the project `awaiting-v2-look-rows`.

No v1 file is changed in place.

## Complete The Three-Job Graph

```text
look-cardinals ──> look-row-9 ──> look-row-10
        └──────────────────────────────^
```

Use the normal commands:

```bash
goodboy generate-handoff <project-dir> --run-id <run-id> --all
goodboy import-generated <project-dir> --run-id <run-id> --map <map.json>
goodboy build-review <project-dir> --run-id <run-id> --row-provenance provider_generated
```

Rows 0–8 come from the preserved standard atlas. Only the direction assets are provider-generated.

## Preservation Evidence

The migration run records:

- source file SHA-256;
- pre-assembly standard RGBA hash;
- post-assembly rows 0–8 RGBA hash;
- whether those pixels remained identical;
- a note when the required one-pass final chroma cleanup changes edge pixels without changing poses or layout.

The final cleanup is intentionally applied to the full v2 atlas once. Therefore, byte or pixel identity is evidence when it holds, but a small edge-only difference is not automatically data loss.

## Completion

After a successful v2 build:

- `goodboy.json` declares `codex-pet-v2`;
- `migration_state` becomes `current`;
- `migration-receipt.json` gains `completed_run_id` and `completed_at`;
- `requires_generation` becomes false;
- the package contains `spriteVersionNumber: 2`;
- the atlas is exactly 1536 × 2288.

The original manifest, original atlas copy, migration input, standard intermediate, and hashes remain available for audit.

## Failure And Retry

If a provider call is interrupted:

```bash
goodboy recover <project-dir> --run-id <run-id>
```

If a direction row fails:

```bash
goodboy repair <project-dir> \
  --run-id <run-id> \
  --job-id look-row-9 \
  --reason "<visible failure>"
```

Repair archives the failed row and invalidates row 10 because it depends on row 9 continuity. It does not invalidate the preserved v1 standard atlas.

## No V1 Atlas Found

Goodboy still archives and updates the manifest, but the receipt reports `preserved_v1_atlas_found: false`. The project remains `awaiting-v2-look-rows` without a migration run. Do not claim that migration is complete. Recover or supply the missing approved v1 atlas before continuing.
