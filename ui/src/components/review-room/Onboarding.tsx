import { ArrowRight, Bot, CheckCircle2, FolderOpen, Images, PlayCircle, Sparkles } from "lucide-react";
import { useState } from "react";

import { ProjectOpen } from "../../features/project/ProjectOpen";
import { useProjectStore } from "../../state/project-store";
import { Button } from "../ui/button";

type OnboardingPath = "create" | "open" | "demo";

const paths: Array<{
  id: OnboardingPath;
  title: string;
  description: string;
  icon: typeof Bot;
  cta: string;
}> = [
  {
    id: "create",
    title: "Create with Codex",
    description: "Start from source images. The agent runs Goodboy and pauses for your visual decisions.",
    icon: Bot,
    cta: "Show guided flow"
  },
  {
    id: "open",
    title: "Open a project",
    description: "Load an existing Goodboy folder and inspect its current artifacts and gates.",
    icon: FolderOpen,
    cta: "Open project"
  },
  {
    id: "demo",
    title: "Explore demo",
    description: "Walk through a sample pet project with sources, baselines, generated rows, QA, and approval.",
    icon: PlayCircle,
    cta: "Start demo"
  }
];

export function Onboarding() {
  const [selectedPath, setSelectedPath] = useState<OnboardingPath>("demo");
  const startDemo = useProjectStore((store) => store.startDemo);
  const closeOnboarding = useProjectStore((store) => store.closeOnboarding);
  const selected = paths.find((path) => path.id === selectedPath) ?? paths[0];
  const SelectedIcon = selected.icon;

  return (
    <div className="onboarding-shell" aria-label="Goodboy onboarding">
      <header className="onboarding-header">
        <div className="onboarding-brand">
          <span className="brand-mark" aria-hidden="true">
            <Sparkles size={17} />
          </span>
          <div>
            <h1>Goodboy Review Room</h1>
            <p>Agent-led pet generation with human visual decisions.</p>
          </div>
        </div>
        <Button variant="ghost" onClick={closeOnboarding}>
          Continue review
          <ArrowRight size={14} />
        </Button>
      </header>

      <main className="onboarding-main">
        <section className="onboarding-intro">
          <p className="onboarding-kicker">Start here</p>
          <h2>Review Room keeps the user decisions clear while Codex handles the pipeline.</h2>
          <p>
            Choose how you want to begin. The app will show where the project is, which artifact needs review, and what happens after approval or feedback.
          </p>
        </section>

        <section className="onboarding-paths" aria-label="Start options">
          {paths.map((path) => {
            const Icon = path.icon;
            return (
              <button
                key={path.id}
                type="button"
                className={`onboarding-path ${path.id === selectedPath ? "active" : ""}`}
                onClick={() => (path.id === "demo" ? startDemo() : setSelectedPath(path.id))}
              >
                <Icon size={20} />
                <strong>{path.title}</strong>
                <span>{path.description}</span>
                <em>{path.cta}</em>
              </button>
            );
          })}
        </section>

        <section className="onboarding-detail" aria-live="polite">
          <div className="onboarding-detail-heading">
            <SelectedIcon size={20} />
            <div>
              <h3>{selected.title}</h3>
              <p>{selected.description}</p>
            </div>
          </div>
          {selectedPath === "create" ? <CreateWithCodex /> : null}
          {selectedPath === "open" ? <ProjectOpen /> : null}
          {selectedPath === "demo" ? <DemoPreview onStart={startDemo} /> : null}
        </section>
      </main>
    </div>
  );
}

function CreateWithCodex() {
  return (
    <div className="onboarding-steps">
      <div className="onboarding-step">
        <CheckCircle2 size={15} />
        <span>Give Codex the source images and ask it to use Goodboy.</span>
      </div>
      <div className="onboarding-step">
        <CheckCircle2 size={15} />
        <span>Codex creates the project, plans baselines, and stops for your choices.</span>
      </div>
      <div className="onboarding-step">
        <CheckCircle2 size={15} />
        <span>Return here to review baselines, QA artifacts, approvals, and exports.</span>
      </div>
      <div className="onboarding-command">
        <Bot size={16} />
        <span>Use Goodboy to create a Codex pet from these source images.</span>
      </div>
    </div>
  );
}

function DemoPreview({ onStart }: { onStart: () => void }) {
  return (
    <div className="demo-preview">
      <div className="demo-preview-grid" aria-hidden="true">
        {Array.from({ length: 12 }).map((_, index) => (
          <span key={index} className={index % 5 === 0 ? "warn" : "pass"} />
        ))}
      </div>
      <div className="demo-preview-copy">
        <h4>Shoulder Kitten demo</h4>
        <p>No files are installed or changed. You can move through each artifact stage and try approval safely.</p>
        <Button variant="primary" onClick={onStart}>
          Start demo walkthrough
          <Images size={14} />
        </Button>
      </div>
    </div>
  );
}
