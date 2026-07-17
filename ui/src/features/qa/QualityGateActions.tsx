import { useState } from "react";

import type { ProjectState } from "../../lib/types";
import { spriteRowsForProject } from "../../lib/sprite";
import { useProjectStore } from "../../state/project-store";
import { Button } from "../../components/ui/button";
import { StatusBadge } from "../../components/ui/status-badge";

const directions = [
  "000", "022.5", "045", "067.5", "090", "112.5", "135", "157.5",
  "180", "202.5", "225", "247.5", "270", "292.5", "315", "337.5"
];

const animationStates = [
  { id: "idle", label: "Idle", expected: "Near-still neutral breathing or blinking; no request for attention." },
  { id: "running-right", label: "Run right", expected: "Clear locomotion toward the pet's anatomical right." },
  { id: "running-left", label: "Run left", expected: "Clear locomotion toward the pet's anatomical left." },
  { id: "waving", label: "Waving", expected: "A friendly, deliberate greeting gesture." },
  { id: "jumping", label: "Jumping", expected: "A readable takeoff, airborne beat, landing, and recovery." },
  { id: "failed", label: "Failed", expected: "Gentle disappointment followed by recovery." },
  { id: "waiting", label: "Waiting", expected: "Expectant pause that asks for user input without looking idle." },
  { id: "running", label: "Active task", expected: "Focused active work; this state means a task is running, not foot-running." },
  { id: "review", label: "Review", expected: "Focused inspection or checking behavior distinct from active work." }
];

function expectedDirection(value: string): string {
  const angle = Number(value);
  if (angle === 0) return "up";
  if (angle === 90) return "right";
  if (angle === 180) return "down";
  if (angle === 270) return "left";
  const vertical = angle > 270 || angle < 90 ? "up" : "down";
  const horizontal = angle > 0 && angle < 180 ? "right" : "left";
  return `${vertical}-${horizontal}`;
}

export function QualityGateActions({ state }: { state: ProjectState }) {
  const runAction = useProjectStore((store) => store.runAction);
  const [blindFiles, setBlindFiles] = useState<File[]>([]);
  const existingDirectionVerdicts = Array.isArray(state.direction_review?.directions)
    ? (state.direction_review.directions as Array<Record<string, unknown>>)
    : [];
  const [directionDrafts, setDirectionDrafts] = useState<
    Record<string, { verdict: string; observed: string; reason: string }>
  >(
    Object.fromEntries(
      existingDirectionVerdicts.map((item) => [
        String(item.direction),
        {
          verdict: String(item.verdict ?? ""),
          observed: String(item.observed ?? ""),
          reason: String(item.reason ?? "")
        }
      ])
    )
  );
  const existingLikenessVerdicts = Array.isArray(state.likeness?.verdicts)
    ? (state.likeness.verdicts as Array<Record<string, unknown>>)
    : [];
  const [likenessDrafts, setLikenessDrafts] = useState<
    Record<string, { verdict: string; evidence: string }>
  >(
    Object.fromEntries(
      existingLikenessVerdicts.map((item) => [
        String(item.trait_id),
        {
          verdict: String(item.verdict ?? ""),
          evidence: String(item.evidence ?? "")
        }
      ])
    )
  );
  const existingAnimationVerdicts = Array.isArray(state.animation_review?.verdicts)
    ? (state.animation_review.verdicts as Array<Record<string, unknown>>)
    : [];
  const [animationDrafts, setAnimationDrafts] = useState<
    Record<string, { verdict: string; stateSemantics: string; motionContinuity: string; identityConsistency: string }>
  >(
    Object.fromEntries(
      existingAnimationVerdicts.map((item) => [
        String(item.state),
        {
          verdict: String(item.verdict ?? ""),
          stateSemantics: String(item.state_semantics ?? ""),
          motionContinuity: String(item.motion_continuity ?? ""),
          identityConsistency: String(item.identity_consistency ?? "")
        }
      ])
    )
  );
  const runId = state.active_run_id;
  const isV2 = spriteRowsForProject(state) >= 11;
  const directionDone = state.direction_review?.status === "reviewed";
  const blindDone = state.direction_blind?.ok === true;
  const likenessDone = state.likeness?.status === "approved";
  const animationDone = state.animation_review?.status === "approved";
  const traits = Array.isArray(state.identity_profile?.traits)
    ? (state.identity_profile?.traits as Array<Record<string, unknown>>).filter(
        (trait) => Boolean(trait.locked) && ["signature", "important"].includes(String(trait.importance))
      )
    : [];

  const recordDirections = () => {
    if (!runId) return;
    const reviewedDirections = directions.map((direction) => {
      const draft = directionDrafts[direction] ?? { verdict: "", observed: "", reason: "" };
      return {
        direction,
        verdict: draft.verdict,
        observed: draft.observed.trim(),
        reason: draft.reason.trim()
      };
    });
    if (reviewedDirections.some((item) => !item.verdict || !item.observed || !item.reason)) return;
    void runAction(
      "/review/directions",
      {
        run_id: runId,
        reviewer: "human",
        directions: reviewedDirections
      },
      "Direction semantics recorded"
    );
  };

  const updateDirection = (
    direction: string,
    update: Partial<{ verdict: string; observed: string; reason: string }>
  ) => {
    setDirectionDrafts((current) => ({
      ...current,
      [direction]: {
        verdict: current[direction]?.verdict ?? "",
        observed: current[direction]?.observed ?? expectedDirection(direction),
        reason: current[direction]?.reason ?? "",
        ...update
      }
    }));
  };

  const directionReviewComplete = directions.every((direction) => {
    const draft = directionDrafts[direction];
    return Boolean(draft?.verdict && draft.observed.trim() && draft.reason.trim());
  });

  const recordLikeness = () => {
    if (!runId) return;
    const verdicts = traits.map((trait) => {
      const traitId = String(trait.id);
      const draft = likenessDrafts[traitId] ?? { verdict: "", evidence: "" };
      return {
        trait_id: traitId,
        target: "final-atlas",
        verdict: draft.verdict,
        evidence: draft.evidence.trim()
      };
    });
    if (verdicts.some((item) => !item.verdict || !item.evidence)) return;
    void runAction(
      "/review/likeness",
      {
        run_id: runId,
        reviewer: "human",
        verdicts
      },
      "Per-trait source likeness review recorded"
    );
  };

  const likenessComplete = traits.length > 0 && traits.every((trait) => {
    const draft = likenessDrafts[String(trait.id)];
    return Boolean(draft?.verdict && draft.evidence.trim());
  });

  const updateLikeness = (traitId: string, update: Partial<{ verdict: string; evidence: string }>) => {
    setLikenessDrafts((current) => ({
      ...current,
      [traitId]: {
        verdict: current[traitId]?.verdict ?? "",
        evidence: current[traitId]?.evidence ?? "",
        ...update
      }
    }));
  };

  const importBlindReviews = async () => {
    if (!runId || blindFiles.length !== 3) return;
    const reviews = await Promise.all(blindFiles.map(async (file) => JSON.parse(await file.text()) as Record<string, unknown>));
    await runAction(
      "/review/directions/blind-payloads",
      { run_id: runId, reviews },
      "Independent blind reviews validated"
    );
  };

  const updateAnimation = (
    animationState: string,
    update: Partial<{
      verdict: string;
      stateSemantics: string;
      motionContinuity: string;
      identityConsistency: string;
    }>
  ) => {
    setAnimationDrafts((current) => ({
      ...current,
      [animationState]: {
        verdict: current[animationState]?.verdict ?? "",
        stateSemantics: current[animationState]?.stateSemantics ?? "",
        motionContinuity: current[animationState]?.motionContinuity ?? "",
        identityConsistency: current[animationState]?.identityConsistency ?? "",
        ...update
      }
    }));
  };

  const animationReviewComplete = animationStates.every(({ id }) => {
    const draft = animationDrafts[id];
    return Boolean(
      draft?.verdict &&
      draft.stateSemantics.trim() &&
      draft.motionContinuity.trim() &&
      draft.identityConsistency.trim()
    );
  });

  const recordAnimations = () => {
    if (!runId) return;
    const verdicts = animationStates.map(({ id }) => {
      const draft = animationDrafts[id];
      return {
        state: id,
        verdict: draft.verdict,
        state_semantics: draft.stateSemantics.trim(),
        motion_continuity: draft.motionContinuity.trim(),
        identity_consistency: draft.identityConsistency.trim()
      };
    });
    if (!animationReviewComplete) return;
    void runAction(
      "/animation/review",
      { run_id: runId, reviewed_by: "human", verdicts },
      "Nine-state animation correctness review recorded"
    );
  };

  return (
    <section className="quality-gate-actions" aria-label="V2 quality gates">
      {isV2 ? <article className="monitor-card animation-review-card">
        <div className="data-row">
          <span>Nine-state animation correctness</span>
          <StatusBadge severity={animationDone ? "success" : "warning"}>{animationDone ? "Approved" : "Pending"}</StatusBadge>
        </div>
        <p>Play every loop in the State Viewer. Judge what the motion means, whether frames form a coherent cycle, and whether the same animal survives every pose. Timing checks alone cannot pass this gate.</p>
        <div className="animation-verdict-grid">
          {animationStates.map(({ id, label, expected }) => {
            const draft = animationDrafts[id] ?? {
              verdict: "",
              stateSemantics: "",
              motionContinuity: "",
              identityConsistency: ""
            };
            return (
              <fieldset className="animation-verdict" key={id} disabled={animationDone}>
                <legend>
                  {label}
                  <span>{expected}</span>
                </legend>
                <label>
                  Verdict
                  <select value={draft.verdict} onChange={(event) => updateAnimation(id, { verdict: event.target.value })}>
                    <option value="">Choose</option>
                    <option value="pass">Pass</option>
                    <option value="warning">Warning</option>
                    <option value="fail">Fail</option>
                  </select>
                </label>
                <label>
                  State meaning evidence
                  <input
                    value={draft.stateSemantics}
                    onChange={(event) => updateAnimation(id, { stateSemantics: event.target.value })}
                    placeholder="What makes this state read correctly?"
                  />
                </label>
                <label>
                  Motion continuity evidence
                  <input
                    value={draft.motionContinuity}
                    onChange={(event) => updateAnimation(id, { motionContinuity: event.target.value })}
                    placeholder="Describe the ordered motion and loop seam"
                  />
                </label>
                <label>
                  Identity consistency evidence
                  <input
                    value={draft.identityConsistency}
                    onChange={(event) => updateAnimation(id, { identityConsistency: event.target.value })}
                    placeholder="Which identity cues remain stable?"
                  />
                </label>
              </fieldset>
            );
          })}
        </div>
        <Button
          variant="default"
          disabled={!runId || animationDone || !animationReviewComplete}
          onClick={recordAnimations}
        >
          Record nine animation verdicts
        </Button>
      </article> : null}
      {isV2 ? <article className="monitor-card direction-review-card">
        <div className="data-row">
          <span>16-direction semantics</span>
          <StatusBadge severity={directionDone ? "success" : "warning"}>{directionDone ? "Reviewed" : "Pending"}</StatusBadge>
        </div>
        <p>Scrub every clockwise pose. Record what is visible and why; Goodboy does not provide a one-click “pass all” shortcut.</p>
        <div className="direction-verdict-grid">
          {directions.map((direction) => {
            const draft = directionDrafts[direction] ?? {
              verdict: "",
              observed: expectedDirection(direction),
              reason: ""
            };
            return (
              <fieldset className="direction-verdict" key={direction} disabled={directionDone}>
                <legend>
                  {direction}°
                  <span>expected {expectedDirection(direction)}</span>
                </legend>
                <label>
                  Verdict
                  <select
                    value={draft.verdict}
                    onChange={(event) => updateDirection(direction, { verdict: event.target.value })}
                  >
                    <option value="">Choose</option>
                    <option value="pass">Pass</option>
                    <option value="warning">Warning</option>
                    <option value="fail">Fail</option>
                  </select>
                </label>
                <label>
                  Observed direction
                  <input
                    value={draft.observed}
                    onChange={(event) => updateDirection(direction, { observed: event.target.value })}
                  />
                </label>
                <label>
                  Visible evidence
                  <input
                    value={draft.reason}
                    onChange={(event) => updateDirection(direction, { reason: event.target.value })}
                    placeholder="Pose, face, ears, or body cue"
                  />
                </label>
              </fieldset>
            );
          })}
        </div>
        <Button
          variant="default"
          disabled={!runId || directionDone || !directionReviewComplete}
          onClick={recordDirections}
        >
          Record 16 semantic verdicts
        </Button>
      </article> : null}
      {isV2 ? <article className="monitor-card blind-review-card">
        <div className="data-row">
          <span>Independent blind direction check</span>
          <StatusBadge severity={blindDone ? "success" : "warning"}>{blindDone ? "Validated" : "3 reviews required"}</StatusBadge>
        </div>
        <p>Collect three isolated JSON classifications of the unlabeled A/B sheet. Reviewers must not see the hidden answer key.</p>
        <input
          type="file"
          accept="application/json,.json"
          multiple
          aria-label="Three independent blind review JSON files"
          disabled={blindDone}
          onChange={(event) => setBlindFiles(Array.from(event.target.files ?? []))}
        />
        <Button variant="default" disabled={blindDone || !runId || blindFiles.length !== 3} onClick={() => void importBlindReviews()}>
          {blindDone ? "Blind review validated" : `Validate ${blindFiles.length || 0}/3 reviews`}
        </Button>
      </article> : null}
      <article className="monitor-card likeness-review-card">
        <div className="data-row">
          <span>Source likeness</span>
          <StatusBadge severity={likenessDone ? "success" : "warning"}>{likenessDone ? "Approved" : `${traits.length} traits pending`}</StatusBadge>
        </div>
        <p>Compare the likeness sheet with the source photos at normal and small display sizes. Record each trait independently; signature failures must be repaired.</p>
        <div className="likeness-trait-grid">
          {traits.map((trait) => {
            const traitId = String(trait.id);
            const draft = likenessDrafts[traitId] ?? { verdict: "", evidence: "" };
            return (
              <div className="likeness-trait" key={traitId}>
                <label htmlFor={`likeness-${traitId}`}>
                  <strong>{String(trait.category)}</strong>
                  <span>{String(trait.value)}</span>
                </label>
                <select
                  id={`likeness-${traitId}`}
                  value={draft.verdict}
                  onChange={(event) => updateLikeness(traitId, { verdict: event.target.value })}
                  disabled={likenessDone}
                >
                  <option value="">Choose verdict</option>
                  <option value="pass">Pass</option>
                  <option value="warning">Warning</option>
                  <option value="fail">Fail</option>
                  <option value="not_visible">Not visible</option>
                  <option value="uncertain">Uncertain</option>
                </select>
                <input
                  value={draft.evidence}
                  onChange={(event) => updateLikeness(traitId, { evidence: event.target.value })}
                  placeholder="What in the source and final pet supports this verdict?"
                  disabled={likenessDone}
                />
              </div>
            );
          })}
        </div>
        <Button
          variant="default"
          disabled={!runId || !likenessComplete || likenessDone}
          onClick={recordLikeness}
        >
          Record per-trait review
        </Button>
      </article>
    </section>
  );
}
