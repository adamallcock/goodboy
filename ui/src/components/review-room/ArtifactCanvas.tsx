import { Columns2, Maximize2, Minus, Play, Plus } from "lucide-react";
import { CSSProperties, useEffect, useState } from "react";
import { ReactCompareSlider } from "react-compare-slider";

import { artifactIsImage, artifactsForStage } from "../../lib/artifacts";
import { shortPath, titleCase } from "../../lib/format";
import type { ArtifactRef, ProjectState, ReviewStage } from "../../lib/types";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";

interface ArtifactCanvasProps {
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  selectedArtifactId: string | null;
  compareMode: boolean;
  zoom: number;
  playbackSpeed: number;
  onSelectArtifact: (artifactId: string) => void;
  onToggleCompare: () => void;
  onZoomChange: (zoom: number) => void;
  onPlaybackSpeedChange: (speed: number) => void;
}

export function ArtifactCanvas({
  state,
  selectedStage,
  selectedArtifact,
  selectedArtifactId,
  compareMode,
  zoom,
  playbackSpeed,
  onSelectArtifact,
  onToggleCompare,
  onZoomChange,
  onPlaybackSpeedChange
}: ArtifactCanvasProps) {
  const stageArtifacts = artifactsForStage(state.artifacts, selectedStage);
  const stageTitle = titleCase(selectedStage);
  return (
    <main className="canvas-shell">
      <div className="canvas-toolbar">
        <div className="canvas-title">
          <h2>{stageTitle}</h2>
          <p>{selectedArtifact ? shortPath(selectedArtifact.relative_path) : "No artifact selected"}</p>
        </div>
        <div className="toolbar-group" aria-label="Artifact controls">
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
        </div>
      </div>
      <section className="artifact-canvas" aria-label="Visual artifact canvas">
        <div className={`artifact-preview ${compareMode ? "compare" : ""}`} style={{ transform: `scale(${zoom})` }}>
          {compareMode ? (
            <ReactCompareSlider
              className="compare-slider"
              boundsPadding={10}
              changePositionOnHover
              itemOne={<SyntheticArtifactPanel title="Current artifact" artifact={selectedArtifact} tone="current" />}
              itemTwo={
                <SyntheticArtifactPanel
                  title="Reference overlay"
                  artifact={selectedArtifact}
                  tone={selectedStage === "qa" ? "qa" : "reference"}
                  subtitle={selectedStage === "qa" ? "Centering + edge preview" : "Source comparison"}
                />
              }
              keyboardIncrement="5%"
              position={52}
            />
          ) : (
            <ArtifactPreviewContent artifact={selectedArtifact} selectedStage={selectedStage} />
          )}
        </div>
        <div className="artifact-filmstrip" aria-label="Stage artifacts">
          {stageArtifacts.map((artifact) => (
            <button
              type="button"
              key={artifact.id}
              className={`artifact-thumb ${artifact.id === selectedArtifactId ? "active" : ""}`}
              onClick={() => onSelectArtifact(artifact.id)}
            >
              <StatusBadge severity={artifact.severity}>{artifact.kind}</StatusBadge>
              <span>{artifact.label}</span>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

function ArtifactPreviewContent({ artifact, selectedStage }: { artifact: ArtifactRef | null; selectedStage: ReviewStage }) {
  if (!artifact) {
    return (
      <div className="artifact-side">
        <strong>No artifact yet</strong>
        <span>{titleCase(selectedStage)} is waiting on the next Goodboy gate.</span>
      </div>
    );
  }
  return (
    <div>
      <div className="artifact-meta">
        <span>{artifact.label}</span>
        <span>{artifactIsImage(artifact) ? `${artifact.width ?? "?"} x ${artifact.height ?? "?"}` : artifact.kind}</span>
      </div>
      <ArtifactMedia artifact={artifact} />
    </div>
  );
}

function ArtifactMedia({ artifact }: { artifact: ArtifactRef }) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [artifact.id]);

  if (artifactIsImage(artifact) && artifact.exists && !artifact.url.startsWith("/demo/") && !failed) {
    return <img className="artifact-image" src={artifact.url} alt={artifact.label} onError={() => setFailed(true)} />;
  }

  return <SyntheticArtifactGrid artifact={artifact} ariaLabel={artifact.url.startsWith("/demo/") ? "Demo artifact preview" : "Synthetic artifact fallback"} />;
}

function SyntheticArtifactGrid({ artifact, ariaLabel, tone = "current" }: { artifact?: ArtifactRef | null; ariaLabel: string; tone?: "current" | "qa" | "reference" }) {
  const cellCount = artifact?.kind === "row-strip" ? 8 : 24;
  const stateClass = artifact?.state ? ` state-${artifact.state}` : "";
  return (
    <div className={`contact-grid ${tone}${artifact?.kind === "row-strip" ? " row-strip-preview" : ""}${stateClass}`} aria-label={ariaLabel}>
      {Array.from({ length: cellCount }).map((_, index) => (
        <div key={index} className={`contact-cell ${index % 7 === 0 ? "warn" : "pass"}`} style={{ "--pose": index } as CSSProperties} />
      ))}
    </div>
  );
}

function SyntheticArtifactPanel({
  title,
  artifact,
  tone,
  subtitle
}: {
  title: string;
  artifact: ArtifactRef | null;
  tone: "current" | "qa" | "reference";
  subtitle?: string;
}) {
  return (
    <div className={`compare-pane ${tone}`}>
      <div className="compare-pane-label">
        <strong>{title}</strong>
        <span>{subtitle ?? artifact?.label ?? "No artifact selected"}</span>
      </div>
      <SyntheticArtifactGrid artifact={artifact} ariaLabel={`${title} visual preview`} tone={tone} />
    </div>
  );
}
