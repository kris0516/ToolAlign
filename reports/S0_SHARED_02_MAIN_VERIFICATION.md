# S0-SHARED-02 main 集成验证

日期：2026-09-06；结论：**VERIFIED**。

[PR #4](https://github.com/kris0516/ToolAlign/pull/4) 已合并为 `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`。R1-r3 对精确完整候选 `f8ec7ff040053f11e073b6858e1f849e888d4ac2` 独立 PASS，P0/P1/P2均为0；审查提交 `ad3b5198c2c222512f51d0c529c8188d20827e41` 以非强制merge保留原SHA。两轮FAIL和原反例均保持原文，见 [r3交接](../coordination/handoffs/S0-SHARED-02-review-r3.md)。

最终PR head `7541e0d864e0ea9f271b49863647d9d0d7ddb548` 在被审候选后增加审查证据、协调状态与README状态说明；源码、依赖、configs/tests、冻结字节和归档脚本未改。其 [CI run 34002514117](https://github.com/kris0516/ToolAlign/actions/runs/34002514117) 的Python3.11/job101403798566和Python3.14/job101403798582全部步骤success。CI实际包括默认58项与P00首轮46项测试，不把本机额外72项复核扩大为CI范围。

## 合并 main 的实际命令

以下全部在上述main合并提交上运行，Python3.14.7/macOS/CPU。默认环境为12个distributions（项目加11个第三方），锁文件93条不是默认安装93个包。

| 命令 | 退出码 | 完整日志 SHA-256 |
|---|---:|---|
| `uv sync --locked --python 3.14` | 0 | `3f382eff3f9f6e259d39b29f4ab3dea231e1641db4e142f44528397d69f6f123` |
| `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py` | 0 | `345b6b6dc0443631edace8111193eed849ce304f238f50dd8b39a55edacde841` |
| `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `uv run --locked python scripts/check_public_content.py` | 0 | `c82d98b3955cbe331e9100c778b0bb60fef577fe6af13ba91bcecb7ac52387fc` |
| `uv run --locked python scripts/check_source_distribution.py` | 0 | `49131f1725a61544597d27bc5b9b122d31acef76e1588a5e4120f1e6bf81d2d3` |
| `uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_additional_boundaries_r3.py` | 0 | `23bf1d1e5261985ddeea1d5e035590b2e7a1c57e6ebcbb1ec2201b6e42e9b2c9` |
| `uv build` | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| `uv run --locked python reports/review/P00/verify_wheel.py` | 0 | `71b8e7ba8a4d4dc3925b3774ab61c31b353c8369d83ecab6044561f18dd3bc6b` |

原始命令、起始UTC、用时、退出码和完整输出保存在私有 `.toolalign-local/evidence/shared-dpo-support/main/`，公共报告只含去敏摘要。176项CPU为58基础+46 P00首轮+72 P00-r2；历史“只有一个extra”结构快照不适用于新增合法组，未改旧探针或将其计入本次通过数。

## 归档与安装范围

main上的实际App合成worktree回归排除241个私有canary，保留18个公开对照及冻结schema，并检查sdist、由sdist重建wheel、直接wheel。原R1-r3补充45私有/21公开边界探针也在main原样通过；各组有重叠，不相加成覆盖率。

实际main `uv build` 的源码包为87,930 bytes，SHA-256 `aa05db8a70d641b4cbf55657355b138f576ae4ba5e52c899caf94b68395386dd`；wheel为18,468 bytes，SHA-256 `bc43b18ed3f2377d0a70dd75c3fa1ee98fb66462d8098c5c9113d3dabd398211`。最终README状态变化会进入包metadata，因此不要求与R1较早候选的wheel摘要相同。

S0另逐项核对实际产物：sdist 37个文件除生成的PKG-INFO外均为Git追踪文件且字节相同；wheel 19个文件中14个源码/资源与追踪文件相同，其余仅项目dist-info。未跟踪payload为0；私有核对结果摘要 `c640c15a6c23c79de5c2f97b9c52324099cbc9305e231cfd8cd1f3452193c224`。没有解包或上传D1旧失败私有tar。

原P00隔离安装脚本验证锁定CPU依赖hash与闭包、安装后的完整schema、五类CLI fixture、脱离源码导入及无ML后端，均通过。所有生成制品仍在本地ignored目录，未发布发行包、模型或数据。

## 发布给worker的范围

生产code_base为上述已验证main合并SHA；S0另在协调提交中公布本报告及后续同步授权。D1/T1/E1保留原始候选和授权，以非强制merge接入新base并交付新完整候选。旧基线仍禁止默认sdist；只有接入已验证修复后的分支才可恢复实际包构建检查。最多两个活跃实现任务，独立R1下一包先审P02技术证据，再审P01/P03。

共享环境与源码包边界已验收；P01模型/数学重放、P02生产实现和kris语义判断、P03完整执行器仍各自待验收。已有可选环境69/90清单沿用独立审查确认的相同依赖字节，本次未导入ML、加载模型或重跑GPU校准。mlx-lm-lora的MIT metadata/Apache LICENSE差异保留。P04/P05正式训练、正式BFCL/隐藏评测、推理服务仍NOT_RUN。
