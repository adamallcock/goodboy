---
title: Goodboy Review Room UI Implementation Plan
date: 2026-05-27
type: plan
status: draft
---

# Goodboy Review Room UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build M10 as a local, artifact-first Review Room web UI for reviewing, steering, approving, exporting, and demoing Goodboy projects.

**Architecture:** Add a local Python web server that exposes typed, path-safe Goodboy project APIs over the existing manifest-first pipeline. Add a React + Vite + TypeScript frontend whose default surface is an immersive Review Room: large central artifact canvas, slim stage rail, contextual inspector, gated next action, and optional advanced drawers for commands, logs, manifests, and job tables.

**Tech Stack:** Python 3.10+, existing Goodboy modules, FastAPI, Uvicorn, python-multipart, React, Vite, TypeScript, Tailwind, shadcn/Radix-style component primitives, Lucide React, TanStack Table, react-dropzone, PhotoSwipe or a small custom zoom viewer, react-compare-slider, cmdk, Sonner, Zustand, Playwright, unittest.

---

## 1. Product Decision

Review Room is the primary M10 direction. Studio Console is not the default shell because it makes the product feel too complex and operational for first use. Goodboy's highest-value moments are visual review moments:

- Are these source references understood correctly?
- Which baseline captures the subject?
- Does the style direction match the user's intent?
- Are the generated row strips centered, unclipped, expressive, and clean?
- Do the GIF previews feel alive?
- Is QA clean enough to approve, install, or export?

The default UI should therefore keep the current artifact large and the current decision obvious. Operational detail remains available through advanced panels, command palette, logs, job tables, and manifest drawers.

## 2. Definition Of Done

M10 is complete when all of the following are true:

- A user can launch the UI locally with one documented command.
- The UI opens an existing Goodboy project.
- The UI can create a new project and ingest source images.
- The UI presents the Review Room shell with stage rail, artifact canvas, contextual inspector, gate banner, activity drawer, and command palette.
- The UI can display source images, candidate baselines, selected baseline, style sheet, row-generation jobs, row strips, contact sheet, GIF previews, edge preview, centering overlay, QA reports, approval records, package files, and exports.
- The UI can perform core Goodboy actions through backend APIs: source ingest, source-card update, candidate planning, candidate-image registration, baseline selection, style update, critique/feedback, row planning, handoff generation, generated-output import, review build, approval, finish/install, project export, and Petdex export.
- The UI prevents install/finish unless the same Goodboy policy gates pass or an explicit override reason is recorded.
- The UI makes missing API keys clear as optional accelerators, not blockers.
- The UI includes a demo mode backed by real fixture artifacts.
- Backend tests cover project state, path safety, artifact indexing, workflow actions, and policy gates.
- Frontend tests cover the primary Review Room flow, visual review surfaces, accessibility basics, and approval/export gates.
- Documentation explains install, launch, usage, demo mode, and troubleshooting.
- The milestone tracker links the implementation and verification evidence.

## 3. Scope Boundaries

### 3.1 In Scope

- Local web server.
- Local React app.
- Path-safe artifact serving.
- Typed project state and artifact view models.
- Review Room shell.
- Source, baseline, style, generation, QA, approval, and export flows.
- Demo mode.
- Tests, docs, skill updates, and tracker updates.

### 3.2 Out Of Scope For M10

- Public hosted SaaS.
- User accounts.
- Remote collaboration.
- Browser-based image generation without Goodboy provider adapters.
- Replacing the CLI or skill.
- Full prompt IDE with Monaco as the default editing surface.
- Complex React Flow graph as the main navigation model.
- Installing raw secrets or writing API keys into project files.

## 4. File Structure

### 4.1 Backend Files

- Create: `src/goodboy/web/__init__.py`
  - Exposes web package version and app factory imports.
- Create: `src/goodboy/web/models.py`
  - Typed dictionaries/dataclasses for API payloads and view models.
- Create: `src/goodboy/web/artifacts.py`
  - Builds a path-safe artifact index from known manifests and filesystem artifacts.
- Create: `src/goodboy/web/registry.py`
  - Manages recent projects and per-session project handles without leaking arbitrary paths.
- Create: `src/goodboy/web/actions.py`
  - Wraps existing Goodboy functions for mutating operations and returns refreshed state.
- Create: `src/goodboy/web/server.py`
  - FastAPI app factory, routes, static artifact serving, SSE events, and error mapping.
- Create: `src/goodboy/web/dev.py`
  - Local launch helper used by `goodboy ui`.
- Modify: `src/goodboy/cli.py`
  - Adds `goodboy ui`.
- Modify: `pyproject.toml`
  - Adds optional UI dependencies.
- Test: `tests/test_web_models.py`
- Test: `tests/test_web_artifacts.py`
- Test: `tests/test_web_api.py`
- Test: `tests/test_web_actions.py`

### 4.2 Frontend Files

- Create: `ui/package.json`
- Create: `ui/package-lock.json`
- Create: `ui/index.html`
- Create: `ui/vite.config.ts`
- Create: `ui/tsconfig.json`
- Create: `ui/tsconfig.node.json`
- Create: `ui/tailwind.config.ts`
- Create: `ui/postcss.config.cjs`
- Create: `ui/playwright.config.ts`
- Create: `ui/src/main.tsx`
- Create: `ui/src/App.tsx`
- Create: `ui/src/styles/global.css`
- Create: `ui/src/styles/tokens.css`
- Create: `ui/src/lib/api.ts`
- Create: `ui/src/lib/types.ts`
- Create: `ui/src/lib/format.ts`
- Create: `ui/src/lib/artifacts.ts`
- Create: `ui/src/state/project-store.ts`
- Create: `ui/src/components/ui/button.tsx`
- Create: `ui/src/components/ui/dialog.tsx`
- Create: `ui/src/components/ui/drawer.tsx`
- Create: `ui/src/components/ui/tabs.tsx`
- Create: `ui/src/components/ui/tooltip.tsx`
- Create: `ui/src/components/ui/segmented-control.tsx`
- Create: `ui/src/components/ui/status-badge.tsx`
- Create: `ui/src/components/review-room/ReviewRoomShell.tsx`
- Create: `ui/src/components/review-room/StageRail.tsx`
- Create: `ui/src/components/review-room/GateBar.tsx`
- Create: `ui/src/components/review-room/ArtifactCanvas.tsx`
- Create: `ui/src/components/review-room/InspectorPanel.tsx`
- Create: `ui/src/components/review-room/ActivityDrawer.tsx`
- Create: `ui/src/components/review-room/CommandPalette.tsx`
- Create: `ui/src/features/project/ProjectOpen.tsx`
- Create: `ui/src/features/sources/SourceReview.tsx`
- Create: `ui/src/features/baselines/BaselineReview.tsx`
- Create: `ui/src/features/style/StyleStudio.tsx`
- Create: `ui/src/features/generation/GenerationReview.tsx`
- Create: `ui/src/features/qa/QaReview.tsx`
- Create: `ui/src/features/approval/ApprovalExport.tsx`
- Create: `ui/src/features/demo/DemoMode.tsx`
- Create: `ui/src/test/fixtures.ts`
- Create: `ui/tests/review-room.spec.ts`
- Create: `ui/tests/approval-gates.spec.ts`
- Create: `ui/tests/accessibility.spec.ts`

### 4.3 Documentation Files

- Modify: `README.md`
- Modify: `docs/2026-05-26-goodboy-user-guide.md`
- Modify: `docs/2026-05-27-goodboy-local-web-ui-requirements.md`
- Modify: `docs/2026-05-27-goodboy-ui-component-scan-and-design-options.md`
- Modify: `tracking/MILESTONES.md`
- Modify: `tracking/STATUS.md`
- Modify: `codex-skill/goodboy/SKILL.md`
- Modify: `/Users/adamallcock/.codex/skills/goodboy/SKILL.md`
- Modify: `plugins/goodboy/skills/goodboy/SKILL.md`

## 5. Data Contracts

Backend and frontend should share these conceptual view models. Backend can implement them as dataclasses or typed dictionaries; frontend should mirror them in `ui/src/lib/types.ts`.

```python
class WorkflowGate(TypedDict):
    stage: str
    next_action: str
    required_user_input: list[str]
    artifacts_to_show_user: list[str]
    blocked_actions: list[str]
    recommended_command: str | None
    install_ready: bool
```

```python
class ArtifactRef(TypedDict):
    id: str
    kind: str
    label: str
    relative_path: str
    url: str
    exists: bool
    width: int | None
    height: int | None
    bytes: int | None
    modified_at: str | None
    stage: str
    state: str | None
    severity: str
```

```python
class ProjectState(TypedDict):
    project_id: str
    project_dir: str
    manifest: dict[str, object]
    gate: WorkflowGate
    artifacts: list[ArtifactRef]
    sources: list[dict[str, object]]
    candidates: list[dict[str, object]]
    selected_candidate: dict[str, object] | None
    character_card: dict[str, object] | None
    style_sheet: dict[str, object] | None
    active_run_id: str | None
    qa: dict[str, object] | None
    approvals: list[dict[str, object]]
    exports: list[ArtifactRef]
    validation: dict[str, object]
```

```typescript
export type ReviewStage =
  | "sources"
  | "baselines"
  | "style"
  | "generation"
  | "qa"
  | "approval"
  | "demo";
```

## 6. Backend API Shape

Initial endpoints:

- `GET /api/health`
- `GET /api/projects/recent`
- `POST /api/projects/open`
- `POST /api/projects/create`
- `GET /api/projects/{project_id}/state`
- `GET /api/projects/{project_id}/artifacts`
- `GET /api/projects/{project_id}/artifacts/{artifact_id}`
- `POST /api/projects/{project_id}/sources/ingest`
- `POST /api/projects/{project_id}/source-card`
- `POST /api/projects/{project_id}/candidates/plan`
- `POST /api/projects/{project_id}/candidates/{candidate_id}/image`
- `POST /api/projects/{project_id}/candidates/{candidate_id}/select`
- `POST /api/projects/{project_id}/style/default`
- `POST /api/projects/{project_id}/critique`
- `POST /api/projects/{project_id}/feedback`
- `POST /api/projects/{project_id}/rows/plan`
- `POST /api/projects/{project_id}/generation/handoff`
- `POST /api/projects/{project_id}/generation/import`
- `POST /api/projects/{project_id}/review/build`
- `POST /api/projects/{project_id}/approval`
- `POST /api/projects/{project_id}/finish`
- `POST /api/projects/{project_id}/export`
- `GET /api/projects/{project_id}/events`

Every mutating endpoint should return fresh `ProjectState`.

## 7. Visual Architecture

The Review Room default shell has five zones:

```text
+---------------------------------------------------------------+
| GateBar: stage, QA/install readiness, next safe action          |
+-------+-------------------------------------------+-----------+
| Stage |                                           | Inspector |
| Rail  |              Artifact Canvas              | Panel     |
|       |                                           |           |
+-------+-------------------------------------------+-----------+
| Activity Drawer: recent actions, command output, provider notes |
+---------------------------------------------------------------+
```

Rules:

- The canvas owns the page.
- StageRail stays slim and calm.
- InspectorPanel is contextual and collapsible.
- GateBar is always visible.
- ActivityDrawer defaults collapsed.
- CommandPalette opens through keyboard and button.
- Advanced job/manifest/log surfaces live in drawers, not in the primary canvas.

## 8. Implementation Tasks

### Task 1: Lock Review Room Direction In Docs

**Files:**
- Modify: `docs/2026-05-27-goodboy-local-web-ui-requirements.md`
- Modify: `docs/2026-05-27-goodboy-ui-component-scan-and-design-options.md`
- Modify: `tracking/MILESTONES.md`
- Modify: `tracking/STATUS.md`
- Create: `docs/superpowers/plans/2026-05-27-goodboy-review-room-ui-implementation-plan.md`

- [ ] **Step 1: Verify the docs say Review Room is primary**

Run:

```bash
rg -n "Review Room|Studio Console|Recommended Direction|Choose Review Room" docs tracking README.md
```

Expected: the requirements and component-scan docs describe Review Room as the primary direction and Studio Console as advanced/debug support.

- [ ] **Step 2: Commit the planning baseline**

Run:

```bash
git add docs tracking README.md
git commit -m "Plan Review Room UI implementation"
```

Expected: one planning commit with no source-code changes.

### Task 2: Add Optional UI Dependencies And Launch Command

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/goodboy/cli.py`
- Create: `src/goodboy/web/__init__.py`
- Create: `src/goodboy/web/dev.py`
- Test: `tests/test_web_api.py`

- [ ] **Step 1: Add a failing CLI test**

Add to `tests/test_web_api.py`:

```python
import unittest

from goodboy.cli import main


class GoodboyWebCliTests(unittest.TestCase):
    def test_ui_help_command_is_registered(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            main(["ui", "--help"])
        self.assertEqual(caught.exception.code, 0)
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_api.GoodboyWebCliTests.test_ui_help_command_is_registered -v
```

Expected: failure because `ui` is not registered.

- [ ] **Step 3: Add optional dependencies**

Modify `pyproject.toml`:

```toml
[project.optional-dependencies]
ui = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "python-multipart>=0.0.9",
  "httpx>=0.27.0",
]
```

- [ ] **Step 4: Add the web package**

Create `src/goodboy/web/__init__.py`:

```python
"""Local web UI support for Goodboy."""

from .dev import launch_dev_server

__all__ = ["launch_dev_server"]
```

Create `src/goodboy/web/dev.py`:

```python
"""Development launcher for the Goodboy local web UI."""

from __future__ import annotations

from pathlib import Path


def launch_dev_server(*, project_dir: Path | None, host: str, port: int, open_browser: bool) -> dict[str, str | int | bool | None]:
    return {
        "project_dir": str(project_dir.resolve()) if project_dir else None,
        "host": host,
        "port": port,
        "open_browser": open_browser,
        "status": "server_not_started_yet",
    }
```

- [ ] **Step 5: Register `goodboy ui`**

Modify `src/goodboy/cli.py` to add:

```python
ui_cmd = sub.add_parser("ui", help="Launch the local Goodboy Review Room web UI.")
ui_cmd.add_argument("project_dir", nargs="?")
ui_cmd.add_argument("--host", default="127.0.0.1")
ui_cmd.add_argument("--port", type=int, default=8787)
ui_cmd.add_argument("--no-open", action="store_true")
```

In the command handler, call:

```python
from .web import launch_dev_server

result = launch_dev_server(
    project_dir=Path(args.project_dir) if args.project_dir else None,
    host=args.host,
    port=args.port,
    open_browser=not args.no_open,
)
print(json.dumps(result, indent=2, sort_keys=True))
return 0
```

- [ ] **Step 6: Run the CLI test**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_api.GoodboyWebCliTests.test_ui_help_command_is_registered -v
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add pyproject.toml src/goodboy/cli.py src/goodboy/web/__init__.py src/goodboy/web/dev.py tests/test_web_api.py
git commit -m "Add local UI launch command"
```

### Task 3: Build Backend View Models

**Files:**
- Create: `src/goodboy/web/models.py`
- Test: `tests/test_web_models.py`

- [ ] **Step 1: Add model tests**

Create `tests/test_web_models.py`:

```python
import unittest

from goodboy.web.models import artifact_id_for, artifact_url_for, severity_for_stage


class WebModelTests(unittest.TestCase):
    def test_artifact_id_is_stable_for_relative_paths(self) -> None:
        self.assertEqual(artifact_id_for("runs/demo/qa/contact-sheet.png"), "runs-demo-qa-contact-sheet-png")

    def test_artifact_url_is_project_scoped(self) -> None:
        self.assertEqual(
            artifact_url_for("project-001", "runs-demo-qa-contact-sheet-png"),
            "/api/projects/project-001/artifacts/runs-demo-qa-contact-sheet-png",
        )

    def test_severity_for_stage_defaults_to_info(self) -> None:
        self.assertEqual(severity_for_stage("sources"), "info")
```

- [ ] **Step 2: Run model tests and verify failure**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_models -v
```

Expected: failure because `goodboy.web.models` is missing helpers.

- [ ] **Step 3: Implement model helpers and typed dictionaries**

Create `src/goodboy/web/models.py` with:

```python
"""View models for the Goodboy local web UI."""

from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

Severity = Literal["info", "success", "warning", "danger"]


class ArtifactRef(TypedDict):
    id: str
    kind: str
    label: str
    relative_path: str
    url: str
    exists: bool
    width: int | None
    height: int | None
    bytes: int | None
    modified_at: str | None
    stage: str
    state: str | None
    severity: Severity


class WorkflowGate(TypedDict):
    stage: str
    next_action: str
    required_user_input: list[str]
    artifacts_to_show_user: list[str]
    blocked_actions: list[str]
    recommended_command: str | None
    install_ready: bool


class ProjectState(TypedDict):
    project_id: str
    project_dir: str
    manifest: dict[str, Any]
    gate: WorkflowGate
    artifacts: list[ArtifactRef]
    sources: list[dict[str, Any]]
    candidates: list[dict[str, Any]]
    selected_candidate: dict[str, Any] | None
    character_card: dict[str, Any] | None
    style_sheet: dict[str, Any] | None
    active_run_id: str | None
    qa: dict[str, Any] | None
    approvals: list[dict[str, Any]]
    exports: list[ArtifactRef]
    validation: dict[str, Any]


def artifact_id_for(relative_path: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", relative_path).strip("-").lower()
    return cleaned or "artifact"


def artifact_url_for(project_id: str, artifact_id: str) -> str:
    return f"/api/projects/{project_id}/artifacts/{artifact_id}"


def severity_for_stage(stage: str) -> Severity:
    if stage in {"qa-fail", "blocked"}:
        return "danger"
    if stage in {"qa-warning", "needs-review"}:
        return "warning"
    if stage in {"approved", "installed", "exported"}:
        return "success"
    return "info"
```

- [ ] **Step 4: Run model tests**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_models -v
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/goodboy/web/models.py tests/test_web_models.py
git commit -m "Add web UI view models"
```

### Task 4: Build Path-Safe Project Registry

**Files:**
- Create: `src/goodboy/web/registry.py`
- Test: `tests/test_web_api.py`

- [ ] **Step 1: Add registry tests**

Add to `tests/test_web_api.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from goodboy.web.registry import ProjectRegistry


class ProjectRegistryTests(unittest.TestCase):
    def test_register_project_returns_stable_id(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = ProjectRegistry()
            first = registry.register(Path(tmp))
            second = registry.register(Path(tmp))
            self.assertEqual(first, second)
            self.assertEqual(registry.resolve(first), Path(tmp).resolve())

    def test_unknown_project_id_raises_key_error(self) -> None:
        registry = ProjectRegistry()
        with self.assertRaises(KeyError):
            registry.resolve("missing")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_api.ProjectRegistryTests -v
```

Expected: failure because `ProjectRegistry` is missing.

- [ ] **Step 3: Implement registry**

Create `src/goodboy/web/registry.py`:

```python
"""Project handle registry for the local web UI."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ProjectRegistry:
    def __init__(self) -> None:
        self._projects: dict[str, Path] = {}
        self._recent: list[str] = []

    def register(self, project_dir: Path) -> str:
        resolved = project_dir.resolve()
        project_id = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        self._projects[project_id] = resolved
        if project_id in self._recent:
            self._recent.remove(project_id)
        self._recent.insert(0, project_id)
        return project_id

    def resolve(self, project_id: str) -> Path:
        if project_id not in self._projects:
            raise KeyError(project_id)
        return self._projects[project_id]

    def recent(self) -> list[dict[str, str]]:
        return [{"project_id": item, "project_dir": str(self._projects[item])} for item in self._recent if item in self._projects]
```

- [ ] **Step 4: Run registry tests**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_api.ProjectRegistryTests -v
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/goodboy/web/registry.py tests/test_web_api.py
git commit -m "Add web UI project registry"
```

### Task 5: Build Artifact Indexing

**Files:**
- Create: `src/goodboy/web/artifacts.py`
- Test: `tests/test_web_artifacts.py`

- [ ] **Step 1: Add artifact index tests**

Create `tests/test_web_artifacts.py`:

```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from goodboy.web.artifacts import ArtifactIndex, build_artifact_index, safe_artifact_path


class ArtifactIndexTests(unittest.TestCase):
    def test_build_index_finds_known_qa_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "runs" / "demo" / "qa"
            qa.mkdir(parents=True)
            image_path = qa / "contact-sheet.png"
            Image.new("RGBA", (20, 10), (255, 255, 255, 255)).save(image_path)

            index = build_artifact_index(root, project_id="project-001")

            self.assertIn("runs-demo-qa-contact-sheet-png", index.by_id)
            ref = index.by_id["runs-demo-qa-contact-sheet-png"]
            self.assertEqual(ref["width"], 20)
            self.assertEqual(ref["height"], 10)

    def test_safe_artifact_path_blocks_traversal(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                safe_artifact_path(root, "../outside.png")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_artifacts -v
```

Expected: failure because artifact indexing does not exist.

- [ ] **Step 3: Implement artifact index**

Create `src/goodboy/web/artifacts.py` with path-safe helpers, image dimension probing through Pillow, and known Goodboy glob patterns:

```python
"""Artifact indexing and path-safe artifact lookup for the Goodboy web UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .models import ArtifactRef, artifact_id_for, artifact_url_for, severity_for_stage

KNOWN_ARTIFACT_PATTERNS = [
    "sources/originals/*",
    "sources/thumbnails/*",
    "candidates/contact-sheet.png",
    "candidates/baseline-*/generated/*",
    "character/selected-baseline.png",
    "runs/*/row-strips/*",
    "runs/*/qa/contact-sheet.png",
    "runs/*/qa/edge-preview-white.png",
    "runs/*/qa/centering-overlay.png",
    "runs/*/qa/previews/*",
    "runs/*/final/spritesheet.webp",
    "runs/*/package/pet.json",
    "runs/*/package/spritesheet.webp",
    "exports/**/*",
]


@dataclass(frozen=True)
class ArtifactIndex:
    artifacts: list[ArtifactRef]
    by_id: dict[str, ArtifactRef]


def safe_artifact_path(project_dir: Path, relative_path: str) -> Path:
    root = project_dir.resolve()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError(f"artifact path escapes project: {relative_path}")
    return candidate


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None, None


def kind_for(relative_path: str) -> str:
    if relative_path.startswith("sources/"):
        return "source"
    if relative_path.startswith("candidates/"):
        return "candidate"
    if relative_path.startswith("character/"):
        return "character"
    if "/qa/" in relative_path:
        return "qa"
    if "/row-strips/" in relative_path:
        return "row-strip"
    if "/final/" in relative_path:
        return "final"
    if "/package/" in relative_path:
        return "package"
    if relative_path.startswith("exports/"):
        return "export"
    return "artifact"


def stage_for(relative_path: str) -> str:
    if relative_path.startswith("sources/"):
        return "sources"
    if relative_path.startswith("candidates/"):
        return "baselines"
    if relative_path.startswith("character/"):
        return "baselines"
    if "/row-strips/" in relative_path:
        return "generation"
    if "/qa/" in relative_path:
        return "qa"
    if "/package/" in relative_path or "/final/" in relative_path or relative_path.startswith("exports/"):
        return "approval"
    return "project"


def build_artifact_index(project_dir: Path, project_id: str) -> ArtifactIndex:
    root = project_dir.resolve()
    artifacts: list[ArtifactRef] = []
    seen: set[str] = set()
    for pattern in KNOWN_ARTIFACT_PATTERNS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root).as_posix()
            if relative_path in seen:
                continue
            seen.add(relative_path)
            artifact_id = artifact_id_for(relative_path)
            width, height = image_dimensions(path)
            stat = path.stat()
            stage = stage_for(relative_path)
            artifacts.append(
                {
                    "id": artifact_id,
                    "kind": kind_for(relative_path),
                    "label": path.name,
                    "relative_path": relative_path,
                    "url": artifact_url_for(project_id, artifact_id),
                    "exists": True,
                    "width": width,
                    "height": height,
                    "bytes": stat.st_size,
                    "modified_at": str(int(stat.st_mtime)),
                    "stage": stage,
                    "state": path.stem if "/previews/" in relative_path or "/row-strips/" in relative_path else None,
                    "severity": severity_for_stage(stage),
                }
            )
    return ArtifactIndex(artifacts=artifacts, by_id={item["id"]: item for item in artifacts})
```

- [ ] **Step 4: Run artifact tests**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_artifacts -v
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/goodboy/web/artifacts.py tests/test_web_artifacts.py
git commit -m "Index Goodboy web artifacts"
```

### Task 6: Build Read-Only Project State API

**Files:**
- Create: `src/goodboy/web/server.py`
- Modify: `src/goodboy/web/actions.py`
- Test: `tests/test_web_api.py`

- [ ] **Step 1: Add API tests**

Add to `tests/test_web_api.py`:

```python
from fastapi.testclient import TestClient

from goodboy.project import init_project
from goodboy.web.server import create_app


class ProjectStateApiTests(unittest.TestCase):
    def test_open_project_and_read_state(self) -> None:
        with TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            client = TestClient(create_app())

            opened = client.post("/api/projects/open", json={"project_dir": str(project_dir)})
            self.assertEqual(opened.status_code, 200)
            project_id = opened.json()["project_id"]

            state = client.get(f"/api/projects/{project_id}/state")
            self.assertEqual(state.status_code, 200)
            payload = state.json()
            self.assertEqual(payload["manifest"]["pet_id"], "demo")
            self.assertEqual(payload["gate"]["stage"], "initialized")
```

- [ ] **Step 2: Run API test and verify failure**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_api.ProjectStateApiTests.test_open_project_and_read_state -v
```

Expected: failure because `create_app` is missing.

- [ ] **Step 3: Implement state assembly in actions**

Create `src/goodboy/web/actions.py`:

```python
"""Backend actions for the Goodboy Review Room UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from goodboy.candidates import CANDIDATE_INDEX, SELECTED_CANDIDATE
from goodboy.ingest import SOURCE_CARD, SOURCE_MANIFEST
from goodboy.jsonio import read_json
from goodboy.project import load_project
from goodboy.style import STYLE_PATH
from goodboy.validation import validate_project
from goodboy.workflow import latest_run_id, next_status, review_status

from .artifacts import build_artifact_index
from .models import ProjectState


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    return read_json(path) if path.is_file() else None


def list_json_items(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = read_json(path)
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def project_state(project_dir: Path, project_id: str) -> ProjectState:
    project = load_project(project_dir)
    gate_status = next_status(project_dir)
    active_run_id = latest_run_id(project_dir)
    artifact_index = build_artifact_index(project_dir, project_id)
    validation = validate_project(project_dir, write_report=False)
    review = review_status(project_dir, active_run_id) if active_run_id else None
    gate = gate_status.to_dict()
    gate["install_ready"] = bool(review and review.get("install_ready"))
    return {
        "project_id": project_id,
        "project_dir": str(project_dir.resolve()),
        "manifest": project.to_dict(),
        "gate": {
            "stage": str(gate.get("stage", "")),
            "next_action": str(gate.get("next_action", "")),
            "required_user_input": list(gate.get("required_user_input", [])),
            "artifacts_to_show_user": list(gate.get("artifacts_to_show_user", [])),
            "blocked_actions": list(gate.get("blocked_actions", [])),
            "recommended_command": gate.get("recommended_command"),
            "install_ready": bool(gate.get("install_ready")),
        },
        "artifacts": artifact_index.artifacts,
        "sources": list_json_items(project_dir / SOURCE_MANIFEST, "images"),
        "candidates": list_json_items(project_dir / CANDIDATE_INDEX, "candidates"),
        "selected_candidate": read_json_if_exists(project_dir / SELECTED_CANDIDATE),
        "character_card": read_json_if_exists(project_dir / "character" / "character-card.json"),
        "style_sheet": read_json_if_exists(project_dir / STYLE_PATH),
        "active_run_id": active_run_id,
        "qa": review,
        "approvals": list(review.get("approvals", [])) if review else [],
        "exports": [item for item in artifact_index.artifacts if item["kind"] == "export"],
        "validation": {
            "ok": validation.ok,
            "issues": [issue.to_dict() for issue in validation.issues],
            "checked_files": validation.checked_files,
        },
    }
```

- [ ] **Step 4: Implement FastAPI app**

Create `src/goodboy/web/server.py`:

```python
"""FastAPI server for the Goodboy local Review Room UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .actions import project_state
from .artifacts import build_artifact_index, safe_artifact_path
from .registry import ProjectRegistry


class OpenProjectRequest(BaseModel):
    project_dir: str


def create_app(registry: ProjectRegistry | None = None) -> FastAPI:
    app = FastAPI(title="Goodboy Review Room")
    projects = registry or ProjectRegistry()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"ok": "true"}

    @app.get("/api/projects/recent")
    def recent() -> list[dict[str, str]]:
        return projects.recent()

    @app.post("/api/projects/open")
    def open_project(payload: OpenProjectRequest) -> dict[str, str]:
        project_dir = Path(payload.project_dir).resolve()
        if not (project_dir / "goodboy.json").is_file():
            raise HTTPException(status_code=400, detail="not a Goodboy project")
        project_id = projects.register(project_dir)
        return {"project_id": project_id, "project_dir": str(project_dir)}

    @app.get("/api/projects/{project_id}/state")
    def state(project_id: str):
        try:
            project_dir = projects.resolve(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown project") from exc
        return project_state(project_dir, project_id)

    @app.get("/api/projects/{project_id}/artifacts/{artifact_id}")
    def artifact(project_id: str, artifact_id: str):
        try:
            project_dir = projects.resolve(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown project") from exc
        index = build_artifact_index(project_dir, project_id)
        ref = index.by_id.get(artifact_id)
        if not ref:
            raise HTTPException(status_code=404, detail="unknown artifact")
        path = safe_artifact_path(project_dir, ref["relative_path"])
        return FileResponse(path)

    return app
```

- [ ] **Step 5: Run API test**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_api.ProjectStateApiTests.test_open_project_and_read_state -v
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/goodboy/web/actions.py src/goodboy/web/server.py tests/test_web_api.py
git commit -m "Expose read-only Review Room API"
```

### Task 7: Add Mutating Backend Actions

**Files:**
- Modify: `src/goodboy/web/actions.py`
- Modify: `src/goodboy/web/server.py`
- Test: `tests/test_web_actions.py`

- [ ] **Step 1: Add action tests for source ingest and candidate planning**

Create `tests/test_web_actions.py`:

```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from goodboy.project import init_project
from goodboy.web.actions import ingest_source_images, plan_candidates_action


class WebActionTests(unittest.TestCase):
    def test_ingest_source_images_returns_refreshed_state(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (16, 16), (255, 255, 255)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")

            state = ingest_source_images(project_dir, "project-001", [source], notes="front view")

            self.assertEqual(state["gate"]["stage"], "sources_ingested")
            self.assertEqual(len(state["sources"]), 1)

    def test_plan_candidates_action_writes_contact_sheet(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "pet"
            source = root / "source.png"
            Image.new("RGB", (16, 16), (255, 255, 255)).save(source)
            init_project(project_dir, pet_id="demo", display_name="Demo", species="dog")
            ingest_source_images(project_dir, "project-001", [source], notes="front view")

            state = plan_candidates_action(project_dir, "project-001", provider="codex_builtin", model_alias="codex-imagegen", count=3)

            self.assertEqual(len(state["candidates"]), 3)
            self.assertTrue((project_dir / "candidates" / "contact-sheet.png").is_file())
```

- [ ] **Step 2: Run action tests and verify failure**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_actions -v
```

Expected: failure because action wrappers are missing.

- [ ] **Step 3: Add action wrappers**

Add wrappers in `src/goodboy/web/actions.py` for:

```python
def ingest_source_images(project_dir: Path, project_id: str, sources: list[Path], notes: str = "") -> ProjectState:
    from goodboy.ingest import draft_source_card, ingest_images

    ingest_images(project_dir, sources, role="primary_reference", notes=notes)
    draft_source_card(project_dir, user_notes=notes)
    return project_state(project_dir, project_id)
```

```python
def plan_candidates_action(project_dir: Path, project_id: str, provider: str, model_alias: str, count: int) -> ProjectState:
    from goodboy.candidates import plan_baseline_candidates

    plan_baseline_candidates(project_dir=project_dir, provider=provider, model_alias=model_alias, count=count)
    return project_state(project_dir, project_id)
```

Then add wrappers with the same pattern for:

- `register_candidate_image_action`
- `select_candidate_action`
- `style_default_action`
- `record_critique_action`
- `record_feedback_action`
- `plan_rows_action`
- `generate_handoff_action`
- `import_generated_action`
- `build_review_action`
- `approve_action`
- `finish_action`
- `export_action`

- [ ] **Step 4: Add routes for mutating actions**

Add routes in `src/goodboy/web/server.py` that resolve project ID, call action wrapper, and return fresh state. Each route should catch `ValueError` as `HTTPException(status_code=400)`.

- [ ] **Step 5: Run action tests**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_actions -v
```

Expected: pass.

- [ ] **Step 6: Run all backend web tests**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest tests.test_web_models tests.test_web_artifacts tests.test_web_api tests.test_web_actions -v
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/goodboy/web/actions.py src/goodboy/web/server.py tests/test_web_actions.py
git commit -m "Add Review Room workflow actions"
```

### Task 8: Scaffold Frontend Workspace

**Files:**
- Create frontend files listed in section 4.2.
- Modify: `.gitignore` if needed.

- [ ] **Step 1: Create Vite app structure**

Run:

```bash
mkdir -p ui/src ui/src/styles ui/src/lib ui/src/state ui/src/components/ui ui/src/components/review-room ui/src/features/project ui/src/features/sources ui/src/features/baselines ui/src/features/style ui/src/features/generation ui/src/features/qa ui/src/features/approval ui/src/features/demo ui/src/test ui/tests
```

- [ ] **Step 2: Create `ui/package.json`**

Use these scripts and dependencies:

```json
{
  "name": "goodboy-review-room-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "test:e2e": "playwright test",
    "typecheck": "tsc -b"
  },
  "dependencies": {
    "@tanstack/react-table": "^8.20.5",
    "cmdk": "^1.0.4",
    "lucide-react": "^0.468.0",
    "photoswipe": "^5.4.4",
    "react": "^18.3.1",
    "react-compare-slider": "^3.1.0",
    "react-dom": "^18.3.1",
    "react-dropzone": "^14.3.5",
    "sonner": "^1.5.0",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "@types/node": "^22.10.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.15",
    "typescript": "^5.7.2",
    "vite": "^6.0.1"
  }
}
```

- [ ] **Step 3: Add Vite, TypeScript, Tailwind, and CSS entry files**

Create `ui/index.html`, `ui/vite.config.ts`, `ui/tsconfig.json`, `ui/tailwind.config.ts`, `ui/postcss.config.cjs`, `ui/src/main.tsx`, `ui/src/App.tsx`, `ui/src/styles/global.css`, and `ui/src/styles/tokens.css`.

- [ ] **Step 4: Install dependencies**

Run:

```bash
cd ui && npm install
```

Expected: `ui/package-lock.json` is created.

- [ ] **Step 5: Verify typecheck/build**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: both pass with the starter app.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui .gitignore
git commit -m "Scaffold Review Room frontend"
```

### Task 9: Add Frontend API Client And Types

**Files:**
- Create: `ui/src/lib/types.ts`
- Create: `ui/src/lib/api.ts`
- Create: `ui/src/lib/format.ts`
- Create: `ui/src/lib/artifacts.ts`
- Create: `ui/src/state/project-store.ts`
- Test: `ui/src/test/fixtures.ts`

- [ ] **Step 1: Define frontend types**

Mirror backend models in `ui/src/lib/types.ts`:

```typescript
export type Severity = "info" | "success" | "warning" | "danger";
export type ReviewStage = "sources" | "baselines" | "style" | "generation" | "qa" | "approval" | "demo";

export interface ArtifactRef {
  id: string;
  kind: string;
  label: string;
  relative_path: string;
  url: string;
  exists: boolean;
  width: number | null;
  height: number | null;
  bytes: number | null;
  modified_at: string | null;
  stage: ReviewStage | string;
  state: string | null;
  severity: Severity;
}

export interface WorkflowGate {
  stage: string;
  next_action: string;
  required_user_input: string[];
  artifacts_to_show_user: string[];
  blocked_actions: string[];
  recommended_command: string | null;
  install_ready: boolean;
}

export interface ProjectState {
  project_id: string;
  project_dir: string;
  manifest: Record<string, unknown>;
  gate: WorkflowGate;
  artifacts: ArtifactRef[];
  sources: Record<string, unknown>[];
  candidates: Record<string, unknown>[];
  selected_candidate: Record<string, unknown> | null;
  character_card: Record<string, unknown> | null;
  style_sheet: Record<string, unknown> | null;
  active_run_id: string | null;
  qa: Record<string, unknown> | null;
  approvals: Record<string, unknown>[];
  exports: ArtifactRef[];
  validation: Record<string, unknown>;
}
```

- [ ] **Step 2: Implement API helpers**

Create `ui/src/lib/api.ts` with `openProject`, `getProjectState`, `postProjectAction`, and typed error handling.

- [ ] **Step 3: Add store**

Create `ui/src/state/project-store.ts` with selected stage, selected artifact ID, project state, loading flag, error, and actions.

- [ ] **Step 4: Add fixture state**

Create `ui/src/test/fixtures.ts` with a realistic `ProjectState` object for component development and Playwright demo mode.

- [ ] **Step 5: Run typecheck**

Run:

```bash
cd ui && npm run typecheck
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src/lib ui/src/state ui/src/test
git commit -m "Add Review Room API client state"
```

### Task 10: Implement Review Room Shell

**Files:**
- Modify: `ui/src/App.tsx`
- Create: `ui/src/components/review-room/ReviewRoomShell.tsx`
- Create: `ui/src/components/review-room/StageRail.tsx`
- Create: `ui/src/components/review-room/GateBar.tsx`
- Create: `ui/src/components/review-room/ArtifactCanvas.tsx`
- Create: `ui/src/components/review-room/InspectorPanel.tsx`
- Create: `ui/src/components/review-room/ActivityDrawer.tsx`
- Create: `ui/src/components/review-room/CommandPalette.tsx`
- Create: `ui/src/components/ui/button.tsx`
- Create: `ui/src/components/ui/status-badge.tsx`
- Modify: `ui/src/styles/global.css`
- Modify: `ui/src/styles/tokens.css`

- [ ] **Step 1: Build design tokens**

Create CSS variables for background, surface, border, text, muted text, accent, success, warning, danger, radius, and spacing. Use a light neutral Review Room palette and avoid chroma-green dominance.

- [ ] **Step 2: Build shell components**

Implement StageRail, GateBar, ArtifactCanvas, InspectorPanel, ActivityDrawer, and CommandPalette using fixture project state.

- [ ] **Step 3: Wire the shell into App**

`App.tsx` should render `ReviewRoomShell` with fixture state until backend connection is wired.

- [ ] **Step 4: Run typecheck/build**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 5: Start local UI and inspect manually**

Run:

```bash
cd ui && npm run dev -- --port 5173
```

Expected: app opens on `http://127.0.0.1:5173` with the Review Room shell.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src/App.tsx ui/src/components ui/src/styles
git commit -m "Build Review Room shell"
```

### Task 11: Implement Project Open And Source Review

**Files:**
- Create: `ui/src/features/project/ProjectOpen.tsx`
- Create: `ui/src/features/sources/SourceReview.tsx`
- Modify: `ui/src/components/review-room/ArtifactCanvas.tsx`
- Modify: `ui/src/components/review-room/InspectorPanel.tsx`
- Modify: `ui/src/state/project-store.ts`
- Test: `ui/tests/review-room.spec.ts`

- [ ] **Step 1: Add project open UI**

Build a compact open-project panel for entering a project directory path and loading `/api/projects/open`.

- [ ] **Step 2: Add source review canvas**

Show source thumbnails, original source viewer, provenance metadata, source-card traits, and source risks.

- [ ] **Step 3: Add drag/drop ingest**

Use react-dropzone for source files. Submit to backend ingest endpoint.

- [ ] **Step 4: Add Playwright source test**

Create `ui/tests/review-room.spec.ts` with a test that opens the app, sees the stage rail, enters a fixture project path when configured, and reaches Sources.

- [ ] **Step 5: Run frontend checks**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src/features/project ui/src/features/sources ui/src/components/review-room ui/src/state ui/tests
git commit -m "Add project open and source review UI"
```

### Task 12: Implement Baseline Review

**Files:**
- Create: `ui/src/features/baselines/BaselineReview.tsx`
- Modify: `ui/src/components/review-room/ArtifactCanvas.tsx`
- Modify: `ui/src/components/review-room/InspectorPanel.tsx`
- Modify: `ui/src/lib/artifacts.ts`
- Test: `ui/tests/review-room.spec.ts`

- [ ] **Step 1: Add baseline gallery**

Show candidates from project state, image presence, style summary, character delta, provider/model, strengths, and risks.

- [ ] **Step 2: Add compare mode**

Allow two selected candidates to be compared with react-compare-slider when both images exist.

- [ ] **Step 3: Add baseline selection action**

Record candidate ID, generated image path, and selection notes through the backend selection endpoint.

- [ ] **Step 4: Add Playwright baseline test**

Extend the test to select the Baselines stage and verify candidate cards, selected state, and disabled selection when no image exists.

- [ ] **Step 5: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src/features/baselines ui/src/components/review-room ui/src/lib ui/tests
git commit -m "Add baseline review UI"
```

### Task 13: Implement Style Studio As Contextual Inspector

**Files:**
- Create: `ui/src/features/style/StyleStudio.tsx`
- Create: `ui/src/components/ui/segmented-control.tsx`
- Create: `ui/src/components/ui/dialog.tsx`
- Modify: `ui/src/components/review-room/InspectorPanel.tsx`
- Test: `ui/tests/review-room.spec.ts`

- [ ] **Step 1: Add style preset controls**

Support soft-lifelike, realistic, anime, storybook, pixel, sticker, and custom.

- [ ] **Step 2: Add subject-kind controls**

Support pet, animal, person, object, inanimate_object, fantasy_creature, and custom.

- [ ] **Step 3: Add critique composer**

Record finding, recommendation, author, optional scores, and apply-to-style toggle.

- [ ] **Step 4: Add style diff preview**

Before applying changes, show the current style sheet and proposed user/AI critique text in a structured dialog.

- [ ] **Step 5: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src/features/style ui/src/components/ui ui/src/components/review-room ui/tests
git commit -m "Add Style Studio inspector"
```

### Task 14: Implement Generation Review

**Files:**
- Create: `ui/src/features/generation/GenerationReview.tsx`
- Create: `ui/src/components/ui/tabs.tsx`
- Modify: `ui/src/components/review-room/ActivityDrawer.tsx`
- Modify: `ui/src/components/review-room/InspectorPanel.tsx`
- Test: `ui/tests/review-room.spec.ts`

- [ ] **Step 1: Show job table**

Use TanStack Table to show state, frame count, provider, model alias, prompt path, expected output, retry policy, selected output path, and status.

- [ ] **Step 2: Show optional accelerators**

Display OpenAI/Gemini key status as optional accelerators. Missing keys should read as "optional, use Codex handoff" and not as a failure.

- [ ] **Step 3: Add handoff generation action**

Expose `generate-handoff --all` through the backend action endpoint.

- [ ] **Step 4: Add generated-output map builder**

Let users map states to generated row-strip image paths and submit `import-generated`.

- [ ] **Step 5: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src/features/generation ui/src/components ui/tests
git commit -m "Add generation review UI"
```

### Task 15: Implement QA Review Room

**Files:**
- Create: `ui/src/features/qa/QaReview.tsx`
- Create: `ui/src/components/ui/tooltip.tsx`
- Modify: `ui/src/components/review-room/ArtifactCanvas.tsx`
- Modify: `ui/src/components/review-room/InspectorPanel.tsx`
- Test: `ui/tests/review-room.spec.ts`

- [ ] **Step 1: Add contact sheet viewer**

Show `qa/contact-sheet.png` large by default with zoom and fit controls.

- [ ] **Step 2: Add GIF preview strip**

Show `qa/previews/*.gif` with pause/restart/speed controls and per-state labels.

- [ ] **Step 3: Add edge and centering overlays**

Support toggling edge preview and centering overlay into the canvas.

- [ ] **Step 4: Add QA metrics**

Display validation, duplicate audit, centering report, install policy, component warnings, green-edge residue, clipping, drift, and static-frame status.

- [ ] **Step 5: Add human review checklist**

Show required review artifacts and allow check completion where backend supports durable approval records.

- [ ] **Step 6: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add ui/src/features/qa ui/src/components ui/tests
git commit -m "Add QA Review Room"
```

### Task 16: Implement Approval, Finish, Install, And Export

**Files:**
- Create: `ui/src/features/approval/ApprovalExport.tsx`
- Create: `ui/src/components/ui/drawer.tsx`
- Modify: `ui/src/components/review-room/GateBar.tsx`
- Modify: `ui/src/components/review-room/InspectorPanel.tsx`
- Test: `ui/tests/approval-gates.spec.ts`

- [ ] **Step 1: Add install policy panel**

Show hard failures, warnings, row provenance, visual approval status, override state, suspicious renderer scripts, and package output paths.

- [ ] **Step 2: Add approval action**

Require non-empty notes. Submit to backend approval endpoint.

- [ ] **Step 3: Add finish/install action**

Enable only when policy allows. If override is needed, require explicit override reason and show it before submission.

- [ ] **Step 4: Add export actions**

Expose project export and Petdex export. Show produced artifact paths.

- [ ] **Step 5: Add Playwright gate tests**

Test disabled install before approval, enabled install after approval in fixture state, and visible override reason requirement when QA blocks install.

- [ ] **Step 6: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build && npm run test:e2e
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add ui/src/features/approval ui/src/components ui/tests
git commit -m "Add approval and export UI"
```

### Task 17: Implement Demo Mode

**Files:**
- Create: `ui/src/features/demo/DemoMode.tsx`
- Modify: `ui/src/App.tsx`
- Modify: `ui/src/test/fixtures.ts`
- Modify: `docs/assets/` only if new generated demo visuals are intentionally added.

- [ ] **Step 1: Add demo route/state**

Add a demo mode that loads fixture `ProjectState` without requiring private filesystem paths.

- [ ] **Step 2: Add narrative strip**

Show Sources -> Baseline -> Style -> Rows -> QA -> Export as a polished but compact timeline.

- [ ] **Step 3: Add before/after story**

Show source thumbnail, selected baseline, final contact sheet, GIF previews, QA pass/warning state, and export package.

- [ ] **Step 4: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add ui/src/features/demo ui/src/App.tsx ui/src/test/fixtures.ts
git commit -m "Add Goodboy UI demo mode"
```

### Task 18: Wire Backend And Frontend For Local Development

**Files:**
- Modify: `src/goodboy/web/dev.py`
- Modify: `src/goodboy/web/server.py`
- Modify: `ui/vite.config.ts`
- Modify: `README.md`
- Test: manual browser smoke.

- [ ] **Step 1: Serve API from Python and frontend from Vite in dev**

Make `goodboy ui` print both backend and frontend URLs when the frontend dev server is expected.

- [ ] **Step 2: Configure Vite proxy**

Proxy `/api` to `http://127.0.0.1:8787`.

- [ ] **Step 3: Add production static serving path**

When `ui/dist` exists, FastAPI should serve built frontend assets.

- [ ] **Step 4: Run backend and frontend together**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli ui /tmp/goodboy-demo --no-open
cd ui && npm run dev -- --port 5173
```

Expected: frontend loads and can call `/api/health`.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/goodboy/web ui/vite.config.ts README.md
git commit -m "Wire local UI development servers"
```

### Task 19: Accessibility And Responsive Polish

**Files:**
- Modify: `ui/src/components/**`
- Modify: `ui/src/features/**`
- Create: `ui/tests/accessibility.spec.ts`

- [ ] **Step 1: Add keyboard flow**

Ensure StageRail, CommandPalette, artifact controls, approval notes, and export buttons are keyboard reachable.

- [ ] **Step 2: Add reduced motion handling**

Pause autoplay effects and respect `prefers-reduced-motion`.

- [ ] **Step 3: Add mobile/tablet review mode**

Collapse stage rail and inspector. Keep artifact canvas and gate visible.

- [ ] **Step 4: Add accessibility test**

Use Playwright to verify focus reaches primary controls and no core action lacks an accessible name.

- [ ] **Step 5: Run checks**

Run:

```bash
cd ui && npm run typecheck && npm run build && npm run test:e2e
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add ui/src ui/tests
git commit -m "Polish Review Room accessibility"
```

### Task 20: Add Backend Policy And Security Hardening

**Files:**
- Modify: `src/goodboy/web/server.py`
- Modify: `src/goodboy/web/artifacts.py`
- Modify: `src/goodboy/web/actions.py`
- Test: `tests/test_web_api.py`
- Test: `tests/test_web_artifacts.py`

- [ ] **Step 1: Add tests for path traversal and missing projects**

Test artifact routes reject unknown projects, unknown artifacts, and traversal attempts.

- [ ] **Step 2: Add tests for policy-gated finish**

Verify finish/install endpoint refuses missing approval and suspicious renderer scripts by surfacing the existing Goodboy policy error.

- [ ] **Step 3: Add secret redaction**

Ensure API responses never include raw values for `OPENAI_API_KEY` or `GEMINI_API_KEY`; only boolean availability and optional accelerator labels.

- [ ] **Step 4: Run backend tests**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest discover -s tests -v
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/goodboy/web tests
git commit -m "Harden Review Room backend safety"
```

### Task 21: Documentation And Skill Updates

**Files:**
- Modify: `README.md`
- Modify: `docs/2026-05-26-goodboy-user-guide.md`
- Modify: `docs/2026-05-27-goodboy-local-web-ui-requirements.md`
- Modify: `tracking/MILESTONES.md`
- Modify: `tracking/STATUS.md`
- Modify: `codex-skill/goodboy/SKILL.md`
- Modify: `/Users/adamallcock/.codex/skills/goodboy/SKILL.md`
- Modify: `plugins/goodboy/skills/goodboy/SKILL.md`

- [ ] **Step 1: Document install**

Add:

```bash
cd /Users/adamallcock/Documents/Coding/goodboy
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m pip install -e ".[ui]"
cd ui && npm install
```

- [ ] **Step 2: Document launch**

Add:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli ui /absolute/path/to/project
cd ui && npm run dev -- --port 5173
```

- [ ] **Step 3: Document usage**

Cover Sources, Baselines, Style, Generation, QA, Approval, Export, Demo Mode, optional API accelerators, and safe install policy.

- [ ] **Step 4: Update skills**

Add guidance that agents should use Review Room for image-heavy inspection when available, while still using `goodboy start`, `advance`, and CLI gates for automation.

- [ ] **Step 5: Run docs checks**

Run:

```bash
rg -n "Review Room|goodboy ui|optional accelerator|visual approval" README.md docs codex-skill plugins/goodboy/skills /Users/adamallcock/.codex/skills/goodboy/SKILL.md
git diff --check
```

Expected: relevant docs mention Review Room and whitespace check passes.

- [ ] **Step 6: Commit**

Run:

```bash
git add README.md docs tracking codex-skill/goodboy/SKILL.md plugins/goodboy/skills/goodboy/SKILL.md
git commit -m "Document Review Room UI workflow"
```

Then copy the updated repo skill to the installed skill location:

```bash
cp codex-skill/goodboy/SKILL.md /Users/adamallcock/.codex/skills/goodboy/SKILL.md
```

### Task 22: Final Verification And Release Commit

**Files:**
- All changed files.

- [ ] **Step 1: Run full Python test suite**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend checks**

Run:

```bash
cd ui && npm run typecheck && npm run build && npm run test:e2e
```

Expected: all checks pass.

- [ ] **Step 3: Launch local UI for visual smoke**

Run:

```bash
PYTHONPATH=src /Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m goodboy.cli ui /tmp/goodboy-demo --no-open
cd ui && npm run dev -- --port 5173
```

Expected: Review Room loads, stages render, artifact canvas is nonblank, and approval gate is visible.

- [ ] **Step 4: Verify git status**

Run:

```bash
git status -sb
```

Expected: clean or only intentional final documentation changes.

- [ ] **Step 5: Push**

Run:

```bash
git push origin main
```

Expected: `main` is updated on `adamallcock/goodboy`.

## 9. Commit Strategy

Use frequent commits matching the task boundaries:

1. `Plan Review Room UI implementation`
2. `Add local UI launch command`
3. `Add web UI view models`
4. `Add web UI project registry`
5. `Index Goodboy web artifacts`
6. `Expose read-only Review Room API`
7. `Add Review Room workflow actions`
8. `Scaffold Review Room frontend`
9. `Add Review Room API client state`
10. `Build Review Room shell`
11. `Add project open and source review UI`
12. `Add baseline review UI`
13. `Add Style Studio inspector`
14. `Add generation review UI`
15. `Add QA Review Room`
16. `Add approval and export UI`
17. `Add Goodboy UI demo mode`
18. `Wire local UI development servers`
19. `Polish Review Room accessibility`
20. `Harden Review Room backend safety`
21. `Document Review Room UI workflow`

## 10. Risk Register For This Plan

| Risk | Impact | Mitigation |
| --- | --- | --- |
| UI becomes too complex again | Review Room loses its simplicity | Keep advanced logs, manifests, and job tables collapsed by default. |
| Backend duplicates CLI logic | State drift and bugs | Wrap existing Goodboy functions and return refreshed project state. |
| Artifact serving leaks local files | Privacy/security failure | Serve only indexed artifacts from registered project roots; test traversal attempts. |
| Missing optional provider keys look like failures | User confusion | Label API keys as optional accelerators and keep Codex handoff path primary. |
| Frontend becomes generic shadcn dashboard | Weak hiring-manager impression | Use custom tokens, artifact-first layout, and Review Room-specific components. |
| Demo mode uses fake artifacts | Product feels shallow | Use synthetic fixture artifacts and real Goodboy artifact shapes. |
| Playwright setup becomes brittle | Slow verification | Keep e2e flows focused on core gates and visual surfaces. |

## 11. Self-Review

Spec coverage:

- Source review is covered in Tasks 11 and 21.
- Baseline review is covered in Task 12.
- Style customization and critique are covered in Task 13.
- Generation handoff and import are covered in Task 14.
- QA review is covered in Task 15.
- Approval/install/export are covered in Task 16.
- Demo mode is covered in Task 17.
- Backend path safety and policy gates are covered in Tasks 5, 6, 7, and 20.
- Documentation and skills are covered in Task 21.

Completion marker scan:

- This plan intentionally avoids unresolved markers and assigns each feature to a concrete task.

Type consistency:

- Backend `ProjectState`, `WorkflowGate`, and `ArtifactRef` are mirrored by frontend types.
- Routes return refreshed `ProjectState` for mutating actions.
- Stage names align with the Review Room stage rail: sources, baselines, style, generation, qa, approval, demo.

Execution note:

- Start with read-only backend and shell before adding mutating actions to keep the first UI slice demonstrable and safe.
