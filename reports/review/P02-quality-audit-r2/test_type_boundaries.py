"""Additional original R1 fixtures for target structure and index rejection."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "prior_review_boundaries", Path(__file__).with_name("test_prior_boundaries.py")
)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)


def change_target(view, change):
    lines = view.read_text().splitlines()
    offset = next(i for i, line in enumerate(lines) if line.startswith("TARGET "))
    target = json.loads(lines[offset].removeprefix("TARGET "))
    change(target)
    lines[offset] = "TARGET " + PRIOR.encoded(target)
    view.write_text("\n".join(lines) + "\n")
    PRIOR.rehash_view(view)


@pytest.mark.parametrize("index", [-1, 999])
@pytest.mark.parametrize("field", ["message", "toolset"])
def test_out_of_range_references_are_rejected(tmp_path, index, field):
    view, packets, _ = PRIOR.view_fixture(tmp_path, "fixture", PRIOR.packet("index-boundary"))
    assert PRIOR.verify_semantic_views.verify(view, packets)["decisions"] == 1
    if field == "message":
        change_target(view, lambda t: t["complete_prefix_message_refs"].__setitem__(0, index))
    else:
        change_target(view, lambda t: t.update(toolset=index))
    with pytest.raises(AssertionError):
        PRIOR.verify_semantic_views.verify(view, packets)


@pytest.mark.parametrize("replacement", [0.0, "false", None, [], {}])
def test_target_nested_types_are_rejected(tmp_path, replacement):
    view, packets, _ = PRIOR.view_fixture(tmp_path, "fixture", PRIOR.packet("target-types"))
    assert PRIOR.verify_semantic_views.verify(view, packets)["decisions"] == 1
    change_target(view, lambda t: t["expected_action"]["tool_calls"][0]["arguments"].update(
        flag=replacement
    ))
    with pytest.raises(AssertionError):
        PRIOR.verify_semantic_views.verify(view, packets)


@pytest.mark.parametrize("replacement", [False, 0, {}, None])
def test_target_prefix_requires_an_array(tmp_path, replacement):
    view, packets, _ = PRIOR.view_fixture(tmp_path, "fixture", PRIOR.packet("prefix-shape"))
    assert PRIOR.verify_semantic_views.verify(view, packets)["decisions"] == 1
    change_target(view, lambda t: t.update(complete_prefix_message_refs=replacement))
    with pytest.raises(AssertionError):
        PRIOR.verify_semantic_views.verify(view, packets)


@pytest.mark.parametrize("field", ["expected_action", "example_id", "source_turn_index"])
def test_missing_target_fields_are_rejected(tmp_path, field):
    view, packets, _ = PRIOR.view_fixture(tmp_path, "fixture", PRIOR.packet("target-shape"))
    assert PRIOR.verify_semantic_views.verify(view, packets)["decisions"] == 1
    change_target(view, lambda t: t.pop(field))
    with pytest.raises(KeyError):
        PRIOR.verify_semantic_views.verify(view, packets)
