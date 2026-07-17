import { create } from "zustand";
import { toast } from "sonner";

import { createProject, getLaunchContext, getProjectState, openProject, postProjectAction, uploadProjectSources } from "../lib/api";
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
  launchContextChecked: boolean;
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
  loadLaunchProject: () => Promise<void>;
  loadProject: (projectDir: string) => Promise<void>;
  createProject: (projectDir: string, petId: string, displayName: string, species: string) => Promise<void>;
  refresh: () => Promise<void>;
  approveDemo: (notes: string) => void;
  approve: (notes: string) => Promise<void>;
  uploadSources: (files: File[], notes?: string) => Promise<void>;
  runAction: (path: string, body: unknown, label: string) => Promise<void>;
}

function stageForGate(stage: string): ReviewStage {
  if (stage.includes("identity")) return "identity";
  if (stage.includes("baseline")) return "baselines";
  if (stage.includes("generation") || stage.includes("rows")) return "generation";
  if (stage.includes("review") || stage.includes("quality")) return "qa";
  if (stage.includes("approved") || stage.includes("installed")) return "approval";
  return "sources";
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
  launchContextChecked: false,
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
  loadLaunchProject: async () => {
    if (get().launchContextChecked) return;
    set({ launchContextChecked: true });
    try {
      const context = await getLaunchContext();
      if (!context.project_id || !context.project_dir) return;
      const state = await getProjectState(context.project_id);
      const stage = stageForGate(state.gate.stage);
      set((current) => ({
        onboardingOpen: false,
        state,
        selectedStage: stage,
        selectedArtifactId: state.artifacts.find((item) => item.stage === stage)?.id ?? null,
        detailsOpen: false,
        error: null,
        activities: [
          {
            id: `launch-${Date.now()}`,
            kind: "system",
            label: "Launch project opened",
            detail: context.project_dir ?? "",
            time: "now"
          },
          ...current.activities
        ]
      }));
    } catch (error) {
      // Vite-only development intentionally has no API unless the Python server is running.
      if (!import.meta.env.DEV) {
        const message = error instanceof Error ? error.message : String(error);
        set({ error: message });
        toast.error("Could not load the launch project", { description: message });
      }
    }
  },
  loadProject: async (projectDir) => {
    set({ loading: true, error: null });
    try {
      const opened = await openProject(projectDir);
      const state = await getProjectState(opened.project_id);
      set({
        onboardingOpen: false,
        state,
        selectedStage: stageForGate(state.gate.stage),
        selectedArtifactId: state.artifacts.find((item) => item.stage === stageForGate(state.gate.stage))?.id ?? null,
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
  createProject: async (projectDir, petId, displayName, species) => {
    set({ loading: true, error: null });
    try {
      const state = await createProject(projectDir, petId, displayName, species);
      set((current) => ({
        onboardingOpen: false,
        state,
        selectedStage: "sources",
        selectedArtifactId: null,
        activities: [
          { id: `create-${Date.now()}`, kind: "action", label: "V2 project created", detail: projectDir, time: "now" },
          ...current.activities
        ]
      }));
      toast.success("Goodboy v2 project created");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      set({ error: message });
      toast.error("Could not create project", { description: message });
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
  approve: async (notes) => {
    const state = get().state;
    if (state.project_id === DEMO_PROJECT_ID) {
      get().approveDemo(notes);
      return;
    }
    if (!state.active_run_id) {
      toast.error("No active run to approve");
      return;
    }
    await get().runAction(
      "/approval",
      { run_id: state.active_run_id, artifact: "final-review", decision: "approved", notes },
      "Visual approval recorded"
    );
  },
  uploadSources: async (files, notes = "") => {
    const projectId = get().state.project_id;
    if (projectId === DEMO_PROJECT_ID) {
      toast.info("The demo is read-only");
      return;
    }
    set({ loading: true, error: null });
    try {
      const state = await uploadProjectSources(projectId, files, notes);
      set((current) => ({
        state,
        selectedStage: "identity",
        activities: [
          { id: `upload-${Date.now()}`, kind: "action", label: "Source images added", detail: `${files.length} local file(s)`, time: "now" },
          ...current.activities
        ]
      }));
      toast.success("Source references added");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      set({ error: message });
      toast.error("Could not add source references", { description: message });
    } finally {
      set({ loading: false });
    }
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
