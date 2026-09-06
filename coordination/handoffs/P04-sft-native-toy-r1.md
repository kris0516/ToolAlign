# P04-SFT-NATIVE-TOY r1 — T1 → S0

状态：`READY_FOR_REVIEW`，所有结果为 T1 自测及原始证据交付，尚无本轮独立 R1 整包验收。

T1；`gpt-6-astra / max`；独立原生 Codex 任务与原隔离 worktree，未创建其他任务或 sub-agent。任务/主机真实标识、完整工作路径及最终交付 commit/parents/tree 存本机私有交接记录，并通过原生交接告知 S0。

- code base：`50867c0be43d110df6c3620c94022fcfdaf779b5`。
- 完整授权：`de86568d73ee77bbf92b6f749a39a9ab38955836`；版本 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0021`。
- 新分支：`work/p04-sft-native-toy`；旧 CPU 分支不推进、不推送。
- 数值源 epoch：`534445bb8eecd600b65e90e541cd30601b4fd07c`；最终生产代码与全部 CPU 组：`fae3d608b6edc3f5dc941dfb3395757ee3db2ef3`；安装验证与第三次数值：`c06782a61857259097932078c661189b4fda781d`（后者只修报告 probe）。
- 本文件所在最终交付提交仅继续加入报告、统计与交接材料；不将历史测量标成最终文档提交上的重跑。最终完整 SHA、parents/tree 以原生交接及私有 delivery 记录为准。

[交付报告](../../reports/experiments/P04_SFT_NATIVE_TOY_REPORT.md) 与 [统计/原回执索引](../../reports/experiments/P04_SFT_NATIVE_TOY_VALIDATION.json) 包含数值、归档、失败记录与限制。配置 hash `fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb`，固定原 cases hash `df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47`，均未变更。

实际结果：

- 3/5 次 framework 启动：source segmented PASS；source unsegmented EXPECTED_NEGATIVE；installed segmented PASS。主子进程均真实回收、原 PID 不存在、实际租约释放；框架前实际租约、GPU default/stream、Torch CPU/2+2 线程、原生 compile 和 setter 恢复证据齐。
- 13 个原 ID、12 种数值载荷、44 个验证监督 token、64 个 float32 参数。完整逐例 CE/梯度、padding/EOS/shift、忽略 logits 不变、默认 padding 反例均实测。未优化真实 P02 数据。
- 8+5 分段真实完成两次 SGD 更新，每个 checkpoint 对 Torch 参数的最大误差均 `1.862645149230957e-9`。分段后评估、尾部重新评估、实际保存重载及错误 checkpoint 拒绝通过。两 source/installed score 记录完全一致，实际选择 step 2。
- 单段 13/accumulation 8 只更新一次，丢失尾 5 微步；与完整两更新参数差 `0.013687163591384888`。
- 完整 CPU 为 931+60+2+13+44 = **1050 passed / 2 HF-only skipped**，等于原 1014 加新 36；110 subtests 与重复运行另记。Ruff、4 契约冻结、公开扫描及 diff 检查记录保留。
- 新 sdist 122 成员；默认/显式 sdist 重建 wheel 各 63 成员，metadata、entry points、license、完整 RECORD 和 Git 字节通过。15 条默认安装 CPU 命令、9 个 SFT 模块来源及第 3 次实际安装版 GPU replay 通过，无源路径回退。普通源码直接 wheel 为 `NOT_RUN`。

允许文件内的实现为新 native 入口、两份既有 SFT 适配/validation 的有限共用改动、新守卫测试、逐字节 S0 配置副本、报告及本交接。S0 协调文件、其他配置、data/model_io/P01/P03、依赖锁、CI、原测试/报告/审查均未修改。原 CPU 默认入口和配置保留。

原日志保留：首次父进程 symlink 统计拒绝（无 framework launch）；首轮 CPU 装配 881 passed/2 failed/48 skipped；原磁盘超限后丢失 supervision 的 S0 反例及后续真实 CPU 故障回归；首轮安装 probe 漏导入 `__main__` 的来源计数失败。修复后全部在新输出验证，两个成功 source 数值未重跑。

两次 segmented stderr 各有一个 `resource_tracker` semaphore 关闭清理 warning。完整日志及最初诊断误分类保留；修正的只读探针针对两个原确切名称均得到 `ENOENT`，无创建/unlink，不称为全局泄漏审计。

私有测量索引绑定 27 份原命令回执、7 组源码快照/409 个 blob、所有完整数组与实际 checkpoint。旧 P01/P04 refs、1559 份旧私有制品与 base 其余 399 份文件全部不变，原 R1 CPU review `800480b0b1e14c21937f1b5073daf543a2ba31fc` 及两次 CPU 失败保留。原测量文件清单 hash `b0f641aeaa9fa6c6c394d588ab6457259f0cf878da00377181a3ef785e0907c4`，最终交付清单另在私有交接登记。

正式训练仍 `training_authorized=false`；无 pretrained 加载、真实 baseline/SFT/DPO、全量重新编码、人工判定代填、外部 tracker/服务、费用或模型/数据上传。等待 S0 分发独立 R1 及最终集成。本轮交付后结束，未用额度不转授；R1/S0 的新框架运行需要后续独立明确范围。
