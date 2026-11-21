"""Deterministic synthetic document classifier for offline conformance fixtures."""

from __future__ import annotations

import hashlib
import json

from .models import Answer, DecisionInput, OptionProbability, ProviderResult, Usage
from .openai import ProviderFailure


class SyntheticDocumentProvider:
    identity = "synthetic-document/v1"
    model = "synthetic-document/v1"
    categories = ("invoice", "credit_note", "other")

    def evaluate(self, request: DecisionInput) -> ProviderResult:
        request = DecisionInput.model_validate(request)
        try:
            document = json.loads(request.evidence)
            if not isinstance(document, dict) or set(document) != {"document_type"}:
                raise ValueError("synthetic document shape required")
            selected = document["document_type"]
            if selected not in self.categories:
                raise ValueError("synthetic document type required")
            if len(request.questions) != 1:
                raise ValueError("one classifier question required")
            question = request.questions[0]
            if (
                question.kind != "choice"
                or tuple(o.value for o in question.options) != self.categories
            ):
                raise ValueError("synthetic classifier options required")
            answer = Answer(
                name=question.name,
                kind="choice",
                choice=selected,
                confidence=1.0,
                probabilities=tuple(
                    OptionProbability(
                        value=value, probability=1.0 if value == selected else 0.0
                    )
                    for value in self.categories
                ),
            )
            result = ProviderResult(
                answers=(answer,),
                model=self.model,
                response_digest="sha256:"
                + hashlib.sha256(answer.model_dump_json().encode()).hexdigest(),
                request_id=None,
                usage=Usage(input_tokens=0),
            )
            result.validate_input(request)
            return result
        except Exception:
            raise ProviderFailure("invalid_synthetic_input") from None
