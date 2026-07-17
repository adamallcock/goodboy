export type Severity = "info" | "success" | "warning" | "danger";
export type ReviewStage = "sources" | "identity" | "baselines" | "style" | "generation" | "qa" | "approval" | "demo";

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
  animation_contract: Record<string, unknown>;
  gate: WorkflowGate;
  artifacts: ArtifactRef[];
  sources: Record<string, unknown>[];
  reference_coverage: Record<string, unknown> | null;
  identity_profile: Record<string, unknown> | null;
  identity_pack: Record<string, unknown> | null;
  candidates: Record<string, unknown>[];
  selected_candidate: Record<string, unknown> | null;
  character_card: Record<string, unknown> | null;
  style_sheet: Record<string, unknown> | null;
  active_run_id: string | null;
  jobs: Record<string, unknown>[];
  job_graph: Record<string, unknown> | null;
  events: Record<string, unknown>[];
  qa: Record<string, unknown> | null;
  likeness: Record<string, unknown> | null;
  animation_review: Record<string, unknown> | null;
  animation_correctness: Record<string, unknown> | null;
  direction_review: Record<string, unknown> | null;
  direction_blind: Record<string, unknown> | null;
  approvals: Record<string, unknown>[];
  exports: ArtifactRef[];
  validation: Record<string, unknown>;
}

export interface ActivityItem {
  id: string;
  kind: "action" | "system" | "qa" | "provider";
  label: string;
  detail: string;
  time: string;
}
