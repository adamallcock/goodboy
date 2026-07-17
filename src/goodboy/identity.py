"""Source-pet identity, reference coverage, likeness review, and receipts."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat

from .ingest import SOURCE_CARD, load_source_images, save_source_images, sha256_file
from .imageutil import pixel_data
from .jsonio import read_json, write_json
from .project import load_project
from .schemas import (
    IdentityEvidence,
    IdentityProfile,
    IdentityTrait,
    LikenessReport,
    LikenessVerdict,
    ReferenceCoverage,
    SourceCard,
    SourceImage,
    utc_now,
)


REFERENCE_COVERAGE = "identity/reference-coverage.json"
PROVIDER_CONSENT_DIR = "decisions/provider-consent"
IDENTITY_PROFILE = "identity/identity-profile.json"
IDENTITY_ANALYSIS_HANDOFF = "identity/analysis-handoff.json"
IDENTITY_ANALYSIS_PROMPT = "identity/analysis-prompt.md"
IDENTITY_PACK = "identity/identity-pack.json"
IDENTITY_SMALL_PREVIEW = "identity/small-size-preview.png"
LIKELINESS_REPORT = "qa/likeness-report.json"
LIKELINESS_RECEIPT = "qa/likeness-receipt.json"
LIKELINESS_RECEIPT_MD = "qa/likeness-receipt.md"
LIKELINESS_QA_SHEET = "qa/likeness-qa-sheet.png"
IDENTITY_DRIFT = "qa/identity-drift.json"

SOURCE_ROLES = {
    "identity_front",
    "identity_three_quarter",
    "identity_left",
    "identity_right",
    "identity_back",
    "body_proportions",
    "marking_detail",
    "face_detail",
    "tail_detail",
    "accessory_detail",
    "personality_reference",
    "style_only",
    "exclude_from_identity",
}

LEGACY_ROLE_MAP = {
    "primary_reference": ["identity_three_quarter", "body_proportions"],
    "face_reference": ["face_detail", "identity_front"],
    "body_reference": ["body_proportions"],
    "style_reference": ["style_only"],
}

RECOMMENDED_ROLE_GROUPS = {
    "clear face": {"identity_front", "identity_three_quarter", "face_detail"},
    "body proportions": {"body_proportions", "identity_three_quarter", "identity_left", "identity_right"},
    "side or marking detail": {"identity_left", "identity_right", "marking_detail"},
}

TRAIT_FIELDS = [
    ("species", "species", "signature"),
    ("breed_or_type", "breed_or_type", "important"),
    ("age_traits", "age", "important"),
    ("size_traits", "size", "important"),
    ("face_traits", "face", "signature"),
    ("eyes", "eyes", "signature"),
    ("nose", "nose", "important"),
    ("ears", "ears", "signature"),
    ("fur", "coat", "important"),
    ("tail", "tail", "important"),
    ("markings", "markings", "signature"),
    ("props", "accessories", "signature"),
    ("colors", "colors", "important"),
    ("personality", "personality", "supporting"),
]


def normalized_roles(source: SourceImage) -> list[str]:
    roles = [item for item in source.roles if item in SOURCE_ROLES]
    if not roles:
        roles = list(LEGACY_ROLE_MAP.get(source.role, ["identity_three_quarter"]))
    return list(dict.fromkeys(roles))


def source_quality(path: Path) -> dict[str, Any]:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        sample = image.copy()
        sample.thumbnail((512, 512), Image.Resampling.LANCZOS)
    grayscale = sample.convert("L")
    edge = grayscale.filter(ImageFilter.FIND_EDGES)
    sharpness = float(ImageStat.Stat(edge).var[0])
    brightness = float(ImageStat.Stat(grayscale).mean[0])
    shortest = min(image.size)
    issues: list[str] = []
    if shortest < 256:
        issues.append("low resolution")
    if sharpness < 120:
        issues.append("possibly blurry or low-detail")
    if brightness < 35:
        issues.append("very dark")
    elif brightness > 225:
        issues.append("very bright or washed out")
    return {
        "width": image.width,
        "height": image.height,
        "shortest_edge": shortest,
        "sharpness_advisory": round(sharpness, 2),
        "brightness_advisory": round(brightness, 2),
        "issues": issues,
    }


def analyze_reference_coverage(project_dir: Path, *, persist_sources: bool = True) -> ReferenceCoverage:
    sources = load_source_images(project_dir)
    roles_present: set[str] = set()
    issues: list[dict[str, Any]] = []
    for source in sources:
        source.roles = normalized_roles(source)
        roles_present.update(source.roles)
        source_path = project_dir / source.path
        try:
            quality = source_quality(source_path)
        except (OSError, ValueError) as exc:
            quality = {"issues": [f"could not inspect image: {exc}"]}
        source.quality = quality
        for issue in quality.get("issues", []):
            issues.append({"source_id": source.id, "severity": "warning", "issue": issue})
    missing = [
        label
        for label, accepted_roles in RECOMMENDED_ROLE_GROUPS.items()
        if not roles_present.intersection(accepted_roles)
    ]
    if not sources:
        issues.append({"source_id": None, "severity": "error", "issue": "no source images"})
    if persist_sources and sources:
        save_source_images(project_dir, sources)
    coverage = ReferenceCoverage(
        version="1",
        source_count=len(sources),
        roles_present=sorted(roles_present),
        missing_recommended_roles=missing,
        issues=issues,
        ready_for_identity=bool(sources),
    )
    write_json(project_dir / REFERENCE_COVERAGE, coverage.to_dict())
    return coverage


def assign_source_roles(
    project_dir: Path,
    *,
    source_id: str,
    roles: list[str],
    provider_permissions: dict[str, bool] | None = None,
) -> SourceImage:
    invalid = sorted(set(roles) - SOURCE_ROLES)
    if invalid:
        raise ValueError(f"unknown source roles: {', '.join(invalid)}")
    sources = load_source_images(project_dir)
    source = next((item for item in sources if item.id == source_id), None)
    if source is None:
        raise ValueError(f"unknown source image `{source_id}`")
    source.roles = list(dict.fromkeys(roles))
    source.role = source.roles[0] if source.roles else "exclude_from_identity"
    if provider_permissions is not None:
        source.provider_permissions = {str(key): bool(value) for key, value in provider_permissions.items()}
    save_source_images(project_dir, sources)
    analyze_reference_coverage(project_dir)
    return source


def create_provider_derivative(project_dir: Path, source: SourceImage) -> Path:
    source_path = project_dir / source.path
    output = project_dir / "sources" / "provider-derivatives" / f"{source.id}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        image.save(output, format="PNG", optimize=True)
    source.provider_derivative_path = str(output.relative_to(project_dir))
    return output


def prepare_provider_derivatives(
    project_dir: Path,
    *,
    provider: str,
    consent: bool,
) -> list[str]:
    project = load_project(project_dir)
    if project.privacy_policy.get("provider_consent_required", True) and not consent:
        raise ValueError("explicit provider consent is required before source images leave the machine")
    sources = load_source_images(project_dir)
    outputs: list[str] = []
    receipt_sources: list[dict[str, Any]] = []
    for source in sources:
        if "exclude_from_identity" in normalized_roles(source):
            continue
        if source.provider_permissions and not source.provider_permissions.get(provider, False):
            continue
        output = create_provider_derivative(project_dir, source)
        relative_output = str(output.relative_to(project_dir))
        source.provider_permissions[provider] = True
        outputs.append(relative_output)
        receipt_sources.append(
            {
                "source_id": source.id,
                "source_sha256": source.sha256,
                "derivative_path": relative_output,
                "derivative_sha256": sha256_file(output),
                "roles": normalized_roles(source),
            }
        )
    save_source_images(project_dir, sources)
    if not outputs:
        raise ValueError(f"no source images are permitted for provider `{provider}`")
    write_json(
        provider_consent_receipt_path(project_dir, provider),
        {
            "schema_version": "1.0",
            "provider": provider,
            "decision": "approved",
            "consent_recorded_at": utc_now(),
            "privacy_policy": project.privacy_policy,
            "source_handling": "EXIF-transposed RGBA PNG derivatives only; originals remain local",
            "sources": receipt_sources,
        },
    )
    return outputs


def provider_consent_receipt_path(project_dir: Path, provider: str) -> Path:
    safe_provider = "".join(character for character in provider if character.isalnum() or character in {"-", "_"})
    if not safe_provider or safe_provider != provider:
        raise ValueError(f"invalid provider id `{provider}`")
    return project_dir / PROVIDER_CONSENT_DIR / f"{safe_provider}.json"


def provider_reference_images(
    project_dir: Path,
    *,
    provider: str,
    max_sources: int = 3,
) -> list[tuple[str, str]]:
    """Return only consented, current, EXIF-stripped provider derivatives."""

    receipt_path = provider_consent_receipt_path(project_dir, provider)
    if not receipt_path.is_file():
        return []
    receipt = read_json(receipt_path)
    if receipt.get("provider") != provider or receipt.get("decision") != "approved":
        return []
    receipt_sources = {
        str(item.get("source_id")): item
        for item in receipt.get("sources", [])
        if isinstance(item, dict)
    }
    sources = [
        source
        for source in load_source_images(project_dir)
        if "style_only" not in normalized_roles(source)
        and "exclude_from_identity" not in normalized_roles(source)
    ]
    ranked = sorted(
        sources,
        key=lambda source: (
            "identity_front" not in normalized_roles(source),
            "identity_three_quarter" not in normalized_roles(source),
            -source.identity_weight,
        ),
    )
    references: list[tuple[str, str]] = []
    for source in ranked:
        entry = receipt_sources.get(source.id)
        if not entry or entry.get("source_sha256") != source.sha256:
            continue
        derivative_path = str(entry.get("derivative_path", ""))
        derivative = project_dir / derivative_path
        if (
            not derivative_path
            or not derivative.is_file()
            or sha256_file(derivative) != entry.get("derivative_sha256")
            or source.provider_derivative_path != derivative_path
            or not source.provider_permissions.get(provider, False)
        ):
            continue
        references.append(
            (
                derivative_path,
                f"consented EXIF-stripped source identity reference: {', '.join(normalized_roles(source))}",
            )
        )
        if len(references) >= max_sources:
            break
    return references


def has_provider_consent(project_dir: Path, provider: str) -> bool:
    return bool(provider_reference_images(project_dir, provider=provider, max_sources=1))


def load_source_card(project_dir: Path) -> SourceCard:
    path = project_dir / SOURCE_CARD
    if not path.is_file():
        return SourceCard(species=load_project(project_dir).species)
    return SourceCard.from_dict(read_json(path))


def evidence_for_category(sources: list[SourceImage], category: str) -> list[IdentityEvidence]:
    preferred_roles = {
        "face": {"face_detail", "identity_front", "identity_three_quarter"},
        "eyes": {"face_detail", "identity_front", "identity_three_quarter"},
        "nose": {"face_detail", "identity_front", "identity_three_quarter"},
        "ears": {"face_detail", "identity_front", "identity_left", "identity_right"},
        "markings": {"marking_detail", "identity_left", "identity_right", "identity_three_quarter"},
        "tail": {"tail_detail", "body_proportions", "identity_left", "identity_right"},
        "accessories": {"accessory_detail", "identity_front", "identity_three_quarter"},
        "size": {"body_proportions"},
        "coat": {"marking_detail", "identity_three_quarter"},
        "colors": {"marking_detail", "identity_three_quarter"},
    }.get(category, set())
    selected = [
        source
        for source in sources
        if preferred_roles.intersection(normalized_roles(source))
        and "exclude_from_identity" not in normalized_roles(source)
    ]
    if not selected:
        selected = [
            source
            for source in sources
            if "style_only" not in normalized_roles(source)
            and "exclude_from_identity" not in normalized_roles(source)
        ]
    return [
        IdentityEvidence(
            source_id=source.id,
            note=f"Reference role: {', '.join(normalized_roles(source))}",
            direct_observation=True,
        )
        for source in selected[:3]
    ]


def next_identity_version(existing: IdentityProfile | None) -> str:
    if existing is None:
        return "1"
    try:
        return str(int(existing.version) + 1)
    except ValueError:
        return f"{existing.version}.1"


def load_identity_profile(project_dir: Path, *, required: bool = False) -> IdentityProfile | None:
    path = project_dir / IDENTITY_PROFILE
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"missing identity profile: {path}")
        return None
    return IdentityProfile.from_dict(read_json(path))


def draft_identity_profile(project_dir: Path, *, replace: bool = False) -> IdentityProfile:
    existing = load_identity_profile(project_dir)
    if existing is not None and not replace:
        return existing
    project = load_project(project_dir)
    sources = load_source_images(project_dir)
    coverage = analyze_reference_coverage(project_dir)
    if not coverage.ready_for_identity:
        raise ValueError("at least one source image is required to draft an identity profile")
    card = load_source_card(project_dir)
    traits: list[IdentityTrait] = []
    for field_name, category, importance in TRAIT_FIELDS:
        value = str(getattr(card, field_name, "") or "").strip()
        if not value:
            continue
        symmetry = "asymmetric" if any(word in value.lower() for word in ("left", "right", "asymmetr")) else "symmetric"
        mirror_policy = "mirror-sensitive" if symmetry == "asymmetric" or category in {"markings", "accessories"} else "mirror-safe"
        traits.append(
            IdentityTrait(
                id=f"{category}.primary",
                category=category,
                value=value,
                importance=importance,
                symmetry=symmetry,
                confidence=0.75,
                locked=importance == "signature",
                mirror_policy=mirror_policy,
                evidence=evidence_for_category(sources, category),
            )
        )
    for index, item in enumerate(card.must_keep):
        if not item.strip() or item.strip().lower() == "preserve identity traits from source images":
            continue
        traits.append(
            IdentityTrait(
                id=f"must_keep.{index + 1}",
                category="must_keep",
                value=item.strip(),
                importance="signature",
                confidence=0.65,
                locked=True,
                mirror_policy="mirror-sensitive" if "side" in item.lower() else "mirror-safe",
                evidence=evidence_for_category(sources, "markings"),
            )
        )
    if not traits:
        traits.append(
            IdentityTrait(
                id="appearance.source",
                category="appearance",
                value="Preserve the specific subject identity shown in the approved source references.",
                importance="signature",
                confidence=0.5,
                locked=True,
                evidence=evidence_for_category(sources, "appearance"),
            )
        )
    profile = IdentityProfile(
        id=f"{project.id}-identity",
        version=next_identity_version(existing),
        pet_id=project.id,
        traits=traits,
        source_image_ids=[source.id for source in sources],
        identity_summary=identity_summary(traits),
        uncertainties=list(card.uncertainties) + [
            f"Missing recommended reference coverage: {item}" for item in coverage.missing_recommended_roles
        ],
    )
    write_json(project_dir / IDENTITY_PROFILE, profile.to_dict())
    card.identity_profile_path = IDENTITY_PROFILE
    write_json(project_dir / SOURCE_CARD, card.to_dict())
    return profile


def identity_summary(traits: list[IdentityTrait]) -> str:
    priority = [trait.value for trait in traits if trait.importance in {"signature", "important"}]
    return "; ".join(priority[:8])


def prepare_identity_analysis_handoff(
    project_dir: Path,
    *,
    provider: str = "codex_builtin",
    provider_consent: bool = False,
) -> dict[str, Any]:
    coverage = analyze_reference_coverage(project_dir)
    if not coverage.ready_for_identity:
        raise ValueError("source images are required before identity analysis")
    inputs = prepare_provider_derivatives(project_dir, provider=provider, consent=provider_consent)
    prompt = (
        "Analyze the attached images as references for one specific pet or mascot. "
        "Return structured JSON only with `traits` and `uncertainties`. Each trait must include "
        "`id`, `category`, `value`, `importance`, `symmetry`, `confidence`, `locked`, "
        "`mirror_policy`, `visibility_policy`, and `evidence`. Evidence entries must name an "
        "attached source id and distinguish direct observation from inference. Cover species/type, "
        "age and size cues, body proportions, face, eyes, nose, ears, coat/material, colors, "
        "distinctive side-specific markings, tail, accessories, and personality cues. For every "
        "side-specific trait, state the pet's anatomical side and the corresponding viewer/screen "
        "side in at least one named source view; explicitly verify the orientation instead of "
        "inferring anatomical left or right from screen position. Do not invent details that are "
        "not visible. Mark ambiguous orientation, lighting-dependent colors, and conflicting photos "
        "as uncertain."
    )
    prompt_path = project_dir / IDENTITY_ANALYSIS_PROMPT
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    handoff = {
        "provider": provider,
        "prompt_path": IDENTITY_ANALYSIS_PROMPT,
        "input_images": inputs,
        "input_image_roles": {
            str(source.provider_derivative_path): normalized_roles(source)
            for source in load_source_images(project_dir)
            if source.provider_derivative_path in inputs
        },
        "expected_output": "identity/analysis-output.json",
        "privacy": {
            "provider_consent": provider_consent,
            "exif_stripped": True,
            "originals_included": False,
        },
        "created_at": utc_now(),
    }
    write_json(project_dir / IDENTITY_ANALYSIS_HANDOFF, handoff)
    return handoff


def import_identity_analysis(project_dir: Path, analysis: dict[str, Any]) -> IdentityProfile:
    traits_raw = analysis.get("traits")
    if not isinstance(traits_raw, list) or not traits_raw:
        raise ValueError("identity analysis must contain a non-empty `traits` list")
    existing = load_identity_profile(project_dir)
    project = load_project(project_dir)
    sources = {source.id for source in load_source_images(project_dir)}
    traits: list[IdentityTrait] = []
    for item in traits_raw:
        if not isinstance(item, dict):
            raise ValueError("every identity trait must be an object")
        trait = IdentityTrait.from_dict(item)
        if trait.importance not in {"signature", "important", "supporting", "uncertain", "ignore"}:
            raise ValueError(f"invalid identity importance `{trait.importance}`")
        if not 0 <= trait.confidence <= 1:
            raise ValueError(f"identity confidence for `{trait.id}` must be between 0 and 1")
        unknown_sources = sorted({evidence.source_id for evidence in trait.evidence} - sources)
        if unknown_sources:
            raise ValueError(f"identity trait `{trait.id}` cites unknown sources: {unknown_sources}")
        traits.append(trait)
    profile = IdentityProfile(
        id=existing.id if existing else f"{project.id}-identity",
        version=next_identity_version(existing),
        pet_id=project.id,
        traits=traits,
        source_image_ids=sorted(sources),
        identity_summary=str(analysis.get("identity_summary") or identity_summary(traits)),
        uncertainties=[str(item) for item in analysis.get("uncertainties", [])],
    )
    write_json(project_dir / IDENTITY_PROFILE, profile.to_dict())
    return profile


def confirm_identity_profile(
    project_dir: Path,
    *,
    confirmed_by: str = "human",
    lock_important: bool = True,
) -> IdentityProfile:
    profile = load_identity_profile(project_dir, required=True)
    assert profile is not None
    if not profile.traits:
        raise ValueError("identity profile has no traits")
    for trait in profile.traits:
        if trait.importance in {"signature", "important"}:
            trait.user_confirmed = True
            if lock_important:
                trait.locked = True
    profile.status = "confirmed"
    profile.confirmed_by = confirmed_by
    profile.confirmed_at = utc_now()
    profile.updated_at = profile.confirmed_at
    write_json(project_dir / IDENTITY_PROFILE, profile.to_dict())
    return profile


def identity_prompt_block(project_dir: Path, *, require_confirmed: bool = True) -> str:
    profile = load_identity_profile(project_dir, required=True)
    assert profile is not None
    if require_confirmed and profile.status != "confirmed":
        raise ValueError("identity profile must be confirmed before generation")
    locked = [
        trait
        for trait in profile.traits
        if trait.locked and trait.importance not in {"ignore", "uncertain"}
    ]
    lines = [
        "IDENTITY CONTRACT — preserve these traits across every pose, direction, and repair:",
        *[
            (
                f"- [{trait.importance}] {trait.id}: {trait.value}; "
                f"symmetry={trait.symmetry}; mirror={trait.mirror_policy}; "
                f"visibility={trait.visibility_policy}"
            )
            for trait in locked
        ],
        "- If a trait is occluded, do not replace it with a contradictory design.",
        "- Preserve anatomical left/right markings when the pet turns; screen direction is not anatomical side.",
    ]
    if profile.uncertainties:
        lines.extend(["UNCERTAINTIES — do not invent certainty:", *[f"- {item}" for item in profile.uncertainties]])
    return "\n".join(lines)


def identity_reference_images(project_dir: Path, *, max_sources: int = 3) -> list[tuple[str, str]]:
    sources = [
        source
        for source in load_source_images(project_dir)
        if "style_only" not in normalized_roles(source)
        and "exclude_from_identity" not in normalized_roles(source)
    ]
    ranked = sorted(
        sources,
        key=lambda source: (
            "identity_front" not in normalized_roles(source),
            "identity_three_quarter" not in normalized_roles(source),
            -source.identity_weight,
        ),
    )
    return [
        (source.path, f"source identity reference: {', '.join(normalized_roles(source))}")
        for source in ranked[:max_sources]
    ]


def create_identity_pack(
    project_dir: Path,
    *,
    run_id: str | None = None,
    baseline_path: str = "character/selected-baseline.png",
) -> dict[str, Any]:
    profile = load_identity_profile(project_dir, required=True)
    assert profile is not None
    baseline = project_dir / baseline_path
    if not baseline.is_file():
        raise FileNotFoundError(f"missing selected baseline: {baseline}")
    with Image.open(baseline) as opened:
        image = opened.convert("RGBA")
        preview = Image.new("RGBA", (96, 104), (0, 0, 0, 0))
        subject = image.copy()
        subject.thumbnail((88, 96), Image.Resampling.LANCZOS)
        preview.alpha_composite(subject, ((96 - subject.width) // 2, (104 - subject.height) // 2))
        preview.save(project_dir / IDENTITY_SMALL_PREVIEW)
    cardinals = None
    if run_id:
        candidate = project_dir / "runs" / run_id / "decoded" / "look-anchors-approved.png"
        if candidate.is_file():
            cardinals = str(candidate.relative_to(project_dir))
    pack = {
        "identity_profile_version": profile.version,
        "status": "awaiting-cardinals" if run_id and not cardinals else "ready-for-review",
        "canonical_base": baseline_path,
        "source_fidelity_identity_anchor": (
            "character/identity-anchor.png"
            if (project_dir / "character" / "identity-anchor.png").is_file()
            else baseline_path
        ),
        "small_size_preview": IDENTITY_SMALL_PREVIEW,
        "cardinal_anchors": cardinals,
        "source_references": [path for path, _role in identity_reference_images(project_dir, max_sources=5)],
        "signature_traits": [
            trait.to_dict() for trait in profile.traits if trait.importance == "signature"
        ],
        "created_at": utc_now(),
    }
    write_json(project_dir / IDENTITY_PACK, pack)
    return pack


def create_likeness_report(
    project_dir: Path,
    *,
    run_id: str,
    target: str = "final-atlas",
) -> LikenessReport:
    profile = load_identity_profile(project_dir, required=True)
    assert profile is not None
    verdicts = [
        LikenessVerdict(
            trait_id=trait.id,
            target=target,
            verdict="pending",
            evidence="Awaiting human or independent vision review.",
        )
        for trait in profile.traits
        if trait.locked and trait.importance not in {"ignore", "uncertain"}
    ]
    drift_path = project_dir / "runs" / run_id / IDENTITY_DRIFT
    report = LikenessReport(
        id=f"{run_id}-likeness",
        run_id=run_id,
        identity_profile_version=profile.version,
        status="awaiting-review",
        verdicts=verdicts,
        advisory_metrics=read_json(drift_path) if drift_path.is_file() else {},
    )
    path = project_dir / "runs" / run_id / LIKELINESS_REPORT
    write_json(path, report.to_dict())
    return report


def record_likeness_review(
    project_dir: Path,
    *,
    run_id: str,
    verdicts: list[dict[str, Any]],
    reviewed_by: str = "human",
    advisory_metrics: dict[str, Any] | None = None,
) -> LikenessReport:
    profile = load_identity_profile(project_dir, required=True)
    assert profile is not None
    traits = {trait.id: trait for trait in profile.traits}
    if not reviewed_by.strip():
        raise ValueError("likeness reviewer is required")
    if advisory_metrics and not advisory_metrics.get("advisory_only", False):
        raise ValueError("automated likeness metrics must be explicitly marked advisory_only")
    parsed: list[LikenessVerdict] = []
    seen_trait_ids: set[str] = set()
    for raw in verdicts:
        verdict = LikenessVerdict.from_dict(raw)
        if verdict.trait_id not in traits:
            raise ValueError(f"likeness verdict cites unknown trait `{verdict.trait_id}`")
        if verdict.trait_id in seen_trait_ids:
            raise ValueError(f"duplicate likeness verdict for `{verdict.trait_id}`")
        seen_trait_ids.add(verdict.trait_id)
        if verdict.verdict not in {"pass", "warning", "fail", "not_visible", "uncertain"}:
            raise ValueError(f"invalid likeness verdict `{verdict.verdict}`")
        if not verdict.evidence.strip():
            raise ValueError(f"likeness verdict for `{verdict.trait_id}` requires evidence")
        parsed.append(verdict)
    reviewed_ids = {item.trait_id for item in parsed}
    required_ids = {
        trait.id
        for trait in profile.traits
        if trait.locked and trait.importance in {"signature", "important"}
    }
    missing = sorted(required_ids - reviewed_ids)
    if missing:
        raise ValueError(f"missing likeness verdicts for locked traits: {', '.join(missing)}")
    signature_failures = [
        verdict.trait_id
        for verdict in parsed
        if traits[verdict.trait_id].importance == "signature"
        and verdict.verdict in {"fail", "not_visible", "uncertain"}
    ]
    warnings = [
        f"{verdict.trait_id}: {verdict.evidence}"
        for verdict in parsed
        if verdict.verdict in {"warning", "uncertain", "not_visible"}
    ]
    report = LikenessReport(
        id=f"{run_id}-likeness",
        run_id=run_id,
        identity_profile_version=profile.version,
        status="failed" if signature_failures else "approved",
        verdicts=parsed,
        signature_failures=signature_failures,
        warnings=warnings,
        advisory_metrics=advisory_metrics or load_identity_drift(project_dir, run_id),
        reviewed_by=reviewed_by,
        reviewed_at=utc_now(),
    )
    write_json(project_dir / "runs" / run_id / LIKELINESS_REPORT, report.to_dict())
    return report


def load_identity_drift(project_dir: Path, run_id: str) -> dict[str, Any]:
    path = project_dir / "runs" / run_id / IDENTITY_DRIFT
    return read_json(path) if path.is_file() else {}


def foreground_signature(image: Image.Image) -> dict[str, Any]:
    rgba = image.convert("RGBA")
    pixels = list(pixel_data(rgba))
    opaque = [(red, green, blue) for red, green, blue, alpha in pixels if alpha > 32]
    if not opaque:
        return {"visible": False, "occupancy": 0.0, "mean_rgb": [0, 0, 0], "bbox_aspect": 0.0}
    bbox = rgba.getbbox()
    assert bbox is not None
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])
    return {
        "visible": True,
        "occupancy": round(len(opaque) / (rgba.width * rgba.height), 4),
        "mean_rgb": [
            round(sum(pixel[index] for pixel in opaque) / len(opaque), 2)
            for index in range(3)
        ],
        "bbox_aspect": round(width / height, 4),
        "bbox": list(bbox),
    }


def identity_drift_metrics(atlas: Image.Image) -> dict[str, Any]:
    """Flag cross-state outliers without claiming to measure source likeness."""

    from statistics import median

    cells: list[dict[str, Any]] = []
    for row in range(11):
        for column in range(8):
            cell = atlas.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208))
            signature = foreground_signature(cell)
            if signature["visible"]:
                cells.append({"row": row, "column": column, **signature})
    if not cells:
        return {
            "schema_version": "1.0",
            "advisory_only": True,
            "ok": False,
            "warnings": ["no visible cells available for identity-drift analysis"],
            "cells": [],
        }
    median_rgb = [
        median(float(cell["mean_rgb"][index]) for cell in cells)
        for index in range(3)
    ]
    median_occupancy = median(float(cell["occupancy"]) for cell in cells)
    median_aspect = median(float(cell["bbox_aspect"]) for cell in cells)
    warnings: list[str] = []
    for cell in cells:
        color_delta = (
            sum(
                (float(cell["mean_rgb"][index]) - median_rgb[index]) ** 2
                for index in range(3)
            )
            ** 0.5
        ) / 441.673
        occupancy_ratio = float(cell["occupancy"]) / max(0.0001, median_occupancy)
        aspect_ratio = float(cell["bbox_aspect"]) / max(0.0001, median_aspect)
        cell["color_delta_from_median"] = round(color_delta, 4)
        cell["occupancy_ratio_to_median"] = round(occupancy_ratio, 4)
        cell["aspect_ratio_to_median"] = round(aspect_ratio, 4)
        if color_delta > 0.22:
            warnings.append(f"row {cell['row']} column {cell['column']} has atypical mean color")
        if occupancy_ratio < 0.45 or occupancy_ratio > 1.8:
            warnings.append(f"row {cell['row']} column {cell['column']} has atypical visible area")
    return {
        "schema_version": "1.0",
        "advisory_only": True,
        "purpose": "flag cross-state consistency outliers; never infer or approve source likeness",
        "ok": True,
        "median_mean_rgb": [round(value, 2) for value in median_rgb],
        "median_occupancy": round(median_occupancy, 4),
        "median_bbox_aspect": round(median_aspect, 4),
        "warnings": warnings,
        "cells": cells,
    }


def create_likeness_review_media(project_dir: Path, *, run_id: str) -> dict[str, Any]:
    """Build the human truth surface and advisory consistency report."""

    run_dir = project_dir / "runs" / run_id
    atlas_path = run_dir / "final" / "spritesheet-v2.webp"
    if not atlas_path.is_file():
        raise FileNotFoundError(f"missing v2 atlas for likeness review: {atlas_path}")
    with Image.open(atlas_path) as opened:
        atlas = opened.convert("RGBA")
    drift = identity_drift_metrics(atlas)
    write_json(run_dir / IDENTITY_DRIFT, drift)

    tiles: list[tuple[str, Image.Image]] = []
    for source in load_source_images(project_dir)[:5]:
        path = project_dir / source.path
        if path.is_file():
            with Image.open(path) as opened:
                tiles.append((f"source {source.id}", opened.convert("RGBA")))
    baseline = project_dir / "character" / "selected-baseline.png"
    identity_anchor = project_dir / "character" / "identity-anchor.png"
    if identity_anchor.is_file():
        with Image.open(identity_anchor) as opened:
            tiles.append(("source-fidelity identity anchor", opened.convert("RGBA")))
    if baseline.is_file():
        with Image.open(baseline) as opened:
            tiles.append(("selected baseline", opened.convert("RGBA")))
    row_labels = [
        "idle",
        "run right",
        "run left",
        "wave",
        "jump",
        "failed",
        "waiting",
        "working",
        "review",
    ]
    for row, label in enumerate(row_labels):
        tiles.append((label, atlas.crop((0, row * 208, 192, (row + 1) * 208))))
    for full_index, direction in zip(
        range(0, 16, 2),
        ["000", "045", "090", "135", "180", "225", "270", "315"],
        strict=True,
    ):
        row = 9 + full_index // 8
        column = full_index % 8
        tiles.append(
            (
                f"look {direction}",
                atlas.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208)),
            )
        )
    tile_width, tile_height = 240, 250
    columns = 5
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(tiles):
        left = (index % columns) * tile_width
        top = (index // columns) * tile_height
        preview = Image.new("RGBA", (220, 210), (246, 247, 249, 255))
        subject = image.copy()
        subject.thumbnail((210, 200), Image.Resampling.LANCZOS)
        preview.alpha_composite(subject, ((220 - subject.width) // 2, (210 - subject.height) // 2))
        sheet.paste(preview.convert("RGB"), (left + 10, top + 8))
        draw.text((left + 12, top + 222), label, fill="black")
    output = run_dir / LIKELINESS_QA_SHEET
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return {
        "qa_sheet": str(output.relative_to(project_dir)),
        "identity_drift": str((run_dir / IDENTITY_DRIFT).relative_to(project_dir)),
        "advisory_only": True,
        "source_tile_count": sum(1 for label, _image in tiles if label.startswith("source ")),
        "animation_tile_count": sum(
            1
            for label, _image in tiles
            if not label.startswith("source ")
            and label not in {"selected baseline", "source-fidelity identity anchor"}
        ),
    }


def load_likeness_report(project_dir: Path, run_id: str) -> LikenessReport | None:
    path = project_dir / "runs" / run_id / LIKELINESS_REPORT
    if not path.is_file():
        return None
    return LikenessReport.from_dict(read_json(path))


def likeness_is_approved(project_dir: Path, run_id: str) -> bool:
    report = load_likeness_report(project_dir, run_id)
    return bool(report and report.status == "approved" and not report.signature_failures)


def write_likeness_receipt(project_dir: Path, *, run_id: str) -> dict[str, Any]:
    profile = load_identity_profile(project_dir, required=True)
    report = load_likeness_report(project_dir, run_id)
    if report is None or report.status != "approved":
        raise ValueError("an approved likeness report is required before writing the receipt")
    assert profile is not None
    project = load_project(project_dir)
    coverage_path = project_dir / REFERENCE_COVERAGE
    coverage = read_json(coverage_path) if coverage_path.is_file() else analyze_reference_coverage(project_dir).to_dict()
    run_dir = project_dir / "runs" / run_id
    jobs_path = run_dir / "generation-jobs.json"
    jobs = read_json(jobs_path).get("jobs", []) if jobs_path.is_file() else []
    selected_path = project_dir / "character" / "selected-candidate.json"
    selected = read_json(selected_path) if selected_path.is_file() else {}
    anchor_path = project_dir / "character" / "identity-anchor.json"
    anchor = read_json(anchor_path) if anchor_path.is_file() else {}
    baseline_decision = {
        key: selected[key]
        for key in (
            "id",
            "evaluation_dimension",
            "style_summary",
            "character_delta",
            "selection_notes",
            "likeness_score",
            "style_score",
            "selected_at",
        )
        if key in selected
    }
    identity_anchor_decision = {
        key: anchor[key]
        for key in (
            "id",
            "variation_id",
            "selection_notes",
            "holistic_gestalt_score",
            "signature_trait_score",
            "small_size_readability_score",
            "overall_identity_score",
            "review_notes",
            "reviewed_by",
            "reviewed_at",
            "selected_at",
            "identity_anchor_image",
        )
        if key in anchor
    }
    pack_path = project_dir / IDENTITY_PACK
    pack = read_json(pack_path) if pack_path.is_file() else {}
    identity_pack_summary = {
        key: pack[key]
        for key in (
            "identity_profile_version",
            "status",
            "canonical_base",
            "source_fidelity_identity_anchor",
            "small_size_preview",
            "cardinal_anchors",
        )
        if key in pack
    }
    identity_pack_summary["signature_trait_ids"] = [
        str(item.get("id"))
        for item in pack.get("signature_traits", [])
        if isinstance(item, dict) and item.get("id")
    ]
    approvals = [
        read_json(path)
        for path in sorted((run_dir / "approvals").glob("*.json"))
    ]
    approved_visual = [
        item
        for item in approvals
        if item.get("decision") == "approved"
        and item.get("artifact") in {"contact-sheet", "final-review"}
    ]
    final_visual_approval = (
        max(approved_visual, key=lambda item: str(item.get("created_at", "")))
        if approved_visual
        else None
    )
    repairs = [
        read_json(path)
        for path in sorted((run_dir / "superseded").glob("*/repair.json"))
    ]
    run_manifest_path = run_dir / "run.json"
    run_lineage = read_json(run_manifest_path) if run_manifest_path.is_file() else {}
    animation_review_path = run_dir / "qa" / "animation-review.json"
    animation_correctness_path = run_dir / "qa" / "animation-correctness.json"
    provider_snapshots: list[dict[str, Any]] = []
    seen_provider_snapshots: set[str] = set()
    for job in jobs:
        snapshot = job.get("provider_snapshot", {})
        if not isinstance(snapshot, dict) or not snapshot:
            continue
        key = str(snapshot.get("sha256") or repr(sorted(snapshot.items())))
        if key in seen_provider_snapshots:
            continue
        seen_provider_snapshots.add(key)
        provider_snapshots.append(snapshot)
    receipt = {
        "pet_id": project.id,
        "goodboy_version": project.goodboy_version,
        "run_id": run_id,
        "contract_id": project.contract_id,
        "contract_version": project.contract_version,
        "backend": {"name": project.backend_name, "version": project.backend_version},
        "identity_profile_version": profile.version,
        "reference_coverage": coverage,
        "confirmed_traits": [
            trait.to_dict() for trait in profile.traits if trait.user_confirmed or trait.locked
        ],
        "verdicts": [item.to_dict() for item in report.verdicts],
        "warnings": report.warnings,
        "advisory_metrics": report.advisory_metrics,
        "baseline_decision": baseline_decision,
        "identity_anchor_decision": identity_anchor_decision,
        "identity_pack": identity_pack_summary,
        "run_lineage": run_lineage,
        "repairs": repairs,
        "approvals": approvals,
        "final_visual_approval": final_visual_approval,
        "provider_snapshots": provider_snapshots,
        "animation_review": (
            read_json(animation_review_path) if animation_review_path.is_file() else None
        ),
        "animation_correctness": (
            read_json(animation_correctness_path)
            if animation_correctness_path.is_file()
            else None
        ),
        "approved_by": report.reviewed_by,
        "approved_at": report.reviewed_at,
        "generated_at": utc_now(),
        "automated_metrics_are_advisory": True,
    }
    receipt_path = run_dir / LIKELINESS_RECEIPT
    write_json(receipt_path, receipt)
    write_likeness_receipt_markdown(run_dir / LIKELINESS_RECEIPT_MD, receipt)
    run_summary_path = run_dir / "run-summary.json"
    if run_summary_path.is_file():
        run_summary = read_json(run_summary_path)
        run_summary["likeness_receipt"] = str(receipt_path.relative_to(project_dir))
        write_json(run_summary_path, run_summary)
    return receipt


def write_likeness_receipt_markdown(path: Path, receipt: dict[str, Any]) -> None:
    baseline = receipt.get("baseline_decision", {})
    anchor = receipt.get("identity_anchor_decision", {})
    approval = receipt.get("final_visual_approval")
    lines = [
        "# Goodboy Likeness Receipt",
        "",
        f"- Pet: `{receipt['pet_id']}`",
        f"- Run: `{receipt['run_id']}`",
        f"- Contract: `{receipt['contract_id']}` `{receipt['contract_version']}`",
        f"- Identity profile: `{receipt['identity_profile_version']}`",
        f"- Reviewed by: `{receipt.get('approved_by') or 'unknown'}`",
        f"- Baseline: `{baseline.get('id', 'not recorded')}`",
        f"- Source-fidelity anchor: `{anchor.get('id', 'not recorded')}`",
        (
            "- Anchor evidence scores: "
            f"gestalt `{anchor.get('holistic_gestalt_score', 'not recorded')}`, "
            f"signature traits `{anchor.get('signature_trait_score', 'not recorded')}`, "
            f"small-size readability `{anchor.get('small_size_readability_score', 'not recorded')}`"
        ),
        f"- Repairs recorded: {len(receipt.get('repairs', []))}",
        f"- Final visual approval: {'recorded' if approval else 'pending'}",
        (
            "- Animation correctness: "
            f"`{(receipt.get('animation_review') or {}).get('status', 'not recorded')}`"
        ),
        "",
        "## Trait Verdicts",
        "",
    ]
    for verdict in receipt.get("verdicts", []):
        lines.append(
            f"- `{verdict.get('trait_id', 'unknown')}`: "
            f"**{verdict.get('verdict', 'unknown')}** — "
            f"{verdict.get('evidence', 'No evidence recorded.')}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Human trait verdicts are the approval evidence. Automated color, "
            "occupancy, and silhouette signals are advisory only and do not "
            "establish source likeness.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def apply_identity_trait_patch(
    project_dir: Path,
    *,
    trait_id: str,
    value: str,
    reason: str,
    author: str = "human",
) -> IdentityProfile:
    current = load_identity_profile(project_dir, required=True)
    assert current is not None
    profile = IdentityProfile.from_dict(current.to_dict())
    trait = next((item for item in profile.traits if item.id == trait_id), None)
    if trait is None:
        raise ValueError(f"unknown identity trait `{trait_id}`")
    old_value = trait.value
    trait.value = value.strip()
    trait.user_confirmed = True
    trait.locked = True
    profile.version = next_identity_version(current)
    profile.status = "confirmed"
    profile.updated_at = utc_now()
    write_json(project_dir / "identity" / "history" / f"identity-v{current.version}.json", current.to_dict())
    write_json(project_dir / IDENTITY_PROFILE, profile.to_dict())
    write_json(
        project_dir / "identity" / "patches" / f"{profile.version}-{trait_id.replace('.', '-')}.json",
        {
            "trait_id": trait_id,
            "old_value": old_value,
            "new_value": trait.value,
            "reason": reason,
            "author": author,
            "created_at": profile.updated_at,
        },
    )
    return profile


def source_contact_sheet(project_dir: Path, output: Path | None = None) -> Path:
    sources = load_source_images(project_dir)
    if not sources:
        raise ValueError("no sources available")
    tile_w, tile_h = 280, 260
    columns = min(3, len(sources))
    rows = (len(sources) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_w, rows * tile_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, source in enumerate(sources):
        left = (index % columns) * tile_w
        top = (index // columns) * tile_h
        with Image.open(project_dir / source.path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGBA")
            image.thumbnail((tile_w - 24, tile_h - 54), Image.Resampling.LANCZOS)
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            sheet.paste(background, (left + (tile_w - image.width) // 2, top + 8))
        draw.text((left + 8, top + tile_h - 40), source.id, fill="black")
        draw.text((left + 8, top + tile_h - 22), ", ".join(normalized_roles(source))[:44], fill=(70, 70, 70))
    target = output or project_dir / "identity" / "source-contact-sheet.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)
    return target


def identity_profile_hash(profile: IdentityProfile) -> str:
    payload = repr(profile.to_dict()).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def copy_identity_artifacts_for_run(project_dir: Path, run_id: str) -> None:
    run_identity = project_dir / "runs" / run_id / "identity"
    run_identity.mkdir(parents=True, exist_ok=True)
    for relative in (IDENTITY_PROFILE, REFERENCE_COVERAGE, IDENTITY_PACK):
        source = project_dir / relative
        if source.is_file():
            shutil.copy2(source, run_identity / source.name)
    source_contact_sheet(project_dir, run_identity / "source-contact-sheet.png")
