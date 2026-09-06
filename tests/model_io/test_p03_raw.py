"""Legal frozen Actions still face the unchanged P03 raw representation limits."""

import json

import pytest

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io import encode_action, validate_action
from toolalign.tools._json import parse_action


@pytest.mark.parametrize("boundary", ["escaped_bytes", "nodes", "depth"])
def test_encoding_preserves_valid_actions_without_relaxing_raw_limits(boundary):
    if boundary == "escaped_bytes":
        action = {"kind": "final", "tool_calls": [], "content": "<" * 22000}
        error = "JSON byte limit"
    else:
        value = [0] * 8192
        if boundary == "depth":
            value = "leaf"
            for _ in range(25):
                value = {"nested": value}
        action = {"kind": "tool_calls", "content": "", "tool_calls": [
            {"call_id": "current-1", "name": "original_tool", "arguments": {"value": value}},
        ]}
        # P03 decode wraps this inner ContractError (a ValueError subclass).
        error = "Invalid JSON"
    assert validate_action(action) == action
    raw = encode_action(action)
    assert canonical_hash(json.loads(raw)) == canonical_hash(action)
    with pytest.raises(ContractError, match=error) as caught:
        parse_action(raw)
    if boundary != "escaped_bytes":
        assert isinstance(caught.value.__cause__, ContractError)
        assert str(caught.value.__cause__) == "JSON complexity limit"
