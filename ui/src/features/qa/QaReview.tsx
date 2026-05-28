import { CheckCircle2, Gauge, Target } from "lucide-react";

import type { ProjectState } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { StatusBadge } from "../../components/ui/status-badge";

export function QaReview({
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
      <h3>QA Review</h3>
      <div className="row-list">
        <div className="data-row">
          <span>
            <Target size={14} /> Centering
          </span>
          <StatusBadge severity="success">Stable</StatusBadge>
        </div>
        <div className="data-row">
          <span>
            <Gauge size={14} /> Drift
          </span>
          <StatusBadge severity="warning">Near threshold</StatusBadge>
        </div>
        <div className="data-row">
          <span>
            <CheckCircle2 size={14} /> Validation
          </span>
          <StatusBadge severity={state.validation.ok ? "success" : "danger"}>{state.validation.ok ? "Pass" : "Fail"}</StatusBadge>
        </div>
      </div>
      <div className="field">
        <label htmlFor="approval-notes">Approval notes</label>
        <textarea id="approval-notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
      </div>
      <Button variant="primary" disabled={!notes.trim()} onClick={() => onApprove(notes)}>
        Approve visual review
      </Button>
    </section>
  );
}
