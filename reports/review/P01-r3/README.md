# P01 / R1-r3 启动初始化修复独立复审

**PASS；剩余 P0=0、P1=0、P2=0。** 唯一残留 R2-F1 已关闭；原 F2/F3 的独立关闭结论保持。日期：2026-09-06；任务 P01-R1-r3；gpt-6-astra / max。完整命令、退出码、SHA-256 与证据边界见 [evidence.json](evidence.json)，交接见 [P01-review-r3.md](../../../coordination/handoffs/P01-review-r3.md)。

| 身份 | 精确提交 |
|---|---|
| 被审完整候选 / 本轮 base | `9fe3cbe3a067725c37dc213bbf38f9c90ceb5066` |
| R1 授权 | `79814897340537c232ddc7e1814fc6d4ecb503bb` |
| 共享生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 已测实现 | `2efc7a55ea0dcc77a97cd7f5a82e95515c32de00` |
| 原 R1-r2 FAIL | `aaae5a4395dbdd73fd487f80174599ffd3ef9be3` |
| 原审查接入 merge | `65437ea2323f21e6c4c1d7e5b916282209dbd25a` |
| 本轮分支 | `review/p01-r3`，直接从完整候选建立 |

已按授权读取 AGENTS、任务包、PROTOCOL、PROJECT_STATUS/GOAL、相关规格和 T1 新交接/报告/生产差异/回归/包检查器。契约仍为 `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`，lock SHA-256 为 `0de339292c43cbd7749c8190e3ef4996f2b2f5ee8834f1d0cb698944c8a87342`。影响文件仅为本目录五份新增审查文件与新交接；全部实现、原测试/报告、公共文件和其他 worktree 只读。

## 关闭依据

原 R2-F1 的两个未修改反例现在均通过。初始 swap EIO 的 Popen 调用数为 0，Popen EAGAIN 的调用数为 1，实际 child 都为 0；两例均传播原异常对象，保存有效 failed/ended_at/exit=1、resources 和一条 `FAILED_INITIALIZATION` 汇总。未启动 child 的真实退出码为 null，未读 RSS 和无完整采样时的 swap 增长/pressure 为 null；Popen 前实际取得的零 swap 基线仍为零。

[新增独立探针](revision_probe.py) 共 13 个场景，直接调用候选 `launch` 和实际报告生成器。为测试终态，使用原创、合法的 prepared-config fixture，替换配置预检与资源供应器；没有加载模型，也不把 fixture 数字当机器测量。

| 场景 | 独立检查与实测 |
|---|---|
| environment 复制失败、初始 swap TimeoutExpired | 原异常对象保留；无 child、无采样、基线 null；登记的尝试可汇总 |
| stdout EACCES / EMFILE | 仅 stdout 打开失败；输出目录仍可写；已取得的 0 / 4096 基线保留 |
| Popen EAGAIN / EINTR | 一次 Popen 调用，实际 child 为 0；0 / 8192 基线保留，不访问进程句柄 |
| math 模式 Popen 失败 | 沿用不建立模型 run manifest 的规则；resources 与失败报告仍存在；未执行数学入口 |
| Process 句柄构造失败、第一次 RSS 读取 EIO | 已持有真实 child，但 RSS 仍 null；分类为 FAILED_MONITOR；原异常保留 |
| 正常 wait 后退出 0 / 7 | 实际等待超时至少两次后自然退出；不发送终止信号，原生退出码分别为 0 / 7；fixture 的零 RSS/零 swap 增长保留 |
| RSS 预算、第一次 RSS 前取消 | 保存既有停止语义和 exit=124；真实 child 回收，取消时不编造资源样本 |

六个运行期场景使用真实原创 CPU child，先核对 PID/PPID 握手；另持有一个无关控制 child。四个异常/停止场景中，自有 child 忽略 SIGTERM，实测经 SIGKILL 退出 -9；`waitpid` 确認已被 launch 回收，测试兜底未承担这次回收。无关 child 在各次检查后仍存活。只缩短探针内部等待宽限期，生产预算与信号策略未修改。正常退出 0 的无模型结果分类为 `UNKNOWN`，没有把它宣称为模型 PASS。

现有运行期 pressure/swap/RSS 故障、普通 wait、已执行工作记账和 GPU 租约入口检查也通过。当前修复只改 launch 与必要报告字段；execution 的其余 AST 未变，其他七个 P01 模块逐字节未变。原 F2 回调计数与非有限数、原 F3 八份历史源码归属保持此前独立结论。

## 检查数量与失败记录

- 未修改的原 R1 七项和 R1-r2 二十二项：**29 passed**。
- 完整适用 CPU 与报告检查：**251 passed**，即原 238 + T1 新增初始化 9 + 报告 4。
- 基数为 **280 个不同的现有 pytest 检查**；独立新增 13 个场景均 PASS，单列为 **293 个不同检查**，不是覆盖率。
- 同一 13 个场景又在隔离安装环境执行通过，用于安装来源验证，不再加到 293；包检查的 15 条子命令也不混入 pytest 总数。旧 shared01 的 57 项快照调查未计入。

最初两条 pytest 命令遗漏 `PYTHONPATH=src`，复用的 CPU venv 没有安装项目，收集阶段分别报 `ModuleNotFoundError: toolalign`，exit=2。只修正命令的源码绑定后，29/251 全部通过；原日志保留，原反例和候选都未修改。这是审查环境调用错误，不计为候选缺陷。没有 xfail、跳过失败或重复相加。

## 原始证据与历史结果

[证据审计器](audit_evidence.py) 核对完整候选 183 份 tracked 文件。相对原 review 的 9 个变化为 2 个修改、7 个新增，1942 新增/75 删除行；其余 174 份字节不变。接入原 review 的 merge 两个父提交为 ac8095f 与原始 aaae5a4；9fe3cbe 的父提交为已测 2efc7a5。原两轮 FAIL、所有原探针和旧交接保持。

T1 新证据实际读取核验：11 条命令的原始日志及对应 metadata、8 份 proof 文件、2 份私有结果、14 条安装命令的 28 份 stdout/stderr、2 个归档。before 与 final 的两组初始化 observation、request/config、run/resources 直接核对，并以当前真实报告接口确认修复前汇总遗漏、修复后可收录。before 日志的源码绑定原 review，早期 after 虽记录旧 HEAD，实际源码 bundle 绑定 2efc7a5；没有用记录 HEAD 冒充当时工作树。

十次历史运行的 **92 份小型身份文件**重新核对，与原独立证据完全一致；包括 config、run、resources、原摘要/进度/日志。此前已独立重哈希的 185 项 manifest 制品仅引用其原证据绑定，本轮全量载荷重哈希为 **NOT_RERUN**。保存的 P01_RESULTS 字节未变，SHA-256 为 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`；本轮没有重新生成历史模型摘要或重新运行长校准。

原 17 组 PyTorch CPU 数学结果引用精确 aaae5a4 的已验证记录及原日志 hash `17307b5921a3e9089effd2d824e287b872ce23ea8e2a0b0fe6522f3cea8cc26e`，本轮 **NOT_RERUN**。core/numerical/fallback/model_probe/samples、mask/reference/2e-6 均未变。math-r2 原记录 HEAD `aaab75ed5d993f9354f11f74b58edb67d0af45c3` 及原工作树源码 hash 保留，八份实际源码继续匹配 `47c03404bab043e85b417cd8a6d0432dc2f85479`。

本轮 P01 限定范围技术 PASS，SFT 与唯一备选 DPO 的受限历史证据继续有效；工程终态阻断已解除。首选 mlx-tune DPO 历史失败、smoke06-r2 的后续降级、smoke06-r3 失败及 1536-r1 pressure 停止均保持原判。正式 G1 协调状态、CI、集成与 main 验证由 S0 决定。

## 新包与安装接口

本轮在自己的候选执行 `uv build --offline`，原日志明确先创建 sdist，再从该 sdist 构建默认 wheel；另实际执行 `uv build --offline --wheel <本轮sdist>`，生成显式重建 wheel。**直接从源码单独构建 wheel：NOT_RUN。**

| 本轮归档 | 字节 / 完整成员 | SHA-256 |
|---|---|---|
| sdist | 116086；49 文件 = 48 tracked + 1 metadata | `649b0f757e321294f0a0b193d35c17f3e6785de831e69820e4a413df65241777` |
| 默认 wheel | 44830；27 文件 = 22 tracked + 5 metadata | `7c83931ab70668727f824df340ded0ce0530779d9058b8a3c4846aa1f4364ae2` |
| 显式 sdist 重建 wheel | 44830；同上 | `7c83931ab70668727f824df340ded0ce0530779d9058b8a3c4846aa1f4364ae2` |

[包核验器](verify_package.py) 逐成员检查集合、路径/链接和当前 Git blob/工作树字节，未追踪载荷为 0。三个归档为本轮实际生成；其 hash 与 T1 同源码构建结果相同。

新建默认 CPU 隔离环境，从锁文件带 hash 离线安装五项依赖和**本轮默认 wheel**，共六个 distributions。15 条实际命令全通过：依赖/安装一致性、八模块字节与安装 prefix、CLI help、schema digest、五种 fixture、13 场景实际 launch，以及报告 CLI。`python -I` 从源码外运行，移除 PYTHONPATH/PYTHONHOME；MLX/Torch/模型/tokenizer 包均不可用。报告脚本不在 wheel 中，明确从精确候选 Git blob 复制到私有测试目录，hash 单独核验；它调用的 execution/contracts/core 来自已安装 wheel。全部子命令 argv、cwd、时间、退出码及原始 stdout/stderr hash 均保留。

复用 CPU 环境的 34 个 distribution 版本与原 lock 一致；执行测试时设置导入守卫，禁止 MLX/Torch/模型/tokenizer。本轮没有新依赖或权重下载。新私有目录磁盘分配快照 13176832 字节，低于 2 GiB；这是磁盘快照，不是内存或资源峰值。

## 重现与日志

在 HEAD 保持精确 9fe3cbe 的独立 worktree 拷入本审查文件后，使用已锁 CPU Python。280 项实际命令和守卫 hash 在 evidence 中；新增探针可运行：

```bash
PYTHONPATH=src <CPU_PYTHON> reports/review/P01-r3/revision_probe.py --output .toolalign-local/review-p01-r3/replay --fixture tests/fixtures/contracts/run.json --report reports/hardware/P01_BUILD_REPORT.py
uv build --offline --out-dir .toolalign-local/review-p01-r3/build
uv build --offline --wheel .toolalign-local/review-p01-r3/build/toolalign-0.0.1.tar.gz --out-dir .toolalign-local/review-p01-r3/rebuilt
<CPU_PYTHON> reports/review/P01-r3/verify_package.py --private-root .toolalign-local/review-p01-r3
```

检查器不会覆盖已有私有输出；重现时使用新的独立 worktree/私有目录。历史审计需要原保留证据，缺失时不能视为通过。原始日志存本机私有目录，公开真实 argv 仅替换工作区绝对路径为 `<R1_WORKTREE>` / `<T1_WORKTREE>`。

<!-- COMMAND_TABLE_BEGIN -->

| 检查 ID | exit | 原始合并日志 SHA-256 |
|---|---:|---|
| original-r1-29 | 2 | `160356dca595ce7e2b75bd5c3a1f42437933f75e7bd73c0b9898d24902e3958b` |
| applicable-cpu-251 | 2 | `5888bdf8c6a453d8a6926716f06b455601494a3bd6fa87fa0a79f466b1af2c73` |
| original-r1-29-bound | 0 | `20a37686d3538045bc230f7e1268fe0d6a06f75bf03afddb99931833afc0c485` |
| applicable-cpu-251-bound | 0 | `b68a8b5380eba50f9a27bee1d57c52d7daed9f47df5ccff4d74c928c3a4f5d82` |
| build-default | 0 | `e7d2db0f1532465e2612240369cee0d6073da8646a2b322ab6626b22ce8ac182` |
| independent-13 | 0 | `2ee480112168dc29ed7273cd281cddfb8d961c12edea88d7497333c49ad6d9b9` |
| rebuild-sdist-wheel | 0 | `58430fba2ec7d0b1377e8b095a2c00f00449b11a3d3613bd0a70a51c06ddaa1b` |
| package-isolation | 0 | `e64ef28b493400543e3f9ce2fca1c19cc3f8e3946e14dd23698aa53a5109b1ea` |
| lint-initial | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| contract-freeze | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| evidence-binding | 0 | `1dc6f614acf77c551966ab72f4e1df6aeacad8891f2222be13edaa6f5a217dd5` |
| environment | 0 | `a4b2fe0c0c994c3050ee4bdeecacd87261363d33418f2eef76e7ee5dfb3d1aaa` |
| final-lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| public-content | 0 | `e0b44dc8636bdbefebe865ae9e4ddddc85fe789c26d5f006d1f9426b89d8ba3a` |
| precommit-scope | 0 | `c62a019c42b8f4787b5f593456d37af7f441498aad0e275793cf56729cbfed5d` |

<!-- COMMAND_TABLE_END -->

NOT_RUN / NOT_RERUN：MLX、Torch、模型或 tokenizer 导入；GPU/模型重放、数学重跑、185 项历史大载荷再哈希、权重/新依赖下载、OS 限制调整；本机 Python 3.11/3.12/3.13；P04/P05、accepted_sft、kris 人工核对、完整真后端 256-token 协议、BFCL/最终测试、长期性能、费用、上传、推理服务或 main 合并。输出介质全面不可写时仍保证落盘不在本次承诺内。提交原始 review 后结束本轮，由 S0 接续。
