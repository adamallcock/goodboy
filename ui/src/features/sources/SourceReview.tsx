import { Upload } from "lucide-react";
import { useDropzone } from "react-dropzone";

import type { ProjectState } from "../../lib/types";

export function SourceReview({ state }: { state: ProjectState }) {
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({ accept: { "image/*": [] } });
  return (
    <section className="inspector-section">
      <h3>Source Review</h3>
      <div className="stage-panel">
        <div className="data-row">
          <span>Images</span>
          <strong>{state.sources.length}</strong>
        </div>
        <div className="data-row">
          <span>Provenance</span>
          <strong>{state.validation.ok ? "Valid" : "Needs attention"}</strong>
        </div>
        <div {...getRootProps()} className="data-row" aria-label="Drop source images">
          <input {...getInputProps()} />
          <span>
            <Upload size={14} /> {isDragActive ? "Drop images" : "Drag source images"}
          </span>
          <strong>{acceptedFiles.length ? `${acceptedFiles.length} ready` : "Local"}</strong>
        </div>
        <div className="row-list">
          {state.sources.map((source) => (
            <div className="data-row" key={String(source.id)}>
              <span>{String(source.id)}</span>
              <strong>{String(source.notes ?? "reference")}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
