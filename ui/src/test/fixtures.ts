import type { ProjectState } from "../lib/types";

const demoAssetRoot = "/assets/demo/companion";

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
  project_dir: "<repo>/projects/companion-demo",
  manifest: {
    id: "companion-demo",
    display_name: "Companion Demo",
    species: "dog",
    sprite_version_number: 1,
    output_contract: { contract_id: "codex-pet-v1", rows: 9, columns: 8, cell_width: 192, cell_height: 208 }
  },
  animation_contract: {
    idle: { frame_count: 6, frame_durations_ms: [280, 110, 110, 140, 140, 320], loop_duration_ms: 1100 },
    "running-right": { frame_count: 8, frame_durations_ms: [120, 120, 120, 120, 120, 120, 120, 220], loop_duration_ms: 1060 },
    "running-left": { frame_count: 8, frame_durations_ms: [120, 120, 120, 120, 120, 120, 120, 220], loop_duration_ms: 1060 },
    waving: { frame_count: 4, frame_durations_ms: [140, 140, 140, 280], loop_duration_ms: 700 },
    jumping: { frame_count: 5, frame_durations_ms: [140, 140, 140, 140, 280], loop_duration_ms: 840 },
    failed: { frame_count: 8, frame_durations_ms: [140, 140, 140, 140, 140, 140, 140, 240], loop_duration_ms: 1220 },
    waiting: { frame_count: 6, frame_durations_ms: [150, 150, 150, 150, 150, 260], loop_duration_ms: 1010 },
    running: { frame_count: 6, frame_durations_ms: [120, 120, 120, 120, 120, 220], loop_duration_ms: 820 },
    review: { frame_count: 6, frame_durations_ms: [150, 150, 150, 150, 150, 280], loop_duration_ms: 1030 }
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
    artifact("sources-originals-source-001-png", "sources", "source", "source-reference.png", "sources/originals/source-reference.png", "info", null, "source-reference.webp"),
    artifact("candidates-contact-sheet-png", "baselines", "candidate", "contact-sheet.png", "candidates/contact-sheet.png", "info", null, "baseline-contact-sheet.webp"),
    artifact("character-selected-baseline-png", "baselines", "character", "selected-baseline.png", "character/selected-baseline.png", "success", null, "selected-baseline.webp"),
    artifact("runs-demo-row-strips-idle-png", "generation", "row-strip", "idle.png", "runs/demo/row-strips/idle.png", "success", "idle", "row-idle.webp", 1536, 208),
    artifact("runs-demo-row-strips-running-right-png", "generation", "row-strip", "running-right.png", "runs/demo/row-strips/running-right.png", "success", "running-right", "row-running-right.webp", 1536, 208),
    artifact("runs-demo-row-strips-running-left-png", "generation", "row-strip", "running-left.png", "runs/demo/row-strips/running-left.png", "success", "running-left", "row-running-left.webp", 1536, 208),
    artifact("runs-demo-row-strips-waiting-png", "generation", "row-strip", "waiting.png", "runs/demo/row-strips/waiting.png", "success", "waiting", "row-waiting.webp", 1536, 208),
    artifact("runs-demo-row-strips-running-png", "generation", "row-strip", "running.png", "runs/demo/row-strips/running.png", "success", "running", "row-running.webp", 1536, 208),
    artifact("runs-demo-row-strips-review-png", "generation", "row-strip", "review.png", "runs/demo/row-strips/review.png", "success", "review", "row-review.webp", 1536, 208),
    artifact("runs-demo-qa-contact-sheet-png", "qa", "qa", "contact-sheet.png", "runs/demo/qa/contact-sheet.png", "warning", null, "qa-contact-sheet.webp", 768, 936),
    artifact("runs-demo-qa-edge-preview-white-png", "qa", "qa", "edge-preview-white.png", "runs/demo/qa/edge-preview-white.png", "success", null, "edge-preview-white.webp", 768, 936),
    artifact("runs-demo-package-spritesheet-webp", "approval", "package", "spritesheet.webp", "runs/demo/package/spritesheet.webp", "success", null, "spritesheet.webp", 1536, 1872)
  ],
  sources: [
    { id: "source-001", path: "sources/originals/source-reference.png", notes: "Demo companion reference", roles: ["identity_three_quarter", "body_proportions"], width: 960, height: 540 }
  ],
  reference_coverage: {
    source_count: 1,
    missing_recommended_roles: ["side or marking detail"],
    ready_for_identity: true
  },
  identity_profile: {
    version: "1",
    status: "confirmed",
    identity_summary: "tiny white companion dog; rounded face; teal bandana",
    traits: [
      { id: "face.primary", category: "face", value: "tiny rounded white face", importance: "signature", locked: true },
      { id: "accessories.primary", category: "accessories", value: "teal bandana", importance: "signature", locked: true }
    ]
  },
  identity_pack: {
    status: "ready-for-review",
    canonical_base: "character/selected-baseline.png"
  },
  candidates: [
    {
      id: "baseline-001",
      style_summary: "soft lifelike companion",
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
    canonical_name: "Companion",
    one_sentence_identity: "A tiny friendly white companion dog with a teal bandana and soft expressive animation poses.",
    do_not_change: ["white companion face", "small rounded body", "teal bandana", "friendly expression"]
  },
  style_sheet: {
    id: "happy-codex-default",
    style_preset: "soft-lifelike",
    subject_kind: "pet",
    base_mood: "generally happy, entertaining, warm, pet-safe, and unobtrusive",
    global_avoid: ["text", "logos", "detached effects", "green chroma-key color in the pet"]
  },
  active_run_id: "demo",
  jobs: [
    { id: "row-idle", state: "idle", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-running-right", state: "running-right", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-running-left", state: "running-left", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-waving", state: "waving", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-jumping", state: "jumping", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-failed", state: "failed", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-waiting", state: "waiting", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-running", state: "running", kind: "row-strip", provider: "codex_builtin", status: "complete" },
    { id: "row-review", state: "review", kind: "row-strip", provider: "codex_builtin", status: "complete" }
  ],
  job_graph: { ready: [], blocked: [], complete: ["row-idle", "row-running-right", "row-running-left"] },
  events: [],
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
  likeness: {
    status: "approved",
    verdicts: [
      { trait_id: "face.primary", verdict: "pass", evidence: "The compact white face matches the source." },
      { trait_id: "accessories.primary", verdict: "pass", evidence: "The teal bandana remains visible." }
    ]
  },
  animation_review: null,
  animation_correctness: null,
  direction_review: null,
  direction_blind: null,
  approvals: [],
  exports: [],
  validation: { ok: true, issues: [], checked_files: ["goodboy.json", "runs/demo/run-summary.json"] }
};
