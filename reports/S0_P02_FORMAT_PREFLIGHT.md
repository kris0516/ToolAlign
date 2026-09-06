# P02 格式｜S0 隔离组合预检

2026-09-06；S0。**本地候选组合检查通过，独立 R1 与主干验收仍待完成。** 本轮提前检查新格式与已验收 P01/P02/P03 的组合，没有推送集成分支或将格式合入 main，也没有模型/训练运行。

## 提交与范围

S0 在自己的新隔离 worktree 从 main `4e04f2af482c753679a0bc6b438ce536c45d3d28` 普通 merge 完整格式候选 `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`，得到本地暂定提交 `f600b9506b0fbc3fdfeed1d5c4dcc61452a3c7cf`。两个父提交均保留，tree 为 `a8b1f2c364c1a3f122898332c03a6fe8993e4d0f`。276 份原 main 文件和 21 份候选新增文件逐字节匹配，没有修改 worker 或被审实现。该本地提交未公开推送；已公开父提交及上述 tree 可用于重建组合。

精确原候选的 [Draft PR8](https://github.com/kris0516/ToolAlign/pull/8) 与 [双 Python CI](https://github.com/kris0516/ToolAlign/actions/runs/34017408825)保持；R1 继续审冻结的 7bada2e，未接入 S0 组合或随后状态文档。

## 实际 CPU 结果

07:02–07:05 UTC，Python 3.14.7，纯 CPU、离线。复用 S0 已有固定 CPU/tokenizer 环境及原来源文件。

| 检查 | 退出码与范围 | 原始日志 SHA-256 |
|---|---|---|
| 完整组合回归 | 0；**768 passed，0 skipped**，46.30s | `7c428b42c4142632dad15482bee10eaee2a64cef8ee45bfa20e15e698c264682` |
| lint 首次调用 | 1；S0 选用的 CPU 环境没有 Ruff | `59c58574a0b8d9adb07275900066fec4b9bcdcf7236bdb657355dca3b0bc3e4e` |
| lint 更正调用 | 0；只改用既有工具环境，无代码修改 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 冻结契约 | 0；4 个绑定文件 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| 公开扫描 | 0；297 个追踪路径 | `393fb0658a78d8ad9aed64ece21ed4ca6b994f0456bc9ce2971f5e1c53185bc4` |
| 实际 sdist/默认 wheel | 0；默认 wheel 来自该 sdist | `9ce25d0e9a26f075a3e8f8f73f8dc8b4769b42a218622eb5c5fd686b26384953` |
| 显式 sdist 重建 wheel | 0 | `459a84f95f84d59fe748482085b3b49aadfc7fd2a896cb2e4e63aaceaabbb87f` |
| 归档核对与隔离接口 | 0；10 条子命令通过 | `e75bbacd4da4b90df5b43e5baff1f3516f70faf6c9a3a859d09d342775c56c71` |

768 = 原 main 组合 655 项 + 新格式 113 项。包含未修改的 P00/P02/P03/P01 原独立反例和真实 native tokenizer 回归；它们是组合复验，不是本轮 R1 新增独立场景。pytest 临时目录位于独立系统临时路径。完整原命令和退出码在私有摘要中绑定，首轮 lint 的失败保留。

```bash
PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$FIXED_TOKENIZER_DIR" "$S0_CPU_PYTHON" -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py reports/review/P01/test_p01_processes.py reports/review/P01/test_p01_failure_counters.py reports/review/P01-r2/test_p01_r2_regressions.py reports/hardware/P01_FIX_R3_REPORT_TESTS.py reports/hardware/P01_FIX_R4_REPORT_TESTS.py --basetemp="$SYSTEM_PYTEST_TEMP"
uv build --offline --no-python-downloads --out-dir "$NEW_ARCHIVES/default"
uv build --offline --no-python-downloads --wheel --out-dir "$NEW_ARCHIVES/rebuilt" "$NEW_ARCHIVES/default/toolalign-0.0.1.tar.gz"
python reports/data/P02_FORMAT_V1_PACKAGE.py --root . --archives "$NEW_ARCHIVES" --out "$NEW_PRIVATE_PACKAGE_CHECK"
```

## 包与安装

| 实际归档 | Bytes / 成员数 | SHA-256 |
|---|---|---|
| sdist | 209074 / 99 | `c86943563cea190c09d4c45624f536c350cc3e33ad8b80897d6f26df20736517` |
| 默认 wheel，由同次 sdist 生成 | 106547 / 52 | `c7364da0874f0573b534bafac4aad8d8178ba501980ac914c72f89598488bf8b` |
| 显式 sdist 重建 wheel | 106547 / 52 | `c7364da0874f0573b534bafac4aad8d8178ba501980ac914c72f89598488bf8b` |

未变的 D1 包核验器检查当前 Git/工作树载荷、成员集合、缺失/重复/链接/逃逸路径。源码直接构建 wheel 为 NOT_RUN。默认 CPU target 安装的 47 个源码/资源全部匹配，52 个 wheel 成员另含 5 个 metadata 文件。

共执行 10 条安装/契约/接口命令：3 条 uv 导出/安装，以及从源码外用 `python -I -S` 执行的 7 条接口/契约命令；20 份 stdout/stderr 已重新核对 hash。12 个原公开/原创 fixture 覆盖包资源、投影、完整 Action 到 P03 原 parser 和序列/shift/padding 接口。该安装测试的序列回调是字符 test double；实际 Qwen completion 比较输入来自 D1 原 native 12 例结果的逐字节私有副本，SHA-256 `5633d00289d65d6f5663b7bb2388cd39d10501b6f7ca49a3adcb4a59ba70c0a0`，未声称新跑一轮 reference 或全量分词。隔离目标没有 tokenizer/模型框架，未从 checkout 导入生产包。

私有摘要 SHA-256：`23094e442a3d04af88646d015db373901bb2da4e427076fd0c9a3690d83a1baf`；包/安装摘要：`0d97212ab536e5451394d79a5ce6f839d6cdbae30c5ed05d8f3d7c680e0d7c35`。全部实际命令、归档、输入副本和异常记录保持。没有新模型/GPU、原数据重建、训练选集或人工判定；R1 结论、最终集成 CI/合并/main 验证及 G-DATA/P04 仍待完成。
