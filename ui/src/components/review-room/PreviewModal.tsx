import { Columns2, Maximize2, Minus, Play, Plus, X } from "lucide-react";

import { artifactIsImage } from "../../lib/artifacts";
import { findSpritesheetArtifact, spriteImageRendering } from "../../lib/sprite";
import type { ArtifactRef, ProjectState, ReviewStage } from "../../lib/types";
import { Button } from "../ui/button";
import { SpriteStateViewer } from "./SpriteStateViewer";

interface PreviewModalProps {
  open: boolean;
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  compareMode: boolean;
  zoom: number;
  playbackSpeed: number;
  onClose: () => void;
  onToggleCompare: () => void;
  onZoomChange: (zoom: number) => void;
  onPlaybackSpeedChange: (speed: number) => void;
}

export function PreviewModal({
  open,
  state,
  selectedStage,
  selectedArtifact,
  compareMode,
  zoom,
  playbackSpeed,
  onClose,
  onToggleCompare,
  onZoomChange,
  onPlaybackSpeedChange
}: PreviewModalProps) {
  if (!open) return null;

  const spritesheet = findSpritesheetArtifact(state);
  const previewArtifact = selectedStage === "qa" || selectedStage === "approval" ? spritesheet ?? selectedArtifact : selectedArtifact;

  return (
    <div className="preview-backdrop">
      <section className="preview-modal" role="dialog" aria-modal="true" aria-label="Large artifact preview">
        <div className="preview-toolbar">
          <div>
            <h2>Large preview</h2>
            <p>{previewArtifact?.relative_path ?? "No artifact selected"}</p>
          </div>
          <div className="toolbar-group" aria-label="Preview controls">
            <Button variant="ghost" aria-label="Zoom out" onClick={() => onZoomChange(Math.max(0.6, zoom - 0.1))}>
              <Minus size={14} />
            </Button>
            <label className="zoom-control">
              Zoom
              <input
                aria-label="Zoom level"
                type="range"
                min="0.6"
                max="1.5"
                step="0.05"
                value={zoom}
                onChange={(event) => onZoomChange(Number(event.target.value))}
              />
              {Math.round(zoom * 100)}%
            </label>
            <Button variant="ghost" aria-label="Zoom in" onClick={() => onZoomChange(Math.min(1.5, zoom + 0.1))}>
              <Plus size={14} />
            </Button>
            <Button variant={compareMode ? "primary" : "default"} aria-label="Toggle compare mode" onClick={onToggleCompare}>
              <Columns2 size={14} />
              Compare
            </Button>
            <Button variant="ghost" aria-label="Toggle playback speed" onClick={() => onPlaybackSpeedChange(playbackSpeed >= 2 ? 0.5 : playbackSpeed + 0.5)}>
              <Play size={14} />
              {playbackSpeed.toFixed(1)}x
            </Button>
            <Button variant="ghost" aria-label="Fit artifact" onClick={() => onZoomChange(1)}>
              <Maximize2 size={14} />
            </Button>
            <Button variant="ghost" aria-label="Close preview" onClick={onClose}>
              <X size={15} />
            </Button>
          </div>
        </div>
        <div className="preview-body">
          <div className="preview-artifact" style={{ transform: `scale(${zoom})` }}>
            {compareMode ? (
              <div className="preview-compare-grid">
                <PreviewPane title="Current artifact" artifact={previewArtifact} state={state} selectedStage={selectedStage} />
                <div className="preview-pane reference">
                  <strong>Reference overlay</strong>
                  <p>Centering, edge cleanup, and source comparison.</p>
                </div>
              </div>
            ) : (
              <PreviewPane title="Current artifact" artifact={previewArtifact} state={state} selectedStage={selectedStage} />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function PreviewPane({
  title,
  artifact,
  state,
  selectedStage
}: {
  title: string;
  artifact: ArtifactRef | null;
  state: ProjectState;
  selectedStage: ReviewStage;
}) {
  if (!artifact) {
    return (
      <div className="preview-pane">
        <strong>{title}</strong>
        <p>No preview artifact is available yet.</p>
      </div>
    );
  }

  if ((selectedStage === "qa" || selectedStage === "approval") && artifact.relative_path.endsWith("spritesheet.webp")) {
    return (
      <div className="preview-pane sprite">
        <SpriteStateViewer spritesheetUrl={artifact.url} imageRendering={spriteImageRendering(state)} />
      </div>
    );
  }

  if (artifactIsImage(artifact)) {
    return (
      <div className="preview-pane image">
        <strong>{title}</strong>
        <img src={artifact.url} alt={artifact.label} />
      </div>
    );
  }

  return (
    <div className="preview-pane">
      <strong>{title}</strong>
      <p>{artifact.label}</p>
    </div>
  );
}
