"""Provider adapter interface and capability registry."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

from .ingest import sha256_file
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
    ),
}


def list_capabilities() -> list[dict[str, object]]:
    return [capability.to_dict() for capability in CAPABILITY_REGISTRY.values()]


def get_capabilities(adapter_id: str) -> AdapterCapabilities:
    try:
        return CAPABILITY_REGISTRY[adapter_id]
    except KeyError as exc:
        raise ValueError(f"unknown generation adapter: {adapter_id}") from exc


def prepare_handoff(project_dir: Path, run_id: str, job_id: str) -> ProviderInvocation:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    raw_jobs = read_json(jobs_path)["jobs"]
    raw_job = next((item for item in raw_jobs if item["id"] == job_id), None)
    if raw_job is None:
        raise ValueError(f"unknown generation job {job_id} in {jobs_path}")
    job = GenerationJob(**raw_job)
    capabilities = get_capabilities(job.provider)
    prompt_path = project_dir / job.prompt_path
    invocation = ProviderInvocation(
        id=f"handoff-{job.id}",
        adapter=job.provider,
        model=job.model_alias or capabilities.default_model_alias,
        status="prepared",
        prompt_hash=prompt_hash(prompt_path),
        input_image_hashes=[],
        output_paths=[],
        started_at=utc_now(),
        request_metadata={
            "job_id": job.id,
            "kind": job.kind,
            "state": job.state,
            "prompt_path": job.prompt_path,
            "input_images": job.input_images,
            "input_image_roles": job.input_image_roles,
            "expected_output": job.expected_output,
            "capabilities": capabilities.to_dict(),
        },
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
) -> ProviderInvocation:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    job_items = read_json(jobs_path)["jobs"]
    index, raw_job = next(
        ((idx, item) for idx, item in enumerate(job_items) if item["id"] == job_id),
        (None, None),
    )
    if raw_job is None or index is None:
        raise ValueError(f"unknown generation job {job_id} in {jobs_path}")
    job = GenerationJob(**raw_job)
    if job.provider != "openai_images":
        raise ValueError(f"job {job.id} uses provider `{job.provider}`, not `openai_images`")
    prompt_path = project_dir / job.prompt_path
    endpoint = "/v1/images/edits" if job.input_images else "/v1/images/generations"
    invocation = ProviderInvocation(
        id=f"openai-{job.id}",
        adapter="openai_images",
        model=job.model_alias or CAPABILITY_REGISTRY["openai_images"].default_model_alias,
        status="prepared" if dry_run else "running",
        prompt_hash=prompt_hash(prompt_path),
        input_image_hashes=[
            sha256_file(project_dir / input_image)
            for input_image in job.input_images
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
            "input_image_count": len(job.input_images),
        },
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
        mark_job_failed(job_items, index, jobs_path, invocation.error)
        write_json(out_path, invocation.to_dict())
        return invocation

    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        if job.input_images:
            body, content_type = multipart_image_edit_body(
                project_dir=project_dir,
                model=invocation.model,
                prompt=prompt_text,
                image_paths=job.input_images,
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
        response_json = json.loads(response_raw)
        output_rel = job.expected_output
        output_abs = project_dir / output_rel
        output_abs.parent.mkdir(parents=True, exist_ok=True)
        image_base64 = response_json["data"][0]["b64_json"]
        output_abs.write_bytes(base64.b64decode(image_base64))
        raw_response_path = out_dir / f"{invocation.id}.response.json"
        safe_response = dict(response_json)
        write_json(raw_response_path, safe_response)
        invocation.status = "complete"
        invocation.finished_at = utc_now()
        invocation.output_paths = [output_rel]
        invocation.raw_response_path = str(raw_response_path.relative_to(project_dir))
        raw_job["status"] = "complete"
        raw_job["selected_output_path"] = output_rel
        raw_job["provider_invocation_id"] = invocation.id
        job_items[index] = raw_job
        write_json(jobs_path, {"jobs": job_items})
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError, ValueError) as exc:
        invocation.status = "failed"
        invocation.finished_at = utc_now()
        invocation.error = str(exc)
        mark_job_failed(job_items, index, jobs_path, invocation.error)
    write_json(out_path, invocation.to_dict())
    return invocation


def execute_gemini_image_job(
    project_dir: Path,
    run_id: str,
    job_id: str,
    *,
    api_key: str | None = None,
    dry_run: bool = False,
) -> ProviderInvocation:
    jobs_path = project_dir / "runs" / run_id / "generation-jobs.json"
    job_items = read_json(jobs_path)["jobs"]
    index, raw_job = next(
        ((idx, item) for idx, item in enumerate(job_items) if item["id"] == job_id),
        (None, None),
    )
    if raw_job is None or index is None:
        raise ValueError(f"unknown generation job {job_id} in {jobs_path}")
    job = GenerationJob(**raw_job)
    if job.provider not in {"gemini_nano_banana_2", "gemini_nano_banana_pro"}:
        raise ValueError(f"job {job.id} uses provider `{job.provider}`, not a Gemini image adapter")
    prompt_path = project_dir / job.prompt_path
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
            for input_image in job.input_images
            if (project_dir / input_image).is_file()
        ],
        output_paths=[],
        started_at=utc_now(),
        request_metadata={
            "job_id": job.id,
            "endpoint": endpoint,
            "input_image_count": len(job.input_images),
        },
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
        mark_job_failed(job_items, index, jobs_path, invocation.error)
        write_json(out_path, invocation.to_dict())
        return invocation
    try:
        payload = gemini_generate_content_payload(project_dir, prompt_path.read_text(encoding="utf-8"), job.input_images)
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
        response_json = json.loads(response_raw)
        image_base64 = first_gemini_inline_image(response_json)
        if not image_base64:
            raise ValueError("Gemini response did not contain inline image data")
        output_rel = job.expected_output
        output_abs = project_dir / output_rel
        output_abs.parent.mkdir(parents=True, exist_ok=True)
        output_abs.write_bytes(base64.b64decode(image_base64))
        raw_response_path = out_dir / f"{invocation.id}.response.json"
        write_json(raw_response_path, response_json)
        invocation.status = "complete"
        invocation.finished_at = utc_now()
        invocation.output_paths = [output_rel]
        invocation.raw_response_path = str(raw_response_path.relative_to(project_dir))
        raw_job["status"] = "complete"
        raw_job["selected_output_path"] = output_rel
        raw_job["provider_invocation_id"] = invocation.id
        job_items[index] = raw_job
        write_json(jobs_path, {"jobs": job_items})
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError, ValueError) as exc:
        invocation.status = "failed"
        invocation.finished_at = utc_now()
        invocation.error = str(exc)
        mark_job_failed(job_items, index, jobs_path, invocation.error)
    write_json(out_path, invocation.to_dict())
    return invocation


def mark_job_failed(job_items: list[dict[str, object]], index: int, jobs_path: Path, error: str | None) -> None:
    raw_job = dict(job_items[index])
    retry_policy = dict(raw_job.get("retry_policy", {}))
    attempts = int(retry_policy.get("attempts", 0)) + 1
    retry_policy["attempts"] = attempts
    retry_policy["last_error"] = error or "unknown provider failure"
    retry_policy["retry_available"] = attempts < int(retry_policy.get("max_attempts", 1))
    raw_job["retry_policy"] = retry_policy
    raw_job["status"] = "failed"
    raw_job["qa_notes"] = retry_policy["last_error"]
    job_items[index] = raw_job
    write_json(jobs_path, {"jobs": job_items})


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
