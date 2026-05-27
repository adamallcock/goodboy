import type { ProjectState } from "../lib/types";

function artifact(id: string, stage: string, kind: string, label: string, relativePath: string, severity = "info", state: string | null = null) {
  return {
    id,
    kind,
    label,
    relative_path: relativePath,
    url: `/demo/${relativePath}`,
    exists: true,
    width: 960,
    height: 540,
    bytes: 240000,
    modified_at: "1779900000",
    stage,
    state,
    severity: severity as "info" | "success" | "warning" | "danger"
  };
}

export const demoProjectState: ProjectState = {
  project_id: "demo-review-room",
  project_dir: "/Users/adamallcock/Documents/Coding/goodboy/projects/demo-review-room",
  manifest: {
    id: "shoulder-kitten",
    display_name: "Shoulder Kitten",
    species: "cat"
  },
  gate: {
    stage: "built_for_review",
    next_action: "visual_review",
    required_user_input: ["visual approval of contact sheet and previews"],
    artifacts_to_show_user: ["runs/demo/qa/contact-sheet.png", "runs/demo/qa/previews/idle.gif"],
    blocked_actions: ["installing before approval"],
    recommended_command: "goodboy advance /project --run-id demo --approval-notes <notes>",
    install_ready: false
  },
  artifacts: [
    artifact("sources-originals-source-001-png", "sources", "source", "source-001.png", "sources/originals/source-001.png"),
    artifact("sources-originals-source-002-png", "sources", "source", "source-002.png", "sources/originals/source-002.png"),
    artifact("candidates-contact-sheet-png", "baselines", "candidate", "contact-sheet.png", "candidates/contact-sheet.png"),
    artifact("character-selected-baseline-png", "baselines", "character", "selected-baseline.png", "character/selected-baseline.png", "success"),
    artifact("runs-demo-row-strips-idle-png", "generation", "row-strip", "idle.png", "runs/demo/row-strips/idle.png", "success", "idle"),
    artifact("runs-demo-row-strips-running-png", "generation", "row-strip", "running.png", "runs/demo/row-strips/running.png", "success", "running"),
    artifact("runs-demo-row-strips-review-png", "generation", "row-strip", "review.png", "runs/demo/row-strips/review.png", "success", "review"),
    artifact("runs-demo-row-strips-waiting-png", "generation", "row-strip", "waiting.png", "runs/demo/row-strips/waiting.png", "success", "waiting"),
    artifact("runs-demo-qa-contact-sheet-png", "qa", "qa", "contact-sheet.png", "runs/demo/qa/contact-sheet.png", "warning"),
    artifact("runs-demo-qa-centering-overlay-png", "qa", "qa", "centering-overlay.png", "runs/demo/qa/centering-overlay.png", "success"),
    artifact("runs-demo-qa-edge-preview-white-png", "qa", "qa", "edge-preview-white.png", "runs/demo/qa/edge-preview-white.png", "success"),
    artifact("runs-demo-qa-previews-idle-gif", "qa", "qa", "idle.gif", "runs/demo/qa/previews/idle.gif", "success"),
    artifact("runs-demo-package-spritesheet-webp", "approval", "package", "spritesheet.webp", "runs/demo/package/spritesheet.webp", "success")
  ],
  sources: [
    { id: "source-001", path: "sources/originals/source-001.png", notes: "front view", width: 1280, height: 960 },
    { id: "source-002", path: "sources/originals/source-002.png", notes: "side markings", width: 1280, height: 960 }
  ],
  candidates: [
    {
      id: "baseline-001",
      style_summary: "soft lifelike kitten mascot",
      character_delta: "balanced realism and charm",
      provider: "codex_builtin",
      model: "codex-imagegen",
      selected: true,
      image_path: "character/selected-baseline.png"
    },
    {
      id: "baseline-002",
      style_summary: "storybook companion",
      character_delta: "more whimsical",
      provider: "codex_builtin",
      model: "codex-imagegen",
      selected: false,
      image_path: "candidates/baseline-002/generated/candidate.png"
    }
  ],
  selected_candidate: { id: "baseline-001", selected: true },
  character_card: {
    canonical_name: "Shoulder Kitten",
    one_sentence_identity: "A tiny tabby-and-white kitten with a soft, curious expression.",
    do_not_change: ["pink nose", "white muzzle", "tabby cap", "round kitten eyes"]
  },
  style_sheet: {
    id: "happy-codex-default",
    style_preset: "soft-lifelike",
    subject_kind: "pet",
    base_mood: "generally happy, entertaining, warm, pet-safe, and unobtrusive",
    global_avoid: ["text", "logos", "detached effects", "green chroma-key color in the pet"]
  },
  active_run_id: "demo",
  qa: {
    run_id: "demo",
    stage: "built_for_review",
    install_policy: {
      ok_to_install: true,
      hard_failures: [],
      warnings: ["idle drift close to threshold"],
      row_provenance: "provider_generated"
    }
  },
  approvals: [],
  exports: [],
  validation: { ok: true, issues: [], checked_files: ["goodboy.json", "runs/demo/run-summary.json"] }
};
