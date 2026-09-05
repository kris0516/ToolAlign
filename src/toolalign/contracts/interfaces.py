"""Module seams for contracts.v1; no model, executor or evaluator implementation.

Typed records describe call sites. Persisted JSON must additionally pass validate_record.
ValidatedCall is not an authorization token: executors must bind it to their registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict

JSONRecord = dict[str, Any]


class ToolCall(TypedDict):
    call_id: str
    name: str
    arguments: JSONRecord


class Message(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCall]
    tool_call_id: str | None


class ToolSpec(TypedDict):
    schema_version: Literal["toolalign.tool.v1"]
    name: str
    description: str
    parameters_json_schema: JSONRecord
    tool_version: str
    side_effect_class: Literal["read_only", "sandbox_only"]
    timeout_ms: int


class ModelInput(TypedDict):
    messages: list[Message]
    tools: list[ToolSpec]


class Action(TypedDict):
    kind: Literal["tool_calls", "final", "clarify", "refuse"]
    tool_calls: list[ToolCall]
    content: str


@dataclass(frozen=True)
class GenerationConfig:
    seed: int
    temperature: float
    top_p: float
    max_new_tokens: int
    deadline_utc: str
    enable_thinking: Literal[False] = False


@dataclass(frozen=True)
class ModelOutput:
    raw_text: str
    parsed_action: Action | None
    parse_failure: str | None
    model_identity: JSONRecord
    input_tokens: int
    output_tokens: int
    finish_reason: Literal["stop", "length", "timed_out", "cancelled", "error"]


@dataclass(frozen=True)
class ValidatedCall:
    call: ToolCall
    tool_version: str
    registry_hash: str


@dataclass(frozen=True)
class Rejection:
    call_id: str
    code: str
    reason: str


class Cancellation(Protocol):
    def is_cancelled(self) -> bool: ...


@dataclass(frozen=True)
class SandboxContext:
    root: Path
    request_id: str
    deadline_utc: str
    cancellation: Cancellation


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    status: Literal["completed", "rejected", "error", "timed_out", "cancelled"]
    output: Any
    error_code: str | None
    retryable: bool


@dataclass(frozen=True)
class OracleTask:
    task_id: str
    group_id: str
    split: Literal["train", "validation", "test", "ood_test"]
    expected_action: Action
    oracle_payload: JSONRecord


@dataclass(frozen=True)
class TaskScore:
    outcome: Literal["success", "failure", "unknown", "not_scored"]
    reason: str
    oracle_version: str


@dataclass(frozen=True)
class DataManifest:
    immutable_id: str
    sha256: str
    split: Literal["train", "validation", "test", "ood_test"]
    record_count: int
    # Paths and full manifests stay private. ArtifactStore verifies their content.


@dataclass(frozen=True)
class TrainingConfig:
    run_id: str
    mode: Literal["sft", "dpo"]
    backend: str
    model_identity: JSONRecord
    reference_model_hash: str | None
    seed: int
    parameters: JSONRecord
    # Backend-specific parameters are pinned and audited in P01; never executable code.


@dataclass(frozen=True)
class VerifiedArtifact:
    immutable_id: str
    path: Path
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class TrainingArtifact:
    run_manifest: JSONRecord
    checkpoint: VerifiedArtifact


class ModelBackend(Protocol):
    def generate(self, request: ModelInput, generation_config: GenerationConfig) -> ModelOutput: ...


class ToolRegistry(Protocol):
    def validate(self, call: ToolCall) -> ValidatedCall | Rejection: ...


class ToolExecutor(Protocol):
    def execute(
        self, validated_call: ValidatedCall, sandbox_context: SandboxContext
    ) -> ToolResult: ...


class TaskOracle(Protocol):
    def score(
        self, task: OracleTask, trace: list[JSONRecord], final_result: Action | None
    ) -> TaskScore: ...


class TrainingBackend(Protocol):
    def train(self, config: TrainingConfig, data_manifest: DataManifest) -> TrainingArtifact: ...


class ArtifactStore(Protocol):
    def resolve(self, immutable_id: str) -> VerifiedArtifact: ...
