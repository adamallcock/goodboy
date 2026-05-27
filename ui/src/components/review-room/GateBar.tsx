import { Activity, Command, Eye, PanelRightClose, PanelRightOpen, RefreshCcw } from "lucide-react";

import { titleCase } from "../../lib/format";
import type { ProjectState } from "../../lib/types";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

interface GateBarProps {
  state: ProjectState;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
  onToggleActivity: () => void;
  onToggleCommand: () => void;
  onRefresh: () => void;
}

export function GateBar({ state, inspectorOpen, onToggleInspector, onToggleActivity, onToggleCommand, onRefresh }: GateBarProps) {
  const displayName = String(state.manifest.display_name ?? state.manifest.id ?? "Goodboy");
  const gateSeverity = state.gate.install_ready ? "success" : state.gate.stage.includes("review") ? "warning" : "info";
  return (
    <header className="gate-bar">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true">
          <Eye size={18} />
        </div>
        <div>
          <h1 className="brand-title">{displayName}</h1>
          <p className="brand-subtitle">Review Room</p>
        </div>
      </div>
      <div className="gate-summary">
        <StatusBadge severity={gateSeverity}>{titleCase(state.gate.stage)}</StatusBadge>
        <span className="gate-text">{titleCase(state.gate.next_action)}</span>
      </div>
      <div className="gate-actions">
        <Button variant="ghost" aria-label="Refresh project state" onClick={onRefresh}>
          <RefreshCcw size={15} />
        </Button>
        <Button variant="ghost" aria-label="Open command palette" onClick={onToggleCommand}>
          <Command size={15} />
          Commands
        </Button>
        <Button variant="ghost" aria-label="Toggle activity drawer" onClick={onToggleActivity}>
          <Activity size={15} />
        </Button>
        <Button variant="ghost" aria-label="Toggle inspector" onClick={onToggleInspector}>
          {inspectorOpen ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}
        </Button>
      </div>
    </header>
  );
}
