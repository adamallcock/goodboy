import type { ArtifactRef, ProjectState } from "./types";

export interface SpriteStateSpec {
  id: string;
  label: string;
  row: number;
  frameCount: number;
  durationMs: number;
  description: string;
}

export const CODEX_PET_FRAME_WIDTH = 192;
export const CODEX_PET_FRAME_HEIGHT = 208;
export const CODEX_PET_COLUMNS = 8;
export const CODEX_PET_ROWS = 9;

export const defaultSpriteStates: SpriteStateSpec[] = [
  { id: "idle", label: "Idle", row: 0, frameCount: 6, durationMs: 1100, description: "Neutral breathing and blinking loop." },
  { id: "running-right", label: "Run Right", row: 1, frameCount: 8, durationMs: 1060, description: "Directional movement toward the right." },
  { id: "running-left", label: "Run Left", row: 2, frameCount: 8, durationMs: 1060, description: "Directional movement toward the left." },
  { id: "waving", label: "Waving", row: 3, frameCount: 4, durationMs: 1000, description: "Friendly greeting animation." },
  { id: "jumping", label: "Jumping", row: 4, frameCount: 5, durationMs: 980, description: "Compact playful hop." },
  { id: "failed", label: "Failed", row: 5, frameCount: 8, durationMs: 1160, description: "Gentle disappointment and recovery." },
  { id: "waiting", label: "Waiting", row: 6, frameCount: 6, durationMs: 1100, description: "Expectant pause while waiting for input." },
  { id: "running", label: "Running", row: 7, frameCount: 6, durationMs: 1100, description: "Focused active-work loop." },
  { id: "review", label: "Review", row: 8, frameCount: 6, durationMs: 1100, description: "Focused inspection and review loop." }
];

export function findSpritesheetArtifact(state: ProjectState): ArtifactRef | null {
  return (
    state.artifacts.find((artifact) => artifact.kind === "package" && artifact.relative_path.endsWith("spritesheet.webp")) ??
    state.artifacts.find((artifact) => artifact.relative_path.endsWith("spritesheet.webp")) ??
    null
  );
}

export function spriteImageRendering(state: ProjectState): "auto" | "pixelated" {
  const stylePreset = String(state.style_sheet?.style_preset ?? state.manifest.style_preset ?? "").toLowerCase();
  const material = String(state.character_card?.material ?? "").toLowerCase();
  return stylePreset.includes("pixel") || material.includes("pixel") ? "pixelated" : "auto";
}
