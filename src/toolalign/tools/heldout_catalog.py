"""Eight read-only tools over original fictional DevOps resources.

All records are fixed below. The functions do not read paths, networks or the
environment. These resource definitions and component examples are not a final
task/oracle set, and the four work domains are not asserted to be isolated groups.
"""

from __future__ import annotations

from .catalog import ToolFault

VERSION = "heldout-devops.v1"
DOMAIN_TOOLS = {
    "releases": ("read_release_manifest", "read_deployment_snapshot"),
    "incidents": ("summarize_incident_window", "assess_incident_policy"),
    "packages": ("inspect_package_build", "assess_test_suite"),
    "storage": ("inspect_storage_pool", "assess_quota_allocation"),
}

# A release manifest describes intended deployment. A dated snapshot records
# what was actually deployed; a rollout can still be running the older release.
RELEASE_MANIFESTS = {
    ("comet-gateway", "4.2.0"): {
        "deployment_id": "comet-blue", "artifact_label": "comet-420",
        "desired_replicas": 4, "channel": "stable",
    },
    ("comet-gateway", "4.3.0"): {
        "deployment_id": "comet-green", "artifact_label": "comet-430",
        "desired_replicas": 6, "channel": "canary",
    },
    ("lattice-worker", "4.2.0"): {
        "deployment_id": "lattice-blue", "artifact_label": "lattice-420",
        "desired_replicas": 3, "channel": "stable",
    },
    ("lattice-worker", "4.3.0"): {
        "deployment_id": "lattice-green", "artifact_label": "lattice-430",
        "desired_replicas": 5, "channel": "canary",
    },
}
DEPLOYMENTS = {
    "comet-blue": {"application": "comet-gateway", "snapshots": {
        "2026-10-12": {"running_release": "4.2.0", "ready_replicas": 4, "state": "healthy"},
        "2026-10-13": {"running_release": "4.2.0", "ready_replicas": 3, "state": "degraded"},
    }},
    "comet-green": {"application": "comet-gateway", "snapshots": {
        "2026-10-12": {"running_release": "4.2.0", "ready_replicas": 2, "state": "rolling"},
        "2026-10-13": {"running_release": "4.3.0", "ready_replicas": 6, "state": "healthy"},
    }},
    "lattice-blue": {"application": "lattice-worker", "snapshots": {
        "2026-10-12": {"running_release": "4.2.0", "ready_replicas": 3, "state": "healthy"},
        "2026-10-13": {"running_release": "4.2.0", "ready_replicas": 1, "state": "degraded"},
    }},
    "lattice-green": {"application": "lattice-worker", "snapshots": {
        "2026-10-12": {"running_release": "4.2.0", "ready_replicas": 1, "state": "rolling"},
        "2026-10-13": {"running_release": "4.3.0", "ready_replicas": 5, "state": "healthy"},
    }},
}

# Windows use UTC minutes since midnight, with an inclusive start and exclusive
# end. Each route/day selects the applicable policy revision explicitly.
INCIDENT_WINDOWS = {
    ("parcel-ingest", "2026-10-18"): {"policy_id": "parcel-rule-1", "events": [
        {"minute": 60, "severity": "warning"}, {"minute": 75, "severity": "critical"},
        {"minute": 90, "severity": "info"}, {"minute": 130, "severity": "warning"},
    ]},
    ("parcel-ingest", "2026-10-19"): {"policy_id": "parcel-rule-2", "events": [
        {"minute": 60, "severity": "warning"}, {"minute": 75, "severity": "warning"},
        {"minute": 90, "severity": "critical"},
    ]},
    ("replica-sync", "2026-10-18"): {"policy_id": "replica-rule-1", "events": [
        {"minute": 65, "severity": "info"}, {"minute": 80, "severity": "warning"},
        {"minute": 120, "severity": "critical"},
    ]},
    ("replica-sync", "2026-10-19"): {"policy_id": "replica-rule-2", "events": [
        {"minute": 60, "severity": "warning"}, {"minute": 95, "severity": "warning"},
        {"minute": 130, "severity": "critical"},
    ]},
}
INCIDENT_POLICIES = {
    "parcel-rule-1": {"event_threshold": 2, "critical_threshold": 1, "recipient": "parcel-primary"},
    "parcel-rule-2": {"event_threshold": 3, "critical_threshold": 2, "recipient": "parcel-primary"},
    "replica-rule-1": {"event_threshold": 4, "critical_threshold": 1, "recipient": "replica-primary"},
    "replica-rule-2": {"event_threshold": 2, "critical_threshold": 2, "recipient": "replica-backup"},
}

# Build existence does not imply that all required tests passed. The suite tool
# reads recorded outcomes; it never compiles, installs or runs a test suite.
PACKAGE_BUILDS = {
    ("cedar-cli", "2.4.0", "linux-amd64"): {"build_id": "cedar-240-x86", "suite_id": "cedar-suite-24"},
    ("cedar-cli", "2.5.0", "linux-amd64"): {"build_id": "cedar-250-x86", "suite_id": "cedar-suite-25"},
    ("cedar-cli", "2.5.0", "linux-arm64"): {"build_id": "cedar-250-arm", "suite_id": "cedar-arm-suite-25"},
    ("drift-agent", "2.4.0", "linux-amd64"): {"build_id": "drift-240-x86", "suite_id": "drift-suite-24"},
    ("drift-agent", "2.5.0", "linux-amd64"): {"build_id": "drift-250-x86", "suite_id": "drift-suite-25"},
    ("drift-agent", "2.5.0", "linux-arm64"): {"build_id": "drift-250-arm", "suite_id": "drift-arm-suite-25"},
}
TEST_SUITES = {
    "cedar-suite-24": {"recorded_on": "2026-10-17", "cases": {
        "install": "pass", "upgrade": "pass", "rollback": "fail", "healthcheck": "pass",
    }},
    "cedar-suite-25": {"recorded_on": "2026-10-18", "cases": {
        "install": "pass", "upgrade": "fail", "rollback": "pass", "healthcheck": "pass",
    }},
    "cedar-arm-suite-25": {"recorded_on": "2026-10-18", "cases": {
        "install": "pass", "upgrade": "not_recorded", "rollback": "pass", "healthcheck": "pass",
    }},
    "drift-suite-24": {"recorded_on": "2026-10-17", "cases": {
        "install": "pass", "upgrade": "fail", "rollback": "fail", "healthcheck": "pass",
    }},
    "drift-suite-25": {"recorded_on": "2026-10-18", "cases": {
        "install": "pass", "upgrade": "pass", "rollback": "pass", "healthcheck": "pass",
    }},
    "drift-arm-suite-25": {"recorded_on": "2026-10-18", "cases": {
        "install": "fail", "upgrade": "not_recorded", "rollback": "not_recorded", "healthcheck": "fail",
    }},
}

# Physical pool space and per-tenant quota are different constraints. Quota IDs
# bind a dated usage snapshot and quota revision; checks never allocate storage.
POOLS = {
    "archive-tier": {"capacity_gib": 512, "free_gib": {"2026-10-20": 100, "2026-10-21": 80}},
    "scratch-tier": {"capacity_gib": 256, "free_gib": {"2026-10-20": 60, "2026-10-21": 20}},
}
QUOTAS = {
    "finch-archive-r1": {"pool": "archive-tier", "tenant": "finch", "snapshot_day": "2026-10-20",
                         "used_gib": 36, "limit_gib": 48, "used_objects": 300, "limit_objects": 1000},
    "finch-archive-r2": {"pool": "archive-tier", "tenant": "finch", "snapshot_day": "2026-10-21",
                         "used_gib": 44, "limit_gib": 64, "used_objects": 440, "limit_objects": 1000},
    "oryx-archive-r1": {"pool": "archive-tier", "tenant": "oryx", "snapshot_day": "2026-10-20",
                        "used_gib": 11, "limit_gib": 24, "used_objects": 200, "limit_objects": 500},
    "oryx-archive-r2": {"pool": "archive-tier", "tenant": "oryx", "snapshot_day": "2026-10-21",
                        "used_gib": 19, "limit_gib": 32, "used_objects": 250, "limit_objects": 500},
    "finch-scratch-r1": {"pool": "scratch-tier", "tenant": "finch", "snapshot_day": "2026-10-20",
                         "used_gib": 18, "limit_gib": 32, "used_objects": 400, "limit_objects": 800},
    "finch-scratch-r2": {"pool": "scratch-tier", "tenant": "finch", "snapshot_day": "2026-10-21",
                         "used_gib": 20, "limit_gib": 32, "used_objects": 600, "limit_objects": 800},
    "oryx-scratch-r1": {"pool": "scratch-tier", "tenant": "oryx", "snapshot_day": "2026-10-20",
                        "used_gib": 70, "limit_gib": 96, "used_objects": 900, "limit_objects": 1024},
    "oryx-scratch-r2": {"pool": "scratch-tier", "tenant": "oryx", "snapshot_day": "2026-10-21",
                        "used_gib": 92, "limit_gib": 96, "used_objects": 950, "limit_objects": 1024},
}


def _enum(values):
    return {"type": "string", "maxLength": 64, "enum": list(values)}


def _integer(minimum, maximum):
    return {"type": "integer", "minimum": minimum, "maximum": maximum}


def _spec(name, description, properties):
    return {
        "schema_version": "toolalign.tool.v1", "name": name, "description": description,
        "parameters_json_schema": {
            "type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False,
        },
        "tool_version": VERSION, "side_effect_class": "read_only", "timeout_ms": 1000,
    }


def specs():
    """Fresh portable schemas for these eight fixed implementations."""
    return [
        _spec("read_release_manifest",
              "Read the intended artifact, replica count and deployment_id for an exact application release; this is not deployed state.",
              {"application": _enum(["comet-gateway", "lattice-worker"]),
               "release": _enum(["4.2.0", "4.3.0"])}),
        _spec("read_deployment_snapshot",
              "Read actual running release, ready replicas and state for a deployment_id on an exact snapshot_day. A missing date is an error.",
              {"deployment_id": _enum(DEPLOYMENTS),
               "snapshot_day": _enum(["2026-10-12", "2026-10-13", "2026-10-14"])}),
        _spec("summarize_incident_window",
              "Count fixed route events within one UTC day: start_minute is inclusive and end_minute exclusive. Return the applicable policy_id and critical count.",
              {"route": _enum(["parcel-ingest", "replica-sync"]),
               "day": _enum(["2026-10-18", "2026-10-19"]),
               "start_minute": _integer(0, 1439), "end_minute": _integer(1, 1440)}),
        _spec("assess_incident_policy",
              "Assess whether supplied counts meet either threshold of an exact policy_id. Critical count cannot exceed event count. Return advice without paging anyone.",
              {"policy_id": _enum(INCIDENT_POLICIES), "event_count": _integer(0, 100),
               "critical_count": _integer(0, 100)}),
        _spec("inspect_package_build",
              "Find a recorded build and its suite_id for an exact package, version and platform. A valid but unavailable combination is an error; no build is run.",
              {"package": _enum(["cedar-cli", "drift-agent"]),
               "version": _enum(["2.4.0", "2.5.0"]),
               "platform": _enum(["linux-amd64", "linux-arm64"])}),
        _spec("assess_test_suite",
              "Read recorded outcomes for required_cases in the supplied order, including repeats. all_passed requires every requested case to be pass; not_recorded is not a pass. No tests are run.",
              {"suite_id": _enum(TEST_SUITES), "required_cases": {
                  "type": "array", "minItems": 1, "maxItems": 4,
                  "items": _enum(["install", "upgrade", "rollback", "healthcheck"]),
              }}),
        _spec("inspect_storage_pool",
              "Read physical pool capacity/free GiB and the tenant's quota_id for an exact snapshot_day. Physical free space is distinct from tenant quota.",
              {"pool": _enum(POOLS), "tenant": _enum(["finch", "oryx"]),
               "snapshot_day": _enum(["2026-10-20", "2026-10-21"])}),
        _spec("assess_quota_allocation",
              "Check a hypothetical additional GiB/object request against one dated tenant quota_id. Both inclusive limits must hold. This checks quota only and never allocates storage.",
              {"quota_id": _enum(QUOTAS), "request_gib": _integer(0, 128),
               "request_objects": _integer(0, 4096)}),
    ]


def read_release_manifest(args):
    return {**args, **RELEASE_MANIFESTS[(args["application"], args["release"])]}


def read_deployment_snapshot(args):
    deployment = DEPLOYMENTS[args["deployment_id"]]
    snapshot = deployment["snapshots"].get(args["snapshot_day"])
    if snapshot is None:
        raise ToolFault("deployment_snapshot_missing")
    return {**args, "application": deployment["application"], **snapshot}


def summarize_incident_window(args):
    if args["start_minute"] >= args["end_minute"]:
        raise ToolFault("invalid_incident_window")
    window = INCIDENT_WINDOWS[(args["route"], args["day"])]
    events = [dict(row) for row in window["events"]
              if args["start_minute"] <= row["minute"] < args["end_minute"]]
    return {**args, "policy_id": window["policy_id"], "events": events,
            "event_count": len(events),
            "critical_count": sum(row["severity"] == "critical" for row in events)}


def assess_incident_policy(args):
    if args["critical_count"] > args["event_count"]:
        raise ToolFault("inconsistent_incident_counts")
    policy = INCIDENT_POLICIES[args["policy_id"]]
    page = (args["event_count"] >= policy["event_threshold"]
            or args["critical_count"] >= policy["critical_threshold"])
    return {**args, **policy, "recommendation": "page" if page else "observe"}


def inspect_package_build(args):
    build = PACKAGE_BUILDS.get((args["package"], args["version"], args["platform"]))
    if build is None:
        raise ToolFault("package_build_missing")
    return {**args, **build}


def assess_test_suite(args):
    suite = TEST_SUITES[args["suite_id"]]
    outcomes = [{"case": name, "outcome": suite["cases"][name]} for name in args["required_cases"]]
    return {**args, "recorded_on": suite["recorded_on"], "outcomes": outcomes,
            "all_passed": all(row["outcome"] == "pass" for row in outcomes)}


def inspect_storage_pool(args):
    pool = POOLS[args["pool"]]
    quota_id = next(name for name, quota in QUOTAS.items()
                    if all(quota[key] == args[key] for key in ("pool", "tenant", "snapshot_day")))
    return {**args, "capacity_gib": pool["capacity_gib"],
            "free_gib": pool["free_gib"][args["snapshot_day"]], "quota_id": quota_id}


def assess_quota_allocation(args):
    quota = QUOTAS[args["quota_id"]]
    gib_after = quota["used_gib"] + args["request_gib"]
    objects_after = quota["used_objects"] + args["request_objects"]
    return {**args, **quota, "gib_after_request": gib_after, "objects_after_request": objects_after,
            "remaining_gib": quota["limit_gib"] - gib_after,
            "remaining_objects": quota["limit_objects"] - objects_after,
            "quota_allows": gib_after <= quota["limit_gib"] and objects_after <= quota["limit_objects"]}


IMPLEMENTATIONS = {
    "read_release_manifest": read_release_manifest,
    "read_deployment_snapshot": read_deployment_snapshot,
    "summarize_incident_window": summarize_incident_window,
    "assess_incident_policy": assess_incident_policy,
    "inspect_package_build": inspect_package_build,
    "assess_test_suite": assess_test_suite,
    "inspect_storage_pool": inspect_storage_pool,
    "assess_quota_allocation": assess_quota_allocation,
}
