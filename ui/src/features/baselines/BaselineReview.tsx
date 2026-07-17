import { Check, Image } from "lucide-react";

import type { ProjectState } from "../../lib/types";
import { StatusBadge } from "../../components/ui/status-badge";

export function BaselineReview({ state }: { state: ProjectState }) {
  return (
    <section className="inspector-section">
      <h3>Baseline Review</h3>
      <div className="row-list">
        {state.candidates.map((candidate) => (
          <div className="data-row" key={String(candidate.id)}>
            <span>
              {candidate.selected ? <Check size={14} /> : <Image size={14} />} {String(candidate.id)}
              {candidate.holistic_gestalt_score != null ? (
                <small>
                  Gestalt {String(candidate.holistic_gestalt_score)} · traits {String(candidate.signature_trait_score)} · small-size {String(candidate.small_size_readability_score)}
                </small>
              ) : null}
            </span>
            <StatusBadge severity={candidate.selected ? "success" : "info"}>{candidate.selected ? "Selected" : String(candidate.provider ?? "planned")}</StatusBadge>
          </div>
        ))}
      </div>
    </section>
  );
}
