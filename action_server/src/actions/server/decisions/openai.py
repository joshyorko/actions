"""Native /v1/decisions REST adapter. No retries, redirects or provider fallback."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable
from typing import Literal

import requests
from pydantic import Field

from .models import Answer, DecisionInput, ProviderResult, Usage, Value


class ProviderFailure(RuntimeError):
    """Sanitized failure code; never includes request, credentials or remote text."""


class HostedPolicy(Value):
    enabled: bool = False
    secret_ref: str = Field(min_length=1, max_length=128)
    model: Literal["gpt-6-luna"] = "gpt-6-luna"
    project_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    max_input_bytes: int = Field(default=16384, ge=1, le=65536)
    timeout_seconds: int = Field(default=10, ge=1, le=30)
    max_response_bytes: int = Field(default=65536, ge=1, le=262144)


class OpenAIDecisionsProvider:
    identity = "openai-decisions/rest-v1/gpt-6-luna"

    def __init__(
        self, policy: HostedPolicy, resolve_secret: Callable[[str], str | None]
    ):
        self.policy = HostedPolicy.model_validate(policy)
        self.identity = type(self).identity
        if self.policy.project_id is not None:
            self.identity += (
                "/project-"
                + hashlib.sha256(self.policy.project_id.encode()).hexdigest()
            )
        self.resolve_secret = resolve_secret
        self._active = threading.Lock()

    @staticmethod
    def serialize(request: DecisionInput) -> dict:
        request = DecisionInput.model_validate(request)
        questions = []
        for question in request.questions:
            item: dict = {
                "name": question.name,
                "type": "predicate" if question.kind == "check" else question.kind,
                "instructions": question.instructions,
            }
            if question.kind == "choice":
                item["choices"] = [o.model_dump() for o in question.options]
            elif question.kind == "score":
                item["levels"] = [
                    {"label": o.value, "description": o.description}
                    for o in question.options
                ]
            questions.append(item)
        return {
            "model": "gpt-6-luna",
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request.evidence}],
                }
            ],
            "questions": questions,
        }

    @staticmethod
    def parse(
        request: DecisionInput, payload: dict, request_id: str | None
    ) -> ProviderResult:
        try:
            if payload["model"] != "gpt-6-luna":
                raise ValueError("unsupported model")
            answers = []
            for raw in payload["answers"]:
                kind = raw["type"]
                if kind == "refusal":
                    raise ProviderFailure("refusal")
                if kind == "predicate":
                    if set(raw) != {"type", "name", "probability"}:
                        raise ValueError("invalid predicate")
                    answer = Answer(
                        name=raw["name"], kind="check", probability=raw["probability"]
                    )
                else:
                    if kind not in ("choice", "score") or set(raw) != {
                        "type",
                        "name",
                        kind,
                        "confidence",
                        "probabilities",
                    }:
                        raise ValueError("invalid answer")
                    answer = Answer.model_validate(
                        {
                            "name": raw["name"],
                            "kind": kind,
                            kind: raw[kind],
                            "confidence": raw["confidence"],
                            "probabilities": tuple(raw["probabilities"]),
                        }
                    )
                answers.append(answer)
            usage = payload["usage"]
            result = ProviderResult(
                answers=tuple(answers),
                model=payload["model"],
                request_id=request_id,
                response_digest="sha256:"
                + hashlib.sha256(
                    json.dumps(
                        payload, sort_keys=True, allow_nan=False, separators=(",", ":")
                    ).encode()
                ).hexdigest(),
                usage=Usage(
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    cached_tokens=usage["input_tokens_details"]["cached_tokens"],
                    cache_write_tokens=usage["input_tokens_details"][
                        "cache_write_tokens"
                    ],
                ),
            )
            result.validate_input(request)
            return result
        except ProviderFailure:
            raise
        except Exception:
            raise ProviderFailure("invalid_response") from None

    def evaluate(self, request: DecisionInput) -> ProviderResult:
        if not self.policy.enabled:
            raise ProviderFailure("egress_disabled")
        body = json.dumps(
            self.serialize(request), ensure_ascii=False, allow_nan=False
        ).encode()
        if len(body) > self.policy.max_input_bytes:
            raise ProviderFailure("input_budget_exceeded")
        if not self._active.acquire(blocking=False):
            raise ProviderFailure("concurrency_budget_exceeded")
        try:
            secret = self.resolve_secret(self.policy.secret_ref)
            if (
                not isinstance(secret, str)
                or not secret
                or "\n" in secret
                or "\r" in secret
            ):
                raise ProviderFailure("credential_unavailable")
            headers = {
                "Authorization": "Bearer " + secret,
                "Content-Type": "application/json",
            }
            if self.policy.project_id is not None:
                headers["OpenAI-Project"] = self.policy.project_id
            deadline = time.monotonic() + self.policy.timeout_seconds
            with requests.Session() as session:
                session.trust_env = False
                with session.post(
                    "https://api.openai.com/v1/decisions",
                    data=body,
                    headers=headers,
                    timeout=min(1, self.policy.timeout_seconds),
                    allow_redirects=False,
                    stream=True,
                ) as response:
                    if response.status_code != 200:
                        code = {
                            401: "authentication_failed",
                            403: "access_denied",
                            429: "throttled_or_credit_exhausted",
                        }.get(response.status_code, "service_unavailable")
                        raise ProviderFailure(code)
                    chunks = bytearray()
                    for chunk in response.iter_content(1):
                        if time.monotonic() >= deadline:
                            raise ProviderFailure("time_budget_exceeded")
                        chunks.extend(chunk)
                        if len(chunks) > self.policy.max_response_bytes:
                            raise ProviderFailure("response_budget_exceeded")
                    return self.parse(
                        request,
                        json.loads(chunks),
                        response.headers.get("x-request-id"),
                    )
        except ProviderFailure:
            raise
        except Exception:
            raise ProviderFailure("service_unavailable") from None
        finally:
            self._active.release()
