import { Command } from "cmdk";
import { CheckCircle2, Download, Eye, GitBranch, Palette, RefreshCcw } from "lucide-react";
import { useEffect } from "react";

import type { ReviewStage } from "../../lib/types";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onStageChange: (stage: ReviewStage) => void;
  onRefresh: () => void;
  onApprove: () => void;
}

export function CommandPalette({ open, onClose, onStageChange, onRefresh, onApprove }: CommandPaletteProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, open]);

  if (!open) return null;
  const run = (action: () => void) => {
    action();
    onClose();
  };
  return (
    <div className="command-backdrop" onClick={onClose}>
      <Command className="command-panel" onClick={(event) => event.stopPropagation()}>
        <Command.Input className="command-input" autoFocus placeholder="Search Goodboy actions..." />
        <Command.List className="command-list">
          <Command.Empty>No action found.</Command.Empty>
          <Command.Item className="command-item" onSelect={() => run(() => onStageChange("qa"))}>
            <span>
              <Eye size={14} /> Open QA Review
            </span>
            <kbd>Q</kbd>
          </Command.Item>
          <Command.Item className="command-item" onSelect={() => run(() => onStageChange("style"))}>
            <span>
              <Palette size={14} /> Open Style Studio
            </span>
            <kbd>S</kbd>
          </Command.Item>
          <Command.Item className="command-item" onSelect={() => run(onRefresh)}>
            <span>
              <RefreshCcw size={14} /> Refresh Artifacts
            </span>
            <kbd>R</kbd>
          </Command.Item>
          <Command.Item className="command-item" onSelect={() => run(onApprove)}>
            <span>
              <CheckCircle2 size={14} /> Approve Review
            </span>
            <kbd>A</kbd>
          </Command.Item>
          <Command.Item className="command-item" onSelect={() => run(() => onStageChange("approval"))}>
            <span>
              <Download size={14} /> Open Export
            </span>
            <kbd>E</kbd>
          </Command.Item>
          <Command.Item className="command-item" onSelect={() => run(() => onStageChange("demo"))}>
            <span>
              <GitBranch size={14} /> Show Demo Story
            </span>
            <kbd>D</kbd>
          </Command.Item>
        </Command.List>
      </Command>
    </div>
  );
}
