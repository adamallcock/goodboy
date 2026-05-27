import { useEffect } from "react";

import { selectedArtifact, useProjectStore } from "../../state/project-store";
import { ActivityDrawer } from "./ActivityDrawer";
import { ArtifactCanvas } from "./ArtifactCanvas";
import { CommandPalette } from "./CommandPalette";
import { GateBar } from "./GateBar";
import { InspectorPanel } from "./InspectorPanel";
import { Onboarding } from "./Onboarding";

export function ReviewRoomShell() {
  const store = useProjectStore();
  const currentArtifact = selectedArtifact(store.state, store.selectedArtifactId);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey) {
        if (event.key.toLowerCase() === "k") {
          event.preventDefault();
          store.toggleCommand();
        }
        return;
      }
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      const key = event.key.toLowerCase();
      if (key === "1") store.setStage("sources");
      if (key === "2") store.setStage("baselines");
      if (key === "3") store.setStage("style");
      if (key === "4") store.setStage("generation");
      if (key === "5") store.setStage("qa");
      if (key === "q") store.setStage("qa");
      if (key === "s") store.setStage("style");
      if (key === "b") store.setStage("baselines");
      if (key === "g") store.setStage("generation");
      if (key === "r") void store.refresh();
      if (key === "i") store.toggleInspector();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [store]);

  if (store.onboardingOpen) {
    return <Onboarding />;
  }

  return (
    <div className={`review-room ${store.inspectorOpen ? "" : "inspector-closed"}`}>
      <GateBar
        state={store.state}
        selectedStage={store.selectedStage}
        inspectorOpen={store.inspectorOpen}
        onOpenOnboarding={store.openOnboarding}
        onStageChange={store.setStage}
        onToggleInspector={store.toggleInspector}
        onToggleActivity={store.toggleActivity}
        onToggleCommand={store.toggleCommand}
        onRefresh={store.refresh}
      />
      <ArtifactCanvas
        key={store.selectedStage}
        state={store.state}
        selectedStage={store.selectedStage}
        selectedArtifact={currentArtifact}
        selectedArtifactId={store.selectedArtifactId}
        compareMode={store.compareMode}
        zoom={store.zoom}
        playbackSpeed={store.playbackSpeed}
        onSelectArtifact={store.selectArtifact}
        onToggleCompare={store.toggleCompare}
        onZoomChange={store.setZoom}
        onPlaybackSpeedChange={store.setPlaybackSpeed}
      />
      <InspectorPanel
        key={`inspector-${store.selectedStage}`}
        open={store.inspectorOpen}
        state={store.state}
        selectedStage={store.selectedStage}
        selectedArtifact={currentArtifact}
        onStageChange={store.setStage}
        onOpenOnboarding={store.openOnboarding}
        onApproveDemo={store.approveDemo}
      />
      <ActivityDrawer open={store.activityOpen} activities={store.activities} />
      <CommandPalette
        open={store.commandOpen}
        onClose={store.toggleCommand}
        onStageChange={store.setStage}
        onRefresh={store.refresh}
        onApprove={() => store.approveDemo("Approved through command palette after reviewing QA artifacts.")}
      />
    </div>
  );
}
