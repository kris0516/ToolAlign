"""Finite, ordered one-epoch calls to the public MLX-LM trainer."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import require


@dataclass(frozen=True)
class Segment:
    start: int
    stop: int
    divisor: int

    @property
    def microsteps(self):
        return self.stop - self.start

    @property
    def updates(self):
        return self.microsteps // self.divisor


@dataclass(frozen=True)
class EpochPlan:
    count: int
    segments: tuple[Segment, ...]

    @property
    def updates(self):
        return sum(segment.updates for segment in self.segments)

    def record(self):
        return {**asdict(self), "optimizer_updates_planned": self.updates,
                "optimizer_updates_executed": 0, "seed": 42, "epochs": 1,
                "micro_batch_size": 1, "shuffle": False, "packing": False,
                "truncation": False, "status": "CPU_PLAN_ONLY",
                "training_reduction": "mean_of_per_example_completion_token_mean_losses"}


def epoch_plan(count: int) -> EpochPlan:
    require(type(count) is int and count > 0, "empty_or_invalid_epoch")
    full = count - count % 8
    segments = ([Segment(0, full, 8)] if full else [])
    if full != count:
        segments.append(Segment(full, count, count - full))
    return EpochPlan(count, tuple(segments))


def validate_plan(plan: EpochPlan, ranks) -> None:
    require(type(plan) is EpochPlan, "invalid_epoch_plan")
    expected = epoch_plan(plan.count)
    require(plan == expected, "noncanonical_or_incomplete_segments")
    ranks = tuple(ranks)
    require(all(type(rank) is int for rank in ranks)
            and ranks == tuple(range(1, plan.count + 1)), "rank_coverage_or_order_mismatch")
