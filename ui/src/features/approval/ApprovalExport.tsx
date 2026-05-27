import { Download, ShieldCheck } from "lucide-react";

import type { ProjectState } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { StatusBadge } from "../../components/ui/status-badge";

export function ApprovalExport({
  state,
  notes,
  setNotes,
  onApprove
}: {
  state: ProjectState;
  notes: string;
  setNotes: (notes: string) => void;
  onApprove: (notes: string) => void;
}) {
  return (
    <section className="inspector-section">
      <h3>Approval And Export</h3>
      <div className="row-list">
        <div className="data-row">
          <span>
            <ShieldCheck size={14} /> Install readiness
          </span>
          <StatusBadge severity={state.gate.install_ready ? "success" : "warning"}>{state.gate.install_ready ? "Ready" : "Approval needed"}</StatusBadge>
        </div>
        <div className="data-row">
          <span>
            <Download size={14} /> Package
          </span>
          <strong>{state.exports.length || 1} artifact</strong>
        </div>
      </div>
      <div className="field">
        <label htmlFor="approval-export-notes">Approval notes</label>
        <textarea id="approval-export-notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
      </div>
      <div className="toolbar-group">
        <Button variant="primary" disabled={!notes.trim()} onClick={() => onApprove(notes)}>
          Record approval
        </Button>
        <Button disabled={!state.gate.install_ready}>Export package</Button>
      </div>
    </section>
  );
}
