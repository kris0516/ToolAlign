# P06 G5 独立语料 CPU 候选 r1

2026-10-27，D1。交付 48 道私有 L1 题、51 条正向脚本、48 条反例和 12 个 A2 开发回放输入。实际分组为 **1 个连通组**；按冻结协议不计算 cluster bootstrap 区间或 leave-one-group-out。CPU 检查支持输入、执行和分组实现；语料仍待 R1 技术审核与 Q1 全题语义审核，正式模型评测为 `NOT_RUN`。

实现提交为 `72b18ad9c47da4932857cb53400b6a3c9ead6aad`，基线为 `beb26eeebefd6f2a42d678e661e6175d0708f003`。只新增 `data/evaluation/` 及其测试，沿用 Action、Example、OracleTask、SemanticOracle、投影、owned executor 和 P02 分组辅助函数。未改旧 preferences、工具、harness、模型后端、contracts 或依赖锁。E1 工具候选 `6027096baf382bb0e50bf3f7463dd11fca0e19d1` 已由 R1 `c6c81db24feda5986436facd66cc0757bb44e269` 独立 PASS，并经 S1 接纳；本包消费的工具源码字节未变。

| 项目 | 实际结果 |
|---|---|
| 四个工作域 | 发布、事件、软件包、存储各 12 题 |
| 六类行为 | 单工具、多步依赖、工具语义区分、无需工具、clarify/refuse、有限恢复各 8 题 |
| clarify/refuse | 4 题缺信息澄清、4 题只读能力拒绝 |
| family / 连通组 | 23 / 1；实体替换未增加独立 family |
| 隔离 | 分组重叠 0 题；长度超限 0 题；最终保留 48 题 |
| 正向 / 反例 | 51 / 48；全部符合预期结果 |
| 多解 / 多步 | 3 题各执行两种合法参数顺序；10 条多步正向历史验证下一请求含首次真实观察及对应标识 |
| 进程 | 99 个 scripted model child、100 个工具 child；199 个全部启动操作、回收并清理工作目录 |
| 原始动作 | 199 次动作解析合法；没有通过修复文本替换 raw Action |
| 原创代码测试 | 22 passed；定点 ruff、契约冻结和公开内容检查通过 |

分组实际纳入 P02 的 11,300 条 assignments、3,517 个历史组，以及 P03 的 10 个公开开发任务和 G4 r2 的完整 20 题。source、tool、schema、normalized-schema、family、规范化 template 键共同求传递闭包，旧组件桥接会隔离整个新组件。四域内的工具连接，加上跨四域共用的只读能力拒绝 family，形成一个真实组件；没有将四个工作域登记成四个独立统计组。

对可读的新旧题目穷举 2,568 对 trigram 比较，沿用 Jaccard ≥ 0.85 阈值；新题与可读旧题的最大值为 0.09375。作者另逐题记录工作目标、工具参数含义、允许策略和与旧 family 的差异，尚待 Q1 独立判断。P02 只读取冻结分组元数据，未读保留测试的题目或答案，也不声称完成新的 P02 全面语义近重复检索。P02 历史分组 manifest 为 `c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`；有效 v3 训练根 manifest 为 `f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437`，二者分别登记。G4 输入 SHA 为 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`，原文件保持不变。

每题明确 JSON 字段和类型、调用目标与调用次数；不调用工具的题目明确所需结构值。多解题保留全部约定顺序，未靠未写明的额外调用限制拒绝答案。反例按类别覆盖错误对象、版本、日期、区间端点、参数类型、工具语义混淆、多余读取、缺信息猜测和伪造执行成功。48 条反例中，39 条因执行策略不符失败、8 条因最终值或动作不符失败、1 条因参数不合法失败。恢复题为单一目标首次 transient 或真实 owned block 后重试，正向均在 3 决策、2 工具轮内结束；正反脚本合计实际观察到 8 次 transient 和 8 次工具超时，未更改冻结时限。

固定 Qwen3-1.7B tokenizer 读取已验证的本地 tokenizer 文件，未加载模型或新装依赖。长度预检覆盖 48 个初始输入与全部 104 个正向脚本历史输入：初始最长 924、历史最长 1,340 tokens，预留 256 后最大 1,596 ≤ 2,048；正向输出含 EOS 最长 62 tokens。没有截断 schema、历史或按模型结果筛选题目。该检查覆盖预写的正向历史；正式模型产生的溢出仍按协议计入失败分母。

A2 文件为 4 组、每组 3 个纯 ModelInput：同一公开开发请求重复两次，再给同工具前缀的另一合法开发请求。序列、租户与请求 ID、顺序已冻结，seed 对应 `42 + 3 * sequence_index + request_index`，存于独立说明。请求最长 1,299 tokens；四组重复请求的完整匹配前缀分别为 1,296 / 1,299 / 1,295 / 1,290 tokens，第三请求与前一请求共有前缀均为 1,239 tokens。这些是输入 token 比较，cache 命中、输出差异与速度测量仍为 `NOT_RUN`。

L1 顶层精确字段为 `schema_version/purpose/catalog/registry_hash/tasks/recovery_task_ids`，catalog 为 `heldout-devops.v1`，registry hash 绑定完整目录；每题只 advertise 所在域的两个工具。A2 顶层为 `schema_version/purpose/sequences`，每个 request 只有 `request_id/model_input`。S1 指定的 T1 reader 源码快照 SHA `1b6da81f4e6e6211b2a77c75ee7e50a60278563eb7791f22e45d43a454312976` 实际读取两份文件通过，生成 104 个 L1/A1 单元与 8 个 A2 序列单元（24 次请求）的固定计划；最终 T1 交付的组合验收由 S1 绑定。

| 私有产物 | SHA-256 |
|---|---|
| 最终 L1 tasks | `10a842b4a0c2d15470ba9d61e010621a8dc0807ce5a9e4c0cc552b994b67d70e` |
| 最终 package manifest | `5a4c0bc5cbaf0adbe4ddc708367fbfbbeda3f520c2b3b210cdcea9c1103b96c0` |
| A2 inputs | `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166` |

实际命令、退出码和完整输出存于私有 evidence index；以下为可移植调用形式，尖括号由审核者代入已冻结私有文件：

```text
python -m toolalign.data.evaluation build --authoring <authoring> --p02-manifest <grouping-manifest> --development <public-P03> --g4-tasks <G4-r2> --semantic-review <author-review> --output <new-private-package>
python -m toolalign.data.evaluation validate-cpu --package <package> --output <new-private-runs>
python -m toolalign.data.evaluation finalize-lengths --package <package> --checks <runs> --tokenizer-root <fixed-tokenizer-root> --output <new-private-final-package>
python -m toolalign.data.evaluation replay --development <public-P03> --pairs <frozen-pairs> --tokenizer-root <fixed-tokenizer-root> --output <new-private-replay>
```

上述四项实际退出码均为 0。初始 ruff 的 import 分组问题与私有 authoring helper 的 raw-answer/answer-record 混用 `KeyError` 均已定点修正；两份 exit 1 原日志保留。原始 recipe、任务、oracle、99 条完整轨迹、分组边、长度逐行结果、作者语义说明和 reader 快照全部留私有，公开文件不包含最终题面或答案。下一步是 R1/Q1 对精确候选独立审核，再由 S1 冻结正式 M0/M1 输入；本包不产生模型效果或 GPU 运行授权。
