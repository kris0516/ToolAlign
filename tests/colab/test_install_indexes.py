"""Parse the actual CUDA lock without resolving or downloading its packages.

Run with pip available on PYTHONPATH; the Colab regression uses pip 24.0.
"""

import json
import sys
from pathlib import Path

import pytest
from test_control import remote


@pytest.mark.parametrize("cli_extra_index", [True, False], ids=["setup-command", "lock-only"])
def test_pip_keeps_both_indexes_after_parsing_cuda_lock(cli_extra_index, record_property):
    pip = pytest.importorskip("pip", reason="requires the pip parser; no installation is performed")
    from pip._internal.commands import create_command
    from pip._internal.req.req_file import parse_requirements

    repository = Path(__file__).resolve().parents[2]
    argv = remote.setup_commands(repository, sys.executable)[1][4:]
    if not cli_extra_index:
        index = argv.index("--extra-index-url")
        del argv[index:index + 2]
    command = create_command("install", isolated=True)
    options, _ = command.parse_args(argv)
    with command._build_session(options) as session:
        finder = command._build_package_finder(options, session)
        record_property("pip_version", pip.__version__)
        record_property("pip_module", pip.__file__)
        record_property("before_indexes", json.dumps(finder.index_urls))
        requirements = list(parse_requirements(
            str(repository / remote.LOCK_FILE), session=session, finder=finder, options=options,
        ))
        record_property("after_indexes", json.dumps(finder.index_urls))
        record_property("requirements_count", len(requirements))
        assert finder.index_urls == ["https://pypi.org/simple", remote.CUDA_INDEX]
        assert any(item.requirement.strip() == "torch==2.8.0+cu128" for item in requirements)
