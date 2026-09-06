"""Dependency-free invariants used before entering a model backend."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


@dataclass(frozen=True)
class EncodedExample:
    """mask[i] supervises token_ids[i], NOT the logit at input position i."""

    token_ids: tuple[int, ...]
    completion_mask: tuple[int, ...]
    prompt_length: int
    eos_id: int

    def validate(self, limit: int) -> None:
        n = len(self.token_ids)
        if not 0 < self.prompt_length < n <= limit:
            raise ValueError("Invalid prompt boundary or sequence exceeds budget; no truncation")
        expected = (0,) * self.prompt_length + (1,) * (n - self.prompt_length)
        if self.completion_mask != expected:
            raise ValueError("Completion mask is shifted or includes prompt/padding")
        if self.token_ids[-1] != self.eos_id:
            raise ValueError("Completion must end at EOS")
        if any(type(x) is not int or x < 0 for x in self.token_ids):
            raise ValueError("Token IDs must be nonnegative integers")


def padded_batch(
    examples: Iterable[EncodedExample], pad_id: int, limit: int, pad_to: int | None = None
) -> tuple[list[list[int]], list[list[int]]]:
    rows = list(examples)
    if not rows:
        raise ValueError("Empty batch")
    for row in rows:
        row.validate(limit)
    n = pad_to or max(len(row.token_ids) for row in rows)
    if n > limit or n < max(len(row.token_ids) for row in rows):
        raise ValueError("Invalid padding length")
    return (
        [list(row.token_ids) + [pad_id] * (n - len(row.token_ids)) for row in rows],
        [list(row.completion_mask) + [0] * (n - len(row.token_ids)) for row in rows],
    )


def standard_dpo(
    chosen: float, rejected: float, ref_chosen: float, ref_rejected: float, beta: float = 0.1
) -> float:
    if not all(math.isfinite(x) for x in (chosen, rejected, ref_chosen, ref_rejected, beta)):
        raise ValueError("DPO inputs must be finite")
    if beta <= 0:
        raise ValueError("beta must be positive")
    z = -beta * ((chosen - rejected) - (ref_chosen - ref_rejected))
    return max(z, 0.0) + math.log1p(math.exp(-abs(z)))


@dataclass(frozen=True)
class ReferenceIdentity:
    base_hash: str
    adapter_hash: str
    tokenizer_hash: str
    template_hash: str
    quantization: str
    code_hash: str
    stage: str

    def validate(self, *, smoke_only: bool) -> None:
        for value in (
            self.base_hash,
            self.adapter_hash,
            self.tokenizer_hash,
            self.template_hash,
            self.code_hash,
        ):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("Reference must bind actual base, adapter and input identities")
        if self.stage != "accepted_sft" and not (smoke_only and self.stage == "sft_smoke"):
            raise ValueError("Reference is not an accepted SFT checkpoint")

    def cache_key(self, chosen: EncodedExample, rejected: EncodedExample) -> str:
        return digest(
            {"identity": asdict(self), "chosen": asdict(chosen), "rejected": asdict(rejected)}
        )

    def assert_unchanged(self, current: ReferenceIdentity) -> None:
        if self != current:
            raise ValueError("Frozen reference identity changed")


def verify_adapter_metadata(expected: dict, actual: dict) -> None:
    for key in ("rank", "scale", "dropout", "keys", "num_layers"):
        if expected.get(key) != actual.get(key):
            raise ValueError(f"Adapter {key} mismatch")


def verify_reload(expected: list[float], actual: list[float], atol: float) -> float:
    if not expected or len(expected) != len(actual) or not math.isfinite(atol) or atol < 0:
        raise ValueError("Invalid reload comparison")
    if not all(math.isfinite(x) for x in expected + actual):
        raise ValueError("Nonfinite reload output")
    delta = max(abs(a - b) for a, b in zip(expected, actual))
    if delta > atol:
        raise ValueError("Saved/reloaded forward deviates beyond tolerance")
    return delta


@dataclass(frozen=True)
class Budget:
    max_wall_seconds: int = 900
    max_microsteps: int = 32
    max_processed_tokens: int = 65536
    max_mlx_bytes: int = 24 * 1024**3
    max_rss_bytes: int = 30 * 1024**3
    max_swap_growth_bytes: int = 1024**3
    max_disk_bytes: int = 20 * 1024**3

    def validate(self) -> None:
        if any(type(v) is not int or v <= 0 for v in asdict(self).values()):
            raise ValueError("Budgets must be positive integers")
        if self.max_mlx_bytes > 24 * 1024**3 or self.max_rss_bytes > 30 * 1024**3:
            raise ValueError("Budget exceeds P01 memory authorization")
        if self.max_disk_bytes > 20 * 1024**3:
            raise ValueError("Budget exceeds P01 disk authorization")
        if self.max_wall_seconds > 900 or self.max_microsteps > 120:
            raise ValueError("P01 probes cannot become formal long training jobs")
        if self.max_processed_tokens > 524288 or self.max_swap_growth_bytes > 1024**3:
            raise ValueError("Budget exceeds P01 token or swap authorization")

    def check(
        self,
        *,
        wall: float,
        microsteps: int = 0,
        processed_tokens: int = 0,
        mlx_bytes: int = 0,
        rss_bytes: int = 0,
        swap_growth_bytes: int = 0,
        pressure: int = 1,
    ) -> None:
        checks = {
            "wall": (wall, self.max_wall_seconds),
            "microsteps": (microsteps, self.max_microsteps),
            "processed_tokens": (processed_tokens, self.max_processed_tokens),
            "mlx_bytes": (mlx_bytes, self.max_mlx_bytes),
            "rss_bytes": (rss_bytes, self.max_rss_bytes),
            "swap_growth_bytes": (swap_growth_bytes, self.max_swap_growth_bytes),
        }
        for name, (actual, limit) in checks.items():
            if not math.isfinite(actual) or actual < 0:
                raise ValueError("Invalid resource measurement")
            if actual > limit:
                raise BudgetExceeded(name)
        if pressure != 1:
            raise BudgetExceeded("memory_pressure")


class BudgetExceeded(RuntimeError):
    """The declared P01 stop policy was reached; this is not a successful run."""


def assert_initial_dpo_loss(value: float, atol: float = 2e-6) -> None:
    if not math.isfinite(value) or abs(value - math.log(2)) > atol:
        raise ValueError("Training-path policy=reference loss violates initial ln2 gate")
