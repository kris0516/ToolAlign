"""Consume the single approved v3 selection and thirteen sealed review arrays.

This module has no tokenizer, training, model-loading or data-building interface.
The two public input pins are release boundaries, not caller-selectable policies.
Original JSONL bytes, historical producer evidence and current CPU consumption
have separate identities. Only the finite review container can be exported.
"""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication as a
from toolalign.data import quality_adjudication_materials as am
from toolalign.data import quality_exclusion
from toolalign.data.common import DataError, encoded, loads
from toolalign.model_io import Sequence

from .collator import Batch, collate_sequence
from .config import consumer_identity as sft_identity
from .config import require
from .data import SelectionView, view_from_records
from .plan import epoch_plan, validate_plan

CONFIG_SHA256 = "e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1"
INPUT_SHA256 = "08e865ff98bd476c94153033bc192664d72cee64443184576532c0289a610dd7"
MATERIALS_SHA256 = "a41f5c24a55eb5e4fed434b9352b655fbf78e5aa68276de5de183671c81412de"
SCOPE = "REVIEW_ARRAY_ADAPTATION_ONLY"
_ARRAYS = ("sequence_ids", "attention_mask", "loss_mask", "causal_input_ids",
           "causal_target_ids", "causal_loss_mask")
_UNPADDED = ("prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask",
             "causal_input_ids", "causal_target_ids", "causal_loss_mask")
_RANKS = ("padding_bucket", "parent_selection_rank", "previous_selection_rank", "selection_rank")
_PROFILES = ("smoke", "formal")
_SPLITS = ("train", "validation")
_ENGINES = (("tokenizers", "native"), ("transformers", "reference"))
_MAX_FILE = 512 * 1024 * 1024
_MAX_EXPORT = 16 * 1024 * 1024


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _cpu_only():
    a.cpu_only()
    require(not {"tokenizers", "transformers", "torch", "mlx", "mlx_lm", "jax", "flax", "tensorflow"}
            & {n.split(".", 1)[0] for n in sys.modules}, "v3_preframework_process_required")


def consumer_identity():
    identity = quality_exclusion.consumer_identity()
    identity["package_files"].update(am.consumer_identity()["package_files"])
    identity["package_files"].update({"training/sft/" + k: v for k, v in sft_identity().items()})
    name = "training/sft/data_v3.py"
    identity["package_files"][name] = _sha(files("toolalign").joinpath(name).read_bytes())
    return identity


def _path(value):
    raw = os.fspath(value)
    require(type(raw) is str and raw and ".." not in raw.split("/") and "\\" not in raw,
            "v3_path_escape")
    path = Path(raw).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "v3_symlink_forbidden")
    return path


def _relative(value):
    require(type(value) is str and value and not value.startswith("/")
            and "\\" not in value and all(p not in ("", ".", "..") for p in value.split("/")),
            "v3_relative_path_escape")
    return value


def _read(path, *, digest=None, size=None, content=True, limit=_MAX_FILE):
    """Hash the same no-follow file descriptor whose bytes may be decoded later."""
    path = _path(path)
    if size is not None:
        require(type(size) is int and 0 <= size <= limit, "v3_input_size_type")
    try:
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "v3_regular_file_budget")
            require(size is None or info.st_size == size, "v3_input_size_mismatch")
            h, parts, total = hashlib.sha256(), [], 0
            while block := stream.read(1024 * 1024):
                total += len(block)
                require(total <= limit, "v3_input_byte_budget")
                h.update(block)
                if content:
                    parts.append(block)
            require(total == info.st_size, "v3_input_changed_during_read")
            require(digest is None or h.hexdigest() == digest, "v3_input_hash_mismatch")
            return b"".join(parts) if content else None
    except OSError as exc:
        raise DataError("v3_input_io_failure") from exc


def _json(data):
    try:
        return loads(data.decode("utf-8"))
    except UnicodeError as exc:
        raise DataError("v3_invalid_utf8") from exc


@dataclass(frozen=True)
class _Bundle:
    root: Path
    manifest_bytes: bytes
    _members: MappingProxyType = field(init=False, repr=False)

    def __post_init__(self):
        manifest = self.manifest
        object.__setattr__(self, "_members", MappingProxyType({k: encoded(v) for k, v in manifest["files"].items()}))

    @property
    def manifest(self):
        require(_sha(self.manifest_bytes) == INPUT_SHA256, "v3_fixed_manifest_required")
        return _json(self.manifest_bytes)

    def descriptor(self, name):
        require(name in self._members, "v3_unlisted_input")
        return _json(self._members[name])

    def path(self, name):
        row = self.descriptor(name)
        if row["kind"] == "exact_copy":
            require(row["relative_path"] == name, "v3_copy_name_mismatch")
            return _path(self.root / _relative(name))
        require(row["kind"] == "read_only_reference" and Path(row["path"]).is_absolute(),
                "v3_input_kind_mismatch")
        return _path(row["path"])

    def read(self, name, *, content=True):
        row = self.descriptor(name)
        require(not content or row["read_mode"] != "hash_only_no_deserialization", "v3_hash_only_payload")
        return _read(self.path(name), digest=row["sha256"], size=row["bytes"], content=content)

    def document(self, name):
        return _json(self.read(name))

    def pin(self, name, expected):
        require(self.descriptor(name)["sha256"] == expected, "v3_declared_binding_mismatch")
        return self.read(name)


def _open_bundle(config_path, manifest_path):
    config_bytes = _read(config_path, digest=CONFIG_SHA256, limit=65536)
    config = _json(config_bytes)
    a.same(config["input_manifest_file_sha256"], INPUT_SHA256, "v3_config_input_binding")
    manifest_path = _path(manifest_path)
    bundle = _Bundle(manifest_path.parent, _read(manifest_path, digest=INPUT_SHA256, limit=1024 * 1024))
    manifest = bundle.manifest
    require(type(manifest["files"]) is dict and len(manifest["files"]) == 609, "v3_input_coverage")
    copies, references = {manifest_path.name}, 0
    for name, row in manifest["files"].items():
        _relative(name)
        require(type(row) is dict and type(row["bytes"]) is int and row["bytes"] >= 0,
                "v3_input_descriptor_type")
        require(type(row["sha256"]) is str and len(row["sha256"]) == 64
                and all(c in "0123456789abcdef" for c in row["sha256"]), "v3_input_digest_type")
        if row["kind"] == "exact_copy":
            copies.add(name)
        else:
            references += 1
        bundle.read(name, content=False)
    require(len(copies) == 7 and references == 603, "v3_input_kind_coverage")
    actual = set()
    for root, directories, names in os.walk(bundle.root, followlinks=False):
        for name in directories + names:
            _path(Path(root) / name)
        actual.update((Path(root) / n).relative_to(bundle.root).as_posix() for n in names)
    a.same(sorted(actual), sorted(copies), "v3_copy_directory_coverage")
    _bind_roots(bundle)
    return config_bytes, bundle


def _bind_roots(bundle):
    manifest = bundle.manifest
    roots = {k: _path(p) for k, p in manifest["roots"].items()}
    require(all(p.is_dir() for p in roots.values()), "v3_missing_verified_root")
    root = roots["d1_verifier_inputs"]
    require(bundle.path("d1-inputs/manifest.json") == root / "manifest.json", "v3_verifier_manifest_path")
    declared = bundle.document("d1-inputs/manifest.json")["files"]
    require(type(declared) is dict and len(declared) == 347, "v3_verifier_member_count")
    a.same(sorted(n.removeprefix("d1-inputs/") for n in manifest["files"] if n.startswith("d1-inputs/")),
           sorted(["manifest.json", *declared]), "v3_verifier_map_coverage")
    for name, descriptor in declared.items():
        _relative(name)
        kind = descriptor["kind"]
        require(kind in ("immutable_existing_artifact", "exact_copy", "S0_derived_frozen_metadata"),
                "v3_verifier_member_kind")
        # A logical ancestor name is not necessarily a path below the verifier
        # root. Bind the explicit immutable reference, without moving its bytes.
        expected = _path(descriptor["path"]) if kind == "immutable_existing_artifact" else root / name
        member = "d1-inputs/" + name
        require(bundle.path(member) == expected, "v3_verifier_member_path")
        for key in ("sha256", "bytes"):
            a.same(bundle.descriptor(member)[key], descriptor[key], "v3_verifier_member_binding")
    for name in manifest["files"]:
        if name.startswith("revision-v3/"):
            expected = roots["revision_v3"] / _relative(name.removeprefix("revision-v3/"))
            require(bundle.path(name) == expected, "v3_root_binding")


def _approval(bundle, config):
    binding = config["data_binding"]
    pins = {
        "d1-inputs/manifest.json": config["d1_input_manifest_file_sha256"],
        "configuration/data-quality.v3.json": binding["quality_config_file_sha256"],
        "configuration/training-data.v1.json": binding["parent_training_config_file_sha256"],
        "revision-v3/manifest.json": binding["manifest_file_sha256"],
        "revision-v3/selection/manifest.json": binding["selection_manifest_file_sha256"],
        "revision-v3/training-binding.json": binding["training_binding_file_sha256"],
        "s0/data-approval.json": config["s0_data_approval_file_sha256"],
        "s0/review-failures.json": config["issue_ledger_file_sha256"],
        "s0/q1-receipt.json": config["independent_quality_review"]["s0_receipt_sha256"],
        "s0/r1-receipt.json": config["independent_technical_review"]["s0_receipt_sha256"],
        "q1-review/adjudication-seal.json": config["independent_quality_review"]["adjudication_seal_sha256"],
        "q1-review/final-evidence-seal.json": config["independent_quality_review"]["final_seal_sha256"],
        "q1-review/adjudications.json": config["q1_adjudications_file_sha256"],
        "q1-review/material-validation.json": config["q1_material_validation_file_sha256"],
    }
    for name, digest in pins.items():
        bundle.pin(name, digest)
    approval = bundle.document("s0/data-approval.json")
    for key in ("data_binding", "independent_quality_review", "independent_technical_review",
                "issue_ledger_file_sha256", "G_DATA", "training_authorized", "optimization_authorized"):
        a.same(approval[key], config[key], "v3_S0_approval_binding")
    require(approval["G_DATA"] == "PASS_FROZEN_V3_SCOPE"
            and approval["training_authorized"] is False and approval["optimization_authorized"] is False,
            "v3_approval_scope")
    for key, name in (("s0_main_verification_sha256", "main-verification"),
                      ("s0_quality_adoption_sha256", "quality-adoption")):
        bundle.pin("s0/" + name + ".json", approval[key])
    ledger = bundle.document("s0/review-failures.json")
    require(ledger["whole_goal_paused"] is False and len(ledger["issues"]) == 82
            and len({r["issue_id"] for r in ledger["issues"]}) == 82, "v3_issue_coverage")
    for issue in ledger["issues"]:
        require(issue["status"].startswith("CLOSED"), "v3_unclosed_issue")
        a.same(issue["consecutive_failed_revisions"], 0, "v3_failure_counter")
    manifest = bundle.manifest
    a.same(manifest["candidate_commit"], approval["candidate_commit"], "v3_candidate_binding")
    a.same(manifest["view_summaries"], config["view_summaries"], "v3_summary_binding")
    for key, review in (("q1_review_commit", "independent_quality_review"),
                        ("r1_review_commit", "independent_technical_review")):
        a.same(manifest[key], config[review]["commit"], "v3_review_commit_binding")
    for seal_name in ("adjudication-seal.json", "final-evidence-seal.json"):
        seal = bundle.document("q1-review/" + seal_name)
        for key, expected in (("candidate_commit", approval["candidate_commit"]), ("reviewer", "Codex-AI(Q1)"),
                              ("model", "gpt-6-astra"), ("thinking", "max"),
                              ("status", "PASS_WITHIN_FIXED_Q1_SCOPE"), ("training_authorized", False)):
            a.same(seal[key], expected, "v3_Q1_seal_binding")
        members = _seal_members(seal, config["independent_quality_review"]["commit"])
        # Seal paths are historical metadata. Open only names in S0's fixed map.
        for name, row in manifest["files"].items():
            if name.startswith("q1-review/"):
                relative = name.removeprefix("q1-review/")
                if relative in ("final-evidence-seal.json", seal_name):
                    continue
                member = members.get(relative)
                require(member is not None and member["sha256"] == row["sha256"]
                        and type(member["bytes"]) is int and member["bytes"] == row["bytes"],
                        "v3_Q1_payload_seal_mismatch")
        if seal_name == "final-evidence-seal.json":
            a.same(seal["commit"], config["independent_quality_review"]["commit"], "v3_Q1_final_commit")
    return approval


def _seal_members(seal, review_commit):
    """Index sealed private payloads; public-at-commit entries stay metadata.

    The final Q1 seal contains three Git-bound public records with
    repository_path rather than relative_path. Their old working-tree paths
    are not an instruction to read current public files or expand this scope.
    """
    members, public = {}, set()
    for row in seal["files"]:
        require(type(row["bytes"]) is int and row["bytes"] >= 0
                and type(row["sha256"]) is str and len(row["sha256"]) == 64
                and all(c in "0123456789abcdef" for c in row["sha256"]), "v3_Q1_seal_member_type")
        if "relative_path" in row:
            name = _relative(row["relative_path"])
            require(name not in members and "repository_path" not in row
                    and row.get("kind") in (None, "private"), "v3_duplicate_Q1_seal_member")
            members[name] = row
        else:
            require(row.get("kind") == "public_at_commit" and row.get("commit") == review_commit,
                    "v3_Q1_public_commit_binding")
            name = _relative(row["repository_path"])
            require(name not in public, "v3_duplicate_Q1_public_member")
            public.add(name)
    return members


def _rows(data):
    require(type(data) is bytes and (not data or data.endswith(b"\n")), "v3_jsonl_line_boundary")
    lines = data.splitlines(keepends=True)
    values = [_json(line) for line in lines]
    require(all(type(v) is dict for v in values), "v3_jsonl_object_type")
    return values, lines


def _generation(bundle, prefix, profile, split):
    examples, lines = _rows(bundle.read(f"{prefix}/{profile}/{split}.examples.jsonl"))
    sidecars, _ = _rows(bundle.read(f"{prefix}/{profile}/{split}.sidecars.jsonl"))
    require(len(examples) == len(sidecars), "v3_ancestor_pair_count")
    result = {}
    for index, (example, sidecar, line) in enumerate(zip(examples, sidecars, lines, strict=True), 1):
        ident = example["example_id"]
        require(ident not in result and sidecar["audit"]["example_id"] == ident, "v3_ancestor_identity")
        a.same(sidecar["selection_rank"], index, "v3_ancestor_continuous_rank")
        result[ident] = (example, sidecar, line)
    return result


def _linked_view(*, current, original, previous, excluded_sources, selection, config, profile, split):
    """Small pure kernel: whole-source exclusion, byte identity, three rank epochs."""
    retained = [i for i, (e, _, _) in original.items() if e["source_record_hash"] not in excluded_sources]
    a.same(list(current), retained, "v3_whole_source_filter_or_refill")
    require(set(current) <= set(previous), "v3_previous_exclusion_reintroduced")
    rows, sidecars, lines = [], [], []
    for ident, (example, sidecar, line) in current.items():
        origin, parent, original_line = original[ident]
        before, previous_sidecar, previous_line = previous[ident]
        require(line == original_line == previous_line, "v3_original_line_bytes")
        a.same(example, origin, "v3_original_example_type")
        a.same(example, before, "v3_previous_example_type")
        for key, expected in (("parent_selection_rank", parent["selection_rank"]),
                              ("previous_selection_rank", previous_sidecar["selection_rank"]),
                              ("parent_sidecar_sha256", canonical_hash(parent)),
                              ("previous_selection_sidecar_sha256", canonical_hash(previous_sidecar)),
                              ("parent_selection_manifest_sha256", selection["parent_selection_manifest_file_sha256"]),
                              ("previous_selection_manifest_sha256", selection["previous_selection_manifest_file_sha256"]),
                              ("quality_revision_sha256", selection["quality_revision_sha256"]),
                              ("quality_config_file_sha256", selection["quality_config_file_sha256"])):
            a.same(sidecar[key], expected, "v3_three_generation_binding")
        for other in (parent, previous_sidecar):
            a.same(sidecar["audit"], other["audit"], "v3_inherited_audit_type")
            a.same(sidecar["ranking_sha256"], other["ranking_sha256"], "v3_stable_ranking")
        for key in _RANKS:
            require(type(sidecar[key]) is int and sidecar[key] > 0, "v3_rank_integer_type")
        rows.append(example)
        sidecars.append(sidecar)
        lines.append((profile, split, ident, _sha(line)))
    summary = selection["profiles"][profile][split]["summary"]
    a.same(summary, config["view_summaries"][profile][split], "v3_actual_summary_mismatch")
    view = view_from_records(examples=rows, sidecars=sidecars, config=selection["parent_training_config"],
        profile=profile, split=split, selection_sha256=config["data_binding"]["selection_manifest_file_sha256"],
        expected_count=summary["effective_selected_count"], expected_identity=summary["selected_identity_sha256"])
    return view, tuple(lines)


@dataclass(frozen=True)
class PreparedV3:
    views: tuple[SelectionView, ...]
    original_line_hashes: tuple[tuple[str, str, str, str], ...]
    report_bytes: bytes
    _config_bytes: bytes
    _bundle: _Bundle

    @property
    def report(self):
        return _json(self.report_bytes)

    def view(self, profile, split):
        require(profile in _PROFILES and split in _SPLITS, "v3_forbidden_view")
        return next(v for v in self.views if (v.profile, v.split) == (profile, split))


def prepare_v3(*, sft_config_path, input_manifest_path) -> PreparedV3:
    """One read-only verify of the pinned corpus; construct train/validation only."""
    _cpu_only()
    config_bytes, bundle = _open_bundle(sft_config_path, input_manifest_path)
    config = _json(config_bytes)
    approval = _approval(bundle, config)
    roots = bundle.manifest["roots"]
    verified = quality_exclusion.verify(output=roots["revision_v3"],
        config_path=bundle.path("configuration/data-quality.v3.json"), input_root=roots["d1_verifier_inputs"])
    a.same(verified, bundle.document("revision-v3/manifest.json"), "v3_verified_manifest_mismatch")
    a.same(verified["quality_revision_sha256"], config["data_binding"]["quality_revision_sha256"], "v3_revision_mismatch")
    a.same(verified["counts"], approval["counts"], "v3_approved_counts")
    selection = bundle.document("revision-v3/selection/manifest.json")
    binding = bundle.document("revision-v3/training-binding.json")
    require(selection["manifest_version"] == "toolalign.quality-excluded-selection.v3"
            and binding["binding_version"] == "toolalign.quality-excluded-training-binding.v3"
            and selection["training_authorized"] is False and binding["training_authorized"] is False,
            "v3_version_or_training_boundary")
    a.same(selection["parent_training_config"], bundle.document("configuration/training-data.v1.json"),
           "v3_parent_training_config")
    for key in ("quality_revision_sha256", "quality_config_file_sha256", "selection_manifest_file_sha256", "effective_files"):
        a.same(binding[key], config["data_binding"][key], "v3_training_binding")
    for name, digest in config["data_binding"]["effective_files"].items():
        bundle.pin("revision-v3/" + name, digest)
    sources, _ = _rows(bundle.read("revision-v3/dispositions/sources.jsonl"))
    excluded = {r["source_record_hash"] for r in sources if r["disposition"] == "exclude_entire_source"}
    views, original_lines, plans = [], [], {}
    for profile in _PROFILES:
        for split in _SPLITS:
            view, lines = _linked_view(
                current=_generation(bundle, "revision-v3/selection", profile, split),
                original=_generation(bundle, "d1-inputs/parent-inputs/parent_selection", profile, split),
                previous=_generation(bundle, "d1-inputs/parent-revision/selection", profile, split),
                excluded_sources=excluded, selection=selection, config=config, profile=profile, split=split)
            views.append(view)
            original_lines.extend(lines)
            if split == "train":
                plan = epoch_plan(len(view))
                validate_plan(plan, (r.sidecar["selection_rank"] for r in view.rows))
                a.same(plan.updates, config["plan"][profile]["updates"], "v3_plan_updates")
                plans[profile] = plan.record()
    report = {"status": "PASS", "scope": SCOPE, "G_DATA": approval["G_DATA"], "plans": plans,
        "views": {v.profile + "/" + v.split: {"count": len(v), "identity_sha256": v.identity_sha256} for v in views},
        "config_file_sha256": CONFIG_SHA256, "input_manifest_file_sha256": INPUT_SHA256,
        "data_binding": config["data_binding"], "consumer": consumer_identity(),
        "quality_review": config["independent_quality_review"], "technical_review": config["independent_technical_review"],
        "original_pending_fields_preserved": True, "new_sequence_calls": 0, "full_data_builds": 0,
        "actual_model_updates": 0, "training_authorized": False, "optimization_authorized": False,
        "real_trainer_consumption": "NOT_RUN", "browser_actual_observation": "NOT_RUN",
        "smoke_1536_capacity": "NOT_RUN", "formal_2048_capacity": "NOT_RUN"}
    _cpu_only()
    return PreparedV3(tuple(views), tuple(original_lines), encoded(report), config_bytes, bundle)


def _check_prepared(prepared):
    _cpu_only()
    require(type(prepared) is PreparedV3 and _sha(prepared._config_bytes) == CONFIG_SHA256,
            "v3_prepared_fixed_config_required")
    require(_sha(prepared._bundle.manifest_bytes) == INPUT_SHA256, "v3_prepared_fixed_input_required")
    a.same(prepared.report["consumer"], consumer_identity(), "v3_CPU_consumer_changed")
    require(type(prepared.views) is tuple and len(prepared.views) == 4, "v3_prepared_views")
    config = _json(prepared._config_bytes)
    for profile in _PROFILES:
        for split in _SPLITS:
            view = prepared.view(profile, split)
            require(type(view) is SelectionView and type(view.rows) is tuple, "v3_immutable_view_required")
            summary = config["view_summaries"][profile][split]
            a.same(len(view), summary["effective_selected_count"], "v3_prepared_count")
            a.same(canonical_hash([r.example["example_id"] for r in view.rows]),
                   summary["selected_identity_sha256"], "v3_prepared_identity")
    return config


def _batch_record(record, case):
    """Type-check every array before the existing Sequence/Batch validators."""
    for key in _UNPADDED:
        value = record["sequence"][key]
        require(type(value) is list and value and all(type(i) is int and i >= 0 for i in value),
                "v3_unpadded_integer_array")
    for key, value in record["padding"].items():
        if key in _ARRAYS:
            require(type(value) is list and value and all(type(i) is int and i >= 0 for i in value),
                    "v3_padded_integer_array")
        else:
            require(type(value) is int and value >= 0, "v3_padding_integer_metadata")
    am.checked_record(record, case)
    data = record["sequence"]
    sequence = Sequence(data["prompt_text"], data["completion_text"], tuple(data["prompt_ids"]),
        tuple(data["concatenated_ids"]), tuple(data["sequence_ids"]), tuple(data["loss_mask"]), data["eos_token_id"])
    batch = collate_sequence(sequence, bucket=record["padding"]["bucket"], pad_token_id=151643)
    a.same(batch.record(), record["padding"], "v3_original_batch_mismatch")
    return sequence, batch


def _case_binding(case, judgment, prepared, config):
    require(case["quality_revision_sha256"] == config["data_binding"]["quality_revision_sha256"], "v3_material_revision")
    for key in ("reviewer", "semantic_verdict", "token_mask_verdict"):
        require(case[key] is None, "v3_original_judgment_columns_modified")
    require(case["example"]["split"] == "train", "v3_material_split")
    for key, expected in (("case_id", case["case_id"]), ("example_id", case["example"]["example_id"]),
                          ("source_record_hash", case["example"]["source_record_hash"]),
                          ("quality_revision_sha256", case["quality_revision_sha256"]),
                          ("current_profiles", case["profiles"]), ("semantic_verdict", "pass"),
                          ("token_mask_verdict", "pass")):
        a.same(judgment[key], expected, "v3_Q1_case_binding")
    ident = case["example"]["example_id"]
    matches = {v.profile: next((r for r in v.rows if r.example["example_id"] == ident), None)
               for v in prepared.views if v.split == "train"}
    if case["category"] == "original_protocol_only":
        require(case["case_id"].startswith("protocol-") and not case["profiles"] and case["audit"] is None
                and case["enters_effective_training"] is False and judgment["enters_effective_train"] is False,
                "v3_protocol_training_boundary")
        require(all(ident != r.example["example_id"] for v in prepared.views for r in v.rows), "v3_protocol_in_view")
        return {"original_jsonl_line_sha256": None, "enters_training_view": False}
    require(case["category"] == "effective_selected_train" and judgment["enters_effective_train"] is True,
            "v3_staging_material_forbidden")
    a.same(sorted(case["profiles"]), sorted(p for p, row in matches.items() if row is not None), "v3_material_profiles")
    line_hashes = {h for p, s, i, h in prepared.original_line_hashes if i == ident and s == "train"}
    require(line_hashes == {case["original_jsonl_line_sha256"]}, "v3_material_original_line")
    for profile, info in case["profiles"].items():
        row = matches[profile]
        a.same(case["example"], row.example, "v3_material_example_reuse")
        a.same(case["audit"], row.sidecar["audit"], "v3_material_audit_reuse")
        a.same(info, {k: row.sidecar[k] for k in _RANKS}, "v3_material_rank_binding")
        require(all(type(info[k]) is int and info[k] > 0 for k in _RANKS), "v3_material_rank_type")
    return {"original_jsonl_line_sha256": case["original_jsonl_line_sha256"], "enters_training_view": True}


def _validation(record, validation, engine_judgment, digest):
    seq, batch = record["sequence"], record["padding"]
    for key, expected in (("status", "PASS"), ("record_file_sha256", digest),
                          ("record_canonical_sha256", canonical_hash(record)),
                          ("all_7_unpadded_array_hashes", {k: canonical_hash(seq[k]) for k in _UNPADDED}),
                          ("full_padded_arrays_sha256", canonical_hash(batch)),
                          ("token_texts_sha256", canonical_hash(record["token_texts"])),
                          ("P", len(seq["prompt_ids"])), ("N_including_eos", batch["unpadded_length"]),
                          ("C_without_eos", len(seq["sequence_ids"]) - len(seq["prompt_ids"]) - 1),
                          ("padding_bucket", batch["bucket"]), ("supervised_target_count", batch["effective_supervised_targets"]),
                          ("first_supervised_causal_position", batch["first_supervised_causal_position"]),
                          ("last_supervised_causal_position", batch["last_supervised_causal_position"]),
                          ("right_padding_tokens", batch["bucket"] - batch["unpadded_length"])):
        a.same(validation[key], expected, "v3_Q1_array_validation_binding")
    a.same(engine_judgment["validation_record_sha256"], canonical_hash(validation), "v3_Q1_validation_record")
    a.same(engine_judgment["record_file_sha256"], digest, "v3_Q1_engine_record")


def _producer(bundle, case, record, label, engine, proof, inheritance):
    prefix = "review-inputs/materials/review-" + label + "/"
    provenance = bundle.document(prefix + "encoding-provenance.json")
    run = bundle.document(prefix + "run.json")
    require(case["encoding_mode"] in ("reuse_original", "new_fixed_example"), "v3_material_encoding_mode")
    epoch_name = "v2-original" if case["encoding_mode"] == "reuse_original" else "v3"
    epoch = proof["original_versus_new_epochs"][epoch_name]
    for name, digest in epoch["authorized_consumer_files"].items():
        bundle.pin(f"review-inputs/measurement-code/{epoch_name}/{epoch['epoch']}/{name}", digest)
    engine_proof = next(p for p in proof["engines"] if p["engine"] == engine)
    require(engine_proof["status"] == "PASS" and engine_proof["old_sequence_reencodings"] == 0,
            "v3_original_encoding_proof")
    if epoch_name == "v2-original":
        match = next(r for r in provenance["records"] if r["case_id"] == case["case_id"])
        prior_name = "review-inputs/" + _relative(match["original_record_file"])
        original = _json(bundle.pin(prior_name, match["original_record_file_sha256"]))
        for key in ("example", "audit"):
            a.same(record["case"][key], original["case"][key], "v3_original_case_inheritance")
        for key in ("sequence", "padding", "token_texts"):
            a.same(record[key], original[key], "v3_complete_array_inheritance")
        inherited = next(r for r in inheritance if (r["case_id"], r["engine"]) == (case["case_id"], engine))
        a.same(inherited["prior_material_file_sha256"], match["original_record_file_sha256"], "v3_prior_material_file")
        require(inherited["complete_example_action_messages_audit_sequence_padding_token_texts_equal"] is True,
                "v3_Q1_inheritance_verdict")
        return {"epoch": epoch, "engine": engine, "inheritance": inherited, "record_provenance": match,
                "original_encoding": provenance["parent_encoding"], "original_command": engine_proof["original_command"],
                "original_command_file_sha256": engine_proof["original_command_file_sha256"],
                "original_run_created_at_utc": engine_proof["original_run_created_at_utc"]}
    match = next(r for r in provenance["new_records"] if r["case_id"] == case["case_id"])
    a.same(match["record_sha256"], canonical_hash(record), "v3_new_original_record")
    require(run["new_sequence_calls"] == engine_proof["new_sequence_calls"] == 2, "v3_historical_encoding_count")
    return {"epoch": epoch, "engine": engine, "record_provenance": match, "original_run": run,
            "original_command": engine_proof["new_command"], "original_consumer": engine_proof["new_consumer"],
            "original_command_file_sha256": engine_proof["new_command_file_sha256"],
            "original_reservation": engine_proof["reservation"], "original_events": engine_proof["events"]}


@dataclass(frozen=True, init=False)
class ReviewArrays:
    """An immutable, finite expected export; properties return fresh JSON values."""

    payload_bytes: bytes
    batches: tuple[Batch, ...]
    sequences: tuple[Sequence, ...]

    @property
    def payload(self):
        return _json(self.payload_bytes)


def _review_arrays(payload_bytes, batches, sequences):
    # No public constructor accepting arbitrary records or review decisions.
    result = object.__new__(ReviewArrays)
    object.__setattr__(result, "payload_bytes", payload_bytes)
    object.__setattr__(result, "batches", tuple(batches))
    object.__setattr__(result, "sequences", tuple(sequences))
    return result


def rebind_review_arrays(prepared: PreparedV3) -> ReviewArrays:
    """Reconstruct exactly thirteen original arrays, with no encoding callbacks."""
    config = _check_prepared(prepared)
    bundle = prepared._bundle
    cases = bundle.document("review-inputs/materials/frozen-materials-r3/cases.json")
    a.same([c["case_id"] for c in cases], config["material_case_ids"], "v3_fixed_material_order")
    judgments = bundle.document("q1-review/adjudications.json")["material_adjudications"]
    validation = bundle.document("q1-review/material-validation.json")
    inheritance = bundle.document("q1-review/material-inheritance-map.json")["inheritance"]
    proof = bundle.document("q1-review/encoding-provenance-validation.json")
    require(len(judgments) == 13 and len(validation["cases"]) == 26 and len(inheritance) == 22,
            "v3_review_coverage")
    a.same(validation["records_canonical_sha256"], config["material_records_canonical_sha256"], "v3_review_array_identity")
    items, sequences, batches, originals = [], [], [], []
    for case in cases:
        judgment = next(j for j in judgments if j["case_id"] == case["case_id"])
        binding = _case_binding(case, judgment, prepared, config)
        records, producers, engine_files = [], [], {}
        for engine, label in _ENGINES:
            name = f"review-inputs/materials/review-{label}/{case['case_id']}.json"
            raw = bundle.read(name)
            record = _json(raw)
            sequence, batch = _batch_record(record, case)
            check = next(r for r in validation["cases"] if (r["case_id"], r["engine"]) == (case["case_id"], engine))
            engine_judgment = next(r for r in judgment["engine_records"] if r["engine"] == engine)
            _validation(record, check, engine_judgment, _sha(raw))
            producers.append(_producer(bundle, case, record, label, engine, proof, inheritance))
            engine_files[engine] = {"original_file_sha256": _sha(raw), "Q1_validation": check}
            records.append(record)
        a.same(records[0], records[1], "v3_engine_array_difference")
        originals.append(records[0])
        sequences.append(sequence)
        batches.append(batch)
        items.append({"case_id": case["case_id"], "original_record": records[0], "batch": batch.record(),
            "binding": binding, "Q1_judgment": judgment, "engine_records": engine_files,
            "original_producers": producers})
    a.same(canonical_hash(originals), config["material_records_canonical_sha256"], "v3_full_material_identity")
    payload = {"schema": "toolalign.sft-review-array-adaptation.v1", "scope": SCOPE, "items": items,
        "config_file_sha256": CONFIG_SHA256, "input_manifest_file_sha256": INPUT_SHA256,
        "data_binding": config["data_binding"], "quality_review": config["independent_quality_review"],
        "consumer": consumer_identity(), "unique_review_materials": 13, "original_engine_records": 26,
        "train_materials": 10, "protocol_only_materials": 3, "new_sequence_calls": 0,
        "actual_model_updates": 0, "optimization_authorized": False, "training_authorized": False,
        "real_trainer_consumption": "NOT_RUN", "browser_actual_observation": "NOT_RUN"}
    _cpu_only()
    return _review_arrays(encoded(payload) + b"\n", batches, sequences)


def _export_manifest(review):
    _cpu_only()
    require(type(review) is ReviewArrays and type(review.payload_bytes) is bytes
            and len(review.payload_bytes) <= _MAX_EXPORT, "v3_finite_review_required")
    payload = review.payload
    require(payload["scope"] == SCOPE and payload["config_file_sha256"] == CONFIG_SHA256
            and payload["input_manifest_file_sha256"] == INPUT_SHA256, "v3_export_scope")
    a.same(payload["consumer"], consumer_identity(), "v3_export_consumer")
    require(payload["optimization_authorized"] is False and payload["training_authorized"] is False,
            "v3_export_training_boundary")
    a.same(payload["new_sequence_calls"], 0, "v3_export_new_encoding")
    require(type(review.batches) is tuple and type(review.sequences) is tuple
            and len(payload["items"]) == len(review.batches) == len(review.sequences) == 13, "v3_export_count")
    a.same(canonical_hash([r["original_record"] for r in payload["items"]]), MATERIALS_SHA256,
           "v3_export_fixed_original_records")
    for item, batch, sequence in zip(payload["items"], review.batches, review.sequences, strict=True):
        require(type(batch) is Batch and type(sequence) is Sequence, "v3_export_immutable_arrays")
        a.same(item["batch"], batch.record(), "v3_export_batch_binding")
        a.same(item["batch"], item["original_record"]["padding"], "v3_export_original_padding")
        a.same(sequence.record(), {k: item["original_record"]["sequence"][k] for k in sequence.record()},
               "v3_export_original_sequence")
    return {"schema": "toolalign.sft-review-array-export.v1", "scope": SCOPE, "complete": True,
        "config_file_sha256": CONFIG_SHA256, "input_manifest_file_sha256": INPUT_SHA256,
        "consumer": payload["consumer"], "new_sequence_calls": 0, "optimization_authorized": False,
        "artifacts": {"review-arrays.json": {"sha256": _sha(review.payload_bytes), "bytes": len(review.payload_bytes)}}}


def _exclusive_write(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def export_review_arrays(review: ReviewArrays, *, output):
    """Publish a new private directory; a complete manifest is linked last."""
    manifest = _export_manifest(review)
    root = _path(output)
    require(".toolalign-local" in root.parts and root.parent.is_dir(), "v3_private_output_required")
    require(not root.exists(), "v3_output_already_exists")
    root.mkdir(mode=0o700)
    _exclusive_write(root / "review-arrays.json", review.payload_bytes)
    _exclusive_write(root / ".manifest.pending", encoded(manifest) + b"\n")
    os.link(root / ".manifest.pending", root / "manifest.json", follow_symlinks=False)
    (root / ".manifest.pending").unlink()
    return manifest


def read_review_arrays(*, output, expected: ReviewArrays) -> tuple[Batch, ...]:
    """Compare to the immutable source rebind, then return typed CPU batches.

    A self-consistent replacement of the output and its manifest cannot replace
    the separately held expected source arrays or their Q1/producer bindings.
    """
    manifest = _export_manifest(expected)
    root = _path(output)
    require(".toolalign-local" in root.parts and root.is_dir(), "v3_private_output_required")
    require({p.name for p in root.iterdir()} == {"review-arrays.json", "manifest.json"}, "v3_incomplete_export")
    actual_manifest = _json(_read(root / "manifest.json", limit=65536))
    a.same(actual_manifest, manifest, "v3_export_manifest_binding")
    actual = _read(root / "review-arrays.json", **{
        "digest": manifest["artifacts"]["review-arrays.json"]["sha256"],
        "size": manifest["artifacts"]["review-arrays.json"]["bytes"]}, limit=_MAX_EXPORT)
    require(actual == expected.payload_bytes, "v3_original_export_bytes")
    payload = _json(actual)
    batches = []
    for item, original in zip(payload["items"], expected.batches, strict=True):
        data = item["batch"]
        for key, value in data.items():
            require((type(value) is list and all(type(i) is int for i in value)) if key in _ARRAYS
                    else type(value) is int, "v3_readback_integer_type")
        batch = Batch(**{k: tuple(v) if k in _ARRAYS else v for k, v in data.items()})
        a.same(batch.record(), original.record(), "v3_readback_original_batch")
        batches.append(batch)
    _cpu_only()
    return tuple(batches)
