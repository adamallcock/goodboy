import { create } from "zustand";
import { toast } from "sonner";

import { getProjectState, openProject, postProjectAction } from "../lib/api";
import type { ActivityItem, ArtifactRef, ProjectState, ReviewStage } from "../lib/types";
import { demoProjectState } from "../test/fixtures";

const DEMO_PROJECT_ID = "demo-review-room";

interface ProjectStore {
  state: ProjectState;
  onboardingOpen: boolean;
  selectedStage: ReviewStage;
  selectedArtifactId: string | null;
  detailsOpen: boolean;
  activityOpen: boolean;
  commandOpen: boolean;
  compareMode: boolean;
  zoom: number;
  playbackSpeed: number;
  loading: boolean;
  error: string | null;
  activities: ActivityItem[];
  setStage: (stage: ReviewStage) => void;
  selectArtifact: (artifactId: string | null) => void;
  toggleDetails: () => void;
  toggleActivity: () => void;
  toggleCommand: () => void;
  toggleCompare: () => void;
  setZoom: (zoom: number) => void;
  setPlaybackSpeed: (speed: number) => void;
  openOnboarding: () => void;
  closeOnboarding: () => void;
  startDemo: () => void;
  loadDemo: () => void;
  loadProject: (projectDir: string) => Promise<void>;
  refresh: () => Promise<void>;
  approveDemo: (notes: string) => void;
  runAction: (path: string, body: unknown, label: string) => Promise<void>;
}

function initialActivities(): ActivityItem[] {
  return [
    { id: "a1", kind: "system", label: "Companion demo loaded", detail: "Review Room is running against a read-only completed pet example.", time: "now" },
    { id: "a2", kind: "qa", label: "QA ready", detail: "Contact sheet, row strips, edge preview, and package artifacts are available.", time: "now" }
  ];
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  state: demoProjectState,
  onboardingOpen: true,
  selectedStage: "qa",
  selectedArtifactId: "runs-demo-qa-contact-sheet-png",
  detailsOpen: false,
  activityOpen: false,
  commandOpen: false,
  compareMode: false,
  zoom: 1,
  playbackSpeed: 1,
  loading: false,
  error: null,
  activities: initialActivities(),
  setStage: (stage) => {
    const artifact = get().state.artifacts.find((item) => item.stage === stage);
    set({ selectedStage: stage, selectedArtifactId: artifact?.id ?? null, compareMode: false, detailsOpen: false });
  },
  selectArtifact: (artifactId) => set({ selectedArtifactId: artifactId }),
  toggleDetails: () => set((current) => ({ detailsOpen: !current.detailsOpen })),
  toggleActivity: () => set((current) => ({ activityOpen: !current.activityOpen })),
  toggleCommand: () => set((current) => ({ commandOpen: !current.commandOpen })),
  toggleCompare: () => set((current) => ({ compareMode: !current.compareMode })),
  setZoom: (zoom) => set({ zoom }),
  setPlaybackSpeed: (playbackSpeed) => set({ playbackSpeed }),
  openOnboarding: () => set({ onboardingOpen: true }),
  closeOnboarding: () => set({ onboardingOpen: false }),
  startDemo: () =>
    set({
      onboardingOpen: false,
      state: demoProjectState,
      selectedStage: "sources",
      selectedArtifactId: "sources-originals-source-001-png",
      detailsOpen: false,
      compareMode: false,
      error: null,
      activities: [
        { id: `demo-${Date.now()}`, kind: "system", label: "Companion walkthrough started", detail: "Explore sources, baseline, style, generation, QA, and export without changing files.", time: "now" },
        ...initialActivities()
      ]
    }),
  loadDemo: () =>
    set({
      onboardingOpen: false,
      state: demoProjectState,
      selectedStage: "qa",
      selectedArtifactId: "runs-demo-qa-contact-sheet-png",
      detailsOpen: false,
      error: null,
      activities: initialActivities()
    }),
  loadProject: async (projectDir) => {
    set({ loading: true, error: null });
    try {
      const opened = await openProject(projectDir);
      const state = await getProjectState(opened.project_id);
      set({
        onboardingOpen: false,
        state,
        selectedStage: "sources",
        selectedArtifactId: state.artifacts.find((item) => item.stage === "sources")?.id ?? null,
        detailsOpen: false,
        activities: [
          { id: `open-${Date.now()}`, kind: "action", label: "Project opened", detail: opened.project_dir, time: "now" },
          ...get().activities
        ]
      });
      toast.success("Goodboy project opened");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      set({ error: message });
      toast.error("Could not open project", { description: message });
    } finally {
      set({ loading: false });
    }
  },
  refresh: async () => {
    const { state } = get();
    set({ loading: true, error: null });
    if (state.project_id === DEMO_PROJECT_ID) {
      set((current) => ({
        loading: false,
        error: null,
        state: demoProjectState,
        selectedArtifactId: "runs-demo-qa-contact-sheet-png",
        activities: [
          { id: `refresh-${Date.now()}`, kind: "system", label: "Demo refreshed", detail: "Fixture artifacts were reloaded locally.", time: "now" },
          ...current.activities
        ]
      }));
      toast.success("Demo refreshed");
      return;
    }
    try {
      const refreshed = await getProjectState(state.project_id);
      set({ state: refreshed });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : String(error) });
    } finally {
      set({ loading: false });
    }
  },
  approveDemo: (notes) => {
    const approval = { artifact: "contact-sheet", decision: "approved", notes, author: "human" };
    set((current) => ({
      state: {
        ...current.state,
        gate: { ...current.state.gate, install_ready: true, stage: "visually_approved", next_action: "export_or_install" },
        approvals: [approval, ...current.state.approvals]
      },
      activities: [
        { id: `approval-${Date.now()}`, kind: "action", label: "Approval recorded", detail: notes, time: "now" },
        ...current.activities
      ]
    }));
    toast.success("Approval recorded");
  },
  runAction: async (path, body, label) => {
    const projectId = get().state.project_id;
    set({ loading: true, error: null });
    try {
      const nextState = await postProjectAction(projectId, path, body);
      set((current) => ({
        state: nextState,
        activities: [{ id: `action-${Date.now()}`, kind: "action", label, detail: path, time: "now" }, ...current.activities]
      }));
      toast.success(label);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      set({ error: message });
      toast.error(label, { description: message });
    } finally {
      set({ loading: false });
    }
  }
}));

export function selectedArtifact(state: ProjectState, selectedArtifactId: string | null): ArtifactRef | null {
  return state.artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;
}
