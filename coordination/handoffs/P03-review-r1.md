# P03 — Independent review R1

结论 **FAIL**，P0=0、P1=2、P2=1；F1/F2 阻断完整候选验收，F3 非阻断。日期：2026-09-06。本交接对应审查分支 `review/p03-r1` 的独立提交，精确 review commit 通过原生消息交给 S0。

| 身份 | SHA |
|---|---|
| candidate | `79a15d990fc27a9a33d033983c94eb92cccfb268` |
| production base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| authorization_commit | `52f9c57a50eaf580a1a90bc5c4b8bd028c83b903` |
| sync / actual merge | `f2a271be616cdb53c01e8d671029f31ae140c037` / `86c5e8abaf0a6518fda0d33dba1b68eb6815737a` |
| original candidate | `85e0905fc82da4504d73bf7eb489c1f1a0d227a7` |
| implementation | `8afb114bd14e69d3a2138212ab423147809fed63` |

读取 `plan-v0.1`、`coordination.v1`、`toolalign.contracts.v1` 与授权任务包规定的 AGENTS/PROTOCOL/STATUS/GOAL、docs/01/04/12/13、protocol/interfaces/lock。审查完整 19 文件、3263 新增/1 删除行；保留原候选、原交接、63 份原始私有文件及 S0 指定基线。未使用后续修复签本候选通过。

| ID | 级别 | 位置 | 触发及影响 | 最小修复方向 |
|---|---|---|---|---|
| F1 | P1，阻断 | `src/toolalign/evaluation/harness.py:225–231`，关联 413–417 | 父进程停止通知写入 EIO 后 `finish()` 重试同一失败写入；两例真实 CPU 子进程最终回收，但 run 抛 OSError，无终止 HarnessResult 和已知用量返回。 | 停止通知失败后仍回收并返回终止 trace、用量和失败原因，使收尾幂等。 |
| F2 | P1，阻断 | `src/toolalign/tools/isolation.py:124–126`，关联 107–111 | 目录 cleanup EIO 发生在真实 Process 关闭后、`_closed=True` 前；两例再清理均 ValueError，掩盖 EIO，无终止结果。目录由 R1 安全清场移除。 | 分别维护回收、句柄关闭、目录清理状态；部分失败后的 close 可重入，保留真实故障与终止结果。 |
| F3 | P2，非阻断 | `src/toolalign/evaluation/oracles/semantic.py:104–116` | 原创正常 trace 调换一次观察/执行次序、连续编号并保持 wire 合法后仍 success。当前 harness 正常路径未发现倒序。 | 先校验事件因果顺序及待完成调用；不可靠 trace 标 unknown。 |

实际证据：原有适用 CPU pytest **309 passed**（core 58 + P03 133 + P00 review 46 + P00-r2 review 72）；新增 **54 项，49 passed / 5 failed**，其中 F1 两例、F2 两例、F3 一例，无 xfail。原始失败日志 SHA-256 为 `f76c90afc0f3c80adcd20b7230db3d5d73b012ca61d20c4c209d0b5d5e7adbf5`；原有 309 日志为 `815305d42ac69da6fd024a5b2b8695bb574256e2d52415f55d70dab9fea5b93f`。命令、退出码、时间、HEAD/tree 和所有 hash 见 [完整报告](../../reports/review/P03/README.md) 与 [evidence.json](../../reports/review/P03/evidence.json)。

四项真实阻塞测试覆盖模型/工具的 timeout/cancel；仅在实际操作 marker 出现后取消，模型 SIGTERM 无效后实测 SIGKILL=-9，工具 -15。直接核验持有 Process 的存活、退出及回收，另一个独立睡眠进程仍存活。F1/F2 的结论是终止证据缺失，未声称存活子进程泄漏、实测 CLI 分母虚增或真实模型指标。

复核 17 份公开原件、63 份私有原件、35 条历史命令与 15 条历史安装子命令；两份历史 scripted demo 各 10/10、90 事件由 R1 独立复算。新构建 sdist 与三个 wheel 逐字节绑定候选；隔离安装另执行 15 条命令，11 个 P03 模块均从安装 prefix 导入，新 10/10 demo 再独立复算。合成 token 和 demo 不代表模型/BFCL benchmark。归档无未知载荷；不重复未变字节的共享 canary 调查。

最终 lint、冻结契约检查、公开内容扫描与 staged 范围检查通过。仅新增 `reports/review/P03/` 下六份文件及本交接单；候选 146 个 tracked 文件逐字节不变。独立审查期间不修改 main、看板/状态/ADR、共享依赖或 E1 工作区，未自行合并或修复候选。

资源：仅 CPU，Python 3.14.7/macOS 26.5.1 arm64；记录时新增私有 P03 目录约 4.24 MiB，与复用基础环境合计约 38.8 MiB，低于 2 GiB。NOT_RUN：模型/tokenizer/MLX/Torch 导入与权重、GPU、P04 真后端/P06 正式评测/BFCL/最终测试、本机 Python 3.11/3.12/3.13、新修复候选、P02 kris 语义批准、业务写入/付费云/上传/公网服务。R1 交回后结束本轮，等待 S0 给出修订候选及授权。
