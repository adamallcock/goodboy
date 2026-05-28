import { CSSProperties, useMemo, useState } from "react";

import {
  CODEX_PET_COLUMNS,
  CODEX_PET_FRAME_HEIGHT,
  CODEX_PET_FRAME_WIDTH,
  CODEX_PET_ROWS,
  defaultSpriteStates,
  SpriteStateSpec
} from "../../lib/sprite";
import type { Severity } from "../../lib/types";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

export interface QaSummaryChip {
  label: string;
  value: string;
  severity: Severity;
}

interface SpriteStateViewerProps {
  spritesheetUrl: string;
  states?: SpriteStateSpec[];
  imageRendering?: "auto" | "pixelated";
  frameWidth?: number;
  frameHeight?: number;
  columns?: number;
  rows?: number;
  qaSummary?: QaSummaryChip[];
  onOpenPreview?: () => void;
}

export function SpriteStateViewer({
  spritesheetUrl,
  states = defaultSpriteStates,
  imageRendering = "auto",
  frameWidth = CODEX_PET_FRAME_WIDTH,
  frameHeight = CODEX_PET_FRAME_HEIGHT,
  columns = CODEX_PET_COLUMNS,
  rows = CODEX_PET_ROWS,
  qaSummary = [],
  onOpenPreview
}: SpriteStateViewerProps) {
  const [selectedStateId, setSelectedStateId] = useState(states[0]?.id ?? "idle");
  const selected = useMemo(() => states.find((state) => state.id === selectedStateId) ?? states[0], [selectedStateId, states]);

  if (!selected) {
    return (
      <section className="sprite-state-viewer empty" data-testid="sprite-state-viewer">
        <strong>No sprite states available</strong>
      </section>
    );
  }

  return (
    <section className="sprite-state-viewer" data-testid="sprite-state-viewer" aria-label="Animated state viewer">
      <div className="sprite-state-stage-card">
        <div className="sprite-state-heading">
          <div>
            <span className="section-kicker">State Viewer</span>
            <h3>{selected.label}</h3>
          </div>
          <StatusBadge severity="info">{`${selected.frameCount} frames`}</StatusBadge>
        </div>
        <div className="sprite-checkerboard" aria-label={`${selected.label} animated preview`}>
          <SpriteCell
            spritesheetUrl={spritesheetUrl}
            state={selected}
            frameWidth={frameWidth}
            frameHeight={frameHeight}
            columns={columns}
            rows={rows}
            imageRendering={imageRendering}
            scale={1.55}
            animated
          />
        </div>
        <div className="sprite-state-footer">
          <p>{selected.description}</p>
          {onOpenPreview ? (
            <Button variant="default" onClick={onOpenPreview}>
              Open large preview
            </Button>
          ) : null}
        </div>
        {qaSummary.length ? (
          <div className="qa-chip-row" aria-label="QA summary">
            {qaSummary.map((chip) => (
              <StatusBadge key={chip.label} severity={chip.severity}>{`${chip.label}: ${chip.value}`}</StatusBadge>
            ))}
          </div>
        ) : null}
      </div>
      <div className="sprite-state-grid" aria-label="Sprite states">
        {states.map((state) => (
          <button
            type="button"
            key={state.id}
            className={`sprite-state-card ${state.id === selected.id ? "active" : ""}`}
            aria-label={`${state.label} Row ${state.row}, ${state.frameCount} frames`}
            onClick={() => setSelectedStateId(state.id)}
          >
            <span>
              <strong>{state.label}</strong>
              <em>
                Row {state.row} - {state.frameCount} frames
              </em>
            </span>
            <SpriteCell
              spritesheetUrl={spritesheetUrl}
              state={state}
              frameWidth={frameWidth}
              frameHeight={frameHeight}
              columns={columns}
              rows={rows}
              imageRendering={imageRendering}
              scale={0.34}
            />
          </button>
        ))}
      </div>
    </section>
  );
}

function SpriteCell({
  spritesheetUrl,
  state,
  frameWidth,
  frameHeight,
  columns,
  rows,
  imageRendering,
  scale,
  animated = false
}: {
  spritesheetUrl: string;
  state: SpriteStateSpec;
  frameWidth: number;
  frameHeight: number;
  columns: number;
  rows: number;
  imageRendering: "auto" | "pixelated";
  scale: number;
  animated?: boolean;
}) {
  const cssVars = {
    "--sprite-url": `url("${spritesheetUrl}")`,
    "--sprite-frame-width": `${frameWidth}px`,
    "--sprite-frame-height": `${frameHeight}px`,
    "--sprite-scale": scale,
    "--sprite-row-y": `${state.row * -frameHeight}px`,
    "--sprite-end-x": `${state.frameCount * -frameWidth}px`,
    "--sprite-duration": `${state.durationMs}ms`,
    "--sprite-steps": state.frameCount,
    "--sprite-sheet-width": `${frameWidth * columns}px`,
    "--sprite-sheet-height": `${frameHeight * rows}px`,
    imageRendering
  } as CSSProperties;

  return (
    <span className="sprite-state-frame" style={cssVars} aria-hidden="true">
      <span
        className={`sprite-state-sprite ${animated ? "animated" : ""}`}
        data-testid={animated ? "sprite-state-animation" : undefined}
        data-state={animated ? state.id : undefined}
        data-row={animated ? state.row : undefined}
        data-frame-count={animated ? state.frameCount : undefined}
      />
    </span>
  );
}
