import type { ProjectState, ReviewStage, Severity } from "./types";

export interface WorkflowStep {
  id: string;
  label: string;
  stage: ReviewStage | null;
}

export const workflowSteps: WorkflowStep[] = [
  { id: "start", label: "Start", stage: null },
  { id: "sources", label: "Sources", stage: "sources" },
  { id: "identity", label: "Identity", stage: "identity" },
  { id: "baselines", label: "Baselines", stage: "baselines" },
  { id: "style", label: "Style", stage: "style" },
  { id: "generation", label: "Generate", stage: "generation" },
  { id: "qa", label: "QA Review", stage: "qa" },
  { id: "approval", label: "Approve", stage: "approval" },
  { id: "export", label: "Export", stage: "approval" }
];

export function workflowIndexFor(state: ProjectState, selectedStage: ReviewStage): number {
  if (state.gate.install_ready) return workflowSteps.findIndex((step) => step.id === "export");
  if (state.gate.stage.includes("approved")) return workflowSteps.findIndex((step) => step.id === "approval");
  const selectedIndex = workflowSteps.findIndex((step) => step.stage === selectedStage);
  return Math.max(1, selectedIndex);
}

export function workflowStatus(index: number, currentIndex: number): "complete" | "current" | "upcoming" {
  if (index < currentIndex) return "complete";
  if (index === currentIndex) return "current";
  return "upcoming";
}

export function currentDecisionFor(state: ProjectState, selectedStage: ReviewStage): { title: string; detail: string; severity: Severity; next: string } {
  if (state.gate.install_ready) {
    return {
      title: "Ready to export",
      detail: "Visual approval is recorded and the package is ready for the final handoff.",
      severity: "success",
      next: "Export package"
    };
  }
  if (selectedStage === "sources") {
    return {
      title: "Confirm the source identity",
      detail: "Check that the source references and identity notes describe the right subject before baseline generation.",
      severity: "info",
      next: "Confirm identity"
    };
  }
  if (selectedStage === "identity") {
    return {
      title: state.identity_profile?.status === "confirmed" ? "Identity confirmed" : "Decision needed: identity",
      detail: "Confirm the evidence-linked traits that must remain recognizable across every pose and direction.",
      severity: state.identity_profile?.status === "confirmed" ? "success" : "warning",
      next: "Generate likeness candidates"
    };
  }
  if (selectedStage === "baselines") {
    return {
      title: "Choose the character baseline",
      detail: "Pick the generated baseline that best preserves the subject and style direction.",
      severity: "info",
      next: "Tune style"
    };
  }
  if (selectedStage === "style") {
    return {
      title: "Set the visual direction",
      detail: "Choose the style and subject treatment before row generation continues.",
      severity: "info",
      next: "Generate rows"
    };
  }
  if (selectedStage === "generation") {
    return {
      title: "Review generated rows",
      detail: "Make sure the row jobs and generated strips are present before building final QA artifacts.",
      severity: "info",
      next: "Run QA review"
    };
  }
  if (selectedStage === "qa") {
    return {
      title: "Decision needed: visual QA",
      detail: "Review the contact sheet, previews, centering, drift, and edge cleanup before approval.",
      severity: "warning",
      next: "Approve or request changes"
    };
  }
  if (selectedStage === "approval") {
    return {
      title: "Record approval",
      detail: "Approve the current review artifacts, then export or install through Goodboy's safety gates.",
      severity: "warning",
      next: "Export package"
    };
  }
  return {
    title: "Walk through the demo",
    detail: "Explore each artifact stage without changing local project files.",
    severity: "info",
    next: "Open Sources"
  };
}

export function previousWorkflowStep(state: ProjectState, selectedStage: ReviewStage): WorkflowStep | null {
  const currentIndex = workflowIndexFor(state, selectedStage);
  return workflowSteps[currentIndex - 1] ?? null;
}

export function currentWorkflowStep(state: ProjectState, selectedStage: ReviewStage): WorkflowStep {
  const currentIndex = workflowIndexFor(state, selectedStage);
  return workflowSteps[currentIndex] ?? workflowSteps[1];
}

export function nextWorkflowStep(state: ProjectState, selectedStage: ReviewStage): WorkflowStep | null {
  const currentIndex = workflowIndexFor(state, selectedStage);
  return workflowSteps[currentIndex + 1] ?? null;
}
