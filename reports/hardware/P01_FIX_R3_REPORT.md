# P01 · R1-r1 定点修复 r3

2026-09-06；T1，gpt-6-astra / max。F1/F2 的 CPU 反例及 F3 来源修正已交付，**等待 S0 安排独立 R1 复审**。本报告是实现者自测，不将原 FAIL 改为验收通过。

| 身份 | 精确提交 |
|---|---|
| 共享生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 修复前完整候选 | `59b3802c81aa6eceaf3609af88f288756bcb1581` |
| 原 R1-r1 FAIL，完整保留 | `ac6bdf78d57c6753865a24a1d216b90dc4478646` |
| S0 定点修复授权 | `a0a800b2a544cb25e7eccad2dce12173acc77ea1` |
| 接入原审查的非强制 merge | `f020046055717f4fc5a821a61fb2664d989e6875` |
| 修复实现、回归测试与 F3 映射 | `5c32e8a72e957df100691e0096d1413eed8ce8f9` |

工作分支为 `work/p01-compatibility`；契约仍为 plan-v0.1 / coordination.v1 / toolalign.contracts.v1。最终完整候选由本报告所在后续证据提交与 T1 原生交接的完整 SHA 定位；其已测实现源码与上表实现提交一致。没有接入无关 P02 实现或修改公共协调文件。

## 修复与证据

### F1 / P1：监控异常也必须产生终态

`launch()` 区分资源门槛/取消与采样异常。采样异常发生后，保存原异常，先对自有 child 执行 terminate → 有界等待 → 必要时 kill → wait 回收，再写 `resources.json` 和 run.v1 的 `failed`、`ended_at`、退出码及制品 hash，最后重新抛出原异常。监控失败记为 `stop_reason=monitor_error`，异常类型/消息独立保存；对外退出码为 1，真实 child 退出码另存 `raw_process_exit_code`。

`TimeoutExpired` 只在轮询 child 的 `wait(timeout=1)` 处被作为正常等待处理，压力读取的同类异常仍为失败。读取压力失败前已采到的 RSS 也会保留。正常 child 退出码、预算/取消的 124 和原 worker 持锁退出路径保持不变。汇总器会收录新失败目录并标记 `FAILED_MONITOR`。

未修改的 R1 两个监控反例现在均保存 `exit_code=1`、`raw_process_exit_code=-9` 和有效 failed manifest；异常分别为 `CalledProcessError`、`ValueError`。新增 CPU 回归另外覆盖读取超时、pressure/wall 超限、取消、成功及 worker 自行退出 2。使用真实惰性 OS child 验证信号升级与 `waitpid` 回收，并证明同次测试创建的另一独立 child 不受影响。测试仅缩短终止宽限期，默认 CPU 测试中的资源读数使用替身；原 R1 探针仍使用真实 psutil，未启动模型。

### F2 / P1：loss 失败不能丢失上游已执行的更新

上游训练器在累积边界先更新 optimizer 并求值，再调用 Callback。修复保留首次真实累积周期逐步 ln(2) 检查和 **2e-6** 容差，将门槛异常暂存，先记录实际 loss、该微步的监督/处理 token、微步数与 `optimizer.step`，将逐步记录和 progress 写入磁盘，再抛出失败。失败不再进入下一次资源检查或训练。

原 R1 第 8 微步反例注入 `0.6945998072624207` 后，失败记录现在包含：总微步 **40**、总 optimizer 更新 **5**（SFT 4 + DPO 1）、监督 token **404**、处理及非 padding token **1006**；该 DPO 步记录监督 token 4、处理 token 6、optimizer step 1 与 failed/ValueError。修复前同一探针只能保留 39 微步/4 更新。以上是原回调逐字提取的 CPU 单元证据，结合已核验的上游调用顺序；没有新执行 GPU 故障注入。

NaN、正/负 Infinity 会以 `null` 写入数值字段，并在 `nonfinite_values` 中保存 `nan`、`inf`、`-inf` 的原类别。非有限辅助指标同样保存失败，避免标准 JSON 拒绝序列化而再次丢记录。报告脚本支持这些失败记录。新增测试覆盖累积周期内外的非有限 loss、有限门槛失败、正常 ln(2) 和后续资源检查抛错时已完成工作的保留。mask、reference、损失公式、累积除法、编译及模型配置未调整。

### F3 / P2：恢复 math-r2 工作树源码身份

原 HEAD `aaab75ed5d993f9354f11f74b58edb67d0af45c3` 只记录当时检出的提交；当时的 `model_probe.py` 和 `numerical.py` 已有未提交修改。原配置的全部 8 个源码 hash 精确映射到后续 `47c03404bab043e85b417cd8a6d0432dc2f85479`，聚合 source hash 仍是 `17479619a5ef1fb0e2d9747211a67a7d1d71acfd266b48ee1514b267ceca6241`。

[逐文件映射](P01_FIX_R3_SOURCES.json) 同时列出记录的工作树、记录 HEAD 和可恢复提交的 SHA-256。[当前原报告](P01_REPORT.md) 已修正表述；旧提交、原 HEAD/source hash、配置与原始制品均保留。该映射不表示历史 math-r2 使用本轮修复代码运行。

## 实际验证

[P01_FIX_R3_VALIDATION.json](P01_FIX_R3_VALIDATION.json) 保存实际 argv、UTC、退出码、原始日志 SHA-256、源码/包 hash、范围与失败探针摘要。原始日志、测试临时文件及历史模型制品只留私有目录。

| 检查 | 结果与范围 |
|---|---|
| 修复前原 R1 pytest | 退出 1；4 通过、3 失败，保留负例 |
| 修复后原 R1 pytest | 7 通过；原探针字节未改 |
| 当前完整适用 CPU pytest | 235 通过 = 原 217 + 新 18 |
| 当前 R1 探针与报告测试 | 10 通过 = 原 R1 7 + 新报告 3 |
| R1 独立 PyTorch CPU 数学脚本 | 17 组通过；float32、2 线程、无 MLX/模型导入 |
| 历史摘要重建 | 10 个 run、185 项 manifest 制品核验；生成 JSON 与原文件逐字节相同 |
| lint / 契约冻结 / 公开扫描 | 退出 0；命令与完整 log hash 见验证索引 |
| 实际新 sdist → wheel 构建 | 退出 0；成员检查与隔离安装通过 |

本轮 pytest 共 **245 个不同检查**（235 + 10），不重复相加修复前、开发中或原 R1 的历史运行。旧 shared01 的 57 项单 extra 结构快照保持原样，未计入当前适用回归。数学对照最大误差：CE loss `4.011570280404442e-7`、CE 梯度 `1.905478064223587e-8`、DPO loss `8.22313996895474e-8`、DPO 梯度 `3.629568690738383e-9`；全部小于 2e-6，输出与原 R1 同脚本的历史 stdout hash 相同。

重建摘要 SHA-256 为 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。这是报告兼容性及制品绑定检查，不替代原 R1 的独立历史审计。复用已有锁环境，没有重查未变依赖或重跑完整 MLX math 入口。

### 新发行包

旧归档已移入私有保留目录，`uv build` 本轮实际新建 sdist 并从中构建 wheel。[包核验脚本](P01_FIX_R3_PACKAGE.py) 只复用旧 T1 审计中的当前追踪字节函数，不运行旧快照 main，也不套用旧 archive SHA。R1 原审计文件不作修改。

| 归档 | 大小 / 成员 | 本轮 SHA-256 |
|---|---|---|
| sdist | 114,450 bytes；48 文件，47 项追踪字节 + PKG-INFO | `024126435a5065ddae8e12c86272cc530ed4a8ae09eddd1fa2b0b0916d6ccf2e` |
| wheel | 44,605 bytes；27 文件，22 项追踪字节 + 5 项 dist-info | `941a1efb88b48cb8479ec9b5869c4db90984fd266e209933ef128b0792fa34e1` |

两包全部非生成成员与当前追踪文件逐字节相同、未追踪 payload 为 0，全部 8 个 P01 模块与冻结 schema 齐全。隔离默认 CPU 环境实际执行 13 项子命令：锁定导出、建 venv、带 hash 安装默认依赖、安装 wheel、依赖检查、8 模块导入和小型既有接口、P01 CLI help、契约 digest、5 类契约 CLI。所有模块来自安装前缀；MLX/Torch/模型包不可用。临时安装环境已清除，没有上传归档。

## 保留项与未运行项

原 R1 FAIL 及 8 个审查文件、P01-r1/P01-base-r2 交接、旧 P01_RESULTS、原配置和失败制品均保持原样。相对原 R1 的本轮变化仅限授权的两个实现模块、P01 测试、hardware 报告与新 P01-fix-r3 交接；各基线的完整文件清单见验证索引。159 个未修改的原 R1 候选文件已逐字节核对；公共依赖/契约/资源锁/配置和原报告生成器以外的旧硬件证据工具未改。

首选 BF16 DPO 失败、smoke06-r2 的原 raw PASS 与后续汇总降级、smoke06-r3 的 reference score 失败和 1536-r1 的 pressure 停止都保留，不改写为新代码通过。旧包选择失败及历次实现/审查中的失败记录仍在其原提交。

**NOT_RUN**：本轮 MLX/模型导入、GPU 重放或故障注入、权重下载、OS 限制调整；P04/P05 正式训练、accepted_sft reference、kris token/mask 人工核对、正式偏好生成、完整 P03 harness/256-token 协议、BFCL/最终测试、长时热/功耗稳定性和服务部署。历史受限容量结果仍不是正式训练或长时稳定性证明。默认 CPU 临时安装已删除，新的持久私有证据远低于本轮 2GiB 预算；未测临时安装峰值，不将其声称为峰值计量。

请 S0 以交接的精确完整候选安排独立 R1 复审；T1 至此结束修复轮，等待下一次授权。
