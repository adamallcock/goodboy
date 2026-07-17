"""Provider adapter interface and capability registry."""

from __future__ import annotations

import base64
import binascii
from contextlib import suppress
import hashlib
import json
import mimetypes
import os
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .ingest import sha256_file
from .identity import provider_reference_images
from .jobs import fail_job, transition_job
from .jsonio import read_json, write_json
from .schemas import GenerationJob, ProviderInvocation, utc_now
from .style import prompt_hash


@dataclass(frozen=True)
class AdapterCapabilities:
    id: str
    display_name: str
    text_to_image: bool
    image_to_image: bool
    multi_image_input: bool
    edit_existing_image: bool
    transparent_background: bool
    seed_support: bool
    aspect_ratio_support: bool
    batch_support: bool
    standalone_api: bool
    codex_context_required: bool
    default_model_alias: str
    notes: str = ""
    max_reference_images: int | None = None
    conversational_edits: bool = False
    high_fidelity_inputs: bool = False
    supported_sizes: tuple[str, ...] = ()
    output_formats: tuple[str, ...] = ("png",)
    provider_policy_version: str = "2026-07-16"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class GenerationAdapter(Protocol):
    capabilities: AdapterCapabilities

    def prepare_handoff(self, project_dir: Path, job: GenerationJob) -> ProviderInvocation:
        ...


CAPABILITY_REGISTRY = {
    "codex_builtin": AdapterCapabilities(
        id="codex_builtin",
        display_name="Codex built-in image generation",
        text_to_image=True,
        image_to_image=True,
        multi_image_input=True,
        edit_existing_image=False,
        transparent_background=False,
        seed_support=False,
        aspect_ratio_support=False,
        batch_support=False,
        standalone_api=False,
        codex_context_required=True,
        default_model_alias="codex-imagegen",
        notes="Interactive Codex context adapter; stores handoff manifests rather than calling a standalone SDK.",
        max_reference_images=5,
        conversational_edits=True,
        high_fidelity_inputs=True,
    ),
    "openai_images": AdapterCapabilities(
        id="openai_images",
        display_name="OpenAI Images API",
        text_to_image=True,
        image_to_image=True,
        multi_image_input=True,
        edit_existing_image=True,
        transparent_background=False,
        seed_support=False,
        aspect_ratio_support=True,
        batch_support=True,
        standalone_api=True,
        codex_context_required=False,
        default_model_alias="gpt-image-2",
        notes="Direct Image API adapter. Model, endpoint, size, quality, format, and background are configurable at runtime; chroma-key remains the default until transparent output is confirmed for a selected model.",
        max_reference_images=8,
        conversational_edits=True,
        high_fidelity_inputs=True,
        supported_sizes=("1024x1024", "1536x1024", "1024x1536"),
        output_formats=("png", "webp", "jpeg"),
    ),
    "gemini_nano_banana_2": AdapterCapabilities(
        id="gemini_nano_banana_2",
        display_name="Gemini Nano Banana 2",
        text_to_image=True,
        image_to_image=True,
        multi_image_input=True,
        edit_existing_image=True,
        transparent_background=False,
        seed_support=False,
        aspect_ratio_support=True,
        batch_support=False,
        standalone_api=True,
        codex_context_required=False,
        default_model_alias="gemini-3.1-flash-image",
        notes="Configurable alias for Gemini native image generation, treated as the high-efficiency Nano Banana 2 adapter.",
        max_reference_images=4,
        conversational_edits=True,
        high_fidelity_inputs=True,
    ),
    "gemini_nano_banana_pro": AdapterCapabilities(
        id="gemini_nano_banana_pro",
        display_name="Gemini Nano Banana Pro",
        text_to_image=True,
        image_to_image=True,
        multi_image_input=True,
        edit_existing_image=True,
        transparent_background=False,
        seed_support=False,
        aspect_ratio_support=True,
        batch_support=False,
        standalone_api=True,
        codex_context_required=False,
        default_model_alias="gemini-3-pro-image-preview",
        notes="Configurable alias for Gemini high-fidelity Nano Banana Pro image generation.",
        max_reference_images=5,
        conversational_edits=True,
        high_fidelity_inputs=True,
    ),
}


def list_capabilities() -> list[dict[str, object]]:
    return [capability.to_dict() for capability in CAPABILITY_REGISTRY.values()]


def get_capabilities(adapter_id: str) -> AdapterCapabilities:
    try:
        return CAPABILITY_REGISTRY[adapter_id]
    except KeyError as exc:
        raise ValueError(f"unknown generation adapter: {adapter_id}") from exc


ROUTING_PROFILES = {
    "best-likeness": {
        "preferred": ["gemini_nano_banana_pro", "openai_images", "codex_builtin"],
        "reason": "prioritize multi-reference identity preservation",
    },
    "fastest": {
        "preferred": ["gemini_nano_banana_2", "codex_builtin", "openai_images"],
        "reason": "prioritize low-latency interactive generation",
    },
    "lowest-cost": {
        "preferred": ["codex_builtin", "gemini_nano_banana_2", "openai_images"],
        "reason": "prefer included or efficient generation paths",
    },
    "private-local": {
        "preferred": [],
        "reason": "requires a configured local adapter; external providers are not selected",
    },
    "manual-provider": {
        "preferred": [],
        "reason": "caller selects the provider explicitly",
    },
}


def capability_snapshot(adapter_id: str, *, model_alias: str | None = None) -> dict[str, Any]:
    capabilities = get_capabilities(adapter_id)
    payload: dict[str, Any] = {
        "adapter": adapter_id,
        "model_alias": model_alias or capabilities.default_model_alias,
        "capabilities": capabilities.to_dict(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def select_provider_for_profile(
    routing_profile: str,
    *,
    available: list[str] | None = None,
) -> str:
    if routing_profile not in ROUTING_PROFILES:
        raise ValueError(f"unknown routing profile `{routing_profile}`")
    candidates = set(available or CAPABILITY_REGISTRY)
    for provider in ROUTING_PROFILES[routing_profile]["preferred"]:
        if provider in candidates:
            return provider
    if routing_profile in {"private-local", "manual-provider"}:
        raise ValueError(f"routing profile `{routing_profile}` requires an explicit configured provider")
    raise ValueError(f"no provider available for routing profile `{routing_profile}`")


def packed_input_images(job: GenerationJob) -> list[str]:
    capabilities = get_capabilities(job.provider)
    if capabilities.max_reference_images is None or len(job.input_images) <= capabilities.max_reference_images:
        return list(job.input_images)
    roles = job.input_image_roles

    def priority(path: str) -> tuple[int, int]:
        role = roles.get(path, "").lower()
        if "canonical" in role:
            return (0, job.input_images.index(path))
        if "approved cardinal" in role or ("approved" in role and "anchor" in role) or "continuity" in role:
            return (1, job.input_images.index(path))
        if "signature" in role or "identity reference" in role:
            return (2, job.input_images.index(path))
        if "guide" in role:
            return (3, job.input_images.index(path))
        return (2, job.input_images.index(path))

    selected = sorted(job.input_images, key=priority)[: capabilities.max_reference_images]
    guides = [path for path in job.input_images if "guide" in roles.get(path, "").lower()]
    if guides and not any(path in selected for path in guides):
        selected[-1] = guides[0]
    return selected


def assert_provider_inputs_safe(
    project_dir: Path,
    *,
    provider: str,
    image_paths: list[str],
) -> None:
    consented_derivatives = {
        path
        for path, _role in provider_reference_images(
            project_dir,
            provider=provider,
            max_sources=10_000,
        )
    }
    for image_path in image_paths:
        normalized = Path(image_path).as_posix().lstrip("./")
        if normalized.startswith("sources/originals/"):
            raise ValueError(
                f"provider input `{image_path}` points at an original source; "
                "prepare and use a consented EXIF-stripped derivative"
            )
        if normalized.startswith("sources/provider-derivatives/") and normalized not in consented_derivatives:
            raise ValueError(
                f"provider input `{image_path}` is not covered by a current consent receipt for `{provider}`"
            )


def prepare_handoff(project_dir: Path, run_id: str, job_id: str) -> ProviderInvocation:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    raw_jobs = read_json(jobs_path)["jobs"]
    raw_job = next((item for item in raw_jobs if item["id"] == job_id), None)
    if raw_job is None:
        raise ValueError(f"unknown generation job {job_id} in {jobs_path}")
    job = GenerationJob(**raw_job)
    if job.status != "ready":
        raise ValueError(
            f"generation job {job.id} is not ready (status={job.status}); "
            "complete its dependencies before preparing a provider handoff"
        )
    capabilities = get_capabilities(job.provider)
    packed_inputs = packed_input_images(job)
    packed_roles = {
        image_path: job.input_image_roles[image_path]
        for image_path in packed_inputs
        if image_path in job.input_image_roles
    }
    assert_provider_inputs_safe(project_dir, provider=job.provider, image_paths=packed_inputs)
    snapshot = capability_snapshot(job.provider, model_alias=job.model_alias)
    prompt_path = project_dir / job.prompt_path
    invocation = ProviderInvocation(
        id=f"handoff-{job.id}",
        adapter=job.provider,
        model=job.model_alias or capabilities.default_model_alias,
        status="prepared",
        prompt_hash=prompt_hash(prompt_path),
        input_image_hashes=[
            sha256_file(project_dir / input_image)
            for input_image in packed_inputs
            if (project_dir / input_image).is_file()
        ],
        output_paths=[],
        started_at=utc_now(),
        request_metadata={
            "job_id": job.id,
            "kind": job.kind,
            "state": job.state,
            "prompt_path": job.prompt_path,
            "input_images": packed_inputs,
            "input_image_roles": packed_roles,
            "expected_output": job.expected_output,
            "capabilities": capabilities.to_dict(),
        },
        provider_snapshot=snapshot,
    )
    out = project_dir / "runs" / run_id / "provider-invocations" / f"{invocation.id}.json"
    write_json(out, invocation.to_dict())
    return invocation


def execute_openai_image_job(
    project_dir: Path,
    run_id: str,
    job_id: str,
    *,
    api_key: str | None = None,
    dry_run: bool = False,
    size: str = "1024x1024",
    quality: str = "medium",
    output_format: str = "png",
    routing_profile: str = "manual-provider",
) -> ProviderInvocation:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    job_items = read_json(jobs_path)["jobs"]
    raw_job = next((item for item in job_items if item["id"] == job_id), None)
    if raw_job is None:
        raise ValueError(f"unknown generation job {job_id} in {jobs_path}")
    job = GenerationJob(**raw_job)
    if job.provider != "openai_images":
        raise ValueError(f"job {job.id} uses provider `{job.provider}`, not `openai_images`")
    if job.status != "ready":
        raise ValueError(f"generation job {job.id} is not ready (status={job.status})")
    prompt_path = project_dir / job.prompt_path
    job_inputs = packed_input_images(job)
    assert_provider_inputs_safe(project_dir, provider=job.provider, image_paths=job_inputs)
    endpoint = "/v1/images/edits" if job.input_images else "/v1/images/generations"
    invocation = ProviderInvocation(
        id=f"openai-{job.id}",
        adapter="openai_images",
        model=job.model_alias or CAPABILITY_REGISTRY["openai_images"].default_model_alias,
        status="prepared" if dry_run else "running",
        prompt_hash=prompt_hash(prompt_path),
        input_image_hashes=[
            sha256_file(project_dir / input_image)
            for input_image in job_inputs
            if (project_dir / input_image).is_file()
        ],
        output_paths=[],
        started_at=utc_now(),
        request_metadata={
            "job_id": job.id,
            "endpoint": endpoint,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "input_image_count": len(job_inputs),
        },
        provider_snapshot=capability_snapshot("openai_images", model_alias=job.model_alias),
        routing_profile=routing_profile,
    )
    out_dir = project_dir / "runs" / run_id / "provider-invocations"
    out_path = out_dir / f"{invocation.id}.json"
    if dry_run:
        write_json(out_path, invocation.to_dict())
        return invocation
    resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved_key:
        invocation.status = "failed"
        invocation.finished_at = utc_now()
        invocation.error = "OPENAI_API_KEY is not set"
        fail_job(project_dir, run_id, job.id, reason=invocation.error)
        write_json(out_path, invocation.to_dict())
        return invocation

    try:
        transition_job(
            project_dir,
            run_id,
            job.id,
            "running",
            event="provider-request-started",
            updates={
                "provider_invocation_id": invocation.id,
                "provider_snapshot": invocation.provider_snapshot,
            },
        )
        prompt_text = prompt_path.read_text(encoding="utf-8")
        started = time.monotonic()
        if job_inputs:
            body, content_type = multipart_image_edit_body(
                project_dir=project_dir,
                model=invocation.model,
                prompt=prompt_text,
                image_paths=job_inputs,
                size=size,
                quality=quality,
                output_format=output_format,
            )
            request = urllib.request.Request(
                "https://api.openai.com/v1/images/edits",
                data=body,
                headers={
                    "Authorization": f"Bearer {resolved_key}",
                    "Content-Type": content_type,
                },
                method="POST",
            )
        else:
            payload = {
                "model": invocation.model,
                "prompt": prompt_text,
                "size": size,
                "quality": quality,
                "output_format": output_format,
            }
            request = urllib.request.Request(
                "https://api.openai.com/v1/images/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resolved_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
        with urllib.request.urlopen(request, timeout=180) as response:
            response_raw = response.read().decode("utf-8")
            invocation.request_id = response.headers.get("x-request-id")
        invocation.latency_ms = round((time.monotonic() - started) * 1000)
        response_json = json.loads(response_raw)
        if not isinstance(response_json, dict):
            raise ValueError("OpenAI response was not a JSON object")
        if isinstance(response_json.get("usage"), dict):
            invocation.usage = dict(response_json["usage"])
        output_rel = job.expected_output
        output_abs = project_dir / output_rel
        output_abs.parent.mkdir(parents=True, exist_ok=True)
        image_base64 = first_openai_image_base64(response_json)
        if not image_base64:
            raise ValueError("OpenAI response did not contain base64 image data")
        output_abs.write_bytes(decode_base64_image(image_base64, provider="OpenAI"))
        raw_response_path = out_dir / f"{invocation.id}.response.json"
        safe_response = dict(response_json)
        write_json(raw_response_path, safe_response)
        invocation.status = "complete"
        invocation.finished_at = utc_now()
        invocation.output_paths = [output_rel]
        invocation.raw_response_path = str(raw_response_path.relative_to(project_dir))
        transition_job(
            project_dir,
            run_id,
            job.id,
            "generated",
            event="provider-output-written",
            updates={
                "selected_output_path": output_rel,
                "provider_invocation_id": invocation.id,
                "provider_snapshot": invocation.provider_snapshot,
            },
        )
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        invocation.status = "failed"
        invocation.finished_at = utc_now()
        invocation.error = str(exc)
        with suppress(ValueError):
            fail_job(project_dir, run_id, job.id, reason=invocation.error)
    write_json(out_path, invocation.to_dict())
    return invocation


def execute_gemini_image_job(
    project_dir: Path,
    run_id: str,
    job_id: str,
    *,
    api_key: str | None = None,
    dry_run: bool = False,
    routing_profile: str = "manual-provider",
) -> ProviderInvocation:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    job_items = read_json(jobs_path)["jobs"]
    raw_job = next((item for item in job_items if item["id"] == job_id), None)
    if raw_job is None:
        raise ValueError(f"unknown generation job {job_id} in {jobs_path}")
    job = GenerationJob(**raw_job)
    if job.provider not in {"gemini_nano_banana_2", "gemini_nano_banana_pro"}:
        raise ValueError(f"job {job.id} uses provider `{job.provider}`, not a Gemini image adapter")
    if job.status != "ready":
        raise ValueError(f"generation job {job.id} is not ready (status={job.status})")
    prompt_path = project_dir / job.prompt_path
    job_inputs = packed_input_images(job)
    assert_provider_inputs_safe(project_dir, provider=job.provider, image_paths=job_inputs)
    model = job.model_alias or CAPABILITY_REGISTRY[job.provider].default_model_alias
    endpoint = f"/v1beta/models/{model}:generateContent"
    invocation = ProviderInvocation(
        id=f"gemini-{job.id}",
        adapter=job.provider,
        model=model,
        status="prepared" if dry_run else "running",
        prompt_hash=prompt_hash(prompt_path),
        input_image_hashes=[
            sha256_file(project_dir / input_image)
            for input_image in job_inputs
            if (project_dir / input_image).is_file()
        ],
        output_paths=[],
        started_at=utc_now(),
        request_metadata={
            "job_id": job.id,
            "endpoint": endpoint,
            "input_image_count": len(job_inputs),
        },
        provider_snapshot=capability_snapshot(job.provider, model_alias=model),
        routing_profile=routing_profile,
    )
    out_dir = project_dir / "runs" / run_id / "provider-invocations"
    out_path = out_dir / f"{invocation.id}.json"
    if dry_run:
        write_json(out_path, invocation.to_dict())
        return invocation
    resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not resolved_key:
        invocation.status = "failed"
        invocation.finished_at = utc_now()
        invocation.error = "GEMINI_API_KEY is not set"
        fail_job(project_dir, run_id, job.id, reason=invocation.error)
        write_json(out_path, invocation.to_dict())
        return invocation
    try:
        transition_job(
            project_dir,
            run_id,
            job.id,
            "running",
            event="provider-request-started",
            updates={
                "provider_invocation_id": invocation.id,
                "provider_snapshot": invocation.provider_snapshot,
            },
        )
        payload = gemini_generate_content_payload(project_dir, prompt_path.read_text(encoding="utf-8"), job_inputs)
        started = time.monotonic()
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-goog-api-key": resolved_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            response_raw = response.read().decode("utf-8")
            invocation.request_id = response.headers.get("x-request-id")
        invocation.latency_ms = round((time.monotonic() - started) * 1000)
        response_json = json.loads(response_raw)
        if not isinstance(response_json, dict):
            raise ValueError("Gemini response was not a JSON object")
        usage = response_json.get("usageMetadata")
        if isinstance(usage, dict):
            invocation.usage = dict(usage)
        image_base64 = first_gemini_inline_image(response_json)
        if not image_base64:
            raise ValueError("Gemini response did not contain inline image data")
        output_rel = job.expected_output
        output_abs = project_dir / output_rel
        output_abs.parent.mkdir(parents=True, exist_ok=True)
        output_abs.write_bytes(decode_base64_image(image_base64, provider="Gemini"))
        raw_response_path = out_dir / f"{invocation.id}.response.json"
        write_json(raw_response_path, response_json)
        invocation.status = "complete"
        invocation.finished_at = utc_now()
        invocation.output_paths = [output_rel]
        invocation.raw_response_path = str(raw_response_path.relative_to(project_dir))
        transition_job(
            project_dir,
            run_id,
            job.id,
            "generated",
            event="provider-output-written",
            updates={
                "selected_output_path": output_rel,
                "provider_invocation_id": invocation.id,
                "provider_snapshot": invocation.provider_snapshot,
            },
        )
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        invocation.status = "failed"
        invocation.finished_at = utc_now()
        invocation.error = str(exc)
        with suppress(ValueError):
            fail_job(project_dir, run_id, job.id, reason=invocation.error)
    write_json(out_path, invocation.to_dict())
    return invocation


def first_openai_image_base64(response_json: dict[str, object]) -> str | None:
    data = response_json.get("data")
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("b64_json"), str):
            return item["b64_json"]
    return None


def decode_base64_image(encoded: str, *, provider: str) -> bytes:
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{provider} response contained invalid base64 image data") from exc
    if not decoded:
        raise ValueError(f"{provider} response contained an empty image")
    return decoded


def gemini_generate_content_payload(project_dir: Path, prompt: str, image_paths: list[str]) -> dict[str, object]:
    parts: list[dict[str, object]] = [{"text": prompt}]
    for image_path in image_paths:
        path = project_dir / image_path
        if not path.is_file():
            raise FileNotFoundError(f"Gemini input image does not exist: {path}")
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                }
            }
        )
    return {"contents": [{"parts": parts}]}


def first_gemini_inline_image(response_json: dict[str, object]) -> str | None:
    candidates = response_json.get("candidates")
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData") or part.get("inline_data")
            if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                return inline["data"]
    return None


def multipart_image_edit_body(
    *,
    project_dir: Path,
    model: str,
    prompt: str,
    image_paths: list[str],
    size: str,
    quality: str,
    output_format: str,
) -> tuple[bytes, str]:
    boundary = "goodboy-openai-boundary"
    parts: list[bytes] = []
    for name, value in {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "output_format": output_format,
    }.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    for image_path in image_paths:
        path = project_dir / image_path
        if not path.is_file():
            raise FileNotFoundError(f"OpenAI input image does not exist: {path}")
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="image[]"; filename="{path.name}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8")
            + path.read_bytes()
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
