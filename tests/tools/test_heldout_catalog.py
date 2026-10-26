"""Component checks of fixed fictional resources, not final evaluation tasks."""

import hashlib
import json
import threading
import time
from dataclasses import asdict
from importlib.resources import files

import pytest
from test_registry_executor import assert_reaped, call, context

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import Rejection, ValidatedCall
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry, heldout_catalog
from toolalign.tools._json import encode
from toolalign.tools.executor import _tool_child
from toolalign.tools.isolation import OwnedProcess

CATALOG = "heldout-devops.v1"


def registry_for(domain):
    return LocalToolRegistry(heldout_catalog.DOMAIN_TOOLS[domain], catalog_id=CATALOG)


def test_default_catalog_bytes_specs_and_manifest_are_unchanged():
    # Recorded from the authorized base before this catalog selector was added.
    expected_source = "8c89c7f2b4a4bc64952791b66954542cf328f814b07a9ba1c3f3e70b5e236792"
    expected_registry = "6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8"
    expected_tools = "bbb7b2de3f520880764e7600c7361e757dcdb418c48fd3da50bf78e004164ced"
    assert hashlib.sha256(files("toolalign.tools").joinpath("catalog.py").read_bytes()).hexdigest() == expected_source
    implicit, explicit = LocalToolRegistry(), LocalToolRegistry(catalog_id="local-devops.v1")
    assert implicit.catalog_id == explicit.catalog_id == "local-devops.v1"
    assert implicit.registry_hash == explicit.registry_hash == expected_registry
    assert encode(implicit.manifest) == encode(explicit.manifest)
    assert hashlib.sha256(encode(implicit.manifest)).hexdigest() == expected_registry
    assert hashlib.sha256(encode(implicit.tools)).hexdigest() == expected_tools
    assert set(implicit.manifest) == {"registry_version", "tools"}
    assert {item["source_hash"] for item in implicit.manifest["tools"]} == {expected_source}


def test_new_manifest_binds_selected_source_and_fixed_implementations():
    registry = LocalToolRegistry(catalog_id=CATALOG)
    source = hashlib.sha256(files("toolalign.tools").joinpath("heldout_catalog.py").read_bytes()).hexdigest()
    assert registry.catalog_id == CATALOG
    with pytest.raises(AttributeError):
        registry.catalog_id = "local-devops.v1"
    assert len(heldout_catalog.DOMAIN_TOOLS) == 4
    assert all(len(names) == 2 for names in heldout_catalog.DOMAIN_TOOLS.values())
    assert {tool["name"] for tool in registry.tools} == {
        name for names in heldout_catalog.DOMAIN_TOOLS.values() for name in names
    } == set(heldout_catalog.IMPLEMENTATIONS)
    assert len(registry.tools) == 8
    assert registry.registry_hash == canonical_hash(registry.manifest)
    assert registry.registry_hash != LocalToolRegistry().registry_hash
    for binding in registry.manifest["tools"]:
        name = binding["spec"]["name"]
        assert binding["source_hash"] == source
        assert binding["implementation"] == "toolalign.tools.heldout_catalog:" + name
        assert heldout_catalog.IMPLEMENTATIONS[name].__name__ == name
        assert binding["spec"]["tool_version"] == CATALOG
        assert binding["spec"]["side_effect_class"] == "read_only"
        assert binding["schema_hash"] == canonical_hash(binding["spec"]["parameters_json_schema"])


@pytest.mark.parametrize("catalog_id", [None, "unknown.v1", "os", "toolalign.tools.heldout_catalog", {}, len])
def test_caller_cannot_select_a_module_or_callable(catalog_id):
    with pytest.raises(ValueError, match="Unknown fixed"):
        LocalToolRegistry(catalog_id=catalog_id)


@pytest.mark.parametrize("domain,first_arguments,links,extra,first_expected,second_expected", [
    ("releases", {"application": "comet-gateway", "release": "4.3.0"}, ["deployment_id"],
     {"snapshot_day": "2026-10-12"}, {"deployment_id": "comet-green", "desired_replicas": 6},
     {"running_release": "4.2.0", "ready_replicas": 2, "state": "rolling"}),
    ("incidents", {"route": "parcel-ingest", "day": "2026-10-18", "start_minute": 60, "end_minute": 90},
     ["policy_id", "event_count", "critical_count"], {},
     {"policy_id": "parcel-rule-1", "event_count": 2, "critical_count": 1,
      "events": [{"minute": 60, "severity": "warning"}, {"minute": 75, "severity": "critical"}]},
     {"recommendation": "page", "recipient": "parcel-primary"}),
    ("packages", {"package": "cedar-cli", "version": "2.5.0", "platform": "linux-amd64"},
     ["suite_id"], {"required_cases": ["install", "upgrade"]},
     {"build_id": "cedar-250-x86", "suite_id": "cedar-suite-25"},
     {"all_passed": False, "outcomes": [{"case": "install", "outcome": "pass"},
                                       {"case": "upgrade", "outcome": "fail"}]}),
    ("storage", {"pool": "archive-tier", "tenant": "finch", "snapshot_day": "2026-10-21"},
     ["quota_id"], {"request_gib": 20, "request_objects": 560},
     {"quota_id": "finch-archive-r2", "capacity_gib": 512, "free_gib": 80},
     {"quota_allows": True, "gib_after_request": 64, "objects_after_request": 1000}),
], ids=["release-to-deployment", "window-to-policy", "build-to-suite", "pool-to-quota"])
def test_four_domains_execute_eight_tools_with_real_two_step_links(
    tmp_path, domain, first_arguments, links, extra, first_expected, second_expected,
):
    registry = registry_for(domain)
    first_name, second_name = heldout_catalog.DOMAIN_TOOLS[domain]
    executor = LocalToolExecutor(registry)
    first = executor.execute(registry.validate(call(first_name, first_arguments)), context(tmp_path))
    assert first.status == "completed"
    assert all(first.output[key] == value for key, value in first_expected.items())
    second_arguments = {key: first.output[key] for key in links} | extra
    second = executor.execute(registry.validate(call(second_name, second_arguments)), context(tmp_path))
    assert second.status == "completed"
    assert all(second.output[key] == value for key, value in second_expected.items())
    assert len(executor.process_records) == 2
    assert all(row["operation_started"] and row["directory_cleaned"] for row in executor.process_records)
    assert_reaped(executor.process_records)
    assert not list(tmp_path.glob("toolalign-owned-*"))
    (tmp_path / "execution-evidence.json").write_text(json.dumps({
        "catalog_id": registry.catalog_id, "registry_hash": registry.registry_hash,
        "advertised_tools": [tool["name"] for tool in registry.tools],
        "first_arguments": first_arguments, "second_arguments": second_arguments,
        "results": [asdict(first), asdict(second)], "process_records": executor.process_records,
    }, indent=2) + "\n")


@pytest.mark.parametrize("domain,name,variants,field,expected", [
    ("releases", "read_release_manifest", [
        {"application": "comet-gateway", "release": "4.3.0"},
        {"application": "comet-gateway", "release": "4.2.0"},
        {"application": "lattice-worker", "release": "4.3.0"},
    ], "deployment_id", ["comet-green", "comet-blue", "lattice-green"]),
    ("releases", "read_deployment_snapshot", [
        {"deployment_id": "comet-green", "snapshot_day": "2026-10-12"},
        {"deployment_id": "comet-green", "snapshot_day": "2026-10-13"},
    ], "running_release", ["4.2.0", "4.3.0"]),
    ("incidents", "summarize_incident_window", [
        {"route": "parcel-ingest", "day": "2026-10-18", "start_minute": 60, "end_minute": 90},
        {"route": "parcel-ingest", "day": "2026-10-19", "start_minute": 60, "end_minute": 90},
        {"route": "replica-sync", "day": "2026-10-18", "start_minute": 60, "end_minute": 90},
    ], "policy_id", ["parcel-rule-1", "parcel-rule-2", "replica-rule-1"]),
    ("packages", "inspect_package_build", [
        {"package": "cedar-cli", "version": "2.4.0", "platform": "linux-amd64"},
        {"package": "cedar-cli", "version": "2.5.0", "platform": "linux-arm64"},
        {"package": "drift-agent", "version": "2.5.0", "platform": "linux-amd64"},
    ], "suite_id", ["cedar-suite-24", "cedar-arm-suite-25", "drift-suite-25"]),
    ("storage", "inspect_storage_pool", [
        {"pool": "archive-tier", "tenant": "finch", "snapshot_day": "2026-10-20"},
        {"pool": "archive-tier", "tenant": "finch", "snapshot_day": "2026-10-21"},
        {"pool": "scratch-tier", "tenant": "finch", "snapshot_day": "2026-10-20"},
        {"pool": "archive-tier", "tenant": "oryx", "snapshot_day": "2026-10-20"},
    ], "quota_id", ["finch-archive-r1", "finch-archive-r2", "finch-scratch-r1", "oryx-archive-r1"]),
])
def test_object_version_platform_and_date_variants_remain_distinct(tmp_path, domain, name, variants, field, expected):
    registry = registry_for(domain)
    executor = LocalToolExecutor(registry)
    results = [executor.execute(registry.validate(call(name, arguments)), context(tmp_path))
               for arguments in variants]
    assert all(result.status == "completed" for result in results)
    assert [result.output[field] for result in results] == expected
    assert_reaped(executor.process_records)


@pytest.mark.parametrize("name,arguments,code", [
    ("read_deployment_snapshot", {"deployment_id": "comet-green", "snapshot_day": "2026-10-14"},
     "deployment_snapshot_missing"),
    ("summarize_incident_window", {"route": "parcel-ingest", "day": "2026-10-18", "start_minute": 90, "end_minute": 60},
     "invalid_incident_window"),
    ("assess_incident_policy", {"policy_id": "parcel-rule-1", "event_count": 1, "critical_count": 2},
     "inconsistent_incident_counts"),
    ("inspect_package_build", {"package": "cedar-cli", "version": "2.4.0", "platform": "linux-arm64"},
     "package_build_missing"),
])
def test_valid_schema_can_still_report_a_semantic_resource_error(tmp_path, name, arguments, code):
    registry = LocalToolRegistry([name], catalog_id=CATALOG)
    validated = registry.validate(call(name, arguments))
    assert isinstance(validated, ValidatedCall)
    executor = LocalToolExecutor(registry)
    result = executor.execute(validated, context(tmp_path))
    assert (result.status, result.error_code, result.retryable) == ("error", code, False)
    assert_reaped(executor.process_records)


def test_missing_test_results_are_not_passes_and_order_is_preserved(tmp_path):
    registry = registry_for("packages")
    executor = LocalToolExecutor(registry)
    result = executor.execute(registry.validate(call("assess_test_suite", {
        "suite_id": "cedar-arm-suite-25", "required_cases": ["upgrade", "install", "install"],
    })), context(tmp_path))
    assert result.status == "completed" and result.output["all_passed"] is False
    assert result.output["outcomes"] == [
        {"case": "upgrade", "outcome": "not_recorded"},
        {"case": "install", "outcome": "pass"}, {"case": "install", "outcome": "pass"},
    ]
    assert_reaped(executor.process_records)


def test_quota_limits_are_inclusive_independent_and_do_not_allocate(tmp_path):
    registry = registry_for("storage")
    executor = LocalToolExecutor(registry)
    business = tmp_path / "unrelated-resource.json"
    business.write_text('{"unchanged":true}')
    arguments = {"quota_id": "finch-archive-r1", "request_gib": 12, "request_objects": 700}
    results = [executor.execute(registry.validate(call("assess_quota_allocation", value)), context(tmp_path))
               for value in (arguments, arguments | {"request_gib": 13},
                             arguments | {"request_objects": 701}, arguments)]
    assert all(result.status == "completed" for result in results)
    assert [result.output["quota_allows"] for result in results] == [True, False, False, True]
    assert results[0].output == results[-1].output
    assert results[0].output["remaining_gib"] == results[0].output["remaining_objects"] == 0
    assert business.read_text() == '{"unchanged":true}'
    assert list(tmp_path.iterdir()) == [business]
    assert_reaped(executor.process_records)


def test_incident_empty_window_and_policy_revision_thresholds(tmp_path):
    registry = registry_for("incidents")
    executor = LocalToolExecutor(registry)
    empty = executor.execute(registry.validate(call("summarize_incident_window", {
        "route": "parcel-ingest", "day": "2026-10-18", "start_minute": 0, "end_minute": 30,
    })), context(tmp_path))
    assert empty.status == "completed" and empty.output["events"] == []
    assert empty.output["event_count"] == empty.output["critical_count"] == 0
    inputs = [
        {key: empty.output[key] for key in ("policy_id", "event_count", "critical_count")},
        {"policy_id": "parcel-rule-1", "event_count": 2, "critical_count": 0},
        {"policy_id": "parcel-rule-2", "event_count": 2, "critical_count": 0},
        {"policy_id": "replica-rule-1", "event_count": 1, "critical_count": 1},
    ]
    results = [executor.execute(registry.validate(call("assess_incident_policy", args)), context(tmp_path))
               for args in inputs]
    assert all(result.status == "completed" for result in results)
    assert [result.output["recommendation"] for result in results] == ["observe", "page", "observe", "page"]
    assert_reaped(executor.process_records)


@pytest.mark.parametrize("tool", LocalToolRegistry(catalog_id=CATALOG).tools, ids=lambda tool: tool["name"])
def test_every_new_tool_requires_explicit_arguments(tool):
    value = LocalToolRegistry(catalog_id=CATALOG).validate(call(tool["name"], {}))
    assert isinstance(value, Rejection) and value.code == "invalid_arguments"


@pytest.mark.parametrize("name,args", [
    ("read_release_manifest", {"application": "/etc/passwd", "release": "4.3.0"}),
    ("read_deployment_snapshot", {"deployment_id": "comet-green", "snapshot_day": "2026-10-13", "path": "https://example.invalid/data"}),
    ("summarize_incident_window", {"route": "parcel-ingest", "day": "2026-10-18", "start_minute": -1, "end_minute": 90}),
    ("summarize_incident_window", {"route": "parcel-ingest", "day": "2026-10-18", "start_minute": 0, "end_minute": 1441}),
    ("assess_incident_policy", {"policy_id": "parcel-rule-1", "event_count": 101, "critical_count": 1}),
    ("inspect_package_build", {"package": "cedar-cli", "version": "2.5.0", "platform": "caller.module:run"}),
    ("assess_test_suite", {"suite_id": "cedar-suite-25", "required_cases": []}),
    ("assess_test_suite", {"suite_id": "cedar-suite-25", "required_cases": ["install"] * 5}),
    ("assess_test_suite", {"suite_id": "cedar-suite-25", "required_cases": ["invented"]}),
    ("inspect_storage_pool", {"pool": "archive-tier", "tenant": "finch", "snapshot_day": "2026-10-22"}),
    ("assess_quota_allocation", {"quota_id": "finch-archive-r1", "request_gib": True, "request_objects": 0}),
    ("assess_quota_allocation", {"quota_id": "finch-archive-r1", "request_gib": 129, "request_objects": 0}),
    ("assess_quota_allocation", {"quota_id": "finch-archive-r1", "request_gib": 1, "request_objects": -1}),
])
def test_unknown_resources_extra_fields_and_numeric_array_bounds_reject_before_spawn(tmp_path, name, args):
    registry = LocalToolRegistry(catalog_id=CATALOG)
    rejected = registry.validate(call(name, args))
    assert isinstance(rejected, Rejection) and rejected.code == "invalid_arguments"
    executor = LocalToolExecutor(registry)
    assert executor.execute(rejected, context(tmp_path)).status == "rejected"
    assert not executor.process_records and not list(tmp_path.iterdir())


def test_subset_limits_advertised_tools_and_keeps_one_use_authority(tmp_path):
    name = "read_release_manifest"
    registry = LocalToolRegistry([name], catalog_id=CATALOG)
    assert [row["name"] for row in registry.tools] == [name]
    assert registry.registry_hash != LocalToolRegistry(catalog_id=CATALOG).registry_hash
    for unadvertised in ("read_deployment_snapshot", "query_build_report"):
        rejected = registry.validate(call(unadvertised, {}))
        assert isinstance(rejected, Rejection) and rejected.code == "unknown_tool"
    with pytest.raises(ValueError, match="Only source-bound"):
        LocalToolRegistry([name, "query_build_report"], catalog_id=CATALOG)
    with pytest.raises(ValueError, match="Only source-bound"):
        LocalToolRegistry([name])
    executor = LocalToolExecutor(registry)
    issued = registry.validate(call(name, {"application": "comet-gateway", "release": "4.3.0"}))
    assert executor.execute(issued, context(tmp_path)).status == "completed"
    assert executor.execute(issued, context(tmp_path)).error_code == "unissued_call"
    other = LocalToolRegistry([name], catalog_id=CATALOG)
    assert other.registry_hash == registry.registry_hash
    assert executor.execute(other.validate(call(name, issued.call["arguments"])), context(tmp_path)).error_code == "unissued_call"
    assert len(executor.process_records) == 1
    assert_reaped(executor.process_records)


@pytest.mark.parametrize("mismatch", ["wrong-catalog", "module-name", "source-hash"])
def test_owned_child_rebuilds_catalog_subset_and_rejects_a_changed_source_binding(tmp_path, mismatch):
    registry = registry_for("releases")
    catalog_id, digest = registry.catalog_id, registry.registry_hash
    if mismatch == "wrong-catalog":
        catalog_id = "local-devops.v1"
    elif mismatch == "module-name":
        catalog_id = "toolalign.tools.heldout_catalog"
    else:
        stale = registry.manifest
        stale["tools"][0]["source_hash"] = "0" * 64
        digest = canonical_hash(stale)
    request = call("read_release_manifest", {"application": "comet-gateway", "release": "4.3.0"})
    child = OwnedProcess(tmp_path.resolve(), _tool_child, (
        catalog_id, [row["name"] for row in registry.tools], digest, request, None,
    ), "binding-test")
    try:
        status, result = child.wait("result.json", time.monotonic() + 5, CancellationToken())
        assert status == "completed"
        assert (result["status"], result["error_code"]) == ("rejected", "child_binding_mismatch")
        assert not (child.directory / "executing.json").exists()
    finally:
        child.close()
    assert_reaped([child.record])
    assert child.record["directory_cleaned"] and not child.directory.exists()
    (tmp_path / "binding-evidence.json").write_text(json.dumps({
        "mismatch": mismatch, "catalog_id": catalog_id, "sent_hash": digest,
        "actual_hash": registry.registry_hash, "result": result, "process": child.record,
    }, indent=2) + "\n")


def test_transient_fault_queue_is_consumed_once_and_next_new_call_runs(tmp_path):
    registry = registry_for("releases")
    executor = LocalToolExecutor(registry, faults={"read_release_manifest": ["transient", None]})
    request = call("read_release_manifest", {"application": "comet-gateway", "release": "4.3.0"})
    first = registry.validate(request)
    result = executor.execute(first, context(tmp_path))
    assert (result.status, result.error_code, result.retryable) == ("error", "injected_transient", True)
    assert executor.execute(first, context(tmp_path)).error_code == "unissued_call"
    result = executor.execute(registry.validate(request), context(tmp_path))
    assert result.status == "completed" and result.output["deployment_id"] == "comet-green"
    assert len(executor.process_records) == 2
    assert_reaped(executor.process_records)


@pytest.mark.parametrize("mode", ["timeout", "cancel"])
def test_new_catalog_blocking_operation_is_stopped_and_reaped(tmp_path, mode):
    registry, token = registry_for("releases"), CancellationToken()
    executor = LocalToolExecutor(registry, faults={"read_release_manifest": ["block"]})
    thread = None
    if mode == "cancel":
        def cancel_after_started():
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if list(tmp_path.glob("toolalign-owned-*/executing.json")):
                    token.cancel()
                    return
                time.sleep(0.01)

        thread = threading.Thread(target=cancel_after_started)
        thread.start()
    request = call("read_release_manifest", {"application": "comet-gateway", "release": "4.3.0"})
    result = executor.execute(registry.validate(request), context(tmp_path, cancellation=token))
    if thread is not None:
        thread.join(timeout=6)
        assert not thread.is_alive()
    assert result.status == ("timed_out" if mode == "timeout" else "cancelled")
    assert result.retryable is (mode == "timeout")
    assert all(row["operation_started"] and row["stopped"] and row["directory_cleaned"]
               for row in executor.process_records)
    assert_reaped(executor.process_records)
    assert not list(tmp_path.iterdir())
