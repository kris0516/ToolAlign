"""Token-weighted validation and deterministic score selection; no backend imports."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass

from toolalign.contracts import canonical_hash

from .config import require


def parameter_content_hash(entries):
    """Hash actual named parameter buffers including dtype and shape (not filenames)."""
    values = []
    for name, dtype, shape, data in entries:
        require(type(name) is str and type(dtype) is str and type(data) is bytes,
                "invalid_parameter_entry")
        require(all(type(n) is int and n >= 0 for n in shape), "invalid_parameter_shape")
        values.append([name, dtype, list(shape), hashlib.sha256(data).hexdigest()])
    require(values and len({v[0] for v in values}) == len(values), "empty_or_duplicate_parameters")
    return canonical_hash(sorted(values))


class ValidationTotals:
    def __init__(self, *, profile, split, expected_ids):
        require(profile in ("smoke", "formal", "TOY_CPU", "TOY_NATIVE_GPU")
                and split == "validation", "validation_scope_mismatch")
        self.profile, self.split = profile, split
        self.expected_ids = tuple(expected_ids)
        require(self.expected_ids and len(set(self.expected_ids)) == len(self.expected_ids),
                "empty_or_duplicate_validation")
        self.count, self.numerator, self.denominator = 0, 0.0, 0

    def add(self, *, example_id, profile, split, ce_sum, tokens):
        require(profile == self.profile and split == self.split, "validation_scope_mismatch")
        require(self.count < len(self.expected_ids) and example_id == self.expected_ids[self.count],
                "validation_coverage_or_order_mismatch")
        require(type(tokens) is int and tokens > 0 and type(ce_sum) in (int, float)
                and math.isfinite(ce_sum) and ce_sum >= 0, "invalid_validation_denominator_or_loss")
        self.numerator += ce_sum
        self.denominator += tokens
        self.count += 1

    def finish(self):
        require(self.count == len(self.expected_ids), "incomplete_validation")
        require(self.denominator > 0 and math.isfinite(self.numerator), "invalid_validation_total")
        return self.numerator / self.denominator


@dataclass(frozen=True)
class Score:
    profile: str
    selection_sha256: str
    validation_identity_sha256: str
    parameter_content_sha256: str
    checkpoint_file_sha256: str
    optimizer_step: int
    processed_microsteps: int
    ce_sum: float
    supervised_tokens: int
    validation_ce: float
    scope: str = "TOY_CPU"

    def record(self):
        return asdict(self)


def validate_score(score):
    require(type(score) is Score and score.scope in ("TOY_CPU", "TOY_NATIVE_GPU")
            and score.profile == score.scope,
            "only_toy_score_authorized")
    for digest in (score.selection_sha256, score.validation_identity_sha256,
                   score.parameter_content_sha256, score.checkpoint_file_sha256):
        require(type(digest) is str and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest), "invalid_score_identity")
    require(type(score.optimizer_step) is int and score.optimizer_step > 0
            and type(score.processed_microsteps) is int
            and score.processed_microsteps >= score.optimizer_step, "invalid_score_counters")
    require(type(score.supervised_tokens) is int and score.supervised_tokens > 0
            and math.isfinite(score.ce_sum) and score.ce_sum >= 0
            and math.isfinite(score.validation_ce)
            and score.validation_ce == score.ce_sum / score.supervised_tokens, "invalid_score_loss")


def choose_score(scores):
    values = tuple(scores)
    require(values, "empty_score_candidates")
    for value in values:
        validate_score(value)
    require(len({(v.profile, v.selection_sha256, v.validation_identity_sha256) for v in values}) == 1,
            "incomparable_validation_scores")
    return min(values, key=lambda s: (s.validation_ce, s.optimizer_step, s.checkpoint_file_sha256))
