---
title: Goodboy UI Component Scan And Design Options
date: 2026-05-27
type: research
status: draft
---

# Goodboy UI Component Scan And Design Options

## 1. Purpose

This document identifies modern off-the-shelf frontend components that can accelerate M10 without making Goodboy look generic. It also defines initial design directions to turn into visual concepts.

The guiding principle is simple: use off-the-shelf components for commodity interaction behavior, then apply a custom Goodboy design system around the parts that matter: artifact review, workflow gates, QA trust, and creative style direction.

## 2. Recommended Stack

### 2.1 Default Choice

Use React + Vite + TypeScript with a shadcn/Radix/Tailwind component layer.

Why:

- shadcn/ui already covers the common app primitives Goodboy needs: sidebar, command, data table, dialog, drawer, tabs, scroll area, select, slider, tooltip, sonner, resizable panels, and more.
- Radix gives accessible, unstyled primitives for the lower-level interaction pieces.
- Tailwind makes it easy to own a custom Goodboy visual system without fighting a full theme framework.
- Copy-owned components are useful for a portfolio-quality app because we can tune the exact chrome, density, states, and interaction polish.

### 2.2 Alternative

Mantine is the best fallback if speed of assembly matters more than total visual ownership. It includes a broad set of accessible React components and hooks, and its docs are unusually friendly to AI-assisted development.

Tradeoff: Mantine will get us a polished baseline quickly, but it may take more work to avoid a recognizable library look. For a hiring-manager showpiece, shadcn/Radix gives better ownership of the final design language.

## 3. Component Recommendations

| Need | Recommended Component | Why It Fits |
| --- | --- | --- |
| App shell, sidebar, tabs, dialogs, drawers, controls, resizable panels | shadcn/ui over Radix | Fast assembly, accessible primitives, code ownership, Tailwind styling, broad component coverage. |
| Low-level accessible primitives | Radix Primitives | Useful if we need finer control than shadcn wrappers expose. |
| Source drag/drop ingest | react-dropzone | Simple hook for HTML5-compliant drag-and-drop file zones. |
| Project/job/QA tables | TanStack Table | Headless table logic with full control over Goodboy's visual design. |
| Command palette | cmdk or shadcn Command | Good fit for project actions, artifact search, and keyboard-first power use. |
| Icons | Lucide React | Clean, consistent SVG icon set that matches the restrained tool aesthetic. |
| Toasts/status notifications | Sonner via shadcn | Simple non-blocking feedback for workflow actions and long-running state changes. |
| Artifact lightbox/gallery | PhotoSwipe or custom wrapper | Good starting point for zoomable source/candidate/review images. |
| Image before/after comparison | react-compare-slider | Small, accessible slider for comparing source/baseline, old/new branch, or QA before/after. |
| Prompt/manifest viewer | @monaco-editor/react, deferred | Useful for advanced mode, but too heavy for MVP unless prompt editing becomes central. |
| Branch lineage and demo story | React Flow, optional | Strong if we want interactive branch/run lineage, but should not be used for ordinary workflow navigation. |
| Simple QA charts | Recharts, optional | Useful only where a chart improves drift/edge clarity; tables and overlays are more important. |
| Client state | Zustand or plain React state | Zustand is useful for UI-only state like selected artifact, panels, filters, and playback speed. |

## 4. Avoid For MVP

- Full dashboard template packs that impose a generic visual language.
- Heavy all-in-one grids unless Goodboy outgrows TanStack Table.
- Complex canvas/editor frameworks for the first UI.
- Animation libraries as a foundation. Use CSS and focused motion first.
- Monaco editor in the first slice unless prompt editing becomes a primary workflow.
- React Flow as the main product shell. It is useful for lineage, not for every screen.

## 5. Design System Direction

Goodboy should use off-the-shelf behavior with custom visual styling:

- Layout: three-pane studio shell with resizable panels.
- Background: quiet neutral canvas, not a single-hue dark slate or beige theme.
- Accent palette: restrained blue/cyan for selected and provider states, amber for warnings, rose/red for hard failures, green only for pass states and never as a dominant accent.
- Surfaces: flat or lightly elevated panels, 6-8 px radius, crisp borders, no nested cards.
- Typography: compact, professional UI text; artifact names and status labels should be readable at dense sizes.
- Icons: Lucide outline icons with consistent stroke width.
- Motion: small state transitions, preview playback controls, and command feedback only.

## 6. Design Direction Options

### Option A: Studio Console

Recommended default.

Structure:

- Left rail: project, Sources, Baselines, Style, Generation, Review, Export.
- Center: large artifact canvas with source images, candidate gallery, contact sheet, GIF previews, or QA overlay.
- Right inspector: selected artifact metadata, style intent, gate status, warnings, actions.
- Bottom drawer: activity log and command stream.

Visual character:

- Premium local creative tool.
- High information density without looking like an admin dashboard.
- Best balance of showpiece polish and real workflow utility.

Best borrowed components:

- shadcn Sidebar, Resizable, Tabs, Sheet/Dialog, Tooltip, Sonner.
- PhotoSwipe/custom viewer for artifacts.
- TanStack Table for jobs and QA.
- react-compare-slider for visual diffs.

### Option B: Storyboard Pipeline

Most explanatory.

Structure:

- Horizontal stage board: Sources -> Baselines -> Style -> Rows -> QA -> Export.
- Each stage has a compact artifact strip and a large selected artifact.
- A timeline ribbon explains the state of the run.
- Detail inspector opens contextually.

Visual character:

- Beautiful for demos and hiring-manager walkthroughs.
- Turns Goodboy into a process narrative, not just a tool.

Best borrowed components:

- shadcn Tabs/Carousel/Scroll Area.
- React Flow or custom SVG for the timeline only.
- PhotoSwipe for artifact inspection.

Risk:

- Detailed QA may need a stronger focused review mode.

### Option C: Review Room

Most visual.

Structure:

- Artifact-first full-screen workspace.
- Minimal left navigation.
- Floating toolbar for zoom, compare, overlay, playback, and approval.
- Collapsible right inspector for QA and provenance.

Visual character:

- Feels like a high-end visual review app.
- Strongest for candidate selection and QA.

Best borrowed components:

- PhotoSwipe/custom zoom viewer.
- react-compare-slider.
- shadcn Sheet, Tooltip, Toggle Group, Slider.
- GIF playback wrapper.

Risk:

- Could hide workflow structure and provider/job state unless the inspector is very strong.

### Option D: Command Center

Most agent/developer oriented.

Structure:

- Gate/status led workspace.
- Command palette prominent.
- Artifact grid and logs side by side.
- QA tables and policy panels are central.

Visual character:

- Trustworthy and operational.
- Strong for debugging and explaining safety rails.

Best borrowed components:

- cmdk/shadcn Command.
- TanStack Table.
- shadcn Alert, Progress, Data Table, Sonner.

Risk:

- Least emotionally polished unless paired with richer artifact presentation.

## 7. Recommendation

Proceed with Option C, Review Room, as the base design.

Review Room is the better primary surface because Goodboy is fundamentally a visual judgment workflow. The permanent UI should ask one clear question at a time: which artifact are we reviewing, what does the QA/provenance say, and what is the next safe action?

Borrow selectively:

- Use Option A's Studio Console as an advanced mode for logs, job tables, manifests, and debugging.
- Use Option B's narrative strip for demo mode and stage orientation.
- Use Option D's command palette and gate explanations for trust and agent compatibility.

This gives us a cleaner showcase surface without sacrificing the serious workflow underneath.

Implementation plan: `docs/superpowers/plans/2026-05-27-goodboy-review-room-ui-implementation-plan.md`

## 8. Visual Concept Brief

Generate a design option board with three high-fidelity desktop mockups:

1. Studio Console: artifact canvas, right inspector, left rail, bottom activity drawer.
2. Storyboard Pipeline: stage timeline with large selected artifact and process narrative.
3. Review Room: immersive artifact review with floating controls and collapsible QA inspector.

All options should:

- Use real-looking pet/source/candidate/contact-sheet/QA preview artifacts.
- Avoid decorative hero treatment.
- Avoid nested cards.
- Avoid one-note purple, dark slate, beige, or orange palettes.
- Feel modern, calm, sophisticated, and practical.
- Make approval gates and QA state visible.

Generated boards:

- Preferred light board: `docs/assets/goodboy-ui-design-directions-light-board.png`
- Earlier dark board, useful only as a structural reference: `docs/assets/goodboy-ui-design-directions-dark-board.png`

The light board is the stronger direction because it avoids over-indexing on a dark developer-dashboard aesthetic while preserving the same information architecture.

## 9. Sources Reviewed

- shadcn/ui components: https://ui.shadcn.com/docs/components
- Radix Primitives introduction: https://www.radix-ui.com/primitives/docs/overview/introduction
- Mantine homepage: https://mantine.dev/
- TanStack Table introduction: https://tanstack.com/table/latest/docs/introduction
- react-dropzone README: https://github.com/react-dropzone/react-dropzone
- PhotoSwipe homepage: https://photoswipe.com/
- React Flow homepage: https://reactflow.dev/
- cmdk README: https://github.com/dip/cmdk
- Lucide homepage: https://lucide.dev/
- Recharts homepage: https://recharts.github.io/
- react-compare-slider npm page: https://www.npmjs.com/package/react-compare-slider
