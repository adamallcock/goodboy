import { Activity, Check, Command, Eye, PanelRightClose, PanelRightOpen, RefreshCcw } from "lucide-react";

import type { ProjectState, ReviewStage } from "../../lib/types";
import { currentDecisionFor, workflowIndexFor, workflowStatus, workflowSteps } from "../../lib/workflow";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

interface GateBarProps {
  state: ProjectState;
  selectedStage: ReviewStage;
  inspectorOpen: boolean;
  onStageChange: (stage: ReviewStage) => void;
  onToggleInspector: () => void;
  onToggleActivity: () => void;
  onToggleCommand: () => void;
  onRefresh: () => void;
}

export function GateBar({ state, selectedStage, inspectorOpen, onStageChange, onToggleInspector, onToggleActivity, onToggleCommand, onRefresh }: GateBarProps) {
  const displayName = String(state.manifest.display_name ?? state.manifest.id ?? "Goodboy");
  const currentIndex = workflowIndexFor(state, selectedStage);
  const decision = currentDecisionFor(state, selectedStage);
  return (
    <header className="gate-bar">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true">
          <Eye size={18} />
        </div>
        <div>
          <h1 className="brand-title">{displayName}</h1>
          <p className="brand-subtitle">Review Room</p>
        </div>
      </div>
      <div className="workflow-header" aria-label="Project workflow">
        <ol className="workflow-timeline">
          {workflowSteps.map((step, index) => {
            const status = workflowStatus(index, currentIndex);
            return (
              <li key={step.id} className={`workflow-step ${status}`}>
                <button type="button" disabled={!step.stage} onClick={() => step.stage && onStageChange(step.stage)} aria-current={status === "current" ? "step" : undefined}>
                  <span className="workflow-dot">{status === "complete" ? <Check size={11} /> : index + 1}</span>
                  <span>{step.label}</span>
                </button>
              </li>
            );
          })}
        </ol>
        <div className="workflow-current">
          <StatusBadge severity={decision.severity}>{decision.title}</StatusBadge>
          <span>Next: {decision.next}</span>
        </div>
      </div>
      <div className="gate-actions">
        <Button variant="ghost" aria-label="Refresh project state" onClick={onRefresh}>
          <RefreshCcw size={15} />
        </Button>
        <Button variant="ghost" aria-label="Open command palette" onClick={onToggleCommand}>
          <Command size={15} />
          Commands
        </Button>
        <Button variant="ghost" aria-label="Toggle activity drawer" onClick={onToggleActivity}>
          <Activity size={15} />
        </Button>
        <Button variant="ghost" aria-label="Toggle inspector" onClick={onToggleInspector}>
          {inspectorOpen ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}
        </Button>
      </div>
    </header>
  );
}
