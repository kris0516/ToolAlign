# E1 → S1/R1/D1：G5 关系约束工具 CPU r2

从授权基线 `1233d0f917bedc5ce1aca31ff514e3ec4e54d18b` 交付 `heldout-constraints.v1`。源码、测试、[报告](../../reports/P06_G5_CONSTRAINT_TOOLS_CPU_R2.md)和本交接同一提交；精确 SHA 记录在原生完成回报及私有 evidence-index 中。

八个工具通过真实 owned child 执行并全部回收，新增 58 项及 2 项既有 reader 回归通过。D1 完整排除参考的 tool/schema/normalized-schema 实算交集为 0。旧 catalog 源码字节、完整/空集/单工具共 18 个变体身份及默认选择保持。

## D1 接口

导入 `toolalign.tools.constraints_catalog`，使用 `VERSION`、`DOMAIN_TOOLS`、`QUORUM_LAYOUTS`、`EVENT_TIMELINES`、`DEPENDENCY_GRAPHS`、`SHARD_PLACEMENTS`。公开固定表含每域两份完整有限关系。通过 `LocalToolRegistry(catalog_id=VERSION)` 取得完整声明/manifest，通过 `LocalToolRegistry(DOMAIN_TOOLS[domain], catalog_id=VERSION)` 取得任务域 subset。

| 域 | 完整读取 → 关系检查 | 必须保留的算法含义 |
|---|---|---|
| releases | `read_quorum_layout` → `check_quorum_removals` | 分阶段累计摘除、重复实例只扣一次、逐分区/逐阶段满足 quorum |
| incidents | `read_event_intervals` → `measure_interval_coverage` | 整数 `[start,end)`，先裁剪，重叠及相邻均合并，再取窗口内补集 |
| packages | `read_dependency_graph` → `check_installation_order` | prerequisite→dependent DAG，目标的传递前置闭包，序列恰好覆盖、无重复且满足先后关系 |
| storage | `read_shard_placement` → `check_shard_recovery` | 故障域整体失效，任一副本存活即保留该唯一 shard，唯一数达到 k 才恢复 |

每次读取足够支持关系推理后的 final；恢复题可使用失败→重试→final。两步题应由实际观察构造检查参数；本包四对实测记录展示了相应依赖。无需工具题需提供完整关系，观察后澄清题需由真实关系揭示约束冲突。参数界限、资源 ID、输出字段和区分实例见报告，不需增加工具或放宽限制来构造题目。

最终源码 SHA-256：`bfb4e6f8991bbfd4db9854ce85905e32a93f8b6adce3f1369480ef34ff8a953e`；完整 registry hash：`6f3623a97707e706afd49640c455f01e10fabcbc4de310dfa881ecd4a4b6ed05`。L1 输入使用 `catalog="heldout-constraints.v1"`、该完整 hash，以及逐任务实际 subset 声明/名称；reader 已按输入 catalog 选择二者。

## 审核与证据

私有入口：`.toolalign-local/p06-g5-constraint-tools-r2/evidence-index.json`。重点为 `candidate-design.json`、`reference-verification.json`、`reference-audit-before.json`、`reference-audit-final.json`、`legacy-baseline.json`、`delivery-verification.json`、`new-registry.json`、`commands/` 和 `pytest-components/*/execution-evidence.json`。

完整参考对应 D1 `2153c6823ed98db58782037acba7ca348e4010ed` / `f159b52d201efde370c572aed973651c68340120`，含 P02 全部元数据/tool lineage、P03、G4、原 48 题及原语义连接。先冻结自然声明与数据，再计算三类键，最后实现算法；交付前确认冻结值未变且仍无交集。三类键无交集不代表最终任务语义独立，四域未计作四个独立 group。

实现范围为新增 catalog、registry 固定映射、reader 的 catalog 选择、两份原创测试和两份说明。未编辑 runner、D1 data/evaluation、旧 oracle、依赖、contracts 或共享状态。未构造最终 28 题，未恢复原 48 题，未运行模型或 GPU。R1 技术审查及后续 Q1 语义审查由 S1 协调接纳。
