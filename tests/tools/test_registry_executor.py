import copy
import json
import multiprocessing
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from toolalign.contracts import canonical_hash, validate_record
from toolalign.contracts.interfaces import Rejection, SandboxContext, ValidatedCall
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry


def context(root, *, seconds=10, cancellation=None):
    return SandboxContext(
        root.resolve(),
        "tool-test",
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(),
        cancellation or CancellationToken(),
    )


def call(name="query_build_report", arguments=None):
    return {
        "call_id": "c1",
        "name": name,
        "arguments": {"report_id": "atlas-110"} if arguments is None else arguments,
    }


def assert_reaped(records):
    assert records
    assert all(record["reaped"] and record["exitcode"] is not None for record in records)
    live = {process.pid for process in multiprocessing.active_children()}
    assert not live.intersection(record["pid"] for record in records)


@pytest.mark.parametrize(
    "name,args,field,value",
    [
        ("lookup_version_document", {"resource_id": "atlas-1.1"}, "timeout_ms", 1200),
        ("query_build_report", {"report_id": "atlas-110"}, "passed", 12),
        (
            "filter_build_logs",
            {"resource_id": "atlas-september", "date": "2026-09-01", "level": "error"},
            "count",
            1,
        ),
        (
            "aggregate_run_records",
            {
                "resource_id": "atlas-runs",
                "date": "2026-09-01",
                "field": "duration_ms",
                "operation": "mean",
            },
            "value",
            1200,
        ),
        (
            "compare_version_compatibility",
            {"resource_id": "atlas-1.1", "runtime_version": "3.11"},
            "compatible",
            False,
        ),
        (
            "convert_numeric_units",
            {"value": 1536, "from_unit": "KiB", "to_unit": "MiB"},
            "converted_value",
            1.5,
        ),
    ],
)
def test_six_categories_execute_in_owned_children(tmp_path, name, args, field, value):
    registry = LocalToolRegistry()
    executor = LocalToolExecutor(registry)
    result = executor.execute(registry.validate(call(name, args)), context(tmp_path))
    assert result.status == "completed"
    assert result.output[field] == value
    assert_reaped(executor.process_records)
    assert executor.process_records[0]["operation_started"]
    assert list(tmp_path.iterdir()) == []


def test_registry_identity_and_defensive_copies():
    first, second = LocalToolRegistry(), LocalToolRegistry()
    assert first.registry_hash == second.registry_hash == canonical_hash(first.manifest)
    assert len(first.tools) == 6
    for binding in first.manifest["tools"]:
        validate_record(binding["spec"], "tool")
        assert binding["schema_hash"] == canonical_hash(binding["spec"]["parameters_json_schema"])
        assert len(binding["source_hash"]) == 64
        assert binding["implementation"].endswith(":" + binding["spec"]["name"])
    changed = first.tools
    changed[0]["side_effect_class"] = "sandbox_only"
    changed[0]["parameters_json_schema"]["properties"].clear()
    assert first.tools == second.tools
    assert LocalToolRegistry(["query_build_report"]).registry_hash != first.registry_hash


@pytest.mark.parametrize(
    "names",
    [
        ["query_build_report", "query_build_report"],
        ["ta_fake"],
        [{"name": "query_build_report", "side_effect_class": "sandbox_only"}],
    ],
)
def test_no_duplicate_conflicting_or_data_registration(names):
    with pytest.raises(ValueError):
        LocalToolRegistry(names)


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"report_id": "../atlas-110"},
        {"report_id": "/etc/passwd"},
        {"report_id": "https://example.invalid/atlas-110"},
        {"report_id": "atlas-110", "shell": "id"},
        {"report_id": "atlas-110\n"},
        {"report_id": "atlas-110", "$ref": "https://example.invalid/schema"},
        {"report_id": "atlas-110", "parameters_json_schema": {"type": "object"}},
        {"report_id": "__import__('os').system('id')"},
        {"report_id": "x" * 20_000},
        {"report_id": 123},
    ],
)
def test_untrusted_paths_code_schema_and_bounds_rejected(arguments):
    assert isinstance(LocalToolRegistry().validate(call(arguments=arguments)), Rejection)


@pytest.mark.parametrize("number", [True, float("nan"), float("inf"), 1e10, "1200"])
def test_conversion_rejects_coercion_and_unbounded_numbers(number):
    result = LocalToolRegistry().validate(
        call("convert_numeric_units", {"value": number, "from_unit": "ms", "to_unit": "s"})
    )
    assert isinstance(result, Rejection)


def test_mutating_original_input_does_not_change_validated_call(tmp_path):
    registry = LocalToolRegistry()
    request = call()
    validated = registry.validate(request)
    request["arguments"]["report_id"] = "beacon-110"
    result = LocalToolExecutor(registry).execute(validated, context(tmp_path))
    assert result.status == "completed" and result.output["object"] == "atlas"


@pytest.mark.parametrize("mutation", ["arguments", "version", "hash", "name", "policy"])
def test_execute_rechecks_modified_validation_and_registry(tmp_path, mutation):
    registry = LocalToolRegistry()
    value = registry.validate(call())
    if mutation == "arguments":
        value.call["arguments"]["report_id"] = "beacon-110"  # Still schema-valid.
    elif mutation == "version":
        object.__setattr__(value, "tool_version", "old-version")
    elif mutation == "hash":
        object.__setattr__(value, "registry_hash", "0" * 64)
    elif mutation == "name":
        value.call["name"] = "ta_historical_schema"
    else:
        registry._specs["query_build_report"]["side_effect_class"] = "sandbox_only"
    executor = LocalToolExecutor(registry)
    result = executor.execute(value, context(tmp_path))
    assert result.status == "rejected"
    assert result.error_code == "stale_or_modified_call"
    assert not executor.process_records


@pytest.mark.parametrize("fabrication", ["copy", "construct", "other_registry"])
def test_forged_calls_with_correct_hash_still_have_no_authority(tmp_path, fabrication):
    registry = LocalToolRegistry()
    issued = registry.validate(call())
    if fabrication == "copy":
        forged = copy.deepcopy(issued)
    elif fabrication == "construct":
        forged = ValidatedCall(issued.call, issued.tool_version, issued.registry_hash)
    else:
        forged = LocalToolRegistry().validate(call())
    executor = LocalToolExecutor(registry)
    result = executor.execute(forged, context(tmp_path))
    assert result.status == "rejected" and result.error_code == "unissued_call"
    assert not executor.process_records


def test_replay_consumed_call_is_rejected(tmp_path):
    registry = LocalToolRegistry()
    executor = LocalToolExecutor(registry)
    validated = registry.validate(call())
    assert executor.execute(validated, context(tmp_path)).status == "completed"
    assert executor.execute(validated, context(tmp_path)).error_code == "unissued_call"
    assert len(executor.process_records) == 1


def test_historical_sandbox_only_schema_is_not_execution_authority(tmp_path):
    registry = LocalToolRegistry()
    schema = registry.spec("query_build_report")
    schema.update(name="ta_query_build_report_deadbeef", side_effect_class="sandbox_only")
    validate_record(schema, "tool")
    rejected = registry.validate(call(schema["name"]))
    assert isinstance(rejected, Rejection) and rejected.code == "unknown_tool"
    fake = ValidatedCall(call(schema["name"]), schema["tool_version"], registry.registry_hash)
    assert LocalToolExecutor(registry).execute(fake, context(tmp_path)).status == "rejected"


@pytest.mark.parametrize(
    "fault,code,retryable",
    [
        ("oversize", "output_limit", False),
        ("transient", "injected_transient", True),
        ("error", "injected_permanent", False),
    ],
)
def test_faults_are_bounded_and_explicit(tmp_path, fault, code, retryable):
    registry = LocalToolRegistry()
    executor = LocalToolExecutor(registry, faults={"query_build_report": [fault]})
    result = executor.execute(registry.validate(call()), context(tmp_path))
    assert result.status == "error" and result.error_code == code
    assert result.output is None and result.retryable == retryable
    assert_reaped(executor.process_records)


def test_tool_timeout_really_reaps_started_blocking_operation(tmp_path):
    registry = LocalToolRegistry()
    executor = LocalToolExecutor(registry, faults={"query_build_report": ["block"]})
    start = time.monotonic()
    result = executor.execute(registry.validate(call()), context(tmp_path))
    assert result.status == "timed_out" and result.retryable
    assert 0.9 <= time.monotonic() - start < 3
    assert_reaped(executor.process_records)
    assert executor.process_records[0]["operation_started"]
    assert executor.process_records[0]["stopped"]


def test_tool_cancellation_really_reaps_started_operation(tmp_path):
    registry, token = LocalToolRegistry(), CancellationToken()
    executor = LocalToolExecutor(registry, faults={"query_build_report": ["block"]})

    def cancel_after_started():
        limit = time.monotonic() + 5
        while time.monotonic() < limit:
            if list(tmp_path.glob("toolalign-owned-*/executing.json")):
                token.cancel()
                return
            time.sleep(0.01)

    thread = threading.Thread(target=cancel_after_started)
    thread.start()
    result = executor.execute(registry.validate(call()), context(tmp_path, cancellation=token))
    thread.join(timeout=6)
    assert not thread.is_alive()
    assert result.status == "cancelled" and not result.retryable
    assert_reaped(executor.process_records)
    assert executor.process_records[0]["operation_started"]


@pytest.mark.parametrize("mode", ["cancelled", "expired", "invalid_deadline", "symlink"])
def test_preflight_failure_creates_no_operation(tmp_path, mode):
    registry, token = LocalToolRegistry(), CancellationToken()
    executor = LocalToolExecutor(registry)
    ctx = context(tmp_path, cancellation=token)
    if mode == "cancelled":
        token.cancel()
    elif mode == "expired":
        ctx = context(tmp_path, seconds=-1)
    elif mode == "invalid_deadline":
        ctx = replace(ctx, deadline_utc="2026-09-01T00:00:00+08:00")
    else:
        link = tmp_path / "alias"
        link.symlink_to(tmp_path, target_is_directory=True)
        ctx = replace(ctx, root=link)
    result = executor.execute(registry.validate(call()), ctx)
    assert result.status != "completed"
    assert not executor.process_records


def test_semantic_tool_error_is_not_schema_error(tmp_path):
    registry = LocalToolRegistry()
    value = registry.validate(
        call("convert_numeric_units", {"value": 1, "from_unit": "s", "to_unit": "B"})
    )
    assert isinstance(value, ValidatedCall)
    result = LocalToolExecutor(registry).execute(value, context(tmp_path))
    assert result.error_code == "incompatible_units" and not result.retryable


def test_no_model_dependency_is_imported():
    import sys

    assert not {"mlx", "torch", "transformers", "mlx_lm"}.intersection(sys.modules)
    assert "sandbox_only" not in json.dumps(LocalToolRegistry().manifest)


@pytest.mark.parametrize("tool", LocalToolRegistry().tools, ids=lambda tool: tool["name"])
def test_each_category_requires_all_explicit_parameters(tool):
    registry = LocalToolRegistry()
    assert isinstance(registry.validate(call(tool["name"], {})), Rejection)


def test_timeout_does_not_reap_a_separate_process(tmp_path):
    separate = multiprocessing.get_context("spawn").Process(target=time.sleep, args=(20,))
    separate.start()
    try:
        registry = LocalToolRegistry()
        executor = LocalToolExecutor(registry, faults={"query_build_report": ["block"]})
        result = executor.execute(registry.validate(call()), context(tmp_path, seconds=0.3))
        assert result.status == "timed_out"
        assert separate.is_alive()
        assert separate.pid not in {record["pid"] for record in executor.process_records}
        assert_reaped(executor.process_records)
    finally:
        separate.terminate()
        separate.join(timeout=3)
        separate.close()


def test_tool_execution_does_not_write_a_business_resource(tmp_path):
    business = tmp_path / "business.json"
    business.write_text('{"balance":100}')
    registry = LocalToolRegistry()
    executor = LocalToolExecutor(registry)
    assert executor.execute(registry.validate(call()), context(tmp_path)).status == "completed"
    assert business.read_text() == '{"balance":100}'
    assert list(tmp_path.iterdir()) == [business]


def test_conflicting_source_catalog_definitions_are_not_silently_overwritten(monkeypatch):
    definitions = LocalToolRegistry().tools
    duplicate = copy.deepcopy(definitions[0])
    duplicate["description"] = "Conflicting original source definition"
    monkeypatch.setattr("toolalign.tools.catalog.specs", lambda: definitions + [duplicate])
    with pytest.raises(ValueError, match="Duplicate or conflicting"):
        LocalToolRegistry()
