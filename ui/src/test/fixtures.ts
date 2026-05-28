import type { ProjectState } from "../lib/types";

const demoAssetRoot = "/assets/demo/millie";

function artifact(
  id: string,
  stage: string,
  kind: string,
  label: string,
  relativePath: string,
  severity = "info",
  state: string | null = null,
  assetName: string | null = null,
  width = 960,
  height = 540
) {
  return {
    id,
    kind,
    label,
    relative_path: relativePath,
    url: assetName ? `${demoAssetRoot}/${assetName}` : `/demo/${relativePath}`,
    exists: true,
    width,
    height,
    bytes: 240000,
    modified_at: "1779900000",
    stage,
    state,
    severity: severity as "info" | "success" | "warning" | "danger"
  };
}

export const demoProjectState: ProjectState = {
  project_id: "demo-review-room",
  project_dir: "/Users/adamallcock/Documents/Coding/goodboy/projects/millie-demo",
  manifest: {
    id: "millie-demo",
    display_name: "Millie Demo",
    species: "dog"
  },
  gate: {
    stage: "built_for_review",
    next_action: "visual_review",
    required_user_input: ["visual approval of contact sheet and previews"],
    artifacts_to_show_user: ["runs/demo/qa/contact-sheet.png", "runs/demo/qa/edge-preview-white.png"],
    blocked_actions: ["installing before approval"],
    recommended_command: "goodboy advance /project --run-id demo --approval-notes <notes>",
    install_ready: false
  },
  artifacts: [
    artifact("sources-originals-source-001-png", "sources", "source", "source-reference.png", "sources/originals/source-reference.png", "info", null, "source-reference.png"),
    artifact("candidates-contact-sheet-png", "baselines", "candidate", "contact-sheet.png", "candidates/contact-sheet.png", "info", null, "baseline-contact-sheet.png"),
    artifact("character-selected-baseline-png", "baselines", "character", "selected-baseline.png", "character/selected-baseline.png", "success", null, "selected-baseline.png"),
    artifact("runs-demo-row-strips-idle-png", "generation", "row-strip", "idle.png", "runs/demo/row-strips/idle.png", "success", "idle", "row-idle.png", 1536, 208),
    artifact("runs-demo-row-strips-running-right-png", "generation", "row-strip", "running-right.png", "runs/demo/row-strips/running-right.png", "success", "running-right", "row-running-right.png", 1536, 208),
    artifact("runs-demo-row-strips-running-left-png", "generation", "row-strip", "running-left.png", "runs/demo/row-strips/running-left.png", "success", "running-left", "row-running-left.png", 1536, 208),
    artifact("runs-demo-row-strips-waiting-png", "generation", "row-strip", "waiting.png", "runs/demo/row-strips/waiting.png", "success", "waiting", "row-waiting.png", 1536, 208),
    artifact("runs-demo-row-strips-running-png", "generation", "row-strip", "running.png", "runs/demo/row-strips/running.png", "success", "running", "row-running.png", 1536, 208),
    artifact("runs-demo-row-strips-review-png", "generation", "row-strip", "review.png", "runs/demo/row-strips/review.png", "success", "review", "row-review.png", 1536, 208),
    artifact("runs-demo-qa-contact-sheet-png", "qa", "qa", "contact-sheet.png", "runs/demo/qa/contact-sheet.png", "warning", null, "qa-contact-sheet.png", 1536, 1872),
    artifact("runs-demo-qa-edge-preview-white-png", "qa", "qa", "edge-preview-white.png", "runs/demo/qa/edge-preview-white.png", "success", null, "edge-preview-white.png", 1536, 1872),
    artifact("runs-demo-package-spritesheet-webp", "approval", "package", "spritesheet.webp", "runs/demo/package/spritesheet.webp", "success", null, "spritesheet.webp", 1536, 1872)
  ],
  sources: [
    { id: "source-001", path: "sources/originals/source-reference.png", notes: "Millie reference", width: 960, height: 540 }
  ],
  candidates: [
    {
      id: "baseline-001",
      style_summary: "soft lifelike Maltese companion",
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
    canonical_name: "Millie",
    one_sentence_identity: "A tiny friendly white Maltese dog with a teal bandana and soft expressive animation poses.",
    do_not_change: ["white Maltese face", "small rounded body", "teal bandana", "friendly expression"]
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
