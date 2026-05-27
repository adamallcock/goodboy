import { useEffect } from "react";

import { selectedArtifact, useProjectStore } from "../../state/project-store";
import { ActivityDrawer } from "./ActivityDrawer";
import { ArtifactCanvas } from "./ArtifactCanvas";
import { CommandPalette } from "./CommandPalette";
import { GateBar } from "./GateBar";
import { InspectorPanel } from "./InspectorPanel";
import { StageRail } from "./StageRail";

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
      if (key === "q") store.setStage("qa");
      if (key === "s") store.setStage("style");
      if (key === "b") store.setStage("baselines");
      if (key === "r") void store.refresh();
      if (key === "i") store.toggleInspector();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [store]);

  return (
    <div className={`review-room ${store.inspectorOpen ? "" : "inspector-closed"}`}>
      <GateBar
        state={store.state}
        inspectorOpen={store.inspectorOpen}
        onToggleInspector={store.toggleInspector}
        onToggleActivity={store.toggleActivity}
        onToggleCommand={store.toggleCommand}
        onRefresh={store.refresh}
      />
      <StageRail selectedStage={store.selectedStage} state={store.state} onStageChange={store.setStage} />
      <ArtifactCanvas
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
        open={store.inspectorOpen}
        state={store.state}
        selectedStage={store.selectedStage}
        selectedArtifact={currentArtifact}
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
