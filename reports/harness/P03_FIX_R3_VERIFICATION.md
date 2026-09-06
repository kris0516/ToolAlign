# P03-fix-r3 最终修复自测

日期：2026-09-06。**E1 已完成 F1/F2/F3 修复及本轮自测，交 S0 安排新精确候选独立 R1 复审。** 原 R1 对 `79a15d9` 的正式 FAIL 保持原文；本报告没有将 E1 复跑结果写成 R1 验收。

## 提交与授权

| 身份 | 精确提交 |
|---|---|
| 原完整候选 | `79a15d990fc27a9a33d033983c94eb92cccfb268` |
| 已验证公共生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 收尾修复授权 | `243821a988a12a6ff9f20b5fbb5ba1ae374d63c9` |
| 本次最终授权 | `fd67511ef4cb7853bb75b0b106ec4692a9d36be8`，具体新增 semantic.py 的 F3 修复 |
| 收尾实现 / checkpoint 报告 | `fde181d3319f36179298a4bec2a928a8354ee6b3` / `2195b2e4ea3219884c3a8c1eed26d413141daa65` |
| 原 R1 review commit | `f34f7c5a4eac54b18a2b092495f4ce8eaa334f98`，唯一父提交严格为原完整候选 |
| 保留原 R1 SHA 的 merge | `5fe4e905cf43af04e744d3801b19472bd839c67a`，父依次为 `2195b2e4ea3219884c3a8c1eed26d413141daa65`、`f34f7c5a4eac54b18a2b092495f4ce8eaa334f98` |
| 最终全部生产代码及测试 | `8d11225861214141de3da77c2b5eaf1752fc43b2` |
| 实现 tree | `90fc20c5d3d3c3e847e2b4b5fc6b8750ee588461` |

分支为原 `work/p03-execution-harness`。最终完整候选还包含本报告及 [P03-fix-r3 交接单](../../coordination/handoffs/P03-fix-r3.md)；文档提交 SHA 与非强制推送后的远端读回由原生交接给 S0，不伪造自指 SHA。上述生产代码、测试及打包输入在文档提交中不再变化。

本次读取 fd67511e 的 AGENTS、任务包末段、PROTOCOL、PROJECT_STATUS，私存授权；GOAL 与上次已读授权字节一致。沿用 `toolalign.contracts.v1` / `toolalign.protocol.v1` / `coordination.v1`。未 merge 后续 main/P01/P02/协调文件，没有 reset、rebase 或 cherry-pick 原审查。

## 各问题与真实反例

| 问题 | 修复行为与当前证据 |
|---|---|
| F1/P1：stop EIO 后重入 finish、结果消失 | `fde181d` 将停止通知与自有进程 close 分离，关闭尝试只执行一次；通知失败仍返回 `harness_cleanup_error` 的合法终态，保留 raw、final、原 parse failure、13/9 已知合成 token 及失败分母。原 R1 两例在 checkpoint 和最终实现均返回结果、没有 OSError、stop 仅 1 次，实际进程退出码 -15，已回收。 |
| F2/P1：目录 cleanup EIO 后重访关闭句柄 | 单独维护 process handle 关闭状态、完整 close 状态及 `directory_cleaned`；目录失败后不会访问已关闭的 Process，恢复访问后可只重试目录 cleanup。原 R1 两例均返回结果、无重入 ValueError；进程实际退出 0、handle 已关闭，但目录仍存在、整体 close 尚未完成。原探针最后移除目录属于测试清场，未记成候选目录清理成功。 |
| F3/P2：观察先于执行仍 success | `8d11225` 按现有串行执行维护单个 pending call，观察必须消费已经发生且尚未完成的调用，并匹配完整 call 的 canonical hash 与 result.call_id。先观察后执行、重复观察、重叠执行、缺失/不匹配绑定标 unknown。合法多解、多步依赖、恢复、无需工具、真正 rejected/失败及未完成执行含义保留；不要求已有 finalized 事件。原 R1 唯一 F3 反例从 success 变为 unknown。 |

原 R1 原文、独立探针和 evidence 全部保留，见 [P03-review-r1](../../coordination/handoffs/P03-review-r1.md) 与 [原 FAIL 报告](../review/P03/README.md)。原候选新增 54 项为 49 passed / 5 failed，是 R1 历史结果。

E1 接入审查文件后，先在 checkpoint 实现 `5fe4e90` 跑未修改的全部 54 项，实际 **53 passed / 1 failed**；唯一失败是 F3。本轮完整回归于已提交 `8d11225` 运行，原 54 项全部通过。其四个阻塞反例真实记录模型忽略 SIGTERM 后以 -9 回收、工具以 -15 回收，无关睡眠进程仍存活；正常/parse/退出 17 的后端崩溃、单调 deadline 回拨对照均通过。

本轮新增 26 项：checkpoint 的 10 项收尾检查与本次 16 项顺序/绑定检查。后者包含 8 个不可靠 trace、4 个合法场景终态前后评分、3 个真实执行失败场景及 1 个未完成调用场景；所有损坏记录先做单条 wire 校验。完整 **389 = 58 基础 + 159 P03 + 46 P00 独立检查 + 72 P00-r2 + 54 原 R1 P03**，没有重复把分组运行计入总数，也未计入旧共享单 extra 快照。

## 保留的开发失败与来源映射

F1/F2 修改前的 E1 原始 4 failed / 3 passed、7 项初版和 10 项 checkpoint 证据见 [原 checkpoint](P03_FIX_R3_CHECKPOINT.md)，报告与原始制品未覆盖。本次接入原审查后的 53/1 同样保留。

新顺序探针初次运行 8 failed / 8 passed：其中 7 个为原语义行为的失败断言，1 个为 E1 探针准备错误——只修改 observing 的 result.call_id，先触发单条 trace 的 call/result ID 一致性校验，尚未到达 oracle。初版修复后 16 passed / 1 failed，所余仍是该准备错误。随后只将该观察记录的 call.call_id 同时改为同一个新 ID，使单条记录合法而与先前 pending call 不同；最终 16 项加原 R1 F3 为 17 passed。原稿、初版修改源码与两轮失败日志均单独保留，没有改动 R1 文件或冻结契约。

上述开发检查的 HEAD 为 `5fe4e90`，运行的是明确保存 hash 的工作树字节；不能把它们写成该 Git 提交原字节的修复后结果。最终两文件字节 manifest 绑定到随后 `8d11225`。完整 389、lint/冻结/公开扫描和新包/安装直接运行于已提交的 `8d11225`。

## 实际命令与日志

所有日志为本轮实际 stdout/stderr；完整命令、退出码、开始时间、HEAD/index tree、原始观察制品仅存本机本轮私有目录。表内中间检查的失败归属见上一节。

| 检查 | 实际命令 | 退出码 | 日志 SHA256 |
|---|---|---:|---|
| checkpoint 实现 + 原 R1：53 passed / 1 failed | `uv run --locked pytest -q reports/review/P03/test_p03_semantics.py reports/review/P03/test_p03_lifecycle.py --basetemp=.toolalign-local/p03-fix-r3/final/r1-before` | 1 | `6805b15d2cd01a1a1fbad4c669bda07062a6e75e59cd2fc08aa53a4be00d4614` |
| 新探针初版：8 failed / 8 passed，含 1 个探针准备错误 | `uv run --locked pytest -q tests/evaluation/harness/test_oracle_order.py --basetemp=.toolalign-local/p03-fix-r3/final/oracle-before` | 1 | `80caf03f7beeaa0ad0273b607a37d7d12540d120229b90096eccf0995935f87e` |
| 初版修复：16 passed / 1 failed，仅余探针准备错误 | `uv run --locked pytest -q tests/evaluation/harness/test_oracle_order.py reports/review/P03/test_p03_semantics.py::test_oracle_marks_observation_before_execution_unknown --basetemp=.toolalign-local/p03-fix-r3/final/oracle-after` | 1 | `09c3a8d7d69aff77ee7ca4bf27b67e15dc211c08ea0a3ac2201c6df5016c2920` |
| 最终 16 项新检查 + 原 F3：17 passed | `uv run --locked pytest -q tests/evaluation/harness/test_oracle_order.py reports/review/P03/test_p03_semantics.py::test_oracle_marks_observation_before_execution_unknown --basetemp=.toolalign-local/p03-fix-r3/final/oracle-final` | 0 | `fa09b8e4b0147900b166463ac7f299ae98cffb871f62c0e1bfca5d9882f783a8` |
| 389 passed，无 skip/xfail | `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P03/test_p03_semantics.py reports/review/P03/test_p03_lifecycle.py --basetemp=.toolalign-local/p03-fix-r3/final/full-cpu` | 0 | `5acb2ab177e0e0da54846b9ec70d08fcf6fbafcbc3fae8db4a64e6c8b2af01fa` |
| PASS | `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 4 个冻结文件 PASS | `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| 实现提交 156 paths PASS | `uv run --locked python scripts/check_public_content.py` | 0 | `4743d16035f35505dacd30b5017b3698b8613312764aec469b73430538af8481` |
| 新 sdist / 默认 wheel PASS | `uv build --out-dir .toolalign-local/p03-fix-r3/final/dist` | 0 | `42606d885484151f5e285e15bd6a5a7adc50849f00b0a5d3781561c00f3818df` |
| 从本轮 sdist 重建 wheel PASS | `uv build --wheel --out-dir .toolalign-local/p03-fix-r3/final/rebuilt .toolalign-local/p03-fix-r3/final/dist/toolalign-0.0.1.tar.gz` | 0 | `5205905dd86cc20b3125781e0189c86890c2681716ec11f34f4dd082aa0da273` |
| 逐成员/追踪字节检查 PASS | `python3 .toolalign-local/p03-fix-r3/final/inspect_archives.py` | 0 | `e92517451291d9d5e8d0d249c98ba38c0d4eab627d4bd42c3801adc7161081b1` |
| 17 条子命令全部退出 0 | `python3 .toolalign-local/p03-fix-r3/final/verify_install.py` | 0 | `c2b838e5f0efc2748306c2d992b2a573ef2c824f7e88e98d7f0a9f5e2c432947` |

## 当前源代码与归档

| 实现/测试 | SHA256 |
|---|---|
| `src/toolalign/evaluation/harness.py` | `b4aff77d4adffea786d742d5c5aeeee72f99feaf3783ee0f01ad504aa84bb987` |
| `src/toolalign/tools/isolation.py` | `84a96791205488bad6bd3fe43a42f33f7abcbfb5fc8bb0b64f27aa13e5667f6f` |
| `src/toolalign/evaluation/oracles/semantic.py` | `29291f5f0bdfd9cd1ad54711dc432b92375195dccb3e8f26670130cc68a8fb56` |
| `tests/evaluation/harness/test_finish_cleanup.py` | `b81acd8bea492da2f4483c21f7e6e0c48c30d4168ff3a9dde62682c9e21d005b` |
| `tests/evaluation/harness/test_oracle_order.py` | `b0ab78a74e461b3273df4ba58662ce793ff5f90a3f50c8f6cb1598a3c39e75fe` |

新归档输出位于本轮 `final/` 私有子目录；原候选和 checkpoint 的全部归档未覆盖。默认 `uv build` 明确从 sdist 构建 wheel，本轮没有把它称为直接工作树 wheel。

| 产物 | 字节数 | SHA256 | 成员核验 |
|---|---:|---|---|
| sdist | 116137 | `622ed5b412d5275656880d364256ba255d868851aba86ab88e0e8effda87187c` | 52 文件，51 tracked + 1 已知 metadata；未知/缺失均 0 |
| default-wheel | 37495 | `c6f0a491bb92c516f5ba13ffc1ec00a40529935a46309f1df1ad4659d760faa1` | 29 文件，24 tracked + 5 已知 metadata；未知/缺失均 0 |
| rebuilt-wheel | 37495 | `c6f0a491bb92c516f5ba13ffc1ec00a40529935a46309f1df1ad4659d760faa1` | 29 文件，24 tracked + 5 已知 metadata；未知/缺失均 0 |

逐成员断言包括与当前 Git blob 字节相同、无未知或遗漏载荷、无符号链接/路径遍历。sdist 包含新的测试文件；wheel 为 24 个源码/资源及 5 个已知 metadata。冻结 schema digest 仍为 `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb`。未修改 pyproject/lock/检查脚本，未重复扩大已通过且未变的共享 canary 调查，历史依据保留在 [base-r2](P03_BASE_R2_VERIFICATION.md)。

## 隔离安装与生命周期

新建本轮 CPU venv，使用锁定 default runtime、require-hashes 安装依赖、no-deps 安装新重建 wheel。17 条实际子命令均退出 0：导出依赖、venv、依赖安装、wheel 安装、pip check、digest、5 类 fixture、help、registry、demo、阻塞探针、收尾探针、oracle 探针。清除 PYTHONPATH/PYTHONHOME 并以 `python -I` 运行；cwd 是私有子目录，位于 worktree 内但不是项目根。入口来源均位于新 venv，三个修改模块的安装字节与本报告源码 hash 一致。

安装后的同一公开 scripted demo 为 10/10、excluded=0。四项工具/模型 timeout/cancel 生命周期检查通过，4 started / 4 reaped；四项 stop/目录故障检查确认真正进入 generate、一次收尾、失败分母和 13/9 用量/parse 保留，目录失败恢复后仅重试目录清理。新增 oracle 探针对该次实际 demo 的 10 个结果分别在 terminal 前后评分，20 个检查均 success；8 种 wire 合法但因果/绑定不可靠的 trace 全部 unknown。这些是重复检查同一组 10 个原创开发场景，不是新增模型评测数据。

## 保留范围与未测项

接入原 R1 时，889 个 checkpoint/旧追踪文件及私有制品全部未变；完成本次修复后，仅其中授权的 semantic.py 变化，余 888 个相同，包括全部 741 个先前私有/归档文件（包含最早受保护的 400 个）。原 R1 七个新增文件与 f34f7c5 的 blob 逐字节相同。checkpoint 的 harness/isolation/测试/报告未再修改；两份旧 handoff、所有 before 失败与旧归档保留。旧源码版本继续存在于原候选和原始审查提交。

安装后磁盘快照：本修复轮私有目录累计 15480 KiB，其中本次 final 子目录 11388 KiB；复用基础 `.venv` 为 35068 KiB。嵌套目录不重复相加；本轮累计新增低于 2 GiB。原始日志、临时进程身份和私有目录绝对路径未写入公开材料。

NOT_RUN：新候选独立 R1 复审、S0 main 集成验收；MLX/Torch/模型/tokenizer 导入与权重下载、GPU、P04 真实 ModelBackend、P06/BFCL/最终隐藏集、真实吞吐/模型质量/长期稳定性、已加载 MLX 对象跨 spawn 兼容、输出语法切换或 P02 至 P04 格式改造、模型服务部署。scripted token 均为合成预算证据。没有费用、业务写入、模型/数据上传、公开推理接口、全局 Git/OS 改动或主干合并。
