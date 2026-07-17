"""Manifest dataclasses for the first Goodboy implementation slice."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import DEFAULT_OUTPUT_CONTRACT, ROW_FRAME_COUNTS, STATE_ORDER


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class PetProject:
    id: str
    display_name: str
    species: str = "pet"
    goodboy_version: str = "0.2.0"
    workspace_version: str = "0.2.0"
    workspace_schema_version: str = "0.2"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    active_run_id: str | None = None
    output_contract: dict[str, Any] = field(default_factory=lambda: asdict(DEFAULT_OUTPUT_CONTRACT))
    contract_id: str = DEFAULT_OUTPUT_CONTRACT.contract_id
    contract_version: str = DEFAULT_OUTPUT_CONTRACT.contract_version
    backend_name: str = "hatch-compatible"
    backend_version: str = "codex-bundled-2026-07-16"
    migration_state: str = "current"
    privacy_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "sources_local_by_default": True,
            "strip_exif_for_provider": True,
            "include_sources_in_exports": False,
            "provider_consent_required": True,
        }
    )
    legacy_compat: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PetProject":
        return cls(**raw)


@dataclass
class FrameManifestRow:
    state: str
    frames: int
    method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceImage:
    id: str
    path: str
    sha256: str
    original_filename: str
    mime_type: str
    width: int
    height: int
    role: str = "primary_reference"
    notes: str = ""
    thumbnail_path: str | None = None
    exif: dict[str, Any] = field(default_factory=dict)
    roles: list[str] = field(default_factory=list)
    view: str | None = None
    identity_weight: float = 1.0
    quality: dict[str, Any] = field(default_factory=dict)
    visible_regions: list[str] = field(default_factory=list)
    provider_permissions: dict[str, bool] = field(default_factory=dict)
    provider_derivative_path: str | None = None
    added_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SourceImage":
        migrated = dict(raw)
        if "roles" not in migrated:
            migrated["roles"] = [str(migrated.get("role", "primary_reference"))]
        return cls(**migrated)


@dataclass
class SourceCard:
    species: str = ""
    breed_or_type: str = ""
    age_traits: str = ""
    size_traits: str = ""
    face_traits: str = ""
    eyes: str = ""
    nose: str = ""
    ears: str = ""
    fur: str = ""
    tail: str = ""
    markings: str = ""
    props: str = ""
    colors: str = ""
    personality: str = ""
    must_keep: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    user_notes: str = ""
    source_image_ids: list[str] = field(default_factory=list)
    source_image_paths: list[str] = field(default_factory=list)
    identity_profile_path: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SourceCard":
        return cls(**raw)


@dataclass
class CharacterCard:
    canonical_name: str
    one_sentence_identity: str
    stable_traits: list[str] = field(default_factory=list)
    style: str = "lifelike soft 3D toy / plush-realistic Codex pet"
    material: str = ""
    proportions: str = ""
    facial_expression_range: str = "warm, happy, gentle, expressive"
    palette: str = ""
    props: str = ""
    animation_personality: str = "happy, entertaining, and unobtrusive"
    do_not_change: list[str] = field(default_factory=list)
    provider_notes: dict[str, str] = field(default_factory=dict)
    selected_baseline_image: str | None = None
    identity_anchor_image: str | None = None
    identity_anchor_candidate_id: str | None = None
    identity_profile_version: str | None = None
    likeness_selection_notes: str = ""
    style_selection_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CharacterCard":
        return cls(**raw)


@dataclass
class StyleCandidate:
    id: str
    image_path: str | None
    prompt_path: str
    provider: str
    model: str
    source_images: list[str]
    style_summary: str
    character_delta: str
    provider_invocation_id: str | None = None
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    selected: bool = False
    selection_notes: str = ""
    selected_at: str | None = None
    evaluation_dimension: str = "likeness"
    identity_profile_version: str | None = None
    likeness_score: float | None = None
    style_score: float | None = None
    variation_id: str = ""
    likeness_mode: str = "legacy"
    identity_role: str = "baseline"
    review_image_path: str | None = None
    holistic_gestalt_score: float | None = None
    signature_trait_score: float | None = None
    small_size_readability_score: float | None = None
    overall_identity_score: float | None = None
    review_notes: str = ""
    reviewed_by: str | None = None
    reviewed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmotionStateSpec:
    state: str
    frame_count: int
    purpose: str
    mood: str
    allowed_motion: str
    forbidden_motion: str
    prompt_notes: str
    layout_notes: str
    centering_policy: str = "component-centered"
    baseline_policy: str = "state-specific"
    qa_overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmotionStyleSheet:
    id: str
    base_mood: str
    state_specs: list[EmotionStateSpec]
    global_avoid: list[str]
    prop_policy: str
    effects_policy: str
    background_policy: str
    centering_policy: str
    qa_thresholds: dict[str, Any]
    style_preset: str = "soft-lifelike"
    subject_kind: str = "pet"
    user_style_overrides: list[str] = field(default_factory=list)
    ai_critique_overrides: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state_specs"] = [state.to_dict() for state in self.state_specs]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EmotionStyleSheet":
        raw = dict(raw)
        raw["state_specs"] = [EmotionStateSpec(**item) for item in raw["state_specs"]]
        return cls(**raw)


@dataclass
class GenerationJob:
    id: str
    kind: str
    status: str
    provider: str
    model_alias: str
    prompt_path: str
    input_images: list[str]
    expected_output: str
    state: str | None = None
    input_image_roles: dict[str, str] = field(default_factory=dict)
    retry_policy: dict[str, Any] = field(default_factory=dict)
    selected_output_path: str | None = None
    provider_invocation_id: str | None = None
    qa_notes: str = ""
    depends_on: list[str] = field(default_factory=list)
    attempt: int = 0
    parent_job_id: str | None = None
    input_artifacts: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    required_gates: list[str] = field(default_factory=list)
    invalidates: list[str] = field(default_factory=list)
    ready_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    blocked_reason: str | None = None
    provider_snapshot: dict[str, Any] = field(default_factory=dict)
    identity_profile_version: str | None = None
    packaging_eligible: bool = True
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderInvocation:
    id: str
    adapter: str
    model: str
    status: str
    prompt_hash: str
    input_image_hashes: list[str]
    output_paths: list[str]
    started_at: str
    finished_at: str | None = None
    request_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cost_estimate: str | None = None
    raw_response_path: str | None = None
    provider_snapshot: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    latency_ms: int | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    routing_profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeedbackEvent:
    id: str
    author: str
    target: str
    text: str
    created_at: str = field(default_factory=utc_now)
    creates_branch: str | None = None
    branch_id: str | None = None
    status: str = "open"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FeedbackEvent":
        return cls(**raw)


@dataclass
class ApprovalRecord:
    id: str
    run_id: str
    artifact: str
    decision: str
    notes: str
    created_at: str = field(default_factory=utc_now)
    author: str = "human"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ApprovalRecord":
        return cls(**raw)


@dataclass
class BranchManifest:
    id: str
    parent: str
    target: str
    reason: str
    author: str
    source_event_id: str
    created_at: str = field(default_factory=utc_now)
    status: str = "open"
    artifact_overrides: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "BranchManifest":
        return cls(**raw)


@dataclass
class CritiqueReport:
    id: str
    target: str
    author: str
    findings: list[str]
    recommendations: list[str]
    identity_score: float | None = None
    style_score: float | None = None
    apply_to_style: bool = False
    created_at: str = field(default_factory=utc_now)
    status: str = "open"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CritiqueReport":
        return cls(**raw)


@dataclass
class QAPolicyDecision:
    ok_to_install: bool
    hard_failures: list[str]
    warnings: list[str]
    override_reason: str | None = None
    install_requested: bool = False
    row_provenance: str | None = None
    visual_approval: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ManifestValidationIssue:
    severity: str
    path: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ManifestValidationReport:
    ok: bool
    checked_files: list[str]
    issues: list[ManifestValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [issue.to_dict() for issue in self.issues]
        return data


@dataclass
class FrameManifest:
    chroma_key: dict[str, Any]
    source: str
    rows: list[FrameManifestRow]
    centering_policy: str
    cleanup_policy: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rows"] = [row.to_dict() for row in self.rows]
        return data


@dataclass
class ValidationReport:
    ok: bool
    file: str
    format: str
    mode: str
    width: int
    height: int
    transparent_rgb_residue_pixels: int
    errors: list[str]
    warnings: list[str]
    cells: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QAReport:
    ok: bool
    states: dict[str, dict[str, Any]]
    duplicate_candidates: list[dict[str, Any]]
    green_edge_pixels: int
    visible_pixels: int
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    ok: bool
    version: str
    source_rows: str
    spritesheet: str
    contact_sheet: str
    edge_preview: str
    validation: str
    review: str
    duplicate_audit: str
    package_dir: str | None = None
    contract_id: str = DEFAULT_OUTPUT_CONTRACT.contract_id
    sprite_version_number: int = DEFAULT_OUTPUT_CONTRACT.sprite_version_number
    backend_version: str = "codex-bundled-2026-07-16"
    likeness_receipt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReferenceCoverage:
    version: str
    source_count: int
    roles_present: list[str]
    missing_recommended_roles: list[str]
    issues: list[dict[str, Any]]
    ready_for_identity: bool
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ReferenceCoverage":
        return cls(**raw)


@dataclass
class IdentityEvidence:
    source_id: str
    note: str
    region: str | None = None
    direct_observation: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "IdentityEvidence":
        return cls(**raw)


@dataclass
class IdentityTrait:
    id: str
    category: str
    value: str
    importance: str = "important"
    symmetry: str = "symmetric"
    confidence: float = 0.5
    locked: bool = False
    user_confirmed: bool = False
    mirror_policy: str = "mirror-safe"
    visibility_policy: str = "when-visible"
    evidence: list[IdentityEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = [item.to_dict() for item in self.evidence]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "IdentityTrait":
        migrated = dict(raw)
        migrated["evidence"] = [
            item if isinstance(item, IdentityEvidence) else IdentityEvidence.from_dict(item)
            for item in migrated.get("evidence", [])
        ]
        return cls(**migrated)


@dataclass
class IdentityProfile:
    id: str
    version: str
    pet_id: str
    traits: list[IdentityTrait]
    status: str = "draft"
    source_image_ids: list[str] = field(default_factory=list)
    identity_summary: str = ""
    uncertainties: list[str] = field(default_factory=list)
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["traits"] = [trait.to_dict() for trait in self.traits]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "IdentityProfile":
        migrated = dict(raw)
        migrated["traits"] = [
            item if isinstance(item, IdentityTrait) else IdentityTrait.from_dict(item)
            for item in migrated.get("traits", [])
        ]
        return cls(**migrated)


@dataclass
class LikenessVerdict:
    trait_id: str
    target: str
    verdict: str
    evidence: str
    reviewer: str = "human"
    state: str | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LikenessVerdict":
        return cls(**raw)


@dataclass
class LikenessReport:
    id: str
    run_id: str
    identity_profile_version: str
    status: str
    verdicts: list[LikenessVerdict]
    signature_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    advisory_metrics: dict[str, Any] = field(default_factory=dict)
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["verdicts"] = [item.to_dict() for item in self.verdicts]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LikenessReport":
        migrated = dict(raw)
        migrated["verdicts"] = [
            item if isinstance(item, LikenessVerdict) else LikenessVerdict.from_dict(item)
            for item in migrated.get("verdicts", [])
        ]
        return cls(**migrated)


@dataclass
class JobEvent:
    id: str
    run_id: str
    job_id: str
    event: str
    from_status: str | None
    to_status: str | None
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_frame_manifest(
    source: Path,
    *,
    centering_policy: str,
    cleanup_policy: str,
    chroma_key: dict[str, Any] | None = None,
    row_methods: dict[str, str] | None = None,
) -> FrameManifest:
    return FrameManifest(
        chroma_key=chroma_key or {"hex": "#00ff00", "rgb": [0, 255, 0]},
        source=str(source),
        rows=[
            FrameManifestRow(
                state=state,
                frames=ROW_FRAME_COUNTS[state],
                method=(row_methods or {}).get(state, "components-centered"),
            )
            for state in STATE_ORDER
        ],
        centering_policy=centering_policy,
        cleanup_policy=cleanup_policy,
    )
