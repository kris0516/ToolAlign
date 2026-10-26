"""Read exact official bytes; materialize answers only after a saved selection."""

from __future__ import annotations

import hashlib
import itertools
import subprocess
from pathlib import Path

from toolalign.data.common import loads, read_json, write_json
from toolalign.data.training_selection import new_private_directory

from . import CATEGORIES, COMMIT, PACKAGE, REPOSITORY, SCAN_LIMIT


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=180)


def question_path(category):
    if category not in CATEGORIES:
        raise ValueError("unsupported_bfcl_category")
    return f"{PACKAGE}/bfcl_eval/data/BFCL_v4_{category}.json"


def fetch_source(output):
    root = new_private_directory(output)
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", REPOSITORY)
    git(root, "fetch", "--filter=blob:none", "--depth=1", "origin", COMMIT)
    git(root, "sparse-checkout", "set", "--no-cone", "/LICENSE", f"/{PACKAGE}/**/*.py",
        f"/{PACKAGE}/pyproject.toml", f"/{PACKAGE}/README.md", *("/" + question_path(c) for c in CATEGORIES))
    git(root, "checkout", "--detach", "FETCH_HEAD")
    return source_identity(root)


def source_identity(root):
    root = Path(root).resolve()
    if git(root, "rev-parse", "HEAD").decode().strip() != COMMIT:
        raise ValueError("bfcl_source_commit_mismatch")
    selected = {"LICENSE", f"{PACKAGE}/pyproject.toml", f"{PACKAGE}/README.md"}
    selected.update(question_path(c) for c in CATEGORIES)
    records = {}
    for entry in git(root, "ls-tree", "-rz", "--full-tree", COMMIT, "LICENSE", PACKAGE).split(b"\0"):
        if not entry:
            continue
        metadata, encoded_name = entry.split(b"\t")
        name = encoded_name.decode()
        if name not in selected and not name.endswith(".py"):
            continue
        mode, kind, digest = metadata.decode().split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError("unsupported_bfcl_source_member")
        data = (root / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != digest:
            raise ValueError("bfcl_source_bytes_mismatch:" + name)
        records[name] = {"git_blob": digest, "sha256": hashlib.sha256(data).hexdigest(),
                         "bytes": len(data), "url": REPOSITORY.removesuffix(".git") + "/blob/" + COMMIT + "/" + name}
    if not selected <= records.keys():
        raise ValueError("bfcl_source_incomplete")
    return {"commit": COMMIT, "repository": REPOSITORY, "files": records}


def first_questions(root):
    """Never parse IDs beyond the first fifty, even when a category retains zero."""
    rows = []
    for category in CATEGORIES:
        with (Path(root) / question_path(category)).open(encoding="utf-8") as stream:
            for ordinal, line in enumerate(itertools.islice(stream, SCAN_LIMIT)):
                rows.append({"category": category, "ordinal": ordinal, "record": loads(line)})
    return rows


def selected_answers(root, selection_path, selection_sha256, output):
    """Read answer rows by the frozen prompt ordinal, as the official runner does."""
    path = Path(selection_path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != selection_sha256:
        raise ValueError("selection_hash_mismatch")
    selection = read_json(path)
    if selection.get("status") != "FROZEN" or selection.get("official_commit") != COMMIT:
        raise ValueError("nonempty_frozen_selection_required")
    chosen = selection["selected"]
    if not chosen:
        raise ValueError("no_selected_answers_to_read")
    identity = source_identity(root)
    if identity != read_json(path.parent / "source.json"):
        raise ValueError("selection_source_binding")
    output = new_private_directory(output)
    answers, sources = {}, {}
    for category in CATEGORIES:
        local = [row for row in chosen if row["category"] == category]
        if not local or category == "irrelevance":
            continue
        relative = f"{PACKAGE}/bfcl_eval/data/possible_answer/BFCL_v4_{category}.json"
        raw = git(root, "show", COMMIT + ":" + relative)
        (output / f"{category}.original.jsonl").write_bytes(raw)
        sources[category] = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
                             "url": REPOSITORY.removesuffix(".git") + "/blob/" + COMMIT + "/" + relative}
        by_ordinal = {row["ordinal"]: row for row in local}
        for ordinal, line in enumerate(itertools.islice(raw.splitlines(), max(by_ordinal) + 1)):
            if ordinal in by_ordinal:
                value = loads(line.decode())
                answers[by_ordinal[ordinal]["task_id"]] = {
                    "answer_id": value["id"], "prompt_ordinal": ordinal, "ground_truth": value["ground_truth"]}
        if any(row["task_id"] not in answers for row in local):
            raise ValueError("missing_official_answer_ordinal")
    result = {"official_commit": COMMIT, "selection_sha256": selection_sha256,
              "sources": sources, "answers": answers}
    write_json(output / "answers.json", result)
    return result
