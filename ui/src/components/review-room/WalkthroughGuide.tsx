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
  { stage: "sources", label: "Start with sources", detail: "Confirm the subject identity and source references.", icon: Images },
  { stage: "baselines", label: "Pick the character", detail: "Choose the baseline that best preserves the pet.", icon: Sparkles },
  { stage: "style", label: "Tune the style", detail: "Record style, subject type, and critique notes.", icon: WandSparkles },
  { stage: "generation", label: "Review rows", detail: "Inspect row strips before final QA is built.", icon: ArrowRight },
  { stage: "qa", label: "Approve QA", detail: "Check centering, drift, clipping, and edge cleanup.", icon: CheckCircle2 }
];

const starterPrompt = "Use Goodboy to create a Codex pet from these source images. Start by planning baseline candidates, then pause for my visual choice before generating rows.";

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
