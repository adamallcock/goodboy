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

export interface ActivityItem {
  id: string;
  kind: "action" | "system" | "qa" | "provider";
  label: string;
  detail: string;
  time: string;
}
