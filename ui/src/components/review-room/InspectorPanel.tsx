import { CheckCircle2, ClipboardCheck, Download, GitBranch, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { formatBytes, shortPath, titleCase } from "../../lib/format";
import type { ArtifactRef, ProjectState, ReviewStage } from "../../lib/types";
import { ApprovalExport } from "../../features/approval/ApprovalExport";
import { BaselineReview } from "../../features/baselines/BaselineReview";
import { DemoMode } from "../../features/demo/DemoMode";
import { GenerationReview } from "../../features/generation/GenerationReview";
import { ProjectOpen } from "../../features/project/ProjectOpen";
import { QaReview } from "../../features/qa/QaReview";
import { SourceReview } from "../../features/sources/SourceReview";
import { StyleStudio } from "../../features/style/StyleStudio";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

interface InspectorPanelProps {
  open: boolean;
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  onApproveDemo: (notes: string) => void;
}

export function InspectorPanel({ open, state, selectedStage, selectedArtifact, onApproveDemo }: InspectorPanelProps) {
  const [notes, setNotes] = useState("Reviewed contact sheet, previews, edge preview, and centering overlay.");
  const policy = useMemo(() => state.qa?.install_policy as Record<string, unknown> | undefined, [state.qa]);
  return (
    <aside className={`inspector ${open ? "" : "closed"}`} aria-label="Inspector panel">
      <div className="inspector-scroll">
        <section className="inspector-section">
          <h3>Current Gate</h3>
          <StatusBadge severity={state.gate.install_ready ? "success" : "warning"}>{titleCase(state.gate.next_action)}</StatusBadge>
          <dl>
            <div className="key-value">
              <dt>Stage</dt>
              <dd>{titleCase(state.gate.stage)}</dd>
            </div>
            <div className="key-value">
              <dt>Run</dt>
              <dd>{state.active_run_id ?? "Not planned"}</dd>
            </div>
            <div className="key-value">
              <dt>Blocked</dt>
              <dd>{state.gate.blocked_actions.join(", ") || "None"}</dd>
            </div>
          </dl>
        </section>
        <ProjectOpen />
        <section className="inspector-section">
          <h3>Selected Artifact</h3>
          {selectedArtifact ? (
            <dl>
              <div className="key-value">
                <dt>Kind</dt>
                <dd>{selectedArtifact.kind}</dd>
              </div>
              <div className="key-value">
                <dt>Path</dt>
                <dd>{shortPath(selectedArtifact.relative_path)}</dd>
              </div>
              <div className="key-value">
                <dt>Size</dt>
                <dd>{formatBytes(selectedArtifact.bytes)}</dd>
              </div>
            </dl>
          ) : (
            <p>No artifact selected.</p>
          )}
        </section>
        <StageInspector stage={selectedStage} state={state} notes={notes} setNotes={setNotes} onApproveDemo={onApproveDemo} />
        <section className="inspector-section">
          <h3>Install Policy</h3>
          <div className="row-list">
            <div className="data-row">
              <span>
                <CheckCircle2 size={14} /> Validation
              </span>
              <StatusBadge severity={state.validation.ok ? "success" : "danger"}>{state.validation.ok ? "Clean" : "Issues"}</StatusBadge>
            </div>
            <div className="data-row">
              <span>
                <ShieldAlert size={14} /> Policy
              </span>
              <StatusBadge severity={state.gate.install_ready ? "success" : "warning"}>{state.gate.install_ready ? "Ready" : "Needs approval"}</StatusBadge>
            </div>
            <div className="data-row">
              <span>
                <ClipboardCheck size={14} /> Warnings
              </span>
              <strong>{Array.isArray(policy?.warnings) ? policy?.warnings.length : 0}</strong>
            </div>
          </div>
        </section>
        <section className="inspector-section">
          <h3>Quick Actions</h3>
          <div className="toolbar-group">
            <Button variant="default">
              <GitBranch size={14} />
              Branch
            </Button>
            <Button variant="default">
              <Download size={14} />
              Export
            </Button>
          </div>
        </section>
      </div>
    </aside>
  );
}

function StageInspector({
  stage,
  state,
  notes,
  setNotes,
  onApproveDemo
}: {
  stage: ReviewStage;
  state: ProjectState;
  notes: string;
  setNotes: (notes: string) => void;
  onApproveDemo: (notes: string) => void;
}) {
  if (stage === "sources") return <SourceReview state={state} />;
  if (stage === "baselines") return <BaselineReview state={state} />;
  if (stage === "style") return <StyleStudio state={state} />;
  if (stage === "generation") return <GenerationReview state={state} />;
  if (stage === "qa") return <QaReview state={state} notes={notes} setNotes={setNotes} onApprove={onApproveDemo} />;
  if (stage === "approval") return <ApprovalExport state={state} notes={notes} setNotes={setNotes} onApprove={onApproveDemo} />;
  return <DemoMode state={state} />;
}
