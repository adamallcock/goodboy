---
title: Plugin-First Installation And Publishing
date: 2026-07-17
type: guide
status: implemented
---

# Plugin-First Installation And Publishing

## Decision

The Codex plugin is Goodboy's primary user-facing installation surface. A user
adds the plugin first and then asks Codex to use Goodboy. The user does not need
to discover or run a Python package-manager command before installing the
plugin.

The Python distribution remains a separate, isolated runtime because the
plugin is an agent workflow package while `goodboy-codex` owns the pipeline,
Review Room server, Pillow processing, manifests, migration, QA, and exports.
The plugin and runtime are released at the same version and the plugin refuses
to operate a different runtime version.

## User Installation

For a released version:

```bash
codex plugin marketplace add adamallcock/goodboy --ref v0.2.0
codex plugin add goodboy@goodboy
```

For a local checkout:

```bash
codex plugin marketplace add /absolute/path/to/goodboy
codex plugin add goodboy@goodboy
```

The user can then attach pet images and ask:

> Use Goodboy to make a Codex pet from these photos.

No manual runtime command precedes these steps.

## First-Use State Machine

The plugin skill derives its plugin root and runs:

```bash
node "<plugin-root>/scripts/goodboy-runtime.mjs" check
```

| State | Exit | Meaning | Allowed next action |
| --- | ---: | --- | --- |
| `ready` | 0 | Exact `goodboy 0.2.0` found | Run the requested workflow |
| `missing` | 10 | No runtime found | Explain and ask to install |
| `mismatch` | 11 | Another Goodboy version found | Explain and ask to replace or update |
| `invalid` | 12 | Executable failed or version was unreadable | Diagnose; do not run it |
| `approval_required` | 20 | Install called without consent marker | Stop and ask the user |
| `uv_missing` | 21 | Approved Goodboy install cannot use uv | Ask separately about installing uv or another method |
| `install_failed` | 22 | uv did not complete | Report the actual failure |
| `post_install_failed` | 23 | Install returned success but exact runtime was not verified | Stop; never claim success |

When installation is needed, Codex must tell the user the found and expected
versions and the exact package `goodboy-codex[ui]==0.2.0`. Only after direct
approval may it run:

```bash
node "<plugin-root>/scripts/goodboy-runtime.mjs" install --user-approved
```

The runner invokes `uv tool install "goodboy-codex[ui]==0.2.0"` without a shell
and without `--force`, rechecks the executable from uv's tool bin, and reports
ready only after `goodboy --version` returns the exact plugin version. The agent
then continues the original request; the user does not repeat it.

Every workflow command runs through the same checked runner:

```bash
node "<plugin-root>/scripts/goodboy-runtime.mjs" run -- start ...
```

`check` and `run` contain no installation path. Installing the plugin, asking
for a pet, or approving provider image generation is not runtime-installation
consent. Approval to install Goodboy is also not approval to download or run a
uv installer.

## Why uv Is Still Behind The Plugin

uv gives Goodboy an isolated tool environment, honors the package's Python
requirement, exposes a stable tool-bin directory, and can recreate an exact
version. It is an implementation detail of the approved bootstrap, not a
prerequisite the user must run before adding the plugin.

Bundling the entire Python engine into the skill would duplicate release
artifacts, weaken dependency isolation, and make security and rollback behavior
harder to inspect. Silently installing during `codex plugin add` would also
erase the consent boundary. Plugin first, explicit bootstrap on first use, and
exact version verification preserve both usability and control.

## Sharing Goodboy

Send another user the two released-install commands above or link them to the
repository README. Pinning `--ref v0.2.0` makes their plugin instructions and
runtime contract reproducible. To update, add or upgrade the marketplace at a
new release tag and update the plugin. To roll back, point the marketplace at a
prior tag; on next use, Goodboy reports the runtime mismatch and asks before
changing the installed runtime.

Do not share local plugin-cache directories, virtual environments, pet project
folders, source photos, or generated provider artifacts. The Git tag plus PyPI
distribution are the public delivery units.

## Maintainer Release Order

The Git plugin must never point at a runtime version that is unavailable from
the package registry. npm publication is delegated to the dedicated
`.github/workflows/publish-npm.yml` workflow through npm trusted publishing;
there is no long-lived `NPM_TOKEN` or `NODE_AUTH_TOKEN` secret. Release in this
order:

1. synchronize `pyproject.toml`, `src/goodboy/__init__.py`, the plugin manifest,
   `plugins/goodboy/runtime.json`, the npm package, skill instructions, and docs;
2. run Python, plugin-runtime, npm-launcher, UI, skill, build, and clean-install
   verification;
3. publish `goodboy-codex[ui]==<version>` to PyPI and verify a clean uv tool
   install from the public registry;
4. create and push the signed or annotated Git tag `v<version>` from the exact
   commit on `main`; the tag starts the npm workflow;
5. wait for the npm workflow to publish the matching
   `@adamallcock/goodboy@<version>`, then verify its `latest` dist-tag and
   downloaded tarball before creating the GitHub release;
6. create the GitHub release for the already-published tag;
7. from a clean Codex home, add `adamallcock/goodboy --ref v<version>`, install
   `goodboy@goodboy`, and exercise first-use check plus one safe CLI command;
8. only then announce the release commands.

The marketplace name is `goodboy`, the plugin name is `goodboy`, and the public
selector is therefore `goodboy@goodboy`.

## npm Trusted Publishing

The npm package `@adamallcock/goodboy` trusts exactly this GitHub Actions
identity:

- owner and repository: `adamallcock/goodboy`;
- workflow filename: `publish-npm.yml`;
- GitHub environment: `npm`;
- allowed npm action: `npm publish` only.

The workflow is publish-capable only for `v*` tag events. Before requesting an
OIDC token, it verifies that the tag equals the npm package version, the tagged
commit is on `main`, the matching PyPI runtime is already public, the npm
version is still unused, the launcher tests pass, and the package contents are
inspectable. The `npm` environment accepts only matching `v*` tags. A manual
workflow dispatch runs validation but deliberately skips publication.

The publish job uses a GitHub-hosted runner and grants only `contents: read` and
`id-token: write`. npm derives a short-lived credential from that OIDC identity
and publishes provenance automatically. Do not add an npm publication token to
the repository or environment.

## Verification Commands

```bash
node --test plugins/goodboy/tests/goodboy-runtime.test.mjs
node --test packages/npm-goodboy/tests/launcher.test.mjs
python -m unittest discover -s tests -v
python scripts/validate_skills.py \
  codex-skill/goodboy \
  plugins/goodboy/skills/goodboy
cmp codex-skill/goodboy/SKILL.md plugins/goodboy/skills/goodboy/SKILL.md
python -m build
```

For a pre-publication clean smoke, install the locally built wheel into isolated
`UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` paths, then point the plugin runner at that
uv environment. After publication, repeat against the exact public PyPI spec;
the public-registry smoke is a release gate, not something local wheel testing
can substitute for.

## Primary References

- [uv tool documentation](https://docs.astral.sh/uv/concepts/tools/)
- [uv CLI reference](https://docs.astral.sh/uv/reference/cli/#uv-tool)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
