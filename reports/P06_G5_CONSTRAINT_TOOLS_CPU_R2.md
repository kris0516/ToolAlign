# P06 G5 关系约束工具 CPU r2

E1 已实现 `heldout-constraints.v1` 的四域八工具及 L1 reader 接入。新增 58 项 CPU 检查和 2 项既有 reader 回归通过；八个新工具各在真实 owned child 中执行一次，全部回收。对 D1 完整排除参考实算 tool/schema/normalized-schema 三类键，交集均为 **0**。D1 可据此构造关系任务，任务语义和最终资格仍交 Q1 审核。

授权基线为 `1233d0f917bedc5ce1aca31ff514e3ec4e54d18b`，范围来自[工具任务](../coordination/tasks/P06_G5_CONSTRAINT_TOOLS_CPU_R2.md)和[已接纳机制](../coordination/tasks/P06_G5_L1_REPLACEMENT_PLAN_R2.md)。本包未构造最终 28 题，未运行模型或分配 GPU。旧 48 题继续整体隔离。

## 接口与固定资源

实现为 [constraints_catalog.py](../src/toolalign/tools/constraints_catalog.py)。`VERSION="heldout-constraints.v1"`，公开 `DOMAIN_TOOLS` 及四个资源表。所有操作只读代码内原创虚构关系，输入有界，不访问路径、网络或环境。读取工具返回所选资源的完整关系及其 ID；对应检查工具用该 ID 绑定同一关系。

| 域 | 读取工具与参数 | 检查工具与参数 | 固定选择项 → 观察返回 ID |
|---|---|---|---|
| releases | `read_quorum_layout(cluster)` | `check_quorum_removals(layout_id, removal_stages)` | `search-ring` → `search-layout-1`；`session-ring` → `session-layout-1` |
| incidents | `read_event_intervals(calendar)` | `measure_interval_coverage(timeline_id, window)` | `index-traffic` → `index-timeline-1`；`snapshot-traffic` → `snapshot-timeline-1` |
| packages | `read_dependency_graph(bundle)` | `check_installation_order(graph_id, targets, installation_order)` | `delivery-cli` → `delivery-graph-1`；`metrics-agent` → `metrics-graph-1` |
| storage | `read_shard_placement(stripe)` | `check_shard_recovery(placement_id, failed_domains)` | `archive-stripe` → `archive-placement-1`；`journal-stripe` → `journal-placement-1` |

全部参数必填，所有 object 关闭额外字段。读取选择项为表中两个枚举；关系 ID 为长度 1–64 的字符串，实例、节点及故障域 ID 为长度 1–32 的字符串。`removal_stages` 有 1–4 阶段，每阶段 0–8 个实例；`window` 为 `{start,end}`，均为 0–120 整数且执行时要求 `start < end`；`targets` 有 1–6 项，`installation_order` 有 0–12 项；`failed_domains` 有 0–8 项。完整可消费声明由 `LocalToolRegistry(catalog_id="heldout-constraints.v1").tools` 返回。

## 关系语义与可区分实例

发布读取返回 `partitions[{partition,instances,quorum}]`。所有实例初始服务，摘除按阶段累计，同一实例在阶段内或阶段间重复均只扣一次；每阶段逐分区判断 `remaining >= quorum`。检查返回每阶段新增/累计摘除、各分区保留数与判断，以及 `all_stages_safe`、从 1 开始的 `first_unsafe_stage`（无失败为 null）。`search-layout-1` 的阶段 `[[e1,e1],[e1,w1,w2],[e2],[]]` 得到保留数 `(2,4),(2,2),(1,2),(1,2)`，安全性为 true、true、false、false。仅摘除 `e1,e2` 时全局仍有 5 个实例，east 已不满足 quorum，不能合并分区计数。

事件读取返回 `time_unit="minute"` 及所有 `events[{event_id,start,end}]`。事件和窗口均为整数左闭右开区间。先裁剪到窗口，再合并重叠和相邻区间；返回有序、互不相交且不相邻的 `covered`、`uncovered`，及各自 `*_units`。`index-timeline-1` 在 `[10,28)` 的覆盖为 `[10,18),[25,28)`，补集 `[18,25)`，长度分别 11、7；窗口 `[18,25)` 的覆盖为空。两份固定关系均包含重叠、相邻和有间隔的事件。

软件包读取返回完整 `nodes`（含孤立节点）及 `dependencies[{prerequisite,dependent}]`。边方向为 prerequisite→dependent；必需集合是显式目标及全部传递前置节点，重复目标不增加要求。安装序列必须恰好覆盖该集合且无重复，额外节点不合法，并满足每条必需依赖的先后顺序。检查返回 `required_nodes`、`missing_nodes`、`extra_nodes`、`duplicate_nodes`、`order_violations` 和 `valid`；缺失/额外/重复列表按名称排序，顺序诊断使用各节点首次出现位置，重复本身已使结果无效。`client` 的闭包为 kernel、crypto、transport、parser、client，不包含孤立 diagnostics；crypto 与 parser 的合法互换顺序均接受。两份固定图均已通过 DAG 检查。

存储读取返回 `k`、完整 `domains` 及 `replicas[{shard_id,domain}]`。失效一个域会丢失该域全部副本；一个 shard 在任何未失效域仍有副本即存活，恢复条件是存活唯一 shard 数 `>= k`。重复故障域按一次处理。返回存活/丢失 shard、唯一存活数、存活副本数、`required_shards` 与 `recoverable`。`journal-placement-1` 丢失 rack-z 后仍有 3 个副本，但仅 2 个唯一 shard，小于 k=3，不能恢复；`archive-placement-1` 丢失 rack-a/rack-b 后有 3 个唯一 shard，恰好可恢复。

未知关系 ID、未知摘除实例、未知目标节点、未知故障域及非正长度窗口返回显式 `ToolFault`。安装序列中的未知节点列入 `extra_nodes` 并使 `valid=false`。这些行为均写入工具声明，未采用隐藏约定。

## D1 消费方式

四个域都可在一次成功读取后，直接用返回的完整有限关系完成计算并 final；无需再次查询某条记录，因此支持失败→重试→final 的三决策恢复结构。单工具题需让上述关系计算影响答案，不能只复制 ID 或某个现成字段。无需工具题可给出所选关系的完整数据，再要求同样的计算。

两步题可从真实读取中取得关系 ID，并根据观察到的分区余量、事件端点、依赖图或副本分布构造第二调用参数。组件实测分别使用观察中的实例/余量构造阶段、事件端点构造窗口、实际图构造合法安装顺序，以及实际副本位置选择故障域；四对调用及其观察、参数、manifest 和进程记录均留在私有证据。

观察后澄清题应由这些实际关系揭示约束冲突，并让取舍影响后续行为。本包提供关系和算法，不预先制定最终题面、答案策略或语义连接。四域不据此计为四个独立 group。

## 完整排除参考与身份

参考由 D1 实现 `2153c6823ed98db58782037acba7ca348e4010ed`、交接 `f159b52d201efde370c572aed973651c68340120` 冻结。首先核对三个入口文件的指定 SHA-256，再用 `verified_build_manifest` 核对其 22 个声明产物。参考包含 P02 全部 11,300 条元数据/3,517 原 group、P03 10 项、G4 20 项、原 G5 全部 48 项；图共 3,595 节点、1,753 边、3,506 组件。原语义桥接和整组隔离保留。

| 参考文件 | SHA-256 |
|---|---|
| evidence-index.json | `16445958531c53f5f4748b5550bf18a35a88d245e543dbfd89ef5859d8a2b356` |
| reference.json | `9e24be0903bd821fc63b38018eb22c988c176caa28b5185d4948fcf3e56e5f44` |
| reference-manifest.json | `6ae740f9be378de15826b3af31dbd8ad6b27e64cd37b34f12afb14b73209fcc5` |

八个自然声明、参数机制说明和固定数据在算法实现/registry 接入前保存为 `candidate-design.json`，SHA-256 为 `655c671f61602cf0acc584d950329edd52cc99a27dcf1c541e1c320e9f8ec26d`。审计复用已有 `schema_shape`、`normalized_schema_semantics` 和 `canonical_hash`，逐工具生成三类键，同时对照完整参考图的键，以及 P02 全部 16,650 行 tool lineage、P03/G4/原 G5 声明和两个旧 catalog。实现前、交付前的交集均为 0；最终声明和固定资源与首次冻结值完全一致，没有因命中而改名、增添字段或修改隔离规则。

| catalog | 源码 SHA-256 | 完整 registry hash |
|---|---|---|
| local-devops.v1 | `8c89c7f2b4a4bc64952791b66954542cf328f814b07a9ba1c3f3e70b5e236792` | `6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8` |
| heldout-devops.v1 | `a13735a3cfd1ec5d3f638504d01d500438248d8efe545c97be085999b2046996` | `66d47196bd207542325c89244a7fbafd2163f14c01e9aeb36e40553e01c7f037` |
| heldout-constraints.v1 | `bfb4e6f8991bbfd4db9854ce85905e32a93f8b6adce3f1369480ef34ff8a953e` | `6f3623a97707e706afd49640c455f01e10fabcbc4de310dfa881ecd4a4b6ed05` |

旧两个模块逐字节相同；其完整、空集和所有单工具 subset 共 18 个变体的 tools、manifest、registry hash 均与修改前一致，默认仍为 local-devops。`registry.py` 仅新增第三个固定映射；L1 reader 明确允许两个 heldout catalog，并用输入 catalog 构建完整 registry 和任务 subset。旧 heldout 输入仍经真实工具/脚本后端链路通过。executor、runner、D1 数据模块、oracle、模型、contracts、依赖和共享状态均未改动。

## 验证与证据

- 新工具检查 53 项、新 reader 检查 5 项通过。完整 58 项首次通过；随后补全 reader 原创 fixture 的 oracle strategy，仅重跑受影响的 5 项并通过。其他源码/测试身份未变。
- 边界验证含累计/重复/分区 quorum、裁剪及端点、闭包/额外/重复/错误顺序、共享故障域与副本去重；另以整数 tick 集验证两份关系的 2,550 个窗口，并检查两图各 120 个排列。这些循环属于上述测试，未当作额外 pytest 项目计数。
- 四对真实调用覆盖全部八工具，8 个 owned child 的实际新 catalog manifest、启动、exit code 0、回收和目录清理均核对。既有 reader 集成及 action-only 输入隔离共 2 项通过。取消、ValidatedCall 和模型数值的未改证据复用，未重复运行相应矩阵。
- 全库 ruff、冻结契约检查通过。实际 sdist、直接 wheel 与从 sdist 重建 wheel 排除 241 个私有 canary，18 个公开 fixture 和冻结 schema 保持；使用既有缓存构建环境，离线、禁用构建隔离及 Python 下载，无新依赖安装。
- 公开内容检查和 `git diff --check` 随最终交付核对；本包只交付源码、原创组件测试及公开说明。未宣称全库 pytest 或独立 R1/Q1 已通过。

私有证据位于 `.toolalign-local/p06-g5-constraint-tools-r2/evidence-index.json`，绑定入口参考、首次设计、两次交集审计、旧身份快照、逐命令输出、新 registry、四对真实执行及最终提交。技术验收由 R1 独立完成；后续正式候选的语义与组件隔离由 Q1 审核。模型评测、性能测量及 GPU 分配保持 NOT_RUN/0。
