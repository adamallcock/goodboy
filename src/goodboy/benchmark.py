"""Blinded, identity-clustered Goodboy versus Hatch Pet benchmark tooling."""

from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import NormalDist
from typing import Any

from .ingest import sha256_file
from .jsonio import append_jsonl, read_json, read_jsonl, write_json
from .schemas import utc_now
from .v2_backend import validate_v2_package


BENCHMARK_MANIFEST = "benchmark.json"
ANSWER_KEY = "private/answer-key.json"
RATINGS = "private/ratings.jsonl"
RESULTS = "results.json"
PROTOCOL_LOCK = "private/protocol-lock.json"
VALID_CHOICES = {"A", "B", "tie"}
QUESTIONS = (
    "likeness",
    "identity_consistency",
    "visual_appeal",
    "animation_clarity",
    "state_semantics",
    "motion_continuity",
    "direction_correctness",
)
ANIMATION_QUESTIONS = (
    "animation_clarity",
    "state_semantics",
    "motion_continuity",
    "direction_correctness",
)
REQUIRED_ANIMATION_STATES = (
    "idle",
    "running-right",
    "running-left",
    "waving",
    "jumping",
    "failed",
    "waiting",
    "running",
    "review",
)


def initialize_benchmark(
    benchmark_dir: Path,
    *,
    benchmark_id: str,
    seed: str,
    release_min_identities: int = 30,
    min_raters_per_identity: int = 3,
) -> dict[str, Any]:
    if not benchmark_id.strip():
        raise ValueError("benchmark id is required")
    if not seed:
        raise ValueError("benchmark randomization seed is required")
    if release_min_identities < 1:
        raise ValueError("release minimum identities must be positive")
    if min_raters_per_identity < 3:
        raise ValueError("at least three independent raters per identity are required")
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = benchmark_dir / BENCHMARK_MANIFEST
    if manifest_path.exists():
        raise FileExistsError(f"benchmark already exists: {manifest_path}")
    protocol = {
        "schema_version": "1.1",
        "benchmark_id": benchmark_id,
        "status": "frozen",
        "created_at": utc_now(),
        "methods": ["goodboy", "hatch"],
        "primary_question": "likeness",
        "questions": list(QUESTIONS),
        "randomization": "deterministic per-identity A/B assignment",
        "seed_sha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "unit_of_analysis": "identity-level majority after independent blinded ratings",
        "min_raters_per_identity": min_raters_per_identity,
        "release_min_identities": release_min_identities,
        "release_win_rate": 0.65,
        "release_null_rate": 0.5,
        "confidence_level": 0.95,
        "validity_parity_tolerance": 0.0,
        "unacceptable_failure_rate_tolerance": 0.0,
        "claim_policy": (
            "Withhold a better-likeness claim unless the predeclared sample, win-rate, "
            "confidence-interval, independently verified v2-validity, unacceptable-failure, "
            "appeal, animation-media, state-semantics, motion-continuity, direction, "
            "and clarity gates all pass."
        ),
        "privacy": {
            "source_images_copied": False,
            "public_repo_safe_by_default": False,
            "instruction": "Keep benchmark directories private unless every input has explicit publication rights.",
        },
        "trials": [],
    }
    write_json(manifest_path, protocol)
    write_json(
        benchmark_dir / PROTOCOL_LOCK,
        {
            "schema_version": "1.0",
            "benchmark_id": benchmark_id,
            "policy_sha256": protocol_policy_sha256(protocol),
            "created_at": utc_now(),
        },
    )
    write_json(
        benchmark_dir / ANSWER_KEY,
        {
            "schema_version": "1.0",
            "benchmark_id": benchmark_id,
            "seed": seed,
            "assignments": [],
            "created_at": utc_now(),
        },
    )
    return protocol


def protocol_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "benchmark_id",
        "status",
        "methods",
        "primary_question",
        "questions",
        "randomization",
        "seed_sha256",
        "unit_of_analysis",
        "min_raters_per_identity",
        "release_min_identities",
        "release_win_rate",
        "release_null_rate",
        "confidence_level",
        "validity_parity_tolerance",
        "unacceptable_failure_rate_tolerance",
        "claim_policy",
    )
    return {key: manifest.get(key) for key in keys}


def protocol_policy_sha256(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        protocol_policy(manifest),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_protocol_lock(benchmark_dir: Path, manifest: dict[str, Any]) -> str:
    lock_path = benchmark_dir / PROTOCOL_LOCK
    if not lock_path.is_file():
        raise ValueError("benchmark protocol lock is missing")
    lock = read_json(lock_path)
    actual = protocol_policy_sha256(manifest)
    if lock.get("benchmark_id") != manifest.get("benchmark_id") or lock.get("policy_sha256") != actual:
        raise ValueError("benchmark policy changed after it was frozen; start a new benchmark")
    return actual


def validate_method_package(raw: dict[str, Any], method: str) -> dict[str, Any]:
    package_text = str(raw.get(f"{method}_package", "")).strip()
    if not package_text:
        return {
            "valid": bool(raw.get(f"{method}_v2_valid", False)),
            "independently_verified": False,
            "evidence": "unverified assertion",
        }
    package_dir = Path(package_text).expanduser().resolve()
    result = validate_v2_package(package_dir)
    hashes: dict[str, str] = {}
    for filename in ("pet.json", "spritesheet.webp"):
        path = package_dir / filename
        if path.is_file():
            hashes[filename] = sha256_file(path)
    return {
        "valid": bool(result["ok"]),
        "independently_verified": True,
        "evidence": {
            "package_dir": str(package_dir),
            "hashes": hashes,
            "errors": result["errors"],
        },
    }


def _media_bundle(raw: dict[str, Any], method: str, primary: Path) -> dict[str, Any]:
    value = raw.get(f"{method}_media", {})
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"{method}_media must be an object")
    media = dict(value)
    media.setdefault("identity", str(primary))
    return media


def _flatten_media(value: Any, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Path]]:
    if isinstance(value, dict):
        flattened: list[tuple[tuple[str, ...], Path]] = []
        for key in sorted(value):
            name = str(key).strip()
            if not name or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in name):
                raise ValueError(f"invalid media key: `{name}`")
            flattened.extend(_flatten_media(value[key], (*prefix, name)))
        return flattened
    if not prefix or not isinstance(value, str) or not value.strip():
        raise ValueError("benchmark media leaves must be non-empty file paths")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"missing benchmark media: {path}")
    return [(prefix, path)]


def _set_nested(target: dict[str, Any], keys: tuple[str, ...], value: Any) -> None:
    cursor = target
    for key in keys[:-1]:
        child = cursor.setdefault(key, {})
        if not isinstance(child, dict):
            raise ValueError(f"benchmark media key collision at `{key}`")
        cursor = child
    cursor[keys[-1]] = value


def _copy_blinded_media(
    *,
    benchmark_dir: Path,
    trial_dir: Path,
    side: str,
    media: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    public: dict[str, Any] = {}
    private: dict[str, Any] = {}
    for keys, source in _flatten_media(media):
        target = trial_dir / side / Path(*keys).with_suffix(source.suffix.lower() or ".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        _set_nested(public, keys, str(target.relative_to(benchmark_dir)))
        _set_nested(
            private,
            keys,
            {"original_path": str(source), "sha256": sha256_file(source)},
        )
    return public, private


def _media_shape(media: dict[str, Any]) -> set[tuple[str, ...]]:
    return {keys for keys, _path in _flatten_media(media)}


def _animation_media_evidence(media: dict[str, Any]) -> dict[str, Any]:
    animations = media.get("animations")
    states = sorted(animations) if isinstance(animations, dict) else []
    missing = sorted(set(REQUIRED_ANIMATION_STATES) - set(states))
    return {
        "complete": not missing
        and "contact_sheet" in media
        and "directions" in media,
        "animation_states": states,
        "missing_animation_states": missing,
        "has_contact_sheet": "contact_sheet" in media,
        "has_directions": "directions" in media,
    }


def prepare_trials(benchmark_dir: Path, comparisons_path: Path) -> dict[str, Any]:
    manifest = read_json(benchmark_dir / BENCHMARK_MANIFEST)
    verify_protocol_lock(benchmark_dir, manifest)
    key_path = benchmark_dir / ANSWER_KEY
    key = read_json(key_path)
    comparisons = read_json(comparisons_path)
    identities = comparisons.get("identities", [])
    if not isinstance(identities, list) or not identities:
        raise ValueError("comparison manifest must contain a non-empty `identities` list")
    seed = str(key["seed"])
    rng = random.Random(seed)
    blinded_dir = benchmark_dir / "blinded"
    blinded_dir.mkdir(parents=True, exist_ok=True)
    trials: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in identities:
        if not isinstance(raw, dict):
            raise ValueError("every comparison identity must be an object")
        identity_id = str(raw.get("identity_id", "")).strip()
        if not identity_id or identity_id in seen:
            raise ValueError(f"identity ids must be non-empty and unique: `{identity_id}`")
        seen.add(identity_id)
        method_paths = {
            "goodboy": Path(str(raw.get("goodboy_output", ""))).expanduser().resolve(),
            "hatch": Path(str(raw.get("hatch_output", ""))).expanduser().resolve(),
        }
        for method, path in method_paths.items():
            if not path.is_file():
                raise FileNotFoundError(f"missing {method} comparison output for `{identity_id}`: {path}")
        method_media = {
            method: _media_bundle(raw, method, method_paths[method])
            for method in ("goodboy", "hatch")
        }
        if _media_shape(method_media["goodboy"]) != _media_shape(method_media["hatch"]):
            raise ValueError(
                f"comparison media must be matched between methods for `{identity_id}`"
            )
        methods = ["goodboy", "hatch"]
        rng.shuffle(methods)
        trial_id = f"trial-{len(trials) + 1:04d}"
        trial_dir = blinded_dir / trial_id
        trial_dir.mkdir(parents=True, exist_ok=False)
        public_outputs: dict[str, str] = {}
        public_media: dict[str, dict[str, Any]] = {}
        private_outputs: dict[str, dict[str, Any]] = {}
        for side, method in zip(("A", "B"), methods, strict=True):
            source = method_paths[method]
            suffix = source.suffix.lower() or ".png"
            target = trial_dir / f"{side}{suffix}"
            shutil.copy2(source, target)
            public_outputs[side] = str(target.relative_to(benchmark_dir))
            private_outputs[side] = {
                "method": method,
                "original_path": str(source),
                "sha256": sha256_file(source),
            }
            blinded_media, private_media = _copy_blinded_media(
                benchmark_dir=benchmark_dir,
                trial_dir=trial_dir,
                side=side,
                media=method_media[method],
            )
            public_media[side] = blinded_media
            private_outputs[side]["media"] = private_media
        trial = {
            "trial_id": trial_id,
            "identity_id": identity_id,
            "outputs": public_outputs,
            "media": public_media,
            "cohort": raw.get("cohort", {}),
            "source_set_id": raw.get("source_set_id"),
            "source_images_included": False,
        }
        assignment = {
            "trial_id": trial_id,
            "identity_id": identity_id,
            "outputs": private_outputs,
            "technical": {
                "goodboy": validate_method_package(raw, "goodboy"),
                "hatch": validate_method_package(raw, "hatch"),
            },
            "provider_budget": raw.get("provider_budget", {}),
            "animation_media": {
                method: _animation_media_evidence(method_media[method])
                for method in ("goodboy", "hatch")
            },
        }
        trials.append(trial)
        assignments.append(assignment)
    manifest["trials"] = trials
    manifest["prepared_at"] = utc_now()
    key["assignments"] = assignments
    key["prepared_at"] = utc_now()
    write_json(benchmark_dir / BENCHMARK_MANIFEST, manifest)
    write_json(key_path, key)
    write_json(
        benchmark_dir / "review-packet.json",
        {
            "benchmark_id": manifest["benchmark_id"],
            "questions": list(manifest.get("questions", QUESTIONS)),
            "instructions": [
                "Review source references separately from this packet.",
                "Do not inspect filenames, metadata, answer keys, or workflow provenance.",
                "Choose A, B, or tie for every question.",
                "Judge likeness from identity images and source references; judge animation questions from the matched contact sheets, direction sheets, and all nine motion previews.",
                "State semantics means each row visibly matches its Codex behavior; motion continuity means no popping, clipping, reversal, or inert duplication; direction correctness means the 16-look loop follows the labeled clockwise directions.",
                "Mark either side unacceptable only for a clear quality failure.",
            ],
            "trials": trials,
        },
    )
    return {"trial_count": len(trials), "review_packet": "review-packet.json"}


def import_ratings(benchmark_dir: Path, ratings_path: Path) -> dict[str, Any]:
    manifest = read_json(benchmark_dir / BENCHMARK_MANIFEST)
    verify_protocol_lock(benchmark_dir, manifest)
    known_trials = {str(item["trial_id"]) for item in manifest.get("trials", [])}
    questions = tuple(str(item) for item in manifest.get("questions", QUESTIONS))
    payload = read_json(ratings_path)
    reviewer_id = str(payload.get("reviewer_id", "")).strip()
    if not reviewer_id:
        raise ValueError("ratings payload requires a non-empty `reviewer_id`")
    ratings = payload.get("ratings", [])
    if not isinstance(ratings, list) or not ratings:
        raise ValueError("ratings payload requires a non-empty `ratings` list")
    existing = read_jsonl(benchmark_dir / RATINGS)
    if any(item.get("reviewer_id") == reviewer_id for item in existing):
        raise ValueError(f"reviewer `{reviewer_id}` has already submitted ratings")
    seen_trials: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in ratings:
        if not isinstance(raw, dict):
            raise ValueError("each rating must be an object")
        trial_id = str(raw.get("trial_id", ""))
        if trial_id not in known_trials or trial_id in seen_trials:
            raise ValueError(f"rating trial must be known and unique: `{trial_id}`")
        seen_trials.add(trial_id)
        item: dict[str, Any] = {"trial_id": trial_id}
        for question in questions:
            choice = str(raw.get(question, ""))
            if choice not in VALID_CHOICES:
                raise ValueError(f"`{question}` for `{trial_id}` must be A, B, or tie")
            item[question] = choice
        unacceptable = raw.get("unacceptable", [])
        if not isinstance(unacceptable, list) or any(side not in {"A", "B"} for side in unacceptable):
            raise ValueError(f"`unacceptable` for `{trial_id}` must be a list containing only A and/or B")
        item["unacceptable"] = sorted(set(unacceptable))
        item["notes"] = str(raw.get("notes", ""))
        normalized.append(item)
    missing = known_trials - seen_trials
    if missing:
        raise ValueError(f"reviewer submission is incomplete; missing trials: {', '.join(sorted(missing))}")
    record = {
        "reviewer_id": reviewer_id,
        "submitted_at": utc_now(),
        "ratings": normalized,
    }
    append_jsonl(benchmark_dir / RATINGS, record)
    return {"reviewer_id": reviewer_id, "ratings_imported": len(normalized)}


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total)
        / denominator
    )
    return (max(0.0, center - radius), min(1.0, center + radius))


def bootstrap_interval(
    values: list[float],
    *,
    iterations: int = 10_000,
    seed: int = 20260716,
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    samples = sorted(
        sum(rng.choice(values) for _ in values) / len(values)
        for _ in range(iterations)
    )
    return (
        samples[max(0, int(iterations * 0.025) - 1)],
        samples[min(iterations - 1, int(iterations * 0.975))],
    )


def method_for_choice(assignment: dict[str, Any], choice: str) -> str:
    if choice == "tie":
        return "tie"
    return str(assignment["outputs"][choice]["method"])


def analyze_benchmark(benchmark_dir: Path) -> dict[str, Any]:
    manifest = read_json(benchmark_dir / BENCHMARK_MANIFEST)
    frozen_policy_hash = verify_protocol_lock(benchmark_dir, manifest)
    key = read_json(benchmark_dir / ANSWER_KEY)
    submissions = read_jsonl(benchmark_dir / RATINGS)
    assignments = {str(item["trial_id"]): item for item in key.get("assignments", [])}
    trials = {str(item["trial_id"]): item for item in manifest.get("trials", [])}
    min_raters = int(manifest["min_raters_per_identity"])
    ratings_by_trial: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for submission in submissions:
        reviewer_id = str(submission.get("reviewer_id", ""))
        for rating in submission.get("ratings", []):
            ratings_by_trial[str(rating["trial_id"])].append(
                {"reviewer_id": reviewer_id, **rating}
            )
    incomplete = [
        trial_id
        for trial_id in trials
        if len({item["reviewer_id"] for item in ratings_by_trial[trial_id]}) < min_raters
    ]
    questions = tuple(str(item) for item in manifest.get("questions", QUESTIONS))
    question_results: dict[str, Any] = {}
    for question in questions:
        identity_scores: list[float] = []
        identity_outcomes: list[dict[str, Any]] = []
        for trial_id, trial in trials.items():
            assignment = assignments.get(trial_id)
            ratings = ratings_by_trial[trial_id]
            if assignment is None or len({item["reviewer_id"] for item in ratings}) < min_raters:
                continue
            methods = [method_for_choice(assignment, str(item[question])) for item in ratings]
            counts = Counter(methods)
            if counts["goodboy"] > counts["hatch"]:
                outcome, score = "goodboy", 1.0
            elif counts["hatch"] > counts["goodboy"]:
                outcome, score = "hatch", 0.0
            else:
                outcome, score = "tie", 0.5
            identity_scores.append(score)
            identity_outcomes.append(
                {
                    "trial_id": trial_id,
                    "identity_id": trial["identity_id"],
                    "outcome": outcome,
                    "votes": dict(counts),
                    "cohort": trial.get("cohort", {}),
                }
            )
        decisive = [score for score in identity_scores if score in {0.0, 1.0}]
        wins = sum(1 for score in decisive if score == 1.0)
        wilson = wilson_interval(wins, len(decisive), float(manifest["confidence_level"]))
        bootstrap = bootstrap_interval(identity_scores)
        question_results[question] = {
            "identity_count": len(identity_scores),
            "decisive_identity_count": len(decisive),
            "goodboy_wins": wins,
            "hatch_wins": len(decisive) - wins,
            "ties": len(identity_scores) - len(decisive),
            "goodboy_decisive_win_rate": round(wins / len(decisive), 4) if decisive else 0.0,
            "goodboy_tie_adjusted_rate": round(sum(identity_scores) / len(identity_scores), 4)
            if identity_scores
            else 0.0,
            "wilson_95": [round(value, 4) for value in wilson],
            "identity_cluster_bootstrap_95": [round(value, 4) for value in bootstrap],
            "identity_outcomes": identity_outcomes,
        }

    unacceptable = Counter()
    for trial_id, ratings in ratings_by_trial.items():
        assignment = assignments.get(trial_id)
        if assignment is None:
            continue
        for rating in ratings:
            for side in rating["unacceptable"]:
                unacceptable[str(assignment["outputs"][side]["method"])] += 1
    technical = [item.get("technical", {}) for item in assignments.values()]
    goodboy_validity = (
        sum(bool(item.get("goodboy", {}).get("valid")) for item in technical) / len(technical)
        if technical
        else 0.0
    )
    hatch_validity = (
        sum(bool(item.get("hatch", {}).get("valid")) for item in technical) / len(technical)
        if technical
        else 0.0
    )
    technical_evidence_complete = bool(technical) and all(
        bool(item.get(method, {}).get("independently_verified"))
        for item in technical
        for method in ("goodboy", "hatch")
    )
    rating_exposures = sum(len(items) for items in ratings_by_trial.values())
    goodboy_unacceptable_rate = (
        unacceptable["goodboy"] / rating_exposures if rating_exposures else 0.0
    )
    hatch_unacceptable_rate = (
        unacceptable["hatch"] / rating_exposures if rating_exposures else 0.0
    )
    primary = question_results.get(str(manifest["primary_question"]), {})
    appeal = question_results.get("visual_appeal", {})
    clarity = question_results.get("animation_clarity", {})
    state_semantics = question_results.get("state_semantics", {})
    motion_continuity = question_results.get("motion_continuity", {})
    direction_correctness = question_results.get("direction_correctness", {})
    animation_media_evidence_complete = bool(assignments) and all(
        bool(item.get("animation_media", {}).get(method, {}).get("complete"))
        for item in assignments.values()
        for method in ("goodboy", "hatch")
    )
    gates = {
        "complete_sample": not incomplete
        and int(primary.get("identity_count", 0)) >= int(manifest["release_min_identities"]),
        "win_rate": float(primary.get("goodboy_decisive_win_rate", 0.0))
        >= float(manifest["release_win_rate"]),
        "confidence_excludes_even": float((primary.get("wilson_95") or [0.0])[0])
        > float(manifest["release_null_rate"]),
        "technical_evidence_complete": technical_evidence_complete,
        "v2_validity_parity": goodboy_validity + float(manifest["validity_parity_tolerance"])
        >= hatch_validity,
        "unacceptable_failure_parity": goodboy_unacceptable_rate
        <= hatch_unacceptable_rate
        + float(manifest["unacceptable_failure_rate_tolerance"]),
        "visual_appeal_not_materially_worse": float(appeal.get("goodboy_tie_adjusted_rate", 0.0))
        >= 0.45,
        "animation_clarity_not_materially_worse": float(clarity.get("goodboy_tie_adjusted_rate", 0.0))
        >= 0.45,
        "animation_media_evidence_complete": animation_media_evidence_complete,
        "state_semantics_not_materially_worse": float(
            state_semantics.get("goodboy_tie_adjusted_rate", 0.0)
        )
        >= 0.45,
        "motion_continuity_not_materially_worse": float(
            motion_continuity.get("goodboy_tie_adjusted_rate", 0.0)
        )
        >= 0.45,
        "direction_correctness_not_materially_worse": float(
            direction_correctness.get("goodboy_tie_adjusted_rate", 0.0)
        )
        >= 0.45,
    }
    result = {
        "schema_version": str(manifest.get("schema_version", "1.1")),
        "benchmark_id": manifest["benchmark_id"],
        "analyzed_at": utc_now(),
        "frozen_policy_sha256": frozen_policy_hash,
        "analysis_manifest_sha256": sha256_file(benchmark_dir / BENCHMARK_MANIFEST),
        "reviewer_count": len(submissions),
        "trial_count": len(trials),
        "incomplete_trials": incomplete,
        "questions": question_results,
        "technical": {
            "goodboy_v2_validity_rate": round(goodboy_validity, 4),
            "hatch_v2_validity_rate": round(hatch_validity, 4),
            "independent_package_evidence_complete": technical_evidence_complete,
            "unacceptable_rating_counts": dict(unacceptable),
            "goodboy_unacceptable_rating_rate": round(goodboy_unacceptable_rate, 4),
            "hatch_unacceptable_rating_rate": round(hatch_unacceptable_rate, 4),
            "animation_media_evidence_complete": animation_media_evidence_complete,
        },
        "release_gates": gates,
        "better_likeness_claim_allowed": all(gates.values()),
        "claim": (
            "The predeclared evidence permits a better source-likeness claim."
            if all(gates.values())
            else "WITHHELD: the predeclared evidence does not permit a better source-likeness claim."
        ),
    }
    write_json(benchmark_dir / RESULTS, result)
    write_benchmark_summary(benchmark_dir, result)
    return result


def write_benchmark_summary(benchmark_dir: Path, result: dict[str, Any]) -> Path:
    primary = result["questions"].get("likeness", {})
    output = benchmark_dir / f"{date.today().isoformat()}-benchmark-report.md"
    gates = "\n".join(
        f"- {'PASS' if passed else 'FAIL'}: `{name}`"
        for name, passed in result["release_gates"].items()
    )
    animation_lines = "\n".join(
        f"- {question.replace('_', ' ').title()}: "
        f"{result['questions'].get(question, {}).get('goodboy_tie_adjusted_rate', 0):.1%} Goodboy tie-adjusted rate"
        for question in ANIMATION_QUESTIONS
    )
    output.write_text(
        (
            "---\n"
            f"title: {result['benchmark_id']} Benchmark Report\n"
            f"date: {date.today().isoformat()}\n"
            "type: report\n"
            "status: complete\n"
            "---\n\n"
            f"# {result['benchmark_id']} Benchmark Report\n\n"
            f"**Claim status:** {result['claim']}\n\n"
            f"- Identities analyzed: {primary.get('identity_count', 0)}\n"
            f"- Goodboy decisive likeness win rate: {primary.get('goodboy_decisive_win_rate', 0):.1%}\n"
            f"- Wilson 95% interval: {primary.get('wilson_95', [0, 0])}\n"
            f"- Identity-cluster bootstrap 95% interval: {primary.get('identity_cluster_bootstrap_95', [0, 0])}\n\n"
            "## Animation Correctness\n\n"
            f"{animation_lines}\n\n"
            "## Predeclared Gates\n\n"
            f"{gates}\n\n"
            "Automated and aggregate results do not replace inspection of failure clusters. "
            "Source material and the private answer key are intentionally excluded from this report.\n"
        ),
        encoding="utf-8",
    )
    return output
