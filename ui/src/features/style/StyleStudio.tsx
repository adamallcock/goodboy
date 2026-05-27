import { useState } from "react";

import type { ProjectState } from "../../lib/types";
import { SegmentedControl } from "../../components/ui/segmented-control";
import { Button } from "../../components/ui/button";

const presets = ["soft-lifelike", "realistic", "anime", "storybook", "pixel", "sticker"];
const subjects = ["pet", "animal", "object", "inanimate_object", "fantasy_creature"];

export function StyleStudio({ state }: { state: ProjectState }) {
  const [preset, setPreset] = useState(String(state.style_sheet?.style_preset ?? "soft-lifelike"));
  const [subject, setSubject] = useState(String(state.style_sheet?.subject_kind ?? "pet"));
  const [critique, setCritique] = useState("Make the silhouette read clearly at pet scale.");
  return (
    <section className="inspector-section">
      <h3>Style Studio</h3>
      <div className="form-grid">
        <div className="field">
          <label>Preset</label>
          <SegmentedControl value={preset} options={presets} onChange={setPreset} />
        </div>
        <div className="field">
          <label>Subject</label>
          <SegmentedControl value={subject} options={subjects} onChange={setSubject} />
        </div>
        <div className="field">
          <label htmlFor="critique">Critique</label>
          <textarea id="critique" value={critique} onChange={(event) => setCritique(event.target.value)} />
        </div>
        <Button>Preview style update</Button>
      </div>
    </section>
  );
}
