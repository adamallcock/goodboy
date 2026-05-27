import { ArrowRight } from "lucide-react";

import type { ProjectState } from "../../lib/types";
import { StatusBadge } from "../../components/ui/status-badge";

const stages = ["Sources", "Baseline", "Style", "Rows", "QA", "Export"];

export function DemoMode({ state }: { state: ProjectState }) {
  return (
    <section className="inspector-section">
      <h3>Demo Story</h3>
      <div className="row-list">
        {stages.map((stage, index) => (
          <div className="data-row" key={stage}>
            <span>
              {stage}
              {index < stages.length - 1 ? <ArrowRight size={13} /> : null}
            </span>
            <StatusBadge severity={index < 5 ? "success" : "warning"}>{index < 5 ? "Done" : state.gate.install_ready ? "Ready" : "Pending"}</StatusBadge>
          </div>
        ))}
      </div>
    </section>
  );
}
