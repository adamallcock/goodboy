import type { Severity } from "../../lib/types";

interface StatusBadgeProps {
  severity?: Severity;
  children: string;
}

export function StatusBadge({ severity = "info", children }: StatusBadgeProps) {
  return <span className={`status-badge ${severity}`}>{children}</span>;
}
