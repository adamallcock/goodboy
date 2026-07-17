import { useState } from "react";
import { Upload } from "lucide-react";
import { useDropzone } from "react-dropzone";

import type { ProjectState } from "../../lib/types";
import { useProjectStore } from "../../state/project-store";
import { Button } from "../../components/ui/button";

export function SourceReview({ state }: { state: ProjectState }) {
  const uploadSources = useProjectStore((store) => store.uploadSources);
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    accept: { "image/*": [] },
    disabled: state.project_id === "demo-review-room",
    onDropAccepted: (files) => void uploadSources(files, "Added through Review Room")
  });
  const coverage = state.reference_coverage;
  const missing = Array.isArray(coverage?.missing_recommended_roles) ? coverage?.missing_recommended_roles as unknown[] : [];
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
        <div className="data-row">
          <span>Reference coverage</span>
          <strong>{missing.length ? `${missing.length} gap(s)` : "Ready"}</strong>
        </div>
        <div {...getRootProps()} className="data-row" aria-label="Drop source images">
          <input {...getInputProps()} />
          <span>
            <Upload size={14} /> {isDragActive ? "Drop images" : "Drag source images"}
          </span>
          <strong>{acceptedFiles.length ? `${acceptedFiles.length} ready` : "Local"}</strong>
        </div>
        <div className="source-role-list">
          {state.sources.map((source) => (
            <SourceRoleEditor
              key={String(source.id)}
              source={source}
              disabled={state.project_id === "demo-review-room"}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function SourceRoleEditor({
  source,
  disabled
}: {
  source: Record<string, unknown>;
  disabled: boolean;
}) {
  const runAction = useProjectStore((store) => store.runAction);
  const sourceId = String(source.id);
  const existingRoles = Array.isArray(source.roles) ? source.roles.map(String) : [];
  const existingPermissions =
    source.provider_permissions && typeof source.provider_permissions === "object"
      ? (source.provider_permissions as Record<string, unknown>)
      : {};
  const [roles, setRoles] = useState(existingRoles.join(", "));
  const [permissions, setPermissions] = useState<Record<string, boolean>>({
    codex_builtin: Boolean(existingPermissions.codex_builtin),
    openai_images: Boolean(existingPermissions.openai_images),
    gemini_nano_banana_2: Boolean(existingPermissions.gemini_nano_banana_2),
    gemini_nano_banana_pro: Boolean(existingPermissions.gemini_nano_banana_pro)
  });
  const normalizedRoles = roles
    .split(",")
    .map((role) => role.trim())
    .filter(Boolean);

  return (
    <fieldset className="source-role-editor" disabled={disabled}>
      <legend>{sourceId}</legend>
      <label>
        Reference roles
        <input
          value={roles}
          onChange={(event) => setRoles(event.target.value)}
          placeholder="identity_front, marking_detail, body_proportions"
        />
      </label>
      <div className="source-provider-permissions" aria-label={`Provider permissions for ${sourceId}`}>
        {Object.entries(permissions).map(([provider, allowed]) => (
          <label key={provider}>
            <input
              type="checkbox"
              checked={allowed}
              onChange={(event) =>
                setPermissions((current) => ({ ...current, [provider]: event.target.checked }))
              }
            />
            {provider}
          </label>
        ))}
      </div>
      <Button
        variant="default"
        disabled={disabled || normalizedRoles.length === 0}
        onClick={() =>
          void runAction(
            `/sources/${sourceId}/roles`,
            { roles: normalizedRoles, provider_permissions: permissions },
            `Source roles and permissions saved for ${sourceId}`
          )
        }
      >
        Save source policy
      </Button>
    </fieldset>
  );
}
