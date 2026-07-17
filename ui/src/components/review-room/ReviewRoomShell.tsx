import { useEffect, useState } from "react";

import { selectedArtifact, useProjectStore } from "../../state/project-store";
import { ActivityDrawer } from "./ActivityDrawer";
import { CommandPalette } from "./CommandPalette";
import { DetailsDrawer } from "./DetailsDrawer";
import { GateBar } from "./GateBar";
import { Onboarding } from "./Onboarding";
import { PreviewModal } from "./PreviewModal";
import { ReviewDecisionSurface } from "./ReviewDecisionSurface";
import { WalkthroughGuide } from "./WalkthroughGuide";

export function ReviewRoomShell() {
  const store = useProjectStore();
  const loadLaunchProject = useProjectStore((state) => state.loadLaunchProject);
  const [walkthroughOpen, setWalkthroughOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const currentArtifact = selectedArtifact(store.state, store.selectedArtifactId);

  useEffect(() => {
    void loadLaunchProject();
  }, [loadLaunchProject]);

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
      if (key === "2") store.setStage("identity");
      if (key === "3") store.setStage("baselines");
      if (key === "4") store.setStage("style");
      if (key === "5") store.setStage("generation");
      if (key === "6") store.setStage("qa");
      if (key === "q") store.setStage("qa");
      if (key === "s") store.setStage("style");
      if (key === "b") store.setStage("baselines");
      if (key === "g") store.setStage("generation");
      if (key === "r") void store.refresh();
      if (key === "i") store.toggleDetails();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [store]);

  if (store.onboardingOpen) {
    return <Onboarding />;
  }

  return (
    <div className="review-room">
      <GateBar
        state={store.state}
        selectedStage={store.selectedStage}
        detailsOpen={store.detailsOpen}
        onOpenOnboarding={store.openOnboarding}
        onStageChange={store.setStage}
        onToggleDetails={store.toggleDetails}
        onToggleActivity={store.toggleActivity}
        onToggleCommand={store.toggleCommand}
        onToggleWalkthrough={() => setWalkthroughOpen((current) => !current)}
        onRefresh={store.refresh}
      />
      <ReviewDecisionSurface
        key={store.selectedStage}
        state={store.state}
        selectedStage={store.selectedStage}
        selectedArtifact={currentArtifact}
        onStageChange={store.setStage}
        onOpenDetails={store.toggleDetails}
        onOpenPreview={() => setPreviewOpen(true)}
        onApprove={(notes) => void store.approve(notes)}
      />
      <DetailsDrawer
        open={store.detailsOpen}
        state={store.state}
        selectedStage={store.selectedStage}
        selectedArtifact={currentArtifact}
        onClose={store.toggleDetails}
      />
      <WalkthroughGuide
        open={walkthroughOpen}
        selectedStage={store.selectedStage}
        onStageChange={store.setStage}
        onClose={() => setWalkthroughOpen(false)}
        onOpenOnboarding={store.openOnboarding}
      />
      <ActivityDrawer open={store.activityOpen} activities={store.activities} />
      <PreviewModal
        open={previewOpen}
        state={store.state}
        selectedStage={store.selectedStage}
        selectedArtifact={currentArtifact}
        compareMode={store.compareMode}
        zoom={store.zoom}
        playbackSpeed={store.playbackSpeed}
        onClose={() => {
          if (store.compareMode) store.toggleCompare();
          setPreviewOpen(false);
        }}
        onToggleCompare={store.toggleCompare}
        onZoomChange={store.setZoom}
        onPlaybackSpeedChange={store.setPlaybackSpeed}
      />
      <CommandPalette
        open={store.commandOpen}
        onClose={store.toggleCommand}
        onStageChange={store.setStage}
        onRefresh={store.refresh}
        onApprove={() => void store.approve("Approved through command palette after reviewing identity, direction, and QA artifacts.")}
      />
    </div>
  );
}
