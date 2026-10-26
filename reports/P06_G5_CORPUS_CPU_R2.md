# P06 G5 新关系语料 CPU 候选 r2

2026-10-27，D1。构造并保留 28 道私有关系任务，实际形成 **4 个连通组**；36 条正向脚本成功、56 条反例失败，216 个 owned child 全部回收。16 条同 Action 预提交依赖调用的反例，在旧 v1 语义评分下均成功，在新版观察评分下均失败。这支持新包的 CPU 执行与观察约束实现；新语料仍待 R1 最终消费审查和 Q1 逐题语义复验，M0/M1、A1/A2 性能及 GPU 运行均为 `NOT_RUN`。

本批次在任何 G5 模型输出前，按 [r2 构造边界](../coordination/tasks/P06_G5_L1_REPLACEMENT_PLAN_R2.md)、[D1 范围](../coordination/tasks/P06_G5_CORPUS_CPU_R2.md)和[冻结协议](../coordination/tasks/P06_G5_PROTOCOL.md)构造。只检查这 28 个新 ID，没有额外候选池或按模型效果筛选。原 48 题另列于完整排除参考，全部永久隔离；Q1-G5-CORPUS-001/002 原首次失败及连续计数各 1 保持，正式关闭由 Q1 复验和 S1 接纳决定。

基线为 `5c859cbb59c808ba941ec89a85fcf8f22e19d888`，实现提交为 `3206fbc49ffe126ea653006306a1edc9c1700583`。公开实现限于 `data/evaluation/{tasks,checks,__main__}.py` 及原创 `test_relations.py`：两个明确 catalog/profile 分支，r2 必须消费完整历史参考，并通过 `select_oracle` 实际检查每个策略的 `after_observation`。旧 v1 构造和消费路径保留。工具、oracle、harness、模型后端、BFCL/analysis、contracts 和依赖均沿用基线。

该实现的 R1 代码预审已由 S1 接纳：复用 34 项作者测试，新增 3 项独立检查通过，6 个 child 回收，覆盖旧 v1 身份、新版恢复观察约束和桥接后整组隔离。D1 回读其 59 份预审产物并核对 18 份当前源码一致。预审状态为 `CODE_PRE_REVIEW_PASS_FINAL_CORPUS_PENDING`，不代替此次 28 题的最终消费和语义审查。S1 已将下表固定 hash 的最终包派发 R1/Q1；输入及 92 条原轨迹保持该版本。

依赖 `heldout-constraints.v1` 工具候选 `6f6a4974d254c8486417a1c4e51c15ba349a8012` 已由 R1 `8e2b6579a2e562a5f500674d9726d2dc978279d9` 独立 PASS，S1 在 `7b022bf` 接纳；当前工具源码字节相同。观察 oracle `ecbb520` 和完整排除参考 `f159b52` 已由 R1 `eba411b` 审核、S1 接纳。本报告不把依赖审核写成新语料的独立审核结果。

| 检查项 | 实际结果 |
|---|---|
| 四域覆盖 | 发布、事件、软件包、存储各 7 题 |
| 行为覆盖 | 单工具、多步、工具语义区分、无需工具、观察后澄清各 4；恢复 8 |
| 恢复故障 | 每域 transient、真实 owned block 超时各 1 题 |
| family / 连通组 | 4 / 4，每组 7 题，由完整连接图计算 |
| 构造与隔离 | 全部检查的新 ID 为 28；分组隔离 0、长度隔离 0；原 48 恢复数 0 |
| 合法策略 | 32 个策略、36 个策略与答案组合，全部实际执行并逐组合重评分成功 |
| 正向 / 反例 | 36 / 56，92 条全部符合预期 |
| 进程与动作 | 92 个 scripted model child、124 个真实工具 child；216 个全部启动、回收并清理；200 次 raw Action 解析合法 |
| 受影响代码测试 | `tests/data/evaluation` 34 passed，含 7 项新测试；定点 ruff 通过 |

四域分别使用累计摘除后的分区 quorum、裁剪后的区间并集与补集、传递前置节点和安装顺序、按唯一 shard 计算的故障域存活关系。单工具和恢复题从原始关系计算结论；无需工具题给全有限数据；多步题从首次实际观察计算第二次参数；澄清题从观察推导冲突证据，再请求选择取舍。旧任务中的查值、事件计数、显式测试用例门控、容量配额和已点名缺字段程序均纳入逐题比较。

答案字段、类型、排序和必要调用由题意明确。允许的三个拓扑顺序、两种集合参数顺序及四题澄清选项的两种顺序均进入合法策略或答案；36 条正向轨迹覆盖所有组合。作者另用前缀集合并、整数刻度集合、可达矩阵及副本域子集判断复算手写答案和 checker 观察，没有调用生产关系算法来生成标准答案。该作者复算不能代替 Q1 独立语义审核。

全部 8 条多步正向历史检查了首次真实观察出现在后续 ModelInput 中，并从该观察重新推导第二调用参数。8 条恢复正向均经历失败、观察、重试、final，在 3 决策/2 工具轮内完成；8 条澄清正向均先读取真实关系。16 条预提交反例覆盖每个多步及恢复合法策略：工具输出和最终答案匹配，但缺少观察之后的新决策，因此均因观察依赖失败。原创测试另保留独立调用的合法 batch。其余反例为最终关系值错误 24 条、调用策略或派生参数错误 16 条；没有用解析错误替代这些语义反例。正反轨迹合计实际观测 12 次 transient 和 12 次真实工具超时。

完整排除参考含 P02 全部 split 的 11,300 条 metadata、3,517 个历史组及 16,650 条工具 lineage，P03 10 题、G4 20 题和原 G5 48 题。实际审计保留 source、tool、schema、normalized-schema、family、template 键和全部 851 条历史边。新图为 3,623 节点、1,923 边、3,510 组件；3,595 个旧节点及其组件划分保持，原 P03/G4/G5 的 78 节点组件没有恢复成员。新四组均没有旧节点。

可读新旧题穷举 2,562 对 trigram，阈值保持 0.85，新旧最大 Jaccard 为 0.0314961。作者阅读全部 78 道可读旧题，记录 28 道新题的具体程序比较及六对新域机制比较，未识别需添加的新语义连接；该判断待 Q1 独立复验，不以 catalog 名称不同作为隔离证据。P02 只读取已绑定 metadata/lineage，没有读取保留测试题面或答案；P02 内容语义近重复检索为 `NOT_RUN`。

固定 Qwen3-1.7B tokenizer 使用 revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` 的既有文件。28 个初始输入最长 970 tokens；84 个正向历史输入最长 1,334，预留 256 后为 1,590 ≤ 2,048；正向 completion 含 EOS 最长 67 ≤ 256。没有截断输入或新装依赖。该测量覆盖全部已声明合法脚本历史；真实模型轨迹仍按协议处理溢出和失败。

当前 `evaluation/cuda_eval/protocol.py` 被直接导入并实际读取最终 L1 和原 A2 文件，reader SHA 为 `a637bdbc7c5cb7fbea0929fb80a4226b97744df5962d018da4a72b2136ac3d0f`。新清单冻结顺序、`42+i` seed、交替模型先后和 8 个 recovery ID，生成 56 个主比较单元及 8 个 A1 单元。A1 seeds 为 47、48、54、55、61、62、68、69。所有实际 ModelInput 都只有 messages/tools；host oracle 和预期答案没有进入投影。

A2 沿用 Q1 已接纳的原 4 组、12 个开发请求及原 hash，没有生成或重新测量回放材料；当前 reader 生成 8 个序列单元，对应 off/on 共 24 次请求。输入审核与计划生成不代表 cache 命中或性能已经测量。

| 绑定产物 | SHA-256 |
|---|---|
| 最终 L1 tasks | `a645b445d37a66522c39d83d110b6384abe8e0e93b15ad4ff8b208eb7eb2b54f` |
| 最终 package manifest | `a22e820e82f5e2addbf52e2c20d2b58c07cef4fd168da6860eb95bd3349bff04` |
| 完整排除 reference | `9e24be0903bd821fc63b38018eb22c988c176caa28b5185d4948fcf3e56e5f44` |
| 排除 reference manifest | `6ae740f9be378de15826b3af31dbd8ad6b27e64cd37b34f12afb14b73209fcc5` |
| 原 A2 inputs | `ec282f4779deca1815af39e2c68c846e831c184965318f3550eeaff973d03166` |

实际命令、退出码、源码字节、完整题目/答案/recipe、92 条轨迹、每条允许策略重评分、长度逐行值、分组全图和计划均由私有 evidence index 绑定。原包的 48 个任务经当前默认 v1 构造在内存中逐项重建，除由原审计提供的 group 赋值外内容与身份完全一致；没有重新执行原 99 条轨迹。原参考、原 G5 包及 E1 输入的 332 份受保护文件回读 hash/字节数均不变，原失败历史完整保留。本轮正式构造、CPU、长度和交付复核命令均为 exit 0。

复现的公开入口如下；审核者使用 evidence index 中的冻结私有路径和已有轻量 tokenizer 环境：

```text
python -m toolalign.data.evaluation build-relations --authoring <authoring> --reference-manifest <complete-reference-manifest> --semantic-review <author-review> --output <new-private-package>
python -m toolalign.data.evaluation validate-cpu --package <package> --output <new-private-runs>
python -m toolalign.data.evaluation finalize-lengths --package <package> --checks <runs> --tokenizer-root <fixed-tokenizer-root> --output <new-private-final-package>
```

R1 可从实现提交、34 项测试日志、`delivery-checks.json`、旧 v1 身份复核和当前 reader 计划进入技术审核。Q1 可从 `authored-task-inventory.json`、最终 package、`semantic-review-input.json`、完整历史 reference 与逐题正反轨迹复验 001/002。精确交付提交及索引位置见交接回报；独立审核通过前不进入模型评测。
