import { useState } from "react";

import { useProjectStore } from "../../state/project-store";
import { Button } from "../../components/ui/button";

export function ProjectOpen() {
  const [projectDir, setProjectDir] = useState("");
  const loadProject = useProjectStore((store) => store.loadProject);
  return (
    <section className="inspector-section">
      <h3>Open Project</h3>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="project-dir">Project directory</label>
          <input id="project-dir" value={projectDir} onChange={(event) => setProjectDir(event.target.value)} />
        </div>
        <Button variant="primary" disabled={!projectDir.trim()} onClick={() => void loadProject(projectDir)}>
          Open project
        </Button>
      </div>
    </section>
  );
}
