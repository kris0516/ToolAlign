"""Read-only historical audit bound to the original candidate, never E1's new edits.

No worker scripts, backend generators, executor, or production oracle are invoked.
Only the already-frozen wire validator is reused; transcript reconstruction is independent.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import stat
import subprocess
import tarfile
import tomllib
import zipfile
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path, PurePosixPath

from toolalign.contracts import validate_record

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "79a15d990fc27a9a33d033983c94eb92cccfb268"
ORIGINAL = "85e0905fc82da4504d73bf7eb489c1f1a0d227a7"
IMPLEMENTATION = "8afb114bd14e69d3a2138212ab423147809fed63"
BASE = "37c00de9abe92e6fb24a0c0e0b7361aa4bb90385"
SYNC = "f2a271be616cdb53c01e8d671029f31ae140c037"
MERGE = "86c5e8abaf0a6518fda0d33dba1b68eb6815737a"
REGISTRY = "6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compact(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def identity(value):
    return sha(compact(value).encode())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(commit, name):
    return git("show", commit + ":" + name)


def safe_file(base, relative):
    name = PurePosixPath(relative)
    assert not name.is_absolute() and ".." not in name.parts and "\\" not in relative
    path = base.joinpath(*name.parts)
    assert not any(
        base.joinpath(*name.parts[:i]).is_symlink() for i in range(1, len(name.parts) + 1)
    )
    assert path.resolve().is_relative_to(base.resolve()) and path.is_file()
    assert path.stat().st_size <= 2 * 1024**2
    return path


def read(base, relative):
    return json.loads(safe_file(base, relative).read_bytes())


def same_value(actual, expected):
    if type(actual) in (int, float) and type(expected) in (int, float):
        return Fraction(str(actual)) == Fraction(str(expected))
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            same_value(actual[k], expected[k]) for k in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            same_value(a, b) for a, b in zip(actual, expected)
        )
    return actual == expected


def audit_demo(directory, cases, bound_source_hash):
    totals = Counter()
    results = Counter()
    checked = {}
    for index, case in enumerate(cases):
        name = f"case-{index:02d}.json"
        item = read(directory, name)
        checked[name] = sha(safe_file(directory, name).read_bytes())
        trace, decisions = item["trace"], item["decisions"]
        manifest = item["registry_manifest"]
        assert identity(manifest) == REGISTRY
        assert len(manifest["tools"]) == 6
        for binding in manifest["tools"]:
            assert binding["source_hash"] == bound_source_hash
            assert binding["schema_hash"] == identity(binding["spec"]["parameters_json_schema"])
            assert binding["implementation"] == "toolalign.tools.catalog:" + binding["spec"]["name"]
            validate_record(binding["spec"], "tool")
        prefix = {
            "messages": [
                {"role": "user", "content": case["prompt"], "tool_calls": [], "tool_call_id": None}
            ],
            "tools": [binding["spec"] for binding in manifest["tools"]],
        }
        assert item["provenance"]["model_input_hash"] == identity(prefix)
        assert item["provenance"]["oracle_payload_hash"] == identity(
            {
                "version": "toolalign.semantic-local.v1",
                "answers": case["answers"],
                "strategies": case["strategies"],
            }
        )
        assert item["provenance"]["registry_hash"] == REGISTRY
        config = item["provenance"]["generation_config"]
        assert config == {
            "seed": 0,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_new_tokens": 256,
            "deadline_utc": trace[0]["deadline_utc"],
            "enable_thinking": False,
        }
        expected_events = ["received", "validated"]
        attempts = [event for event in trace if event["event"] == "tool_execution"]
        observations = [event for event in trace if event["event"] == "observing"]
        assert len(attempts) == len(observations)
        observed_index, rounds = 0, 0
        actual_strategy = []
        assert len(decisions) == len(case["scripted_responses"])
        for decision, raw in zip(decisions, case["scripted_responses"]):
            assert decision["model_input_hash"] == identity(prefix)
            assert decision["raw_text"] == raw
            action = json.loads(raw)
            assert decision["raw_action"] == action
            assert all(
                decision[key] is None
                for key in (
                    "raw_parse_failure",
                    "repaired_output",
                    "backend_parsed_action",
                    "backend_parse_failure",
                )
            )
            assert decision["input_tokens"] == 11 and decision["output_tokens"] == 7
            assert decision["finish_reason"] == "stop"
            expected_events.extend(["generating", "parsing"])
            if action["kind"] == "tool_calls":
                rounds += 1
                tool_messages = []
                for call in action["tool_calls"]:
                    attempt, observation = attempts[observed_index], observations[observed_index]
                    observed_index += 1
                    assert attempt["tool_call"] == observation["tool_call"] == call
                    assert attempt["event_index"] + 1 == observation["event_index"]
                    result = observation["tool_result"]
                    assert result["call_id"] == call["call_id"]
                    actual_strategy.append(
                        {
                            "name": call["name"],
                            "arguments": call["arguments"],
                            **{
                                key: result[key]
                                for key in ("status", "output", "error_code", "retryable")
                            },
                        }
                    )
                    tool_messages.append(
                        {
                            "role": "tool",
                            "content": compact(result),
                            "tool_calls": [],
                            "tool_call_id": call["call_id"],
                        }
                    )
                    expected_events.extend(["tool_execution", "observing"])
                    results[result["status"]] += 1
                prefix["messages"].append(
                    {
                        "role": "assistant",
                        "content": action["content"],
                        "tool_calls": action["tool_calls"],
                        "tool_call_id": None,
                    }
                )
                prefix["messages"].extend(tool_messages)
            else:
                assert action == item["final_result"]
                assert any(
                    answer["kind"] == action["kind"]
                    and same_value(json.loads(action["content"]), answer["value"])
                    for answer in case["answers"]
                )
        expected_events.append("finalized")
        assert observed_index == len(observations)
        assert [event["event"] for event in trace] == expected_events
        assert any(same_value(actual_strategy, strategy) for strategy in case["strategies"])
        for event_index, event in enumerate(trace):
            validate_record(event, "trace")
            assert event["event_index"] == event_index
            assert all(
                event[key] == trace[0][key]
                for key in ("trace_id", "request_id", "deadline_utc", "model")
            )
            assert event["parse_failure"] is None and event["validation_failure"] is None
            assert event["budget_consumed"]["model_decisions"] <= 3
            assert event["budget_consumed"]["tool_rounds"] <= 2
            if event_index:
                before = trace[event_index - 1]
                assert event["latency_ms"] >= before["latency_ms"]
                assert all(
                    event["budget_consumed"][key] >= count
                    for key, count in before["budget_consumed"].items()
                )
        assert trace[-1]["budget_consumed"] == {
            "model_decisions": len(decisions),
            "tool_rounds": rounds,
            "input_tokens": len(decisions) * 11,
            "output_tokens": len(decisions) * 7,
        }
        assert item["score"] == trace[-1]["task_outcome"]
        assert item["score"]["outcome"] == "success" and item["token_accounting_complete"]
        processes = item["process_records"]
        assert len(processes) == 1 + len(observations)
        assert sum(entry["label"] == "model" for entry in processes) == 1
        assert all(
            entry["operation_started"] and entry["reaped"] and entry["exitcode"] is not None
            for entry in processes
        )
        assert len({entry["owner_id"] for entry in processes}) == len(processes)
        totals.update(
            cases=1,
            trace_events=len(trace),
            model_decisions=len(decisions),
            tool_rounds=rounds,
            synthetic_input_tokens=len(decisions) * 11,
            synthetic_output_tokens=len(decisions) * 7,
            owned_processes=len(processes),
            reaped_processes=len(processes),
            operations_started=len(processes),
        )
    assert dict(totals) == {
        "cases": 10,
        "trace_events": 90,
        "model_decisions": 20,
        "tool_rounds": 10,
        "synthetic_input_tokens": 220,
        "synthetic_output_tokens": 140,
        "owned_processes": 20,
        "reaped_processes": 20,
        "operations_started": 20,
    }
    assert dict(results) == {"completed": 9, "error": 1}
    summary = read(directory, "summary.json")
    assert summary["total"] == summary["success"] == 10 and summary["excluded"] == 0
    assert summary["failure"] == summary["unknown"] == summary["not_scored"] == 0
    assert summary["synthetic_tokens_only"] and summary["real_model_benchmark"] == "NOT_RUN"
    assert summary["formal_hidden_test"] == "NOT_RUN" and summary["repairs"] == "DISABLED"
    checked["summary.json"] = sha(safe_file(directory, "summary.json").read_bytes())
    assert (
        checked["summary.json"]
        == "7491882e51f13f2b800834d17b155c5f7941187ba044fd00b5785487d4334396"
    )
    return {
        "counts": dict(totals),
        "tool_results": dict(results),
        "artifact_sha256": checked,
        "actual_process_liveness_now": "NOT_INFERRED_FROM_HISTORICAL_RECORDS",
    }


def archive_check(path, expected, generated):
    members = {}
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            assert sum(member.size for member in archive.getmembers()) < 25 * 1024**2
            for member in archive.getmembers():
                name = PurePosixPath(member.name)
                assert name.parts[0] == "toolalign-0.0.1"
                assert not name.is_absolute() and ".." not in name.parts
                if member.isdir():
                    continue
                assert member.isfile() and not member.issym() and not member.islnk()
                relative = str(PurePosixPath(*name.parts[1:]))
                assert relative not in members
                members[relative] = archive.extractfile(member).read()
    else:
        with zipfile.ZipFile(path) as archive:
            assert sum(member.file_size for member in archive.infolist()) < 25 * 1024**2
            for member in archive.infolist():
                name = PurePosixPath(member.filename)
                assert not name.is_absolute() and ".." not in name.parts
                assert stat.S_IFMT(member.external_attr >> 16) != stat.S_IFLNK
                assert member.filename not in members
                members[member.filename] = archive.read(member)
    assert set(members) == set(expected) | generated
    assert all(members[name] == data for name, data in expected.items())
    return {
        "sha256": sha(path.read_bytes()),
        "bytes": path.stat().st_size,
        "archive_files": len(members),
        "tracked_files_matched": len(expected),
        "generated_metadata_files": len(generated),
        "untracked_payloads": 0,
    }


def package_expectations():
    config = tomllib.loads(blob(CANDIDATE, "pyproject.toml").decode())
    roots = config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    names = git("ls-tree", "-r", "--name-only", CANDIDATE).decode().splitlines()
    expected = {
        name: blob(CANDIDATE, name)
        for name in names
        if name == ".gitignore"
        or any(name == root or name.startswith(root + "/") for root in roots)
    }
    wheel = {
        name.removeprefix("src/"): data
        for name, data in expected.items()
        if name.startswith("src/toolalign/")
    }
    metadata = {
        "toolalign-0.0.1.dist-info/" + name
        for name in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")
    }
    return expected, wheel, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e1-root", type=Path, required=True)
    parser.add_argument("--package-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    e1 = args.e1_root.resolve(strict=True)
    old, new = e1 / ".toolalign-local/p03", e1 / ".toolalign-local/p03-base-r2"
    preserved = read(new, "preserved-r1.json")
    assert preserved["previous_head"] == ORIGINAL
    assert len(preserved["public_files"]) == 17 and len(preserved["prior_private_files"]) == 63
    for name, digest in preserved["public_files"].items():
        # E1 may be actively repairing; its mutable worktree is deliberately not used.
        assert sha(blob(ORIGINAL, name)) == sha(blob(CANDIDATE, name)) == digest
        assert sha((ROOT / name).read_bytes()) == digest
    for name, digest in preserved["prior_private_files"].items():
        assert sha(safe_file(old, name).read_bytes()) == digest
    assert git("show", "-s", "--format=%P", MERGE).decode().split() == [ORIGINAL, SYNC]
    changed = git("diff", "--name-only", SYNC, CANDIDATE).decode().splitlines()
    assert len(changed) == 19
    assert not git(
        "diff",
        SYNC,
        CANDIDATE,
        "--",
        "src/toolalign/data",
        "src/toolalign/training",
        "pyproject.toml",
        "uv.lock",
    )
    for name in ("pyproject.toml", "uv.lock", "contracts.v1.lock.json"):
        assert blob(CANDIDATE, name) == blob(BASE, name)
    commands = []
    for label, directory in (("original", old), ("base-r2", new)):
        for path in sorted((directory / "checks").glob("*.json")):
            metadata = read(directory, "checks/" + path.name)
            log = safe_file(directory, "checks/" + path.stem + ".log")
            assert metadata["label"] == path.stem
            assert sha(log.read_bytes()) == metadata["log_sha256"]
            assert datetime.fromisoformat(metadata["started_at"]).tzinfo is not None
            assert metadata["elapsed_seconds"] >= 0
            item = copy.deepcopy(metadata)
            item.update(group=label, log_bytes=log.stat().st_size)
            commands.append(item)
    assert read(old, "checks/pytest-commit.json")["head"] == IMPLEMENTATION
    assert read(new, "checks/cpu.json")["head"] == MERGE
    assert "191 passed" in safe_file(old, "checks/pytest-commit.log").read_text()
    assert "309 passed" in safe_file(new, "checks/cpu.log").read_text()
    corrected = read(new, "final-check-summary.json")
    for name, digest in corrected["helper_sha256"].items():
        assert sha(safe_file(new, name).read_bytes()) == digest
    installed = read(new, "isolated-verification.json")
    assert len(installed["commands"]) == 15
    for item in installed["commands"]:
        assert item["exit_code"] == 0
        assert (
            sha(safe_file(new, "isolated/" + item["label"] + ".log").read_bytes())
            == item["log_sha256"]
        )
    cases = json.loads(blob(CANDIDATE, "tests/fixtures/tools/development.json"))["cases"]
    source_hash = sha(blob(CANDIDATE, "src/toolalign/tools/catalog.py"))
    demos = {
        "original-candidate": audit_demo(old / "demo-candidate", cases, source_hash),
        "base-r2-installed": audit_demo(new / "isolated/demo", cases, source_hash),
    }
    original_manifest = read(old, "demo-artifact-manifest.json")
    assert demos["original-candidate"]["artifact_sha256"] == original_manifest["files"]
    sdist, wheel, metadata = package_expectations()
    expected_archives = read(new, "artifact-verification.json")["archives"]
    archives = {}
    for row in expected_archives:
        route = row["route"]
        path = args.package_snapshot / (
            ("rebuilt-" if route == "rebuilt-wheel" else "") + row["filename"]
        )
        checked = archive_check(
            path,
            sdist if route == "sdist" else wheel,
            {"PKG-INFO"} if route == "sdist" else metadata,
        )
        assert all(checked[key] == row[key] for key in checked)
        archives[route] = checked
    result = {
        "candidate": CANDIDATE,
        "production_base": BASE,
        "candidate_changed_files": changed,
        "original_public_files_bound_to_both_commits": preserved["public_files"],
        "original_private_files_unchanged": preserved["prior_private_files"],
        "commands": commands,
        "historical_installed_commands": installed["commands"],
        "historical_installed_blocking_probe": installed["process_probe"],
        "demos": demos,
        "archives": archives,
        "original_command_count": sum(item["group"] == "original" for item in commands),
        "base_r2_command_count": sum(item["group"] == "base-r2" for item in commands),
        "own_new_ml_or_model_execution": "NOT_RUN",
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    encoded = encoded.replace(str(e1), "<E1_WORKTREE>").replace(str(ROOT), "<R1_WORKTREE>")
    args.output.write_text(encoded + "\n")
    print(
        json.dumps(
            {
                "result": "PASS",
                "candidate": CANDIDATE,
                "original_public_files": 17,
                "original_private_files": 63,
                "command_logs": len(commands),
                "installed_command_logs": 15,
                "demos": {key: value["counts"] for key, value in demos.items()},
                "archives": archives,
                "audit_sha256": sha((encoded + "\n").encode()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
