import { CheckCircle2, Clock3, FileImage, MessageSquareText, PackageCheck, Sparkles, Upload, WandSparkles } from "lucide-react";

import { artifactIsImage, artifactsForStage } from "../../lib/artifacts";
import { StyleStudio } from "../../features/style/StyleStudio";
import { shortPath, titleCase } from "../../lib/format";
import { findSpritesheetArtifact, spriteImageRendering } from "../../lib/sprite";
import type { ArtifactRef, ProjectState, ReviewStage } from "../../lib/types";
import { currentDecisionFor } from "../../lib/workflow";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";
import { SpriteStateViewer } from "./SpriteStateViewer";

interface ReviewDecisionSurfaceProps {
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  onStageChange: (stage: ReviewStage) => void;
  onOpenDetails: () => void;
  onOpenPreview: () => void;
  onApproveDemo: (notes: string) => void;
}

export function ReviewDecisionSurface({
  state,
  selectedStage,
  selectedArtifact,
  onStageChange,
  onOpenDetails,
  onOpenPreview,
  onApproveDemo
}: ReviewDecisionSurfaceProps) {
  const decision = currentDecisionFor(state, selectedStage);
  const spritesheet = findSpritesheetArtifact(state);
  const stageTitle = selectedStage === "qa" ? "QA Review" : selectedStage === "style" ? "Style Studio" : titleCase(selectedStage);
  const approvalNotes = "Reviewed animated state viewer, QA summary, centering, drift, edge cleanup, and generated files.";

  return (
    <main className="decision-shell" aria-label={`${stageTitle} decision surface`}>
      <div className="decision-main">
        <section className="decision-hero">
          <div>
            <span className="section-kicker">{decision.title}</span>
            <h2>{stageTitle}</h2>
            <p>{decision.detail}</p>
          </div>
          <div className="decision-hero-actions">
            <Button variant="default" onClick={onOpenDetails}>
              <FileImage size={14} />
              View details
            </Button>
            {selectedStage === "qa" || selectedStage === "approval" ? (
              <Button variant="primary" onClick={() => onApproveDemo(approvalNotes)}>
                <CheckCircle2 size={14} />
                Approve visual review
              </Button>
            ) : null}
          </div>
        </section>
        <StageDecision
          state={state}
          selectedStage={selectedStage}
          selectedArtifact={selectedArtifact}
          spritesheet={spritesheet}
          onOpenPreview={onOpenPreview}
          onStageChange={onStageChange}
          onOpenDetails={onOpenDetails}
        />
      </div>
    </main>
  );
}

function StageDecision({
  state,
  selectedStage,
  selectedArtifact,
  spritesheet,
  onOpenPreview,
  onStageChange,
  onOpenDetails
}: {
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  spritesheet: ArtifactRef | null;
  onOpenPreview: () => void;
  onStageChange: (stage: ReviewStage) => void;
  onOpenDetails: () => void;
}) {
  if (selectedStage === "qa" && spritesheet) {
    return (
      <div className="decision-stack">
        <SpriteStateViewer
          spritesheetUrl={spritesheet.url}
          imageRendering={spriteImageRendering(state)}
          onOpenPreview={onOpenPreview}
          qaSummary={[
            { label: "Centering", value: "Stable", severity: "success" },
            { label: "Drift", value: "Near threshold", severity: "warning" },
            { label: "Transparency", value: "Clean", severity: "success" },
            { label: "Duplicates", value: "None", severity: "success" }
          ]}
        />
        <div className="decision-action-card">
          <div>
            <h3>Approve this pet or request changes</h3>
            <p>The animated states are the primary review surface. Open details only when you need raw QA files, provenance, or policy evidence.</p>
          </div>
          <div className="toolbar-group">
            <Button variant="default" onClick={() => onStageChange("style")}>
              <MessageSquareText size={14} />
              Request changes
            </Button>
            <Button variant="default" onClick={onOpenDetails}>
              Open QA details
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (selectedStage === "baselines") {
    return <BaselineDecision state={state} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "generation") {
    return <GenerationStatus state={state} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "style") {
    return <StyleDecision state={state} onStageChange={onStageChange} />;
  }

  if (selectedStage === "approval") {
    return <ExportDecision state={state} spritesheet={spritesheet} onOpenPreview={onOpenPreview} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "sources") {
    return <SourceDecision state={state} selectedArtifact={selectedArtifact} onOpenDetails={onOpenDetails} />;
  }

  return <DemoDecision state={state} />;
}

function BaselineDecision({ state, onOpenDetails }: { state: ProjectState; onOpenDetails: () => void }) {
  const candidates = state.candidates.slice(0, 3);
  const selectedBaseline = state.artifacts.find((artifact) => artifact.kind === "character");
  return (
    <section className="decision-card-grid" aria-label="Baseline candidates">
      {candidates.map((candidate, index) => (
        <article className={`decision-card candidate ${candidate.selected ? "active" : ""}`} key={String(candidate.id)}>
          {selectedBaseline && index === 0 && artifactIsImage(selectedBaseline) ? <img src={selectedBaseline.url} alt="" /> : <span className="candidate-placeholder" />}
          <div>
            <h3>{String(candidate.id)}</h3>
            <p>{String(candidate.style_summary ?? candidate.character_delta ?? "Generated baseline")}</p>
          </div>
          <StatusBadge severity={candidate.selected ? "success" : "info"}>{candidate.selected ? "Selected" : String(candidate.provider ?? "planned")}</StatusBadge>
        </article>
      ))}
      <article className="decision-card helper">
        <Sparkles size={18} />
        <h3>Choose one baseline</h3>
        <p>Goodboy records the selected style and identity traits so later rows can be regenerated consistently.</p>
        <Button variant="default" onClick={onOpenDetails}>Open candidate files</Button>
      </article>
    </section>
  );
}

function GenerationStatus({ state, onOpenDetails }: { state: ProjectState; onOpenDetails: () => void }) {
  const rowArtifacts = state.artifacts.filter((artifact) => artifact.kind === "row-strip");
  return (
    <section className="monitor-card" aria-label="Generation monitor">
      <div className="monitor-heading">
        <WandSparkles size={18} />
        <div>
          <h3>Codex generated the row strips</h3>
          <p>Review Room stays quiet here unless a generation job needs attention.</p>
        </div>
      </div>
      <div className="state-count-grid">
        {rowArtifacts.map((artifact) => (
          <div className="data-row" key={artifact.id}>
            <span>{artifact.state ?? artifact.label}</span>
            <StatusBadge severity={artifact.severity}>{artifact.exists ? "Present" : "Missing"}</StatusBadge>
          </div>
        ))}
      </div>
      <Button variant="default" onClick={onOpenDetails}>Open generated files</Button>
    </section>
  );
}

function StyleDecision({ state, onStageChange }: { state: ProjectState; onStageChange: (stage: ReviewStage) => void }) {
  return (
    <section className="monitor-card style-decision" aria-label="Style decision">
      <StyleStudio state={state} />
      <div className="decision-action-card inline">
        <p>Use the recorded style card unless you want the agent to branch for a specific look such as realistic, anime, plush, or object mascot.</p>
        <Button variant="primary" onClick={() => onStageChange("generation")}>Use style and continue</Button>
      </div>
    </section>
  );
}

function SourceDecision({ state, selectedArtifact, onOpenDetails }: { state: ProjectState; selectedArtifact: ArtifactRef | null; onOpenDetails: () => void }) {
  return (
    <section className="source-decision-grid" aria-label="Source identity review">
      <div className="source-preview-card">
        {selectedArtifact && artifactIsImage(selectedArtifact) ? <img src={selectedArtifact.url} alt={selectedArtifact.label} /> : <Upload size={28} />}
      </div>
      <div className="monitor-card">
        <div className="monitor-heading">
          <Upload size={18} />
          <div>
            <h3>Start with clear references</h3>
            <p>{String(state.character_card?.one_sentence_identity ?? "Confirm the subject identity before generating baselines.")}</p>
          </div>
        </div>
        <div className="state-count-grid">
          <div className="data-row">
            <span>Sources</span>
            <strong>{state.sources.length}</strong>
          </div>
          <div className="data-row">
            <span>Validation</span>
            <StatusBadge severity={state.validation.ok ? "success" : "danger"}>{state.validation.ok ? "Clean" : "Issues"}</StatusBadge>
          </div>
        </div>
        <Button variant="default" onClick={onOpenDetails}>Open source details</Button>
      </div>
    </section>
  );
}

function ExportDecision({
  state,
  spritesheet,
  onOpenPreview,
  onOpenDetails
}: {
  state: ProjectState;
  spritesheet: ArtifactRef | null;
  onOpenPreview: () => void;
  onOpenDetails: () => void;
}) {
  return (
    <section className="monitor-card" aria-label="Export package">
      <div className="monitor-heading">
        <PackageCheck size={18} />
        <div>
          <h3>{state.gate.install_ready ? "Package ready" : "Approval needed"}</h3>
          <p>Export stays behind the visual approval gate so agents do not install unreviewed pets.</p>
        </div>
      </div>
      <div className="state-count-grid">
        <div className="data-row">
          <span>Spritesheet</span>
          <StatusBadge severity={spritesheet ? "success" : "warning"}>{spritesheet ? shortPath(spritesheet.relative_path) : "Missing"}</StatusBadge>
        </div>
        <div className="data-row">
          <span>Install policy</span>
          <StatusBadge severity={state.gate.install_ready ? "success" : "warning"}>{state.gate.install_ready ? "Ready" : "Needs approval"}</StatusBadge>
        </div>
      </div>
      <div className="toolbar-group">
        <Button variant="default" onClick={onOpenPreview}>Open large preview</Button>
        <Button variant="default" onClick={onOpenDetails}>Open package details</Button>
      </div>
    </section>
  );
}

function DemoDecision({ state }: { state: ProjectState }) {
  return (
    <section className="monitor-card" aria-label="Demo walkthrough">
      <div className="monitor-heading">
        <Clock3 size={18} />
        <div>
          <h3>Companion demo walkthrough</h3>
          <p>Use the stepper to see the same gates that a real Goodboy run asks you to review.</p>
        </div>
      </div>
      <div className="state-count-grid">
        {artifactsForStage(state.artifacts, "qa").map((artifact) => (
          <div className="data-row" key={artifact.id}>
            <span>{artifact.label}</span>
            <StatusBadge severity={artifact.severity}>{artifact.kind}</StatusBadge>
          </div>
        ))}
      </div>
    </section>
  );
}
