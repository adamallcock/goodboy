import { ArrowRight, CheckCircle2, Clipboard, Images, Sparkles, WandSparkles } from "lucide-react";
import { toast } from "sonner";

import type { ReviewStage } from "../../lib/types";
import { Button } from "../ui/button";

interface WalkthroughGuideProps {
  open: boolean;
  selectedStage: ReviewStage;
  onStageChange: (stage: ReviewStage) => void;
  onClose: () => void;
  onOpenOnboarding: () => void;
}

const walkthroughSteps: Array<{ stage: ReviewStage; label: string; detail: string; icon: typeof Images }> = [
  { stage: "sources", label: "Start with sources", detail: "Review source coverage, privacy, and reference roles.", icon: Images },
  { stage: "baselines", label: "Pick the character", detail: "Choose the baseline that best preserves the pet.", icon: Sparkles },
  { stage: "style", label: "Tune the style", detail: "Record style, subject type, and critique notes.", icon: WandSparkles },
  { stage: "generation", label: "Follow the DAG", detail: "Generate only ready rows and repair the smallest failed scope.", icon: ArrowRight },
  { stage: "qa", label: "Complete v2 review", detail: "Check animation, 16 directions, likeness, geometry, and edges.", icon: CheckCircle2 }
];

const starterPrompt = "Use Goodboy v2 in My Pet mode with these source images. Build an evidence-linked identity, ask before sending EXIF-stripped derivatives to a provider, pause for my likeness baseline choice, and require direction plus trait-level likeness review before installation.";

export function WalkthroughGuide({ open, selectedStage, onStageChange, onClose, onOpenOnboarding }: WalkthroughGuideProps) {
  if (!open) return null;

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(starterPrompt);
      toast.success("Starter prompt copied");
    } catch {
      toast.error("Could not copy starter prompt");
    }
  };

  return (
    <aside className="walkthrough-guide" aria-label="Review Room walkthrough guide">
      <div className="walkthrough-guide-header">
        <div>
          <strong>Companion demo walkthrough</strong>
          <span>Follow the same decisions you will make for your own Codex pet.</span>
        </div>
        <button type="button" aria-label="Hide walkthrough guide" onClick={onClose}>
          Hide
        </button>
      </div>
      <div className="walkthrough-step-list">
        {walkthroughSteps.map((step, index) => {
          const Icon = step.icon;
          const active = selectedStage === step.stage;
          return (
            <button key={step.stage} type="button" className={`walkthrough-step ${active ? "active" : ""}`} onClick={() => onStageChange(step.stage)}>
              <span>{index + 1}</span>
              <Icon size={14} />
              <strong>{step.label}</strong>
              <em>{step.detail}</em>
            </button>
          );
        })}
      </div>
      <div className="walkthrough-cta">
        <Button variant="primary" onClick={copyPrompt}>
          <Clipboard size={14} />
          Copy starter prompt
        </Button>
        <Button variant="default" onClick={onOpenOnboarding}>
          Create your own
        </Button>
      </div>
    </aside>
  );
}
