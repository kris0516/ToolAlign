# P02 v3 定点排除：R1 技术审查

**PASS；P0=0、P1=0、P2=0。** 精确候选 `5825d789ee89afedbfff31e828223608c6f435e2`；原实现与实际新编码提交 `6054b349c344cbbad30c12ce8fe8820c59e8bc10`。本轮没有修改被审实现，也没有产生新的正式失败事件。

审查身份为独立 `Codex-AI(R1)`，`gpt-6-astra / max`；授权 `7a731c5f08a561f5941fcba5996004706f373392`，基线 `d3e56f68ebd67cc576d912b6f06636682b4170ab`。契约为 plan-v0.1、coordination.v1、toolalign.contracts.v1、Action JSON v1 与 ADR-0025。冻结的 19 份授权、347 项输入及全部 11 个新增候选文件已审阅；553 个基线文件保持，最终候选相对 6054b34 仅增加三份交接/报告文件。

## 实际验证

| 范围 | R1 结果 |
|---|---|
| 现有纯 CPU 环境 | 839 passed、48 optional skipped；未重跑无关的 427 项历史报告检查 |
| 全量 v3 输出 | 一次独立安装版构建；29 个稳定文件与 D1 两份原产物完全一致 |
| 原行与选择 | 15,577 次原 JSONL 行比较、7,928 份三代 rank sidecar 核对通过 |
| 固定材料 | 一次完整静态核验，13 个唯一身份、双引擎 26 份完整记录一致；37,888 行 HTML token 表通过 |
| 独立反例 | 21 次预期拒绝、6 个原创小 fixture 正常对照通过 |
| 现存归档/安装 | sdist 140 项、两份 wheel 各 69 项；64 份包文件、RECORD/metadata 和一次隔离 target 安装通过 |
| 安装入口 | help、build、verify 通过；配置字节改动与覆盖已有目录被拒绝；未从源码目录导入 |
| 原始命令与源码 | 44 条原命令、18 个源码时点的 9,999 份源码快照及 18 份索引核验通过；6 条原安装命令均符合预期退出码 |
| 保全与约束 | 49,844 条路径、1,086 个链接核对；旧根身份、旧 scope/测试目录及原 Git/快照保持；ruff 与契约冻结通过 |

完整数据 manifest 为 `f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437`，quality revision 为 `919ee616fd11993f39bbab6d38146ea827f4bbc3d7bafc07aae0e2c7dd95e5c8`。完整材料 records 为 `a41f5c24a55eb5e4fed434b9352b655fbf78e5aa68276de5de183671c81412de`。

## 数据处置与材料绑定

P02-Q-081 的两条决策均从有效集合和原 formal 选择中排除，包含错误历史之前的目标；两项局部 Action PASS、prefix 子结论和原始行均保留。旧 83 来源处置没有被改写，3 个来源的 3 项原字节恢复保持，staging 保持引用、未晋升。新排除来源同 group 的其余 5,532 项原有效决策保持；全部受影响 group 中其余 5,181 个来源、5,551 项决策仍保留。这两组统计的范围不同。

有效 train/validation 为 **7,419/230**，formal 为 **5,938/213**，smoke 为 **1,583/194**。选择没有补选或重排；`parent_selection_rank` 仍指向 v1，`previous_selection_rank` 指向 v2，本轮 rank 连续。formal train 有 5,929 份连续 rank 随删除而改变，其他三组为 0。正式 train 相对 6,000 的不足 62 项仍按原规划偏差登记。

11 个旧例按 Example 身份复用，完整 sequence、padding、token_texts 与原记录逐类型一致；编号变化有显式旧 case 映射。旧编码实际时间分别为 11:10:09、11:11:25 UTC，新发布没有将它们写成本轮重新编码。两新例每引擎各编码一次，实际原命令均在干净 6054b34 上运行，并晚于精确 S0 放行；预留记录、四次开始/完成事件、输出 run 和 18 份消费源码绑定一致。仅来源审查的第三个目标没有增加编码。

独立小反例覆盖：局部自洽但遗漏首/末决策的整来源包、重新计算局部 hash 后的 rank 互换、相等数值的 float/bool 替换、从 v2 补回不存在成员、错 Example 复用、旧 revision 与 parent run/source/time 冒用、validation/test/ood 新材料，以及第二份文件写入失败。最后一项保留首份部分文件且不暴露成功 manifest。小 fixture 来自仓库原创例，未读取真实最终集；parent 材料测试只替代固定选择输入，实际记录/manifest/run/消费源码验证仍执行。

## 失败与限制

D1 两次早期 fixture/assertion 失败、4 次只读查询失败及旧轮负结果全部保留。R1 三条检查脚本失败也保留：原因表总数与已审子集混淆；把旧 revision 校验放在会重绑元数据的底层复用函数；预期了晚于实际严格类型拒绝的错误码。分别修正 R1 断言和验证层级后通过，没有更改候选或放宽已固定输入。两次只读元数据结构显示错误另外登记。审查 helper 最后仅由 ruff 调整 import 顺序，原执行源码快照保留。

本轮额度实际为：全量输出 1 次、完整 13 例静态核验 1 次、临时 target 安装 1 次。真实分词、新归档、新依赖/持久环境/下载、模型/框架/GPU、API、浏览器重试与训练均为 0。新制品和新 pytest 目录纳入最终私有封存，限额 1 GiB；原 2,569 份新测试文件和 149 个链接不清理或复用。

本结论仅验收上述 CPU 技术范围。材料中的语义与 token/mask 判定列保持空白，实际处置与内容由独立 Q1 另行裁定；R1 没有代填人工身份或修改 S0 台账。浏览器实显仍 NOT_RUN，真实 trainer 消费仍 NOT_RUN_PENDING_SEPARATE_ADAPTATION，G-DATA 与正式 P04 未由本审查放行。

[结构化证据](EVIDENCE.json)绑定每条已执行检查的 UTC、退出码、stdout/stderr hash、源码时点以及本机完整参数/输入清单。公开复核 helper 为 [数据](check_data.py)、[材料](check_materials.py)、[归档](check_archives.py)、[独立反例](check_boundaries.py)；授权输入、真实 argv、失败原文、发布后检查和最终 seal 仅保留于本机交接范围。最终 review commit 由普通推送后的原生交接绑定。
