import { CSSProperties, useEffect, useMemo, useState } from "react";

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
  const [directionIndex, setDirectionIndex] = useState(0);
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
        {rows >= 11 ? (
          <div className="direction-scrubber" aria-label="16-direction look scrubber">
            <div className="sprite-checkerboard compact">
              <SpriteCell
                spritesheetUrl={spritesheetUrl}
                state={{
                  id: "direction",
                  label: "Direction",
                  row: directionIndex < 8 ? 9 : 10,
                  frameCount: 1,
                  durationMs: 0,
                  description: ""
                }}
                frameIndex={directionIndex % 8}
                frameWidth={frameWidth}
                frameHeight={frameHeight}
                columns={columns}
                rows={rows}
                imageRendering={imageRendering}
                scale={0.8}
              />
            </div>
            <label>
              <span>Clockwise look: {(directionIndex * 22.5).toFixed(directionIndex % 4 === 0 ? 0 : 1)}°</span>
              <input
                type="range"
                min={0}
                max={15}
                step={1}
                value={directionIndex}
                onChange={(event) => setDirectionIndex(Number(event.target.value))}
              />
            </label>
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
  frameIndex = 0,
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
  frameIndex?: number;
  animated?: boolean;
}) {
  const [timedFrameIndex, setTimedFrameIndex] = useState(frameIndex);
  const frameDurations =
    state.frameDurationsMs?.length === state.frameCount
      ? state.frameDurationsMs
      : Array.from(
          { length: Math.max(1, state.frameCount) },
          () => Math.max(1, Math.round(state.durationMs / Math.max(1, state.frameCount)))
        );
  const frameDurationsKey = frameDurations.join(",");

  useEffect(() => {
    const initialFrame = frameIndex % Math.max(1, state.frameCount);
    setTimedFrameIndex(initialFrame);
    if (!animated || state.frameCount <= 1 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return undefined;
    }
    let currentFrame = initialFrame;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const scheduleNext = () => {
      timeout = setTimeout(() => {
        currentFrame = (currentFrame + 1) % state.frameCount;
        setTimedFrameIndex(currentFrame);
        scheduleNext();
      }, frameDurations[currentFrame]);
    };
    scheduleNext();
    return () => {
      if (timeout !== undefined) clearTimeout(timeout);
    };
  }, [animated, frameDurationsKey, frameIndex, state.frameCount, state.id]);

  const visibleFrameIndex = animated ? timedFrameIndex : frameIndex;
  const cssVars = {
    "--sprite-url": `url("${spritesheetUrl}")`,
    "--sprite-frame-width": `${frameWidth}px`,
    "--sprite-frame-height": `${frameHeight}px`,
    "--sprite-scale": scale,
    "--sprite-row-y": `${state.row * -frameHeight}px`,
    "--sprite-column-x": `${visibleFrameIndex * -frameWidth}px`,
    "--sprite-sheet-width": `${frameWidth * columns}px`,
    "--sprite-sheet-height": `${frameHeight * rows}px`,
    imageRendering
  } as CSSProperties;

  return (
    <span className="sprite-state-frame" style={cssVars} aria-hidden="true">
      <span
        className="sprite-state-sprite"
        data-testid={animated ? "sprite-state-animation" : undefined}
        data-state={animated ? state.id : undefined}
        data-row={animated ? state.row : undefined}
        data-frame-count={animated ? state.frameCount : undefined}
        data-frame-index={animated ? visibleFrameIndex : undefined}
        data-frame-durations={animated ? frameDurationsKey : undefined}
        data-loop-duration={animated ? state.durationMs : undefined}
      />
    </span>
  );
}
