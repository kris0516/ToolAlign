"""Original, fictional CPU resources and six explicitly bound read-only tools.

Resource IDs are enums. No resource is loaded from a dataset, URL or caller path.
These development fixtures are not a hidden final evaluation set.
"""

from __future__ import annotations

from decimal import Decimal

VERSION = "local-devops.v1"

DOCUMENTS = {
    "atlas-1.0": {
        "object": "atlas",
        "version": "1.0",
        "date": "2026-08-01",
        "timeout_ms": 800,
        "minimum_runtime": "3.11",
        "report_id": "atlas-100",
    },
    "atlas-1.1": {
        "object": "atlas",
        "version": "1.1",
        "date": "2026-09-01",
        "timeout_ms": 1200,
        "minimum_runtime": "3.12",
        "report_id": "atlas-110",
    },
    "beacon-1.1": {
        "object": "beacon",
        "version": "1.1",
        "date": "2026-09-01",
        "timeout_ms": 900,
        "minimum_runtime": "3.11",
        "report_id": "beacon-110",
    },
}
REPORTS = {
    "atlas-100": {
        "object": "atlas",
        "version": "1.0",
        "date": "2026-08-01",
        "passed": 8,
        "failed": 2,
        "duration_ms": 800,
    },
    "atlas-110": {
        "object": "atlas",
        "version": "1.1",
        "date": "2026-09-01",
        "passed": 12,
        "failed": 0,
        "duration_ms": 1200,
    },
    "beacon-110": {
        "object": "beacon",
        "version": "1.1",
        "date": "2026-09-01",
        "passed": 9,
        "failed": 1,
        "duration_ms": 900,
    },
}
LOGS = {
    "atlas-september": [
        {"date": "2026-09-01", "level": "info", "message": "Build atlas-110 passed"},
        {"date": "2026-09-01", "level": "error", "message": "Cache unavailable"},
        {"date": "2026-09-02", "level": "error", "message": "Retry limit reached"},
    ],
    "beacon-september": [
        {"date": "2026-09-01", "level": "error", "message": "Build beacon-110 failed"},
    ],
}
RECORDS = {
    "atlas-runs": [
        {"date": "2026-09-01", "duration_ms": 1000, "failed": 0},
        {"date": "2026-09-01", "duration_ms": 1400, "failed": 0},
        {"date": "2026-09-02", "duration_ms": 900, "failed": 1},
    ],
    "beacon-runs": [{"date": "2026-09-01", "duration_ms": 900, "failed": 1}],
}
UNITS = {
    "ms": ("time", Decimal("0.001")),
    "s": ("time", Decimal(1)),
    "min": ("time", Decimal(60)),
    "B": ("bytes", Decimal(1)),
    "KiB": ("bytes", Decimal(1024)),
    "MiB": ("bytes", Decimal(1048576)),
}


class ToolFault(Exception):
    def __init__(self, code, retryable=False):
        self.code = code
        self.retryable = retryable
        super().__init__(code)


def _enum(values):
    return {"type": "string", "maxLength": 64, "enum": list(values)}


def _spec(name, description, properties):
    return {
        "schema_version": "toolalign.tool.v1",
        "name": name,
        "description": description,
        "parameters_json_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
        "tool_version": VERSION,
        "side_effect_class": "read_only",
        "timeout_ms": 1000,
    }


def specs():
    """Fresh schemas for the fixed implementation catalog; not a registration API."""
    dates = _enum(["2026-08-01", "2026-09-01", "2026-09-02"])
    return [
        _spec(
            "lookup_version_document",
            "Retrieve a fictional version document by resource ID.",
            {"resource_id": _enum(DOCUMENTS)},
        ),
        _spec(
            "query_build_report",
            "Retrieve actual test counts from a fictional build report.",
            {"report_id": _enum(REPORTS)},
        ),
        _spec(
            "filter_build_logs",
            "Filter a fixed log resource by exact date and severity.",
            {"resource_id": _enum(LOGS), "date": dates, "level": _enum(["info", "error"])},
        ),
        _spec(
            "aggregate_run_records",
            "Aggregate one numeric field on one exact date.",
            {
                "resource_id": _enum(RECORDS),
                "date": dates,
                "field": _enum(["duration_ms", "failed"]),
                "operation": _enum(["sum", "mean", "count"]),
            },
        ),
        _spec(
            "compare_version_compatibility",
            "Check the runtime minimum in a version document.",
            {
                "resource_id": _enum(DOCUMENTS),
                "runtime_version": _enum(["3.11", "3.12", "3.13", "3.14"]),
            },
        ),
        _spec(
            "convert_numeric_units",
            "Convert time or byte units; incompatible dimensions fail.",
            {
                "value": {"type": "number", "minimum": -1e9, "maximum": 1e9},
                "from_unit": _enum(UNITS),
                "to_unit": _enum(UNITS),
            },
        ),
    ]


def lookup_version_document(args):
    return {"resource_id": args["resource_id"], **DOCUMENTS[args["resource_id"]]}


def query_build_report(args):
    return {"report_id": args["report_id"], **REPORTS[args["report_id"]]}


def filter_build_logs(args):
    rows = [
        row
        for row in LOGS[args["resource_id"]]
        if row["date"] == args["date"] and row["level"] == args["level"]
    ]
    return {**args, "rows": rows, "count": len(rows)}


def aggregate_run_records(args):
    values = [
        row[args["field"]] for row in RECORDS[args["resource_id"]] if row["date"] == args["date"]
    ]
    if not values:
        raise ToolFault("no_records")
    value = {"count": len(values), "sum": sum(values), "mean": sum(values) / len(values)}
    return {**args, "value": value[args["operation"]], "count": len(values)}


def compare_version_compatibility(args):
    doc = DOCUMENTS[args["resource_id"]]
    runtime = tuple(int(x) for x in args["runtime_version"].split("."))
    minimum = tuple(int(x) for x in doc["minimum_runtime"].split("."))
    return {**args, "minimum_runtime": doc["minimum_runtime"], "compatible": runtime >= minimum}


def convert_numeric_units(args):
    source, target = UNITS[args["from_unit"]], UNITS[args["to_unit"]]
    if source[0] != target[0]:
        raise ToolFault("incompatible_units")
    value = Decimal(str(args["value"])) * source[1] / target[1]
    return {**args, "converted_value": float(value)}


# This table is source code owned by E1; model/dataset inputs never extend it.
IMPLEMENTATIONS = {
    "lookup_version_document": lookup_version_document,
    "query_build_report": query_build_report,
    "filter_build_logs": filter_build_logs,
    "aggregate_run_records": aggregate_run_records,
    "compare_version_compatibility": compare_version_compatibility,
    "convert_numeric_units": convert_numeric_units,
}
