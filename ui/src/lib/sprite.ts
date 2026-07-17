import type { ArtifactRef, ProjectState } from "./types";

export interface SpriteStateSpec {
  id: string;
  label: string;
  row: number;
  frameCount: number;
  durationMs: number;
  frameDurationsMs?: number[];
  description: string;
}

export const CODEX_PET_FRAME_WIDTH = 192;
export const CODEX_PET_FRAME_HEIGHT = 208;
export const CODEX_PET_COLUMNS = 8;
export const CODEX_PET_ROWS = 11;

export const defaultSpriteStates: SpriteStateSpec[] = [
  { id: "idle", label: "Idle", row: 0, frameCount: 6, durationMs: 1100, frameDurationsMs: [280, 110, 110, 140, 140, 320], description: "Neutral breathing and blinking loop." },
  { id: "running-right", label: "Run Right", row: 1, frameCount: 8, durationMs: 1060, frameDurationsMs: [120, 120, 120, 120, 120, 120, 120, 220], description: "Directional movement toward the right." },
  { id: "running-left", label: "Run Left", row: 2, frameCount: 8, durationMs: 1060, frameDurationsMs: [120, 120, 120, 120, 120, 120, 120, 220], description: "Directional movement toward the left." },
  { id: "waving", label: "Waving", row: 3, frameCount: 4, durationMs: 700, frameDurationsMs: [140, 140, 140, 280], description: "Friendly greeting animation." },
  { id: "jumping", label: "Jumping", row: 4, frameCount: 5, durationMs: 840, frameDurationsMs: [140, 140, 140, 140, 280], description: "Compact playful hop." },
  { id: "failed", label: "Failed", row: 5, frameCount: 8, durationMs: 1220, frameDurationsMs: [140, 140, 140, 140, 140, 140, 140, 240], description: "Gentle disappointment and recovery." },
  { id: "waiting", label: "Waiting", row: 6, frameCount: 6, durationMs: 1010, frameDurationsMs: [150, 150, 150, 150, 150, 260], description: "Expectant pause while waiting for input." },
  { id: "running", label: "Running", row: 7, frameCount: 6, durationMs: 820, frameDurationsMs: [120, 120, 120, 120, 120, 220], description: "Focused active-work loop." },
  { id: "review", label: "Review", row: 8, frameCount: 6, durationMs: 1030, frameDurationsMs: [150, 150, 150, 150, 150, 280], description: "Focused inspection and review loop." },
  { id: "look-000-to-157.5", label: "Look 0–157.5°", row: 9, frameCount: 8, durationMs: 800, frameDurationsMs: [100, 100, 100, 100, 100, 100, 100, 100], description: "First half of the clockwise v2 direction ring." },
  { id: "look-180-to-337.5", label: "Look 180–337.5°", row: 10, frameCount: 8, durationMs: 800, frameDurationsMs: [100, 100, 100, 100, 100, 100, 100, 100], description: "Second half of the clockwise v2 direction ring." }
];

export function spriteRowsForProject(state: ProjectState): number {
  const output = state.manifest.output_contract as Record<string, unknown> | undefined;
  return Number(output?.rows ?? (state.manifest.sprite_version_number === 1 ? 9 : 11));
}

export function spriteStatesForProject(state: ProjectState): SpriteStateSpec[] {
  return defaultSpriteStates
    .filter((item) => item.row < spriteRowsForProject(state))
    .map((item) => {
      const timing = state.animation_contract?.[item.id] as Record<string, unknown> | undefined;
      const rawDurations = Array.isArray(timing?.frame_durations_ms)
        ? timing.frame_durations_ms.map(Number)
        : item.frameDurationsMs;
      const frameDurationsMs = rawDurations?.every((duration) => Number.isFinite(duration) && duration > 0)
        ? rawDurations
        : item.frameDurationsMs;
      return {
        ...item,
        frameCount: Number(timing?.frame_count ?? item.frameCount),
        frameDurationsMs,
        durationMs: Number(
          timing?.loop_duration_ms ??
          frameDurationsMs?.reduce((total, duration) => total + duration, 0) ??
          item.durationMs
        )
      };
    });
}

export function findSpritesheetArtifact(state: ProjectState): ArtifactRef | null {
  const activeRunPrefix = state.active_run_id ? `runs/${state.active_run_id}/` : null;
  if (activeRunPrefix) {
    const activeRunSpritesheet =
      state.artifacts.find(
        (artifact) =>
          artifact.relative_path.startsWith(activeRunPrefix) &&
          artifact.kind === "package" &&
          artifact.relative_path.endsWith("spritesheet.webp")
      ) ??
      state.artifacts.find(
        (artifact) =>
          artifact.relative_path.startsWith(activeRunPrefix) &&
          artifact.relative_path.endsWith("spritesheet.webp")
      );
    if (activeRunSpritesheet) {
      return activeRunSpritesheet;
    }
  }
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
