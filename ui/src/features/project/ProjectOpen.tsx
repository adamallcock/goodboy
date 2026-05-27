import { useState } from "react";
import { FolderOpen } from "lucide-react";

import { useProjectStore } from "../../state/project-store";
import { Button } from "../../components/ui/button";

export function ProjectOpen() {
  const [projectDir, setProjectDir] = useState("");
  const loadProject = useProjectStore((store) => store.loadProject);
  return (
    <section className="inspector-section">
      <h3>Open Project</h3>
      <div className="project-open-card">
        <div className="project-open-icon" aria-hidden="true">
          <FolderOpen size={18} />
        </div>
        <div>
          <strong>Paste a Goodboy folder path</strong>
          <p>
            Use the local project folder that contains <code>goodboy.json</code>.
          </p>
        </div>
        <label className="field project-path-field" htmlFor="project-dir">
          <span>Project directory</span>
          <input
            id="project-dir"
            value={projectDir}
            placeholder="/Users/adamallcock/Documents/Coding/goodboy/projects/my-pet"
            onChange={(event) => setProjectDir(event.target.value)}
          />
        </label>
        <Button variant="primary" disabled={!projectDir.trim()} onClick={() => void loadProject(projectDir)}>
          Open project
        </Button>
      </div>
    </section>
  );
}
