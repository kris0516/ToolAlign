# P00 / R1 原创复现与证据

日期：2026-09-06。被审 base `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`，candidate `15706079c9516197b67dd59a19a0d0c4aa5adea8`；结论 **FAIL**。完整优先级/影响/决议见 [REVIEW 交接单](../../../coordination/handoffs/P00-review-r1.md)。本目录不含生产修复、原始训练数据、真实凭据、真实对话 ID 或本机绝对路径。

## 可重复运行

在上述候选加本审查文件的 worktree 中执行：

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv build
uv run --locked python reports/review/P00/verify_wheel.py
uv run --locked pytest -q reports/review/P00/test_independent.py --tb=short
```

原有 pytest 配置只默认发现 `tests/`，因此默认测试通过不能说明本目录负例已通过；须显式运行最后一条命令。候选上的预期实测结果：基础测试 **34 passed**；独立 probes **36 passed / 10 failed**，最后一条退出 **1**。没有 xfail，也没有为了绿色结果改原有测试期待值。

全部 CPU。`verify_wheel.py` 只安装本次已构建的 wheel：以 `uv export --locked --no-dev --no-emit-project` 导出带 hash 的 runtime 依赖，`uv venv --python 3.14` 建临时环境，`uv pip install --require-hashes` 安装依赖，再 `uv pip install --no-deps` 安装 wheel。运行 `uv pip check`、隔离 Python 的 schema digest、五类 console CLI 验证，并确认导入来自临时 venv 且 mlx/torch 不存在。临时环境自动清理；没有模型下载或 GPU 作业。

本次在纯候选上完成 `uv build` 后再添加审查文件；后续重建时 sdist 可能包含审查说明，wheel 的源包范围不因此改变。本次 wheel SHA-256：`0b8131764b0b59340905b4a341c7be4fbe0426411f70c207c2d9bf53460e35df`。安装后 schema SHA-256：`ee3c0620d50639b87519dda77f9be4792e563ad63f74b8bdddb75802bd3f82ad`。

## 失败项单独复现

下列命令均以 `uv run --locked pytest -q reports/review/P00/test_independent.py --tb=short` 为前缀，附相应 `-k`。各次失败断言表示候选未满足拒绝规则，不是外部环境未就绪。

| ID | `-k` 选择器 | 候选失败数 | 观察 |
|---|---|---:|---|
| R1-01 | `forbidden_schema_cannot_hide` | 3 | object 的 items 引用、string 的 properties 引用、object 的 items 正则均被接受；受检 socket/DNS 未调用 |
| R1-02 | `public_scan_checks_staged` | 1 | index 保留合成 token，工作副本擦除后 scanner 错误退出 0；擦除前控制扫描退出 1 |
| R1-03 | `cli_error_does_not_echo` | 1 | stderr 包含数据控制的 `synthetic_private_marker` |
| R1-04 | `identity_fields_reject` | 4 | Git/model hash、tool name、trace ID 接受末尾 LF |
| R1-05 | `target_call_ids` | 1 | 当前目标重复历史 call ID 仍被接受 |

R1-01 的最小结构是在原有 tool fixture 的 `parameters_json_schema` 根加入：

```json
{"items": {"$ref": "https://example.invalid/schema"}}
```

原根 `type=object`、properties/required/additionalProperties 均保留。这是在不适用位置藏入禁止 schema 的例子；此版本 jsonschema 没有使用该 items，不应声称它已访问网络。

R1-02 只在测试创建的临时 Git repo 中构造一次性假 token，不联网、不提交。测试先证明原 matcher 能检测该标记，再保留 staged blob 而擦除工作副本，最后要求扫描仍失败。因此问题在扫描对象选择，不在假 token 未匹配 regex。

R1-05 的输入先包含 assistant `call-1` 及配对 tool observation，再令 expected_action 使用 `call-1`。当前 validate_record 接受该样本。额外手动复现：将相同目标/observation 再追加到 messages、把新目标设为 final，同一 validator 报 `Call IDs must be unique within a conversation`；这说明两个单步样本衔接不一致。

## 实际命令与原始日志索引

下表全部来自 R1 本次执行。日志在审查 worktree 的私有目录 `.toolalign-local/evidence/review-P00-r1/`，索引为该目录 `index.json`；表中仅存相对文件名和原始 stdout+stderr 的 SHA-256。原始 pytest 失败输出可能带测试环境路径，未复制到公共目录。

| 命令 | 退出码 / 结果 | 私有日志相对名 | 原始日志 SHA-256 |
|---|---|---|---|
| `uv sync --locked --python 3.14` | 0；Python 3.14.7；初次已在干净 worktree 成功建 venv，表内为带日志复验 | `sync.log` | `f07b680681692fab879165c792595d9b50183fd432eff61bf6abc0d15200184e` |
| `uv run --locked pytest -q` | 0；34 passed | `pytest.log` | `64f6187e0148485c328151d1263ccb3fbac29497f0f0bd9c51be0075f162ce91` |
| `uv run --locked ruff check .` | 0；All checks passed | `ruff.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0；4 files | `contract-freeze.log` | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0；干净候选 82 个文件 | `public-scan.log` | `de5b35d2f92d4c3d8a95dcd6f164461469c9d6ff12380a9429e1ada5090568a0` |
| `uv build` | 0；sdist + wheel | `build.log` | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv run --locked python reports/review/P00/verify_wheel.py` | 0；全部内部步骤退出 0 | `wheel-independent.log` | `644578ea0b5e2969f6f6ffd601be7f856f85b0de83e536310bb5ee4376ed21f4` |
| `uv run --locked pytest -q reports/review/P00/test_independent.py --tb=short` | **1；36 passed / 10 failed** | `independent-final.log` | `86dca58b20fd6e9653afff5528011f735f54e1321ffa1dbefbfb05921fa67cfc` |

最终提交前再检验 review 文件的 lint、公开内容和 diff 范围；结果通过任务交回。未复用 S0 私有自测日志作为上述证据。没有进行 GitHub CI 读回、Python 3.11/3.12/3.13 本机验证、GPU 性能测试、模型/数据/真实 oracle 评测、main 合并验收或 P01–P03 实现，这些均为 NOT_RUN。
