"""Publication checks use isolated Git indices, never real credentials."""

import subprocess
import sys
from pathlib import Path

import pytest

SCANNER = Path(__file__).resolve().parents[1] / "scripts/check_public_content.py"


@pytest.fixture
def repository(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def scan(repository):
    return subprocess.run(
        [sys.executable, str(SCANNER)], cwd=repository, capture_output=True, text=True, timeout=10
    )


def stage(repository, name):
    subprocess.run(["git", "-C", str(repository), "add", "--", name], check=True)


@pytest.mark.parametrize("dirty_copy", [True, False])
def test_checks_both_staged_blob_and_working_tree(repository, dirty_copy):
    path = repository / "candidate.txt"
    fake_token = "ghp_" + "z" * 40
    path.write_text("safe index" if dirty_copy else fake_token)
    stage(repository, "candidate.txt")
    path.write_text(fake_token if dirty_copy else "safe working copy")
    result = scan(repository)
    assert result.returncode == 1
    assert fake_token not in result.stdout + result.stderr
    assert "working tree" in result.stdout if dirty_copy else "index" in result.stdout


def test_rejects_staged_symlink_even_after_regular_file_replacement(repository):
    path = repository / "candidate.txt"
    path.symlink_to("absent-file")
    stage(repository, "candidate.txt")
    path.unlink()
    path.write_text("safe replacement")
    result = scan(repository)
    assert result.returncode == 1
    assert "index" in result.stdout and "symlink" in result.stdout


def test_scans_untracked_files_and_accepts_safe_index(repository):
    path = repository / "candidate.txt"
    path.write_text("original public fixture")
    stage(repository, "candidate.txt")
    assert scan(repository).returncode == 0
    (repository / "untracked.txt").write_text("sk-" + "s" * 40)
    assert scan(repository).returncode == 1
