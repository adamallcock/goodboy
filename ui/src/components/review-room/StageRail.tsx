import { Box, CheckCircle2, ClipboardCheck, GitBranch, Image, Palette, Sparkles, Wand2 } from "lucide-react";

import type { ProjectState, ReviewStage } from "../../lib/types";

const stages: Array<{ id: ReviewStage; label: string; icon: typeof Image }> = [
  { id: "sources", label: "Sources", icon: Image },
  { id: "baselines", label: "Baselines", icon: Sparkles },
  { id: "style", label: "Style", icon: Palette },
  { id: "generation", label: "Generation", icon: Wand2 },
  { id: "qa", label: "QA", icon: ClipboardCheck },
  { id: "approval", label: "Export", icon: CheckCircle2 },
  { id: "demo", label: "Demo", icon: GitBranch }
];

interface StageRailProps {
  selectedStage: ReviewStage;
  state: ProjectState;
  onStageChange: (stage: ReviewStage) => void;
}

export function StageRail({ selectedStage, state, onStageChange }: StageRailProps) {
  return (
    <nav className="stage-rail" aria-label="Review stages">
      <div className="brand-mark" aria-hidden="true">
        <Box size={18} />
      </div>
      {stages.map((stage) => {
        const Icon = stage.icon;
        const hasArtifact = state.artifacts.some((artifact) => artifact.stage === stage.id);
        return (
          <button
            key={stage.id}
            type="button"
            className={`stage-button ${selectedStage === stage.id ? "active" : ""} ${hasArtifact ? "ready" : ""}`}
            aria-label={stage.label}
            aria-current={selectedStage === stage.id ? "page" : undefined}
            title={stage.label}
            onClick={() => onStageChange(stage.id)}
          >
            <Icon size={19} />
            <span className="stage-dot" />
          </button>
        );
      })}
    </nav>
  );
}
