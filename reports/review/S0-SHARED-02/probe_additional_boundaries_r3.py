"""Check additional case-sensitive boundary details using only synthetic public/private bytes."""

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from hatchling.builders.sdist import SdistBuilder
from probe_case_boundaries_r2 import ROOT, archive_files, run

PRIVATE = (
    ".dS_sToRe", ".PyTeSt_CaChE/sample.json", ".MyPy_CaChE/sample.json",
    ".RuFf_CaChE/sample.json", ".CoVeRaGe", "HtMlCoV/sample.json",
    ".CoDeX/sample.json", ".WoRkTrEeS/sample.json", ".ToOlAlIgN-LoCaL/sample.json",
    "sample.PyC", "sample.pYd", "sample.PYo", ".ENV.EXAMPLES", ".eNv.ExAmPlE.private",
)
PUBLIC = (
    ".env.example", ".ENV.EXAMPLE", ".eNv.eXaMpLe", "weights.PT.example",
    "credentials.KEY.example", "sample.PYI", "ordinary-public.JSON",
)


def main():
    tracked = run(["git", "ls-files", "-z"], ROOT).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="r3-extra-boundaries-") as temporary:
        parent = Path(temporary)
        repository = parent / "repository"
        repository.mkdir()
        for name in filter(None, tracked):
            source, destination = ROOT / name, repository / name
            assert source.is_file() and not source.is_symlink()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        run(["git", "init", "-q"], repository)
        run(["git", "add", "."], repository)
        run(["git", "-c", "user.name=Review Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "--no-gpg-sign", "-qm", "Public r3 fixture"], repository)
        checkout = parent / ".codex/worktrees/fixture"
        checkout.parent.mkdir(parents=True)
        run(["git", "worktree", "add", "--detach", "-q", str(checkout), "HEAD"], repository)
        assert (checkout / ".git").is_file()
        assert run(["git", "config", "--get", "core.ignorecase"], checkout).strip() == b"true"
        assert not SdistBuilder(str(checkout)).config.load_vcs_exclusion_patterns()
        marker = b"R3_SYNTHETIC_PRIVATE_" + os.urandom(24)
        private = [f"{directory}/r3-private-{index}/{name}"
                   for directory in ("configs", "tests", "src/toolalign")
                   for index, name in enumerate(PRIVATE)]
        private += [f"DaTa/{directory}/r3-private.json" for directory in ("RaW", "PrOcEsSeD", "PrIvAtE")]
        for name in private:
            path = checkout / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(marker)
            assert run(["git", "check-ignore", "--", name], checkout).strip()
        public = {}
        for directory in ("configs", "tests", "src/toolalign"):
            for index, name in enumerate(PUBLIC):
                relative = f"{directory}/r3-public-{index}/{name}"
                data = b"R3_PUBLIC: bool\n" if name.endswith(".PYI") else b'{"synthetic_public":true}\n'
                path = checkout / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                public[relative] = data
        visible = set(run(["git", "ls-files", "--others", "--exclude-standard", "-z"], checkout).decode().split("\0"))
        assert set(public) <= visible and not set(private) & visible
        expected = {name: (checkout / name).read_bytes() for name in filter(None, tracked)
                    if name.startswith(("src/toolalign/", "configs/", "tests/"))} | public
        run(["uv", "run", "--locked", "python", "scripts/check_public_content.py"], checkout)
        artifacts = parent / "artifacts"
        run(["uv", "build", "--sdist", "--out-dir", str(artifacts)], checkout)
        (sdist,) = artifacts.glob("toolalign-*.tar.gz")
        outputs = {"sdist": archive_files(sdist)}
        for route, source in [("wheel-from-sdist", str(sdist)), ("wheel-direct", ".")]:
            destination = artifacts / route
            run(["uv", "build", "--wheel", "--out-dir", str(destination), source], checkout)
            (wheel,) = destination.glob("toolalign-*.whl")
            outputs[route] = archive_files(wheel, wheel=True)
        for route, files in outputs.items():
            leaked = sorted(name for name, data in files.items() if marker in data)
            wanted = expected if route == "sdist" else {
                name.removeprefix("src/"): data for name, data in expected.items()
                if name.startswith("src/toolalign/")
            }
            assert not leaked, leaked
            assert all(files.get(name) == data for name, data in wanted.items())
            print(json.dumps({"route": route, "ignored_private_inputs": len(private),
                              "new_public_inputs": len(public), "public_files_preserved": len(wanted),
                              "private_leaks": leaked, "git_core_ignorecase": True,
                              "git_setting_forced": False, "hatch_vcs_rules": 0,
                              "archive_files": len(files)}, sort_keys=True), flush=True)
        print("schema_sha256=" + hashlib.sha256(
            outputs["wheel-direct"]["toolalign/contracts/v1.json"]
        ).hexdigest())
        print("PASS: extra privacy classes, exact public exceptions and public bytecode lookalikes")


if __name__ == "__main__":
    main()
