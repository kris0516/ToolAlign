"""Read-only views of verified selected train/validation records, without encoding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data import training_selection
from toolalign.data.common import encoded, file_hash, loads

from .config import consumer_identity, load_config, require
from .plan import epoch_plan, validate_plan


@dataclass(frozen=True)
class SelectedRow:
    """JSON buffers prevent a consumer from mutating a view through returned dicts."""

    example_bytes: bytes
    sidecar_bytes: bytes

    @property
    def example(self):
        return loads(self.example_bytes.decode("utf-8"))

    @property
    def sidecar(self):
        return loads(self.sidecar_bytes.decode("utf-8"))


@dataclass(frozen=True)
class SelectionView:
    profile: str
    split: str
    selection_sha256: str
    identity_sha256: str
    rows: tuple[SelectedRow, ...]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        return self.rows[index]


def view_from_records(*, examples, sidecars, config, profile, split, selection_sha256,
                      expected_count, expected_identity) -> SelectionView:
    """Structural kernel for original fixtures; production callers use prepare()."""
    require(type(profile) is str and profile in config["profiles"], "invalid_profile")
    require(split in ("train", "validation"), "forbidden_split")
    examples, sidecars = tuple(examples), tuple(sidecars)
    require(len(examples) == len(sidecars) == expected_count and expected_count > 0,
            "view_coverage_mismatch")
    ids, keys, rows = [], [], []
    for rank, (example, sidecar) in enumerate(zip(examples, sidecars, strict=True), 1):
        require(type(sidecar) is dict and sidecar.get("profile") == profile
                and sidecar.get("split") == split and example.get("split") == split,
                "view_profile_split_mismatch")
        training_selection.validate_pair(example, sidecar["audit"], config)
        key = training_selection.rank_key(example["example_id"])
        require(type(sidecar.get("selection_rank")) is int and sidecar["selection_rank"] == rank
                and sidecar.get("ranking_sha256") == key[0], "view_rank_mismatch")
        buckets = config["profiles"][profile]["padding_buckets"]
        bucket = next((b for b in buckets if b >= sidecar["audit"]["total_tokens"]), None)
        require(bucket is not None and type(sidecar.get("padding_bucket")) is int
                and sidecar["padding_bucket"] == bucket, "view_padding_bucket_mismatch")
        ids.append(example["example_id"])
        keys.append(key)
        rows.append(SelectedRow(encoded(example), encoded(sidecar)))
    require(len(set(ids)) == len(ids) and keys == sorted(keys), "view_duplicate_or_order_mismatch")
    require(canonical_hash(ids) == expected_identity, "view_identity_mismatch")
    return SelectionView(profile, split, selection_sha256, expected_identity, tuple(rows))


def prepare(*, sft_config_path, public_selection_manifest_path, selection_path, **input_paths):
    """Fully verify fixed inputs/output, then open only the four selected views.

    The existing verifier hashes the complete original artifact manifest and
    skips final-split audit rows; its data loading opens train/validation only.
    This function neither calls build() nor tokenizes anything.
    """
    config = load_config(sft_config_path)
    require(file_hash(public_selection_manifest_path) == config["public_selection_manifest_file_sha256"],
            "public_selection_manifest_mismatch")
    root = Path(selection_path).resolve()
    require(file_hash(root / "manifest.json") == config["private_selection_manifest_file_sha256"],
            "private_selection_manifest_mismatch")
    manifest = training_selection.verify(output=root, **input_paths)
    identity = canonical_hash(manifest)
    require(identity == config["private_selection_manifest_canonical_sha256"],
            "selection_canonical_mismatch")
    views, plans = {}, {}
    for profile in ("smoke", "formal"):
        views[profile] = {}
        for split in ("train", "validation"):
            summary = manifest["profiles"][profile][split]
            view = view_from_records(
                examples=training_selection.read_rows(root / profile / (split + ".examples.jsonl")),
                sidecars=training_selection.read_rows(root / profile / (split + ".sidecars.jsonl")),
                config=manifest["config"], profile=profile, split=split, selection_sha256=identity,
                expected_count=summary["selected_count"], expected_identity=summary["selected_identity_sha256"])
            views[profile][split] = view
        plan = epoch_plan(len(views[profile]["train"]))
        validate_plan(plan, (r.sidecar["selection_rank"] for r in views[profile]["train"].rows))
        plans[profile] = plan.record()
    report = {"status": "PASS", "scope": "CPU_PREPARATION_ONLY", "training_authorized": False,
              "selection_sha256": identity, "plans": plans, "consumer": consumer_identity(),
              "upstream_consumer": training_selection.consumer_identity(),
              "views": {p: {s: {"count": len(v), "identity_sha256": v.identity_sha256}
                               for s, v in splits.items()} for p, splits in views.items()},
              "full_selection_tokenizations": 0, "final_split_training_views": 0,
              "human_review": "PENDING", "formal_training": "NOT_RUN"}
    return views, report
