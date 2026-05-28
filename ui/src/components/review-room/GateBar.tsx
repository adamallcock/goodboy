import { Activity, ArrowLeft, ArrowRight, Command, Home, Map, PanelRightClose, PanelRightOpen, RefreshCcw } from "lucide-react";

import type { ProjectState, ReviewStage } from "../../lib/types";
import { currentDecisionFor, currentWorkflowStep, nextWorkflowStep, previousWorkflowStep } from "../../lib/workflow";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

interface GateBarProps {
  state: ProjectState;
  selectedStage: ReviewStage;
  inspectorOpen: boolean;
  onOpenOnboarding: () => void;
  onStageChange: (stage: ReviewStage) => void;
  onToggleInspector: () => void;
  onToggleActivity: () => void;
  onToggleCommand: () => void;
  onToggleWalkthrough: () => void;
  onRefresh: () => void;
}

export function GateBar({
  state,
  selectedStage,
  inspectorOpen,
  onOpenOnboarding,
  onStageChange,
  onToggleInspector,
  onToggleActivity,
  onToggleCommand,
  onToggleWalkthrough,
  onRefresh
}: GateBarProps) {
  const displayName = String(state.manifest.display_name ?? state.manifest.id ?? "Goodboy");
  const decision = currentDecisionFor(state, selectedStage);
  const previousStep = previousWorkflowStep(state, selectedStage);
  const currentStep = currentWorkflowStep(state, selectedStage);
  const nextStep = nextWorkflowStep(state, selectedStage);
  return (
    <header className="gate-bar">
      <div className="brand-lockup">
        <button type="button" className="brand-mark home-mark" aria-label="Back to start" onClick={onOpenOnboarding}>
          <Home size={16} />
        </button>
        <div>
          <h1 className="brand-title">{displayName}</h1>
          <p className="brand-subtitle">Review Room</p>
        </div>
      </div>
      <div className="workflow-header" aria-label="Project progress">
        <div className="workflow-summary">
          <button type="button" disabled={!previousStep?.stage} onClick={() => previousStep?.stage && onStageChange(previousStep.stage)}>
            <ArrowLeft size={13} />
            <span>{previousStep?.label ?? "Start"}</span>
          </button>
          <div className="workflow-focus" aria-current="step">
            <span>Current step</span>
            <strong>{currentStep.label}</strong>
          </div>
          <button type="button" disabled={!nextStep?.stage} onClick={() => nextStep?.stage && onStageChange(nextStep.stage)}>
            <span>{nextStep?.label ?? "Done"}</span>
            <ArrowRight size={13} />
          </button>
        </div>
        <div className="workflow-current">
          <StatusBadge severity={decision.severity}>{decision.title}</StatusBadge>
          <span>Next: {decision.next}</span>
        </div>
      </div>
      <div className="gate-actions">
        <Button variant="ghost" aria-label="Refresh project state" onClick={onRefresh}>
          <RefreshCcw size={15} />
        </Button>
        <Button variant="ghost" aria-label="Toggle walkthrough guide" onClick={onToggleWalkthrough}>
          <Map size={15} />
          Guide
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
