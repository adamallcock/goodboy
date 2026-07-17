import type { ProjectState } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function openProject(projectDir: string): Promise<{ project_id: string; project_dir: string }> {
  return request("/api/projects/open", {
    method: "POST",
    body: JSON.stringify({ project_dir: projectDir })
  });
}

export async function createProject(
  projectDir: string,
  petId: string,
  displayName: string,
  species: string
): Promise<ProjectState> {
  return request("/api/projects/create", {
    method: "POST",
    body: JSON.stringify({ project_dir: projectDir, pet_id: petId, display_name: displayName, species })
  });
}

export async function getProjectState(projectId: string): Promise<ProjectState> {
  return request(`/api/projects/${projectId}/state`);
}

export async function getLaunchContext(): Promise<{
  project_id: string | null;
  project_dir: string | null;
}> {
  return request("/api/launch-context");
}

export async function postProjectAction(projectId: string, path: string, body: unknown): Promise<ProjectState> {
  return request(`/api/projects/${projectId}${path}`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function uploadProjectSources(projectId: string, files: File[], notes = ""): Promise<ProjectState> {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  body.append("notes", notes);
  const response = await fetch(`/api/projects/${projectId}/sources/upload`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    throw new Error((await response.text()) || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as ProjectState;
}
