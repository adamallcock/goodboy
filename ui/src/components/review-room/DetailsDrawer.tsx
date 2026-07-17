import { CheckCircle2, ClipboardCheck, FileText, ShieldAlert, X } from "lucide-react";

import { artifactsForStage } from "../../lib/artifacts";
import { formatBytes, shortPath, titleCase } from "../../lib/format";
import type { ArtifactRef, ProjectState, ReviewStage } from "../../lib/types";
import { currentDecisionFor } from "../../lib/workflow";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

interface DetailsDrawerProps {
  open: boolean;
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  onClose: () => void;
}

export function DetailsDrawer({ open, state, selectedStage, selectedArtifact, onClose }: DetailsDrawerProps) {
  if (!open) return null;

  const decision = currentDecisionFor(state, selectedStage);
  const policy = state.qa?.install_policy as Record<string, unknown> | undefined;
  const stageArtifacts = artifactsForStage(state.artifacts, selectedStage);
  const warnings = Array.isArray(policy?.warnings) ? policy.warnings.length : 0;

  return (
    <>
      <button type="button" className="details-scrim" aria-label="Dismiss backdrop" onClick={onClose} />
      <aside className="details-drawer" aria-label="Details drawer">
        <div className="details-header">
          <div>
            <span className="section-kicker">Advanced details</span>
            <h2>{titleCase(selectedStage)}</h2>
          </div>
          <Button variant="ghost" aria-label="Close details" onClick={onClose}>
            <X size={15} />
          </Button>
        </div>

        <section className="details-section">
          <h3>Decision</h3>
          <StatusBadge severity={decision.severity}>{decision.title}</StatusBadge>
          <p>{decision.detail}</p>
        </section>

        <section className="details-section" aria-label="Generated files">
          <h3>Generated files</h3>
          <div className="row-list">
            {(stageArtifacts.length ? stageArtifacts : state.artifacts).map((artifact) => (
              <div className="data-row details-file-row" key={artifact.id}>
                <span>
                  <FileText size={14} />
                  {artifact.label}
                  <em>{shortPath(artifact.relative_path)}</em>
                </span>
                <StatusBadge severity={artifact.severity}>{artifact.kind}</StatusBadge>
              </div>
            ))}
          </div>
        </section>

        <section className="details-section">
          <h3>Selected artifact</h3>
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

        <section className="details-section">
          <h3>Install policy</h3>
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
              <strong>{warnings}</strong>
            </div>
          </div>
        </section>

        <section className="details-section">
          <h3>Provenance and command</h3>
          <dl>
            <div className="key-value">
              <dt>Run</dt>
              <dd>{state.active_run_id ?? "not started"}</dd>
            </div>
            <div className="key-value">
              <dt>Rows</dt>
              <dd>{String(policy?.row_provenance ?? "unknown")}</dd>
            </div>
            <div className="key-value">
              <dt>Next command</dt>
              <dd>{state.gate.recommended_command ?? "No command required"}</dd>
            </div>
          </dl>
        </section>

        <section className="details-section" aria-label="Durable job event history">
          <h3>Recent durable events</h3>
          <div className="row-list">
            {state.events.slice(-8).reverse().map((event, index) => (
              <div className="data-row details-file-row" key={String(event.id ?? index)}>
                <span>
                  {String(event.event ?? "event")}
                  <em>{String(event.job_id ?? state.active_run_id ?? "project")}</em>
                </span>
                <StatusBadge severity={event.to_status === "failed" || event.to_status === "qa_failed" ? "danger" : "info"}>
                  {String(event.to_status ?? event.from_status ?? "recorded")}
                </StatusBadge>
              </div>
            ))}
            {!state.events.length ? <p>No durable run events yet.</p> : null}
          </div>
        </section>
      </aside>
    </>
  );
}
