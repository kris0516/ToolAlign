# Contributing to ToolAlign

Documentation corrections, small reproducible bug reports, and improvements to the public CPU examples are useful starting points. Read the [README](README.md) for the current results and the [reproduction guide](docs/19_REPRODUCTION_AND_DELIVERY.md) for the boundary between public examples and recorded model experiments.

## Report an issue

Open a [GitHub issue](https://github.com/kris0516/ToolAlign/issues) with:

- The commit, Python/uv versions, and operating system.
- The exact command and a minimal public input or scripted example.
- Expected behavior, observed behavior, and relevant sanitized output.

Separate format validity, successful tool execution, and complete task success. Keep reported failures and `NOT_RUN` outcomes visible. Do not attach credentials, private conversations, raw datasets, model weights, adapters, hidden evaluation inputs/answers, or local task identifiers. Source and redistribution boundaries are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Propose a change

Keep each PR focused and work on a separate branch/worktree. Describe what changes for a reader or caller, cite the evidence for result claims, and include the checks actually run. Documentation-only changes need content, link, and publication checks; do not rerun model experiments merely to edit documentation.

Coordinated Codex work follows [AGENTS.md](AGENTS.md) and the [collaboration protocol](coordination/PROTOCOL.md): independent Codex conversations and isolated worktrees, no sub-agents, R1 review, and S1 integration. S1 owns `coordination/BOARD.md`, `coordination/PROJECT_STATUS.md`, and `coordination/DECISIONS.md`, and coordinates shared contracts and dependencies. Offer unassigned changes as a **draft PR** for coordination; do not mark them accepted or merge them yourself.

## Checks

From the repository root, after installing the locked CPU environment in the README:

```sh
git diff --check
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
```

Check relative links and documented commands against the changed source. For code changes, run the affected tests and `uv run --locked ruff check .`; give each test run a new, task-specific `--basetemp` directory as required by the collaboration protocol. The [CPU workflow](.github/workflows/cpu.yml) also runs the full suite and source-distribution checks on pull requests. Report skipped or unrun checks explicitly.

Original code and documentation retain the [MIT license](LICENSE). Third-party material retains its own terms; a contribution must not silently change those terms or publish private research artifacts.
