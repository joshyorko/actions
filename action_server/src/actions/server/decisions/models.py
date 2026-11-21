"""Versioned, bounded decision contracts. Probabilities never grant authority."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class Value(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )


class Option(Value):
    value: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=512)


class Question(Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: Literal["choice", "check", "score"]
    instructions: str = Field(min_length=1, max_length=2048)
    options: tuple[Option, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def valid_options(self):
        if self.kind == "check":
            if self.options:
                raise ValueError("check does not take options")
        elif not 2 <= len(self.options) <= (10 if self.kind == "score" else 32):
            raise ValueError("bounded options required")
        if len({o.value for o in self.options}) != len(self.options):
            raise ValueError("unique options required")
        return self


class DecisionInput(Value):
    schema_version: Literal["actions.decisions/v1"] = "actions.decisions/v1"
    # Trusted composition supplies only approved extracts, never complete payloads.
    evidence: str = Field(min_length=1, max_length=8192)
    questions: tuple[Question, ...] = Field(min_length=1, max_length=16)
    policy_revision: Digest

    @model_validator(mode="after")
    def unique_names(self):
        if len({q.name for q in self.questions}) != len(self.questions):
            raise ValueError("unique question names required")
        return self


class OptionProbability(Value):
    value: str | int
    probability: Probability
    label: str | None = Field(default=None, max_length=64)


class Answer(Value):
    name: str
    kind: Literal["choice", "check", "score"]
    choice: str | None = None
    probability: Probability | None = None
    score: float | None = Field(default=None, allow_inf_nan=False)
    confidence: Probability | None = None
    probabilities: tuple[OptionProbability, ...] = ()

    def validate_question(self, question: Question) -> None:
        if self.name != question.name or self.kind != question.kind:
            raise ValueError("answer does not match question")
        if self.kind == "check":
            if (
                self.probability is None
                or any(
                    x is not None for x in (self.choice, self.score, self.confidence)
                )
                or self.probabilities
            ):
                raise ValueError("invalid predicate answer")
            return
        if self.confidence is None or self.probability is not None:
            raise ValueError("explicit confidence required")
        expected = (
            tuple(o.value for o in question.options)
            if self.kind == "choice"
            else tuple(range(len(question.options)))
        )
        actual = tuple(p.value for p in self.probabilities)
        if len(actual) != len(expected) or set(actual) != set(expected):
            raise ValueError("complete unique distribution required")
        if not math.isclose(
            sum(p.probability for p in self.probabilities), 1, abs_tol=1e-6
        ):
            raise ValueError("probabilities must sum to one")
        if self.kind == "choice":
            if (
                self.choice not in expected
                or self.score is not None
                or any(p.label is not None for p in self.probabilities)
            ):
                raise ValueError("invalid choice answer")
        else:
            if self.choice is not None or self.score is None:
                raise ValueError("invalid score answer")
            if not 0 <= self.score <= len(question.options) - 1:
                raise ValueError("score outside declared levels")
            for p in self.probabilities:
                if (
                    not isinstance(p.value, int)
                    or p.label != question.options[p.value].value
                ):
                    raise ValueError("invalid score level")
            weighted = sum(int(p.value) * p.probability for p in self.probabilities)
            if not math.isclose(self.score, weighted, abs_tol=1e-6):
                raise ValueError("score differs from distribution")


class Usage(Value):
    input_tokens: int = Field(ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def valid_cache_counts(self):
        if self.cached_tokens + self.cache_write_tokens > self.input_tokens:
            raise ValueError("cache counts exceed input")
        return self


class ProviderResult(Value):
    answers: tuple[Answer, ...]
    model: str = Field(min_length=1, max_length=128)
    response_digest: Digest
    request_id: str | None = Field(default=None, max_length=256)
    usage: Usage

    def validate_input(self, request: DecisionInput) -> None:
        if len(self.answers) != len(request.questions):
            raise ValueError("missing or unexpected answers")
        for answer, question in zip(self.answers, request.questions):
            answer.validate_question(question)
