---
title: Goodboy Privacy And Data Handling
date: 2026-07-16
type: reference
status: current
---

# Goodboy Privacy And Data Handling

Goodboy projects may contain private pet photos, personal filenames, generated identity art, provider metadata, and installation artifacts. The public repository must never contain user projects under `projects/` or equivalent local output trees.

## Data Classes

| Data | Default location | Provider eligible | Default project export | Diagnostic export |
| --- | --- | --- | --- | --- |
| Original source images | `sources/originals/` | Never | Excluded | Excluded |
| Thumbnails | `sources/thumbnails/` | Never | Excluded | Excluded |
| EXIF-stripped derivatives | `sources/provider-derivatives/` | Only with current consent and permission | Excluded | Excluded |
| Source manifest/card | `sources/*.json` | Local orchestration only | Excluded | Excluded |
| Identity profile | `identity/identity-profile.json` | Compiled into prompts | Included | Excluded unless needed as redacted structure |
| Source comparison sheets | `identity/` and run `qa/` | No | Excluded | Excluded |
| Generated baselines/rows | `candidates/`, `character/`, `runs/` | Provider outputs | Included when part of project/run | Excluded |
| Provider prompts | run `prompts/` | Yes | Included in project export | Excluded |
| Raw provider responses | run `provider-invocations/` | Provider-originated | May remain in a full project export | Excluded |
| Codex package | run `package/` | No | Included | Metadata only |

## Consent

Source images do not become provider inputs merely because they were ingested.

Consent is:

- explicit;
- provider-specific;
- recorded in `decisions/provider-consent/<provider>.json`;
- bound to each source hash and derivative hash;
- invalidated in practice when the source or derivative no longer matches its receipt;
- further restricted by per-source `provider_permissions`.

The consent receipt records source IDs and hashes, not raw credentials.

## Provider Derivatives

Goodboy:

1. opens the local source;
2. applies EXIF orientation;
3. converts it to RGBA;
4. writes an optimized PNG;
5. omits EXIF metadata;
6. hashes the derivative;
7. uses only the consented derivative path in candidate, identity-analysis, and animation handoffs.

Validation rejects original-source paths in provider candidate or generation job inputs.

## API Keys

OpenAI and Gemini keys are read from environment variables:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Goodboy does not write raw keys into manifests, logs, reports, exports, or memory. Users should prefer a persistent secret manager or shell environment over `.env` files inside the repository.

## Export Modes

### Project

```bash
goodboy export project <project-dir> --run-id <run-id>
```

Default behavior:

- excludes the source tree;
- excludes source contact sheets and likeness sheets containing source pixels;
- normalizes machine-local deterministic paths;
- includes the selected run and reusable project metadata.

The resulting project is useful for review and handoff but cannot recreate source-aware provider calls until source references are deliberately reattached.

Explicit inclusion:

```bash
goodboy export project <project-dir> \
  --run-id <run-id> \
  --include-sources
```

This copies originals, thumbnails, provider derivatives, source manifests, and source-bearing review media. Treat it as private material.

### Petdex

```bash
goodboy export petdex <project-dir> --run-id <run-id>
```

Contains:

- `pet.json`
- `spritesheet.webp`
- export metadata and README

It does not contain source images or prompts.

### Diagnostic

```bash
goodboy export diagnostic <project-dir> --run-id <run-id>
```

Diagnostic bundles omit:

- all raster images;
- source manifests and source pixels;
- prompts;
- raw provider responses;
- request IDs;
- input hashes;
- API keys and credential-like strings.

Paths in job inputs are classified into redacted categories such as canonical baseline, layout guide, cardinal anchors, or generated row.

The built-in scanner blocks the diagnostic export if it finds a supported image suffix or common credential pattern.

## Public Issue Reports

Before posting a bug report:

- use the diagnostic export when possible;
- do not attach project exports unless reviewed;
- do not attach screenshots containing source photos without permission;
- redact pet/user names if they are identifying;
- remove local home-directory paths;
- never include `.env`, provider response files, account identifiers, or keys.

## Limitations

Goodboy cannot guarantee that a third-party image provider will not retain data after receiving a consented derivative. Provider retention and training policies are controlled by that provider. Review those policies before granting consent.

The source-free project export protects source pixels, not every descriptive identity fact. Identity profiles and prompts may contain textual descriptions of markings, breed, accessories, or other traits. Use the diagnostic export for a more aggressively sanitized support bundle.
