import { CheckCircle2, Clock3, FileImage, MessageSquareText, PackageCheck, Sparkles, Upload, WandSparkles } from "lucide-react";
import { useState } from "react";

import { artifactIsImage, artifactsForStage } from "../../lib/artifacts";
import { StyleStudio } from "../../features/style/StyleStudio";
import { SourceReview } from "../../features/sources/SourceReview";
import { QualityGateActions } from "../../features/qa/QualityGateActions";
import { shortPath, titleCase } from "../../lib/format";
import { findSpritesheetArtifact, spriteImageRendering, spriteRowsForProject, spriteStatesForProject } from "../../lib/sprite";
import type { ArtifactRef, ProjectState, ReviewStage } from "../../lib/types";
import { currentDecisionFor } from "../../lib/workflow";
import { useProjectStore } from "../../state/project-store";
import { Button } from "../ui/button";
import { StatusBadge } from "../ui/status-badge";
import { SpriteStateViewer } from "./SpriteStateViewer";

interface ReviewDecisionSurfaceProps {
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  onStageChange: (stage: ReviewStage) => void;
  onOpenDetails: () => void;
  onOpenPreview: () => void;
  onApprove: (notes: string) => void;
}

export function ReviewDecisionSurface({
  state,
  selectedStage,
  selectedArtifact,
  onStageChange,
  onOpenDetails,
  onOpenPreview,
  onApprove
}: ReviewDecisionSurfaceProps) {
  const decision = currentDecisionFor(state, selectedStage);
  const spritesheet = findSpritesheetArtifact(state);
  const stageTitle = selectedStage === "qa" ? "QA Review" : selectedStage === "style" ? "Style Studio" : titleCase(selectedStage);
  const approvalNotes = "Reviewed identity traits, animated states, all 16 directions, source likeness, centering, continuity, edge cleanup, and generated files.";
  const reviewGates = state.qa?.review_gates as Record<string, unknown> | undefined;
  const installPolicy = state.qa?.install_policy as Record<string, unknown> | undefined;
  const hardFailures = Array.isArray(installPolicy?.hard_failures) ? installPolicy.hard_failures : [];
  const canApprove =
    state.project_id === "demo-review-room" ||
    Boolean(
      state.active_run_id &&
      reviewGates?.all_reviews_complete &&
      state.validation.ok &&
      hardFailures.length === 0
    );

  return (
    <main className="decision-shell" aria-label={`${stageTitle} decision surface`}>
      <div className="decision-main">
        <section className="decision-hero">
          <div>
            <span className="section-kicker">{decision.title}</span>
            <h2>{stageTitle}</h2>
            <p>{decision.detail}</p>
          </div>
          <div className="decision-hero-actions">
            <Button variant="default" onClick={onOpenDetails}>
              <FileImage size={14} />
              View details
            </Button>
            {selectedStage === "qa" || selectedStage === "approval" ? (
              <Button
                variant="primary"
                disabled={!canApprove}
                title={canApprove ? "Record final visual approval" : "Complete direction, likeness, validation, and QA gates first"}
                onClick={() => onApprove(approvalNotes)}
              >
                <CheckCircle2 size={14} />
                Approve visual review
              </Button>
            ) : null}
          </div>
        </section>
        <StageDecision
          state={state}
          selectedStage={selectedStage}
          selectedArtifact={selectedArtifact}
          spritesheet={spritesheet}
          onOpenPreview={onOpenPreview}
          onStageChange={onStageChange}
          onOpenDetails={onOpenDetails}
        />
      </div>
    </main>
  );
}

function StageDecision({
  state,
  selectedStage,
  selectedArtifact,
  spritesheet,
  onOpenPreview,
  onStageChange,
  onOpenDetails
}: {
  state: ProjectState;
  selectedStage: ReviewStage;
  selectedArtifact: ArtifactRef | null;
  spritesheet: ArtifactRef | null;
  onOpenPreview: () => void;
  onStageChange: (stage: ReviewStage) => void;
  onOpenDetails: () => void;
}) {
  if (selectedStage === "qa" && spritesheet) {
    const policy = state.qa?.install_policy as Record<string, unknown> | undefined;
    const warnings = Array.isArray(policy?.warnings) ? policy.warnings.length : 0;
    const directionStatus = String(state.direction_review?.status ?? "pending");
    const likenessStatus = String(state.likeness?.status ?? "pending");
    const animationStatus = String(state.animation_review?.status ?? "pending");
    return (
      <div className="decision-stack">
        <SpriteStateViewer
          spritesheetUrl={spritesheet.url}
          states={spriteStatesForProject(state)}
          rows={spriteRowsForProject(state)}
          imageRendering={spriteImageRendering(state)}
          onOpenPreview={onOpenPreview}
          qaSummary={[
            { label: "Manifest", value: state.validation.ok ? "Pass" : "Fail", severity: state.validation.ok ? "success" : "danger" },
            { label: "QA warnings", value: String(warnings), severity: warnings ? "warning" : "success" },
            { label: "Animation", value: animationStatus, severity: animationStatus === "approved" ? "success" : animationStatus === "failed" ? "danger" : "warning" },
            { label: "Directions", value: directionStatus, severity: directionStatus === "reviewed" ? "success" : "warning" },
            { label: "Likeness", value: likenessStatus, severity: likenessStatus === "approved" ? "success" : likenessStatus === "failed" ? "danger" : "warning" }
          ]}
        />
        <QualityGateActions state={state} />
        <div className="decision-action-card">
          <div>
            <h3>Approve this pet or request changes</h3>
            <p>The animated states are the primary review surface. Open details only when you need raw QA files, provenance, or policy evidence.</p>
          </div>
          <div className="toolbar-group">
            <Button variant="default" onClick={() => onStageChange("style")}>
              <MessageSquareText size={14} />
              Request changes
            </Button>
            <Button variant="default" onClick={onOpenDetails}>
              Open QA details
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (selectedStage === "baselines") {
    return <BaselineDecision state={state} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "identity") {
    return <IdentityDecision state={state} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "generation") {
    return <GenerationStatus state={state} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "style") {
    return <StyleDecision state={state} onStageChange={onStageChange} />;
  }

  if (selectedStage === "approval") {
    return <ExportDecision state={state} spritesheet={spritesheet} onOpenPreview={onOpenPreview} onOpenDetails={onOpenDetails} />;
  }

  if (selectedStage === "sources") {
    return <SourceDecision state={state} selectedArtifact={selectedArtifact} onOpenDetails={onOpenDetails} />;
  }

  return <DemoDecision state={state} />;
}

function BaselineDecision({ state, onOpenDetails }: { state: ProjectState; onOpenDetails: () => void }) {
  const candidates = state.candidates.slice(0, 3);
  return (
    <section className="decision-card-grid" aria-label="Baseline candidates">
      {candidates.map((candidate, index) => (
        <CandidateDecisionCard
          candidate={candidate}
          candidateArtifact={
            state.artifacts.find((artifact) =>
              artifact.relative_path === String(candidate.review_image_path ?? candidate.image_path ?? "")
            ) ?? (index === 0 ? state.artifacts.find((artifact) => artifact.kind === "character") : undefined)
          }
          disabled={state.project_id === "demo-review-room"}
          key={String(candidate.id)}
        />
      ))}
      <article className="decision-card helper">
        <Sparkles size={18} />
        <h3>Prove likeness, then choose</h3>
        <p>Score whole-animal gestalt, signature traits, and small-size readability. The winner becomes a preserved identity anchor for later style and animation.</p>
        <Button variant="default" onClick={onOpenDetails}>Open candidate files</Button>
      </article>
    </section>
  );
}

function CandidateDecisionCard({
  candidate,
  candidateArtifact,
  disabled
}: {
  candidate: Record<string, unknown>;
  candidateArtifact: ArtifactRef | undefined;
  disabled: boolean;
}) {
  const runAction = useProjectStore((store) => store.runAction);
  const candidateId = String(candidate.id);
  const [imagePath, setImagePath] = useState("");
  const [gestaltScore, setGestaltScore] = useState(String(candidate.holistic_gestalt_score ?? ""));
  const [traitScore, setTraitScore] = useState(String(candidate.signature_trait_score ?? ""));
  const [smallSizeScore, setSmallSizeScore] = useState(String(candidate.small_size_readability_score ?? ""));
  const [reviewNotes, setReviewNotes] = useState(String(candidate.review_notes ?? ""));
  const hasImage = Boolean(candidate.image_path);
  const reviewed = [
    candidate.holistic_gestalt_score,
    candidate.signature_trait_score,
    candidate.small_size_readability_score
  ].every((score) => score != null);
  const scoresValid = [gestaltScore, traitScore, smallSizeScore].every((raw) => {
    const score = Number(raw);
    return Number.isFinite(score) && score >= 1 && score <= 5;
  });
  return (
    <article className={`decision-card candidate ${candidate.selected ? "active" : ""}`}>
      {candidateArtifact && artifactIsImage(candidateArtifact)
        ? <img src={candidateArtifact.url} alt={`${candidateId} normalized source-likeness review`} />
        : <span className="candidate-placeholder" />}
      <div>
        <h3>{candidateId}</h3>
        <p>{String(candidate.style_summary ?? candidate.character_delta ?? "Generated baseline")}</p>
      </div>
      <StatusBadge severity={candidate.selected ? "success" : hasImage ? "info" : "warning"}>
        {candidate.selected ? "Selected" : hasImage ? "Ready to compare" : String(candidate.provider ?? "planned")}
      </StatusBadge>
      {!hasImage ? (
        <div className="candidate-import">
          <label htmlFor={`candidate-image-${candidateId}`}>Generated candidate path</label>
          <input
            id={`candidate-image-${candidateId}`}
            value={imagePath}
            onChange={(event) => setImagePath(event.target.value)}
            placeholder="/absolute/path/generated-candidate.png"
            disabled={disabled}
          />
          <Button
            variant="default"
            disabled={disabled || !imagePath.trim()}
            onClick={() =>
              void runAction(
                `/candidates/${candidateId}/image`,
                { image_path: imagePath.trim() },
                `Imported ${candidateId}`
              )
            }
          >
            Import candidate
          </Button>
        </div>
      ) : null}
      {!candidate.selected && hasImage ? (
        <div className="candidate-review-fields">
          <label>
            Holistic gestalt (1–5)
            <input type="number" min="1" max="5" step="0.5" value={gestaltScore} onChange={(event) => setGestaltScore(event.target.value)} disabled={disabled || reviewed} />
          </label>
          <label>
            Signature traits (1–5)
            <input type="number" min="1" max="5" step="0.5" value={traitScore} onChange={(event) => setTraitScore(event.target.value)} disabled={disabled || reviewed} />
          </label>
          <label>
            Small-size readability (1–5)
            <input type="number" min="1" max="5" step="0.5" value={smallSizeScore} onChange={(event) => setSmallSizeScore(event.target.value)} disabled={disabled || reviewed} />
          </label>
          <label>
            Source-linked review notes
            <input value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="Visible anatomy, coat, markings, and small-size evidence" disabled={disabled || reviewed} />
          </label>
          {!reviewed ? (
            <Button
              variant="default"
              disabled={disabled || !scoresValid || !reviewNotes.trim()}
              onClick={() =>
                void runAction(
                  `/candidates/${candidateId}/review`,
                  {
                    holistic_gestalt_score: Number(gestaltScore),
                    signature_trait_score: Number(traitScore),
                    small_size_readability_score: Number(smallSizeScore),
                    notes: reviewNotes.trim(),
                    reviewed_by: "human"
                  },
                  `Reviewed ${candidateId}`
                )
              }
            >
              Record likeness evidence
            </Button>
          ) : (
            <StatusBadge severity="success">Identity evidence recorded</StatusBadge>
          )}
          <Button
            variant="default"
            disabled={disabled || !reviewed}
            onClick={() =>
              void runAction(
                `/candidates/${candidateId}/select`,
                { notes: "Selected in Review Room for strongest source likeness." },
                `Selected ${candidateId}`
              )
            }
          >
            Choose for likeness
          </Button>
        </div>
      ) : null}
    </article>
  );
}

function IdentityDecision({ state, onOpenDetails }: { state: ProjectState; onOpenDetails: () => void }) {
  const runAction = useProjectStore((store) => store.runAction);
  const traits = Array.isArray(state.identity_profile?.traits)
    ? (state.identity_profile?.traits as Array<Record<string, unknown>>)
    : [];
  const [selectedId, setSelectedId] = useState(String(traits[0]?.id ?? ""));
  const selected = traits.find((trait) => String(trait.id) === selectedId) ?? traits[0];
  const [draftValue, setDraftValue] = useState(String(selected?.value ?? ""));
  const [reason, setReason] = useState("");
  const [providerConsent, setProviderConsent] = useState(false);
  const [provider, setProvider] = useState("codex_builtin");
  const missing = Array.isArray(state.reference_coverage?.missing_recommended_roles)
    ? (state.reference_coverage?.missing_recommended_roles as unknown[])
    : [];
  const confirmed = state.identity_profile?.status === "confirmed";

  const selectTrait = (id: string) => {
    const trait = traits.find((item) => String(item.id) === id);
    setSelectedId(id);
    setDraftValue(String(trait?.value ?? ""));
    setReason("");
  };

  return (
    <section className="identity-decision-grid" aria-label="Evidence-linked identity">
      <div className="monitor-card">
        <div className="monitor-heading">
          <Sparkles size={18} />
          <div>
            <h3>{confirmed ? "Canonical identity confirmed" : "Confirm what makes this pet recognizable"}</h3>
            <p>{String(state.identity_profile?.identity_summary ?? "Review every defining trait before generation.")}</p>
          </div>
        </div>
        <div className="row-list">
          {traits.map((trait) => (
            <button type="button" className="data-row identity-trait-row" key={String(trait.id)} onClick={() => selectTrait(String(trait.id))}>
              <span>
                {String(trait.category)}
                <em>{String(trait.value)}</em>
              </span>
              <StatusBadge severity={trait.importance === "signature" ? "warning" : "info"}>{String(trait.importance)}</StatusBadge>
            </button>
          ))}
        </div>
        {missing.length ? <p className="field-help">Coverage still recommended: {missing.map(String).join(", ")}</p> : null}
        <div className="field">
          <label htmlFor="identity-provider">Image provider receiving approved derivatives</label>
          <select
            id="identity-provider"
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
          >
            <option value="codex_builtin">Codex built-in image generation</option>
            <option value="openai_images">OpenAI Images API</option>
            <option value="gemini_nano_banana_2">Gemini Nano Banana 2</option>
            <option value="gemini_nano_banana_pro">Gemini Nano Banana Pro</option>
          </select>
        </div>
        <label className="consent-check">
          <input
            type="checkbox"
            checked={providerConsent}
            onChange={(event) => setProviderConsent(event.target.checked)}
          />
          <span>
            Allow EXIF-stripped copies of approved source photos to be sent to the selected image provider.
            Original files stay local and are never packaged.
          </span>
        </label>
        <div className="toolbar-group">
          <Button variant="default" onClick={onOpenDetails}>View source evidence</Button>
          <Button
            variant="primary"
            disabled={confirmed || !traits.length || !providerConsent}
            onClick={() =>
              void runAction(
                "/advance",
                {
                  confirm_identity: true,
                  provider_consent: true,
                  provider,
                  model_alias:
                    provider === "openai_images"
                      ? "gpt-image-2"
                      : provider === "gemini_nano_banana_2"
                        ? "gemini-3.1-flash-image"
                        : provider === "gemini_nano_banana_pro"
                          ? "gemini-3-pro-image-preview"
                        : "codex-imagegen"
                },
                `Identity confirmed; consented ${provider} likeness candidates planned`
              )
            }
          >
            Confirm identity
          </Button>
        </div>
      </div>
      <div className="monitor-card">
        <h3>Correct a trait</h3>
        <div className="field">
          <label htmlFor="identity-trait">Trait</label>
          <select id="identity-trait" value={selectedId} onChange={(event) => selectTrait(event.target.value)}>
            {traits.map((trait) => <option value={String(trait.id)} key={String(trait.id)}>{String(trait.id)}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="identity-value">Canonical description</label>
          <textarea id="identity-value" value={draftValue} onChange={(event) => setDraftValue(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="identity-reason">Why this is more accurate</label>
          <input id="identity-reason" value={reason} onChange={(event) => setReason(event.target.value)} />
        </div>
        <Button
          variant="default"
          disabled={!selected || !draftValue.trim() || !reason.trim()}
          onClick={() =>
            void runAction(
              "/identity/patch",
              { trait_id: selectedId, value: draftValue, reason, author: "human", run_id: state.active_run_id },
              "Identity trait corrected"
            )
          }
        >
          Save versioned correction
        </Button>
      </div>
    </section>
  );
}

function GenerationStatus({ state, onOpenDetails }: { state: ProjectState; onOpenDetails: () => void }) {
  const runAction = useProjectStore((store) => store.runAction);
  const jobs = state.jobs;
  const runId = state.active_run_id;
  const [mappingText, setMappingText] = useState("{\n  \"idle\": \"/absolute/path/idle.png\"\n}");
  const [mappingError, setMappingError] = useState("");
  const [repairJobId, setRepairJobId] = useState(String(jobs[0]?.id ?? ""));
  const [repairReason, setRepairReason] = useState("");
  const allJobsComplete = jobs.length > 0 && jobs.every((job) => job.status === "complete");
  const isDemo = state.project_id === "demo-review-room";
  const graph = state.job_graph;
  const readyJobs = Array.isArray(graph?.ready) ? graph.ready.length : jobs.filter((job) => job.status === "ready").length;
  const blockedJobs = Array.isArray(graph?.blocked) ? graph.blocked.length : jobs.filter((job) => job.status === "blocked").length;
  const completeJobs = Array.isArray(graph?.complete) ? graph.complete.length : jobs.filter((job) => job.status === "complete").length;

  const importGenerated = () => {
    if (!runId) return;
    try {
      const mapping = JSON.parse(mappingText) as unknown;
      if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) {
        throw new Error("The output map must be a JSON object.");
      }
      setMappingError("");
      void runAction(
        "/generation/import",
        { run_id: runId, mapping, extraction_method: "auto" },
        "Generated outputs imported"
      );
    } catch (error) {
      setMappingError(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <section className="generation-workspace" aria-label="Generation monitor">
      <div className="monitor-card">
      <div className="monitor-heading">
        <WandSparkles size={18} />
        <div>
          <h3>V2 generation dependency graph</h3>
          <p>Only ready jobs should be sent to a provider. Imports, recovery, and repair mutate the same durable graph used by the CLI.</p>
        </div>
      </div>
      <div className="qa-chip-row" aria-label="Dependency graph summary">
        <StatusBadge severity={readyJobs ? "info" : "success"}>{`${readyJobs} ready`}</StatusBadge>
        <StatusBadge severity={blockedJobs ? "warning" : "success"}>{`${blockedJobs} blocked`}</StatusBadge>
        <StatusBadge severity="success">{`${completeJobs} complete`}</StatusBadge>
      </div>
      <div className="state-count-grid">
        {jobs.map((job) => (
          <div className="data-row" key={String(job.id)}>
            <span>
              {String(job.state ?? job.id)}
              <em>
                {Array.isArray(job.depends_on) && job.depends_on.length
                  ? `after ${job.depends_on.map(String).join(", ")}`
                  : String(job.blocked_reason ?? job.kind ?? "")}
              </em>
            </span>
            <StatusBadge severity={job.status === "complete" ? "success" : job.status === "qa_failed" || job.status === "failed" ? "danger" : job.status === "blocked" ? "warning" : "info"}>
              {String(job.status)}
            </StatusBadge>
          </div>
        ))}
        {!jobs.length ? <div className="data-row"><span>No run planned</span><StatusBadge severity="info">Waiting</StatusBadge></div> : null}
      </div>
      <div className="toolbar-group">
        <Button
          variant="default"
          disabled={!runId || isDemo}
          onClick={() =>
            runId &&
            void runAction(
              "/generation/handoff",
              { run_id: runId, all_jobs: true },
              "Ready provider handoffs generated"
            )
          }
        >
          Generate ready handoffs
        </Button>
        <Button
          variant="default"
          disabled={!runId || isDemo}
          onClick={() =>
            runId &&
            void runAction("/recover", { run_id: runId }, "Interrupted jobs reconciled")
          }
        >
          Recover interrupted run
        </Button>
        <Button variant="default" onClick={onOpenDetails}>Open generated files</Button>
      </div>
      </div>
      <div className="monitor-card generation-import-card">
        <h3>Import generated output map</h3>
        <p>Paste the provider output paths keyed by state or job ID. Goodboy imports only dependency-ready work and records provenance.</p>
        <label htmlFor="generated-output-map">Generated output JSON</label>
        <textarea
          id="generated-output-map"
          value={mappingText}
          onChange={(event) => setMappingText(event.target.value)}
          disabled={isDemo}
        />
        {mappingError ? <p className="field-error" role="alert">{mappingError}</p> : null}
        <div className="toolbar-group">
          <Button variant="primary" disabled={!runId || isDemo} onClick={importGenerated}>
            Import ready outputs
          </Button>
          <Button
            variant="default"
            disabled={!runId || !allJobsComplete || isDemo}
            onClick={() =>
              runId &&
              void runAction(
                "/review/build",
                { run_id: runId, row_provenance: "provider_generated" },
                "V2 review artifacts built"
              )
            }
          >
            Build final review
          </Button>
        </div>
      </div>
      <div className="monitor-card generation-repair-card">
        <h3>Targeted repair</h3>
        <p>The selected job and its dependency closure are archived and invalidated. Unrelated completed work is preserved.</p>
        <label htmlFor="repair-job">Job</label>
        <select
          id="repair-job"
          value={repairJobId}
          onChange={(event) => setRepairJobId(event.target.value)}
          disabled={isDemo || !jobs.length}
        >
          {jobs.map((job) => <option value={String(job.id)} key={String(job.id)}>{String(job.id)}</option>)}
        </select>
        <label htmlFor="repair-reason">Visible problem and intended correction</label>
        <textarea
          id="repair-reason"
          value={repairReason}
          onChange={(event) => setRepairReason(event.target.value)}
          placeholder="The left-ear marking drifts in frames 3–5; preserve its anatomical side."
          disabled={isDemo}
        />
        <Button
          variant="default"
          disabled={!runId || !repairJobId || !repairReason.trim() || isDemo}
          onClick={() =>
            runId &&
            void runAction(
              "/repair",
              {
                run_id: runId,
                job_ids: [repairJobId],
                reason: repairReason.trim(),
                author: "human"
              },
              `Repair planned for ${repairJobId}`
            )
          }
        >
          Archive and repair selected scope
        </Button>
      </div>
    </section>
  );
}

function StyleDecision({ state, onStageChange }: { state: ProjectState; onStageChange: (stage: ReviewStage) => void }) {
  const runAction = useProjectStore((store) => store.runAction);
  return (
    <section className="monitor-card style-decision" aria-label="Style decision">
      <StyleStudio state={state} />
      <div className="decision-action-card inline">
        <p>Use the recorded style card unless you want the agent to branch for a specific look such as realistic, anime, plush, or object mascot.</p>
        <Button
          variant="primary"
          onClick={() => {
            onStageChange("generation");
            if (state.project_id !== "demo-review-room") {
              void runAction("/advance", {}, "V2 generation planned");
            }
          }}
        >
          Use style and continue
        </Button>
      </div>
    </section>
  );
}

function SourceDecision({ state, selectedArtifact, onOpenDetails }: { state: ProjectState; selectedArtifact: ArtifactRef | null; onOpenDetails: () => void }) {
  return (
    <section className="source-decision-grid" aria-label="Source identity review">
      <div className="source-preview-card">
        {selectedArtifact && artifactIsImage(selectedArtifact) ? <img src={selectedArtifact.url} alt={selectedArtifact.label} /> : <Upload size={28} />}
      </div>
      <div className="monitor-card">
        <div className="monitor-heading">
          <Upload size={18} />
          <div>
            <h3>Start with clear references</h3>
            <p>{String(state.character_card?.one_sentence_identity ?? "Confirm the subject identity before generating baselines.")}</p>
          </div>
        </div>
        <div className="state-count-grid">
          <div className="data-row">
            <span>Sources</span>
            <strong>{state.sources.length}</strong>
          </div>
          <div className="data-row">
            <span>Validation</span>
            <StatusBadge severity={state.validation.ok ? "success" : "danger"}>{state.validation.ok ? "Clean" : "Issues"}</StatusBadge>
          </div>
        </div>
        <Button variant="default" onClick={onOpenDetails}>Open source details</Button>
        <SourceReview state={state} />
      </div>
    </section>
  );
}

function ExportDecision({
  state,
  spritesheet,
  onOpenPreview,
  onOpenDetails
}: {
  state: ProjectState;
  spritesheet: ArtifactRef | null;
  onOpenPreview: () => void;
  onOpenDetails: () => void;
}) {
  const runAction = useProjectStore((store) => store.runAction);
  const [exportKind, setExportKind] = useState("petdex");
  const [outputDir, setOutputDir] = useState("");
  const [includeSources, setIncludeSources] = useState(false);
  const [installRoot, setInstallRoot] = useState("");
  const [finishNotes, setFinishNotes] = useState(
    "Approved identity, motion, 16 directions, edges, and source likeness."
  );
  const runId = state.active_run_id;
  const isDemo = state.project_id === "demo-review-room";
  return (
    <section className="monitor-card" aria-label="Export package">
      <div className="monitor-heading">
        <PackageCheck size={18} />
        <div>
          <h3>{state.gate.install_ready ? "Package ready" : "Approval needed"}</h3>
          <p>Export stays behind the visual approval gate so agents do not install unreviewed pets.</p>
        </div>
      </div>
      <div className="state-count-grid">
        <div className="data-row">
          <span>Spritesheet</span>
          <StatusBadge severity={spritesheet ? "success" : "warning"}>{spritesheet ? shortPath(spritesheet.relative_path) : "Missing"}</StatusBadge>
        </div>
        <div className="data-row">
          <span>Install policy</span>
          <StatusBadge severity={state.gate.install_ready ? "success" : "warning"}>{state.gate.install_ready ? "Ready" : "Needs approval"}</StatusBadge>
        </div>
      </div>
      <div className="toolbar-group">
        <Button variant="default" onClick={onOpenPreview}>Open large preview</Button>
        <Button variant="default" onClick={onOpenDetails}>Open package details</Button>
      </div>
      <div className="finish-export-grid">
        <div className="finish-export-panel">
          <h4>Create an export</h4>
          <label htmlFor="export-kind">Export kind</label>
          <select id="export-kind" value={exportKind} onChange={(event) => setExportKind(event.target.value)}>
            <option value="petdex">Petdex package</option>
            <option value="diagnostic">Sanitized diagnostic</option>
            <option value="project">Project archive</option>
          </select>
          <label htmlFor="export-output-dir">Output directory (optional)</label>
          <input
            id="export-output-dir"
            value={outputDir}
            onChange={(event) => setOutputDir(event.target.value)}
            placeholder="/absolute/path/to/exports"
          />
          {exportKind === "project" ? (
            <label className="consent-check">
              <input
                type="checkbox"
                checked={includeSources}
                onChange={(event) => setIncludeSources(event.target.checked)}
              />
              <span>Include private source pixels in this project archive.</span>
            </label>
          ) : null}
          <Button
            variant="primary"
            disabled={!runId || !state.gate.install_ready || isDemo}
            onClick={() =>
              runId &&
              void runAction(
                "/export",
                {
                  kind: exportKind,
                  run_id: runId,
                  output_dir: outputDir.trim() || null,
                  include_sources: exportKind === "project" && includeSources
                },
                `${exportKind} export created`
              )
            }
          >
            Export approved package
          </Button>
        </div>
        <div className="finish-export-panel">
          <h4>Install explicitly</h4>
          <label htmlFor="finish-install-root">Codex package root</label>
          <input
            id="finish-install-root"
            value={installRoot}
            onChange={(event) => setInstallRoot(event.target.value)}
            placeholder="/absolute/path/to/codex/pets"
          />
          <label htmlFor="finish-notes">Final approval evidence</label>
          <textarea
            id="finish-notes"
            value={finishNotes}
            onChange={(event) => setFinishNotes(event.target.value)}
          />
          <Button
            variant="default"
            disabled={
              !runId ||
              !state.gate.install_ready ||
              !installRoot.trim() ||
              !finishNotes.trim() ||
              isDemo
            }
            onClick={() =>
              runId &&
              void runAction(
                "/finish",
                {
                  run_id: runId,
                  approval_notes: finishNotes.trim(),
                  row_provenance: "provider_generated",
                  install_root: installRoot.trim()
                },
                "Approved v2 pet installed"
              )
            }
          >
            Finish and install
          </Button>
        </div>
      </div>
      {state.exports.length ? (
        <div className="row-list" aria-label="Created exports">
          {state.exports.map((artifact) => (
            <div className="data-row" key={artifact.id}>
              <span>{artifact.label}</span>
              <strong>{shortPath(artifact.relative_path)}</strong>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function DemoDecision({ state }: { state: ProjectState }) {
  return (
    <section className="monitor-card" aria-label="Demo walkthrough">
      <div className="monitor-heading">
        <Clock3 size={18} />
        <div>
          <h3>Companion demo walkthrough</h3>
          <p>Use the stepper to see the same gates that a real Goodboy run asks you to review.</p>
        </div>
      </div>
      <div className="state-count-grid">
        {artifactsForStage(state.artifacts, "qa").map((artifact) => (
          <div className="data-row" key={artifact.id}>
            <span>{artifact.label}</span>
            <StatusBadge severity={artifact.severity}>{artifact.kind}</StatusBadge>
          </div>
        ))}
      </div>
    </section>
  );
}
