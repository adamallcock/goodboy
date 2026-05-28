import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";

import type { ProjectState } from "../../lib/types";
import { StatusBadge } from "../../components/ui/status-badge";

interface JobRow {
  state: string;
  frames: string;
  provider: string;
  status: string;
}

export function GenerationReview({ state }: { state: ProjectState }) {
  const rows: JobRow[] = ["idle", "running", "review", "waiting"].map((item) => ({
    state: item,
    frames: item === "running" ? "6" : "8",
    provider: "codex_builtin",
    status: state.active_run_id ? "planned" : "waiting"
  }));
  const helper = createColumnHelper<JobRow>();
  const table = useReactTable({
    data: rows,
    columns: [
      helper.accessor("state", { header: "State" }),
      helper.accessor("frames", { header: "Frames" }),
      helper.accessor("provider", { header: "Provider" }),
      helper.accessor("status", { header: "Status" })
    ],
    getCoreRowModel: getCoreRowModel()
  });
  return (
    <section className="inspector-section">
      <h3>Generation</h3>
      <div className="row-list" role="table" aria-label="Generation jobs">
        {table.getRowModel().rows.map((row) => (
          <div className="data-row" role="row" key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <span key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</span>
            ))}
          </div>
        ))}
      </div>
      <div className="data-row">
        <span>API accelerators</span>
        <StatusBadge severity="info">Optional</StatusBadge>
      </div>
    </section>
  );
}
