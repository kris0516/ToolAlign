"""Original public fixtures; no upstream records or hidden test oracle."""

import copy

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data.toolace import MARKER


@pytest.fixture
def source():
    return {
        "source": "toolalign-original-fixtures",
        "source_revision": "fixture-v1",
        "license_id": "MIT",
    }


@pytest.fixture
def original_tool():
    return {
        "name": "read_build",
        "description": "Read one original sandbox build fixture.",
        "parameters": {
            "type": "object",
            "properties": {"build_id": {"type": "string", "maxLength": 64}},
            "required": ["build_id"],
            "additionalProperties": False,
        },
        "required": None,
        "side_effect_class": "sandbox_only",
        "tool_version": "fixture-v1",
        "timeout_ms": 1000,
    }


@pytest.fixture
def record_factory(original_tool):
    import json

    def create(tool=None, value="build-001", second=False):
        tool = copy.deepcopy(tool or original_tool)
        turns = [
            {"from": "user", "value": f"Read original build {value}."},
            {"from": "assistant", "value": f'[{tool["name"]}(build_id="{value}")]'},
        ]
        if second:
            turns += [
                {
                    "from": "tool",
                    "value": json.dumps([{"name": tool["name"], "results": {"status": "pass"}}]),
                },
                {"from": "assistant", "value": f'[{tool["name"]}(build_id="build-002")]'},
            ]
        return {"system": MARKER + "\n" + json.dumps([tool]), "conversations": turns}

    return create


@pytest.fixture
def example(record_factory, source):
    from toolalign.data.toolace import inspect_record

    _, examples = inspect_record(record_factory(), source, 0)
    return examples[0]


@pytest.fixture
def lineage(example):
    return {k: example[k] for k in ("example_id", "source_record_hash", "group_id", "split")} | {
        "normalized_hash": example["example_id"],
        "augmentation_parent": None,
        "group_keys": ["schema:" + canonical_hash(example["tools"][0]["parameters_json_schema"])],
    }
