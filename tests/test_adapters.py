from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goodboy.adapters import (
    assert_provider_inputs_safe,
    decode_base64_image,
    execute_gemini_image_job,
    execute_openai_image_job,
    first_gemini_inline_image,
    first_openai_image_base64,
    gemini_generate_content_payload,
    get_capabilities,
    list_capabilities,
    multipart_image_edit_body,
    packed_input_images,
    select_provider_for_profile,
)
from goodboy.jobs import load_jobs
from goodboy.project import init_project
from goodboy.schemas import GenerationJob
from goodboy.style import plan_row_generation_jobs, save_default_style_sheet


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object], *, request_id: str = "request-test") -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = {"x-request-id": request_id}

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class ProviderAdapterTests(unittest.TestCase):
    def plan_jobs(self, project_dir: Path, *, run_id: str, provider: str) -> list[GenerationJob]:
        init_project(project_dir, pet_id=f"{run_id}-pet", display_name="Adapter Pet", species="dog")
        save_default_style_sheet(project_dir)
        return plan_row_generation_jobs(
            project_dir=project_dir,
            run_id=run_id,
            provider=provider,
            model_alias=get_capabilities(provider).default_model_alias,
        )

    def test_capability_routing_and_reference_budget_are_deterministic(self) -> None:
        self.assertEqual(len(list_capabilities()), 4)
        self.assertEqual(select_provider_for_profile("best-likeness"), "gemini_nano_banana_pro")
        self.assertEqual(
            select_provider_for_profile("fastest", available=["openai_images", "codex_builtin"]),
            "codex_builtin",
        )
        with self.assertRaisesRegex(ValueError, "unknown generation adapter"):
            get_capabilities("missing")
        with self.assertRaisesRegex(ValueError, "unknown routing profile"):
            select_provider_for_profile("missing")
        with self.assertRaisesRegex(ValueError, "requires an explicit configured provider"):
            select_provider_for_profile("private-local")
        with self.assertRaisesRegex(ValueError, "no provider available"):
            select_provider_for_profile("best-likeness", available=["gemini_nano_banana_2"])

        paths = [f"reference-{index}.png" for index in range(6)]
        roles = {
            paths[0]: "canonical identity reference",
            paths[1]: "approved row-10 anchor reference",
            paths[2]: "signature identity reference",
            paths[3]: "secondary identity reference",
            paths[4]: "layout guide only",
            paths[5]: "secondary identity reference",
        }
        job = GenerationJob(
            id="packed",
            kind="row-strip",
            status="ready",
            provider="gemini_nano_banana_2",
            model_alias="gemini-3.1-flash-image",
            prompt_path="prompt.md",
            input_images=paths,
            input_image_roles=roles,
            expected_output="output.png",
        )
        self.assertEqual(
            packed_input_images(job),
            [paths[0], paths[1], paths[2], paths[4]],
        )

    def test_provider_input_safety_and_payload_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "pet"
            init_project(project_dir, pet_id="safe", display_name="Safe")
            with self.assertRaisesRegex(ValueError, "original source"):
                assert_provider_inputs_safe(
                    project_dir,
                    provider="openai_images",
                    image_paths=["sources/originals/source-001.jpg"],
                )
            with self.assertRaisesRegex(ValueError, "current consent receipt"):
                assert_provider_inputs_safe(
                    project_dir,
                    provider="openai_images",
                    image_paths=["sources/provider-derivatives/openai_images/source-001.png"],
                )

            image = project_dir / "reference.png"
            image.write_bytes(b"image-bytes")
            gemini_payload = gemini_generate_content_payload(
                project_dir,
                "preserve identity",
                ["reference.png"],
            )
            parts = gemini_payload["contents"][0]["parts"]  # type: ignore[index]
            self.assertEqual(parts[0], {"text": "preserve identity"})
            self.assertEqual(base64.b64decode(parts[1]["inline_data"]["data"]), b"image-bytes")

            multipart, content_type = multipart_image_edit_body(
                project_dir=project_dir,
                model="gpt-image-2",
                prompt="preserve identity",
                image_paths=["reference.png"],
                size="1024x1024",
                quality="medium",
                output_format="png",
            )
            self.assertIn(b'image[]"; filename="reference.png"', multipart)
            self.assertIn(b"image-bytes", multipart)
            self.assertIn("boundary=goodboy-openai-boundary", content_type)

            with self.assertRaises(FileNotFoundError):
                gemini_generate_content_payload(project_dir, "prompt", ["missing.png"])
            with self.assertRaises(FileNotFoundError):
                multipart_image_edit_body(
                    project_dir=project_dir,
                    model="gpt-image-2",
                    prompt="prompt",
                    image_paths=["missing.png"],
                    size="1024x1024",
                    quality="medium",
                    output_format="png",
                )

        encoded = base64.b64encode(b"decoded-image").decode("ascii")
        self.assertEqual(first_openai_image_base64({"data": [{"b64_json": encoded}]}), encoded)
        self.assertIsNone(first_openai_image_base64({"data": [{"url": "https://example.invalid"}]}))
        self.assertEqual(
            first_gemini_inline_image(
                {"candidates": [{"content": {"parts": [{"inlineData": {"data": encoded}}]}}]}
            ),
            encoded,
        )
        self.assertIsNone(first_gemini_inline_image({"candidates": [{"content": {"parts": [{"text": "no image"}]}}]}))
        self.assertEqual(decode_base64_image(encoded, provider="Test"), b"decoded-image")
        with self.assertRaisesRegex(ValueError, "invalid base64"):
            decode_base64_image("not-base64!", provider="Test")
        with self.assertRaisesRegex(ValueError, "empty image"):
            decode_base64_image("", provider="Test")

    def test_openai_mocked_success_and_malformed_response_update_job_state(self) -> None:
        encoded = base64.b64encode(b"openai-image").decode("ascii")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "success"
            jobs = self.plan_jobs(project_dir, run_id="openai-success", provider="openai_images")
            response = {
                "data": [{"b64_json": encoded}],
                "usage": {"input_tokens": 12, "output_tokens": 3},
            }
            with patch(
                "goodboy.adapters.urllib.request.urlopen",
                return_value=FakeHTTPResponse(response, request_id="openai-request"),
            ) as urlopen:
                invocation = execute_openai_image_job(
                    project_dir,
                    "openai-success",
                    jobs[0].id,
                    api_key="test-key",
                )
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.openai.com/v1/images/edits")
            self.assertIn("multipart/form-data", request.headers["Content-type"])
            self.assertEqual(invocation.status, "complete")
            self.assertEqual(invocation.request_id, "openai-request")
            self.assertEqual(invocation.usage["input_tokens"], 12)
            self.assertEqual((project_dir / jobs[0].expected_output).read_bytes(), b"openai-image")
            self.assertEqual(load_jobs(project_dir, "openai-success")[0].status, "generated")

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "malformed"
            jobs = self.plan_jobs(project_dir, run_id="openai-malformed", provider="openai_images")
            with patch(
                "goodboy.adapters.urllib.request.urlopen",
                return_value=FakeHTTPResponse({"data": []}),
            ):
                invocation = execute_openai_image_job(
                    project_dir,
                    "openai-malformed",
                    jobs[0].id,
                    api_key="test-key",
                )
            failed_job = load_jobs(project_dir, "openai-malformed")[0]
            self.assertEqual(invocation.status, "failed")
            self.assertIn("did not contain base64 image data", invocation.error or "")
            self.assertEqual(failed_job.status, "failed")
            self.assertEqual(failed_job.retry_policy["attempts"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "missing-input"
            jobs = self.plan_jobs(project_dir, run_id="openai-missing", provider="openai_images")
            (project_dir / jobs[0].input_images[0]).unlink()
            invocation = execute_openai_image_job(
                project_dir,
                "openai-missing",
                jobs[0].id,
                api_key="test-key",
            )
            self.assertEqual(invocation.status, "failed")
            self.assertIn("input image does not exist", invocation.error or "")
            self.assertEqual(load_jobs(project_dir, "openai-missing")[0].status, "failed")
            with self.assertRaisesRegex(ValueError, "is not ready"):
                execute_openai_image_job(
                    project_dir,
                    "openai-missing",
                    jobs[0].id,
                    api_key="test-key",
                    dry_run=True,
                )

    def test_gemini_mocked_success_and_malformed_response_update_job_state(self) -> None:
        encoded = base64.b64encode(b"gemini-image").decode("ascii")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "success"
            jobs = self.plan_jobs(
                project_dir,
                run_id="gemini-success",
                provider="gemini_nano_banana_2",
            )
            response = {
                "candidates": [{"content": {"parts": [{"inlineData": {"data": encoded}}]}}],
                "usageMetadata": {"promptTokenCount": 7},
            }
            with patch(
                "goodboy.adapters.urllib.request.urlopen",
                return_value=FakeHTTPResponse(response, request_id="gemini-request"),
            ) as urlopen:
                invocation = execute_gemini_image_job(
                    project_dir,
                    "gemini-success",
                    jobs[0].id,
                    api_key="test-key",
                )
            request = urlopen.call_args.args[0]
            self.assertIn(":generateContent", request.full_url)
            self.assertEqual(request.headers["X-goog-api-key"], "test-key")
            self.assertEqual(invocation.status, "complete")
            self.assertEqual(invocation.request_id, "gemini-request")
            self.assertEqual(invocation.usage["promptTokenCount"], 7)
            self.assertEqual((project_dir / jobs[0].expected_output).read_bytes(), b"gemini-image")
            self.assertEqual(load_jobs(project_dir, "gemini-success")[0].status, "generated")

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "malformed"
            jobs = self.plan_jobs(
                project_dir,
                run_id="gemini-malformed",
                provider="gemini_nano_banana_2",
            )
            response = {
                "candidates": [{"content": {"parts": [{"text": "no image"}]}}],
            }
            with patch(
                "goodboy.adapters.urllib.request.urlopen",
                return_value=FakeHTTPResponse(response),
            ):
                invocation = execute_gemini_image_job(
                    project_dir,
                    "gemini-malformed",
                    jobs[0].id,
                    api_key="test-key",
                )
            failed_job = load_jobs(project_dir, "gemini-malformed")[0]
            self.assertEqual(invocation.status, "failed")
            self.assertIn("did not contain inline image data", invocation.error or "")
            self.assertEqual(failed_job.status, "failed")
            self.assertEqual(failed_job.retry_policy["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
