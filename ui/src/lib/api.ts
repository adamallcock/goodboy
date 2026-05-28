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

export async function getProjectState(projectId: string): Promise<ProjectState> {
  return request(`/api/projects/${projectId}/state`);
}

export async function postProjectAction(projectId: string, path: string, body: unknown): Promise<ProjectState> {
  return request(`/api/projects/${projectId}${path}`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}
