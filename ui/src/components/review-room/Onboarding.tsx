import { ArrowRight, Bot, CheckCircle2, Clipboard, FolderOpen, Images, PlayCircle, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

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
    title: "Explore companion demo",
    description: "Walk through a completed legacy pet example; real v2 projects add identity, direction, and repair gates.",
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
            The demo is read-only, so it is safe to explore before making your own.
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
  const [projectDir, setProjectDir] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [petId, setPetId] = useState("");
  const [species, setSpecies] = useState("pet");
  const createProject = useProjectStore((store) => store.createProject);
  const prompt = "Use Goodboy v2 in My Pet mode. Build an evidence-linked identity from my source images, pause for identity confirmation, then generate a Codex v2 pet and require direction plus likeness review.";
  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      toast.success("Prompt copied");
    } catch {
      toast.error("Could not copy prompt");
    }
  };

  return (
    <div className="onboarding-steps">
      <div className="onboarding-step">
        <CheckCircle2 size={15} />
        <span>Give Codex the source images and ask it to use Goodboy.</span>
      </div>
      <div className="onboarding-step">
        <CheckCircle2 size={15} />
        <span>Create the local v2 workspace here, then add source images in Review Room.</span>
      </div>
      <div className="onboarding-step">
        <CheckCircle2 size={15} />
        <span>Return here to review baselines, QA artifacts, approvals, and exports.</span>
      </div>
      <div className="onboarding-command">
        <Bot size={16} />
        <span>{prompt}</span>
      </div>
      <div className="project-create-grid">
        <label className="project-path-field">
          <span>Project folder</span>
          <input value={projectDir} onChange={(event) => setProjectDir(event.target.value)} placeholder="/absolute/path/to/my-pet" />
        </label>
        <label className="project-path-field">
          <span>Display name</span>
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Millie" />
        </label>
        <label className="project-path-field">
          <span>Pet ID</span>
          <input value={petId} onChange={(event) => setPetId(event.target.value)} placeholder="millie" />
        </label>
        <label className="project-path-field">
          <span>Species or type</span>
          <input value={species} onChange={(event) => setSpecies(event.target.value)} placeholder="dog" />
        </label>
      </div>
      <div className="toolbar-group onboarding-cta-row">
        <Button
          variant="primary"
          disabled={!projectDir.trim() || !displayName.trim() || !petId.trim()}
          onClick={() => void createProject(projectDir.trim(), petId.trim(), displayName.trim(), species.trim() || "pet")}
        >
          Create v2 project
          <ArrowRight size={14} />
        </Button>
        <Button variant="primary" onClick={copyPrompt}>
          <Clipboard size={14} />
          Copy agent prompt
        </Button>
        <Button variant="default" onClick={() => toast.info("Attach source images in Codex, then paste the copied prompt.")}>
          What next?
        </Button>
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
        <h4>Companion demo</h4>
        <p>Uses a completed legacy v1 package to demonstrate backward-compatible review. No files are installed or changed.</p>
        <Button variant="primary" onClick={onStart}>
          Start demo walkthrough
          <Images size={14} />
        </Button>
      </div>
    </div>
  );
}
