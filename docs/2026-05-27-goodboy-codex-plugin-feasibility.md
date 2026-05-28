---
title: Goodboy Codex Plugin Feasibility
date: 2026-05-27
type: decision-record
status: accepted
---

# Goodboy Codex Plugin Feasibility

## Decision

Goodboy should ship a repo-scoped Codex plugin now, with a narrow first implementation: package the existing Goodboy skill and expose it through a repo marketplace. The plugin is feasible and useful for distribution, discoverability, and keeping Codex agents on the safe `start`/`advance` rails.

The plugin should not claim to provide a rich visual review UI yet. Candidate-grid review, animated preview browsing, and point-and-click approval remain better served by generated local artifacts and, later, an optional local web UI unless Codex plugin UI surfaces become richer for image-heavy workflows.

## Evidence

OpenAI's Codex plugin documentation says a local skill is the right starting point for one repo or one personal workflow, and a plugin becomes appropriate when the workflow should be shared, bundled with app integrations or MCP config, lifecycle hooks, or published as a stable package.

The same documentation defines the required plugin entry point as `.codex-plugin/plugin.json`, with optional `skills/`, `hooks/`, `.app.json`, `.mcp.json`, and `assets/` at the plugin root. This matches Goodboy's current maturity: the CLI and skill are stable enough to package, while MCP/hooks/apps are optional future additions.

The docs also define repo marketplaces at `$REPO_ROOT/.agents/plugins/marketplace.json`, with plugin sources under `$REPO_ROOT/plugins/` and `source.path` pointing at `./plugins/<plugin-name>`. That is the chosen implementation shape for Goodboy.

Sources:

- OpenAI Codex build plugins documentation: `https://developers.openai.com/codex/plugins/build`
- Local plugin creator validator: `$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py`

## Requirements Checked

### Can the plugin present image grids?

Not directly in this first slice. The documented plugin package structure supports install-surface metadata, bundled skills, MCP servers, apps/connectors, hooks, and assets. It does not itself replace Goodboy's generated contact sheets, GIF previews, edge previews, or centering overlays.

Decision: keep visual review as file artifacts for now. Revisit with a local web UI or app integration if Codex plugin app surfaces become appropriate.

### Can it call built-in image generation directly?

Not as a direct plugin API in the documented package surface. Goodboy should continue using the `codex_builtin` handoff path for built-in Codex image generation and the direct OpenAI/Gemini adapters when API keys are intentionally configured.

Decision: package orchestration and guardrails in the plugin; keep provider calls in Goodboy adapters and Codex handoff.

### Can it manage local files safely?

Yes, through the Goodboy CLI and existing manifest-first project folders. The plugin bundles the skill that tells agents to use `goodboy start`, `goodboy advance --agent-mode`, `import-generated`, visual approval, install policy, and validation rather than shell loops or ad hoc renderer scripts.

Decision: use the plugin as a safe workflow steering layer over the CLI, not as a new file mutation engine.

### Can it install into `~/.codex/pets` with user approval?

Yes, indirectly through Goodboy's install policy and installer. The plugin itself does not bypass approval; it preserves the current requirement for recorded visual approval, row provenance, QA policy, and renderer-script scan.

Decision: install remains owned by `goodboy advance`/`finish` and Goodboy install policy.

### Can it maintain resumable job state?

Yes, by relying on Goodboy's durable manifests: `workflow-state.json`, source/candidate/job/provider manifests, QA reports, approval records, run summaries, and package manifests.

Decision: plugin state should be derived from project files, not duplicated in plugin-private state.

## Implemented First Slice

The accepted plugin slice is:

- `plugins/goodboy/.codex-plugin/plugin.json`
- `plugins/goodboy/skills/goodboy/SKILL.md`
- `.agents/plugins/marketplace.json`

This provides:

- repo marketplace discovery
- plugin install metadata
- a bundled Goodboy skill
- starter prompts
- safe-agent workflow guidance

## Deferred Work

- bundled MCP server for structured Goodboy status/project tools
- hooks for optional session-start context loading
- app/connectors or local web UI for richer candidate/QA review
- official/public plugin directory packaging once self-serve publishing is available

## Completion Criteria

This spike is complete when:

- the plugin package validates with the plugin creator validator
- the repo marketplace validates structurally
- docs and tracking mark the first plugin slice complete
- the normal Goodboy unit suite still passes
- no local pet project artifacts are accidentally tracked

