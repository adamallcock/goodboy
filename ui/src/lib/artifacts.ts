import type { ArtifactRef, ReviewStage } from "./types";

export function artifactsForStage(artifacts: ArtifactRef[], stage: ReviewStage): ArtifactRef[] {
  return artifacts.filter((artifact) => artifact.stage === stage);
}

export function primaryArtifactForStage(artifacts: ArtifactRef[], stage: ReviewStage): ArtifactRef | null {
  const stageArtifacts = artifactsForStage(artifacts, stage);
  if (stage === "qa") {
    return stageArtifacts.find((artifact) => artifact.relative_path.includes("contact-sheet")) ?? stageArtifacts[0] ?? null;
  }
  if (stage === "approval") {
    return stageArtifacts.find((artifact) => artifact.relative_path.includes("spritesheet")) ?? stageArtifacts[0] ?? null;
  }
  return stageArtifacts[0] ?? null;
}

export function artifactIsImage(artifact: ArtifactRef | null): boolean {
  if (!artifact) return false;
  return /\.(png|jpe?g|gif|webp)$/i.test(artifact.relative_path);
}
