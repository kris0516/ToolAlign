# P05 G4 语料局部修订 r2

状态：READY_FOR_REVIEW。D1 针对 `Q1-G4-CORPUS-001` 修订原固定任务数组第 10、13 项，将最终版本字段和版本列表元素明确规定为 JSON 字符串，并同步各自的约束证据。四条定点 CPU 轨迹符合预期：两条原字符串答案 success，两条同值数字答案 failure。数字答案现在违反明确的提示要求；工具、oracle、封闭答案和生产提取逻辑均未改。

本轮起点为 S1 提交 `6adfd14167288ce2e3c2e542b2b7ac196251d11c`，工作分支 `codex/d1-p05-g4-corpus-r2`，沿用冻结 v1 契约及既有 builder。原独立 Q1 审阅 `fd0e8f34f3e7bf80d70914e5177d84cc8386a50e` 的 [REQUEST_CHANGES](https://github.com/kris0516/ToolAlign/blob/fd0e8f34f3e7bf80d70914e5177d84cc8386a50e/reports/reviews/P05_G4_CORPUS_Q1_R1.md) 保留：原分母 20，18 条通过，2 条共用该问题。新自验结果等待 Q1 定点复审，不替换原审阅结论或分母。

## 改动与身份传导

私有 authoring 输入仅四处值改变：两项 prompt，以及各自的 `constraints.evidence`。其余 18 条 authoring 记录完全不变；全部 20 条的答案、合法策略、正反脚本、faults、family 和 category 不变。原 r1 包、轨迹和 Q1 原反例原样保留，没有新增任务或策略。

提示参与来源 hash，因此两项 source hash/task ID 改变。builder 按 task ID 排序后，原第 10、13 项分别移至新数组第 5、11 项，共 9 项数组位置变化。group hash 依赖全组任务身份，所以全部 20 个任务对象的 group 引用都改变；其余 18 项只发生三处 group 字段变化，不能称为任务文件字节不变。

| 原序号 → 新序号 | 原任务对象 canonical SHA256 | 新任务对象 canonical SHA256 |
|---|---|---|
| 10 → 5 | `fee82cde634a18faa0cd47c747fca5095de8a0395b096705c9e7a8854fa0e72f` | `a9739fc435521cd1fc1e9ad1f2f0822d9c837244d1c035e1aa533e995ef05b14` |
| 13 → 11 | `fa18b64766c4f91cf678bb403cab8d2e41fa221fe1d45aaf4c48a550ea4b9a41` | `c268e67881a67b1ef16bb21b70397d0429da8ec800df382e14646d4033106b55` |

原 group hash 为 `945f419966e0c7fa5da62a5558b17a8a3662b4dbb60ad352f4ab7aaaadb1f417`，新 group hash 为 `ec8b545e826c4f5e85f78dd5ea7237d37f081f2203f50a6b9ec471d673fd9177`。私有 mapping 记录全部 20 项的新旧 ID、位置、source/task hash 和逐字段差异。

## 分组与定点验证

现有 builder 重新读取冻结 P02 分组元数据。新旧 P02 manifest/元数据绑定相同；新分组审计经 ID 映射后与原审计完全一致。仍为 20 个 train 任务、12 个 family、10 类、1 个六工具/schema 连通组，隔离 0；与 P03 的 200 条共享工具/schema 关系不变，P03 原 validation 身份不变。同组后续评测仍只能作为 seen-group 诊断。

本轮仅新运行四条 scripted CPU 轨迹，每项使用一条原字符串正向脚本和 Q1 原数字反例。反例与正向保持相同调用及数值，只改变版本答案的 JSON 类型。实际请求包含新提示，逐轮 ModelInput 与 trace 绑定通过；当前最终决策分别判 legal/illegal，所有自有进程已回收。检查命令使用已有 Python 环境执行本轮私有修订验证脚本，exit 0；完整 argv、时间、源码提交和日志见私有证据索引。

未重复执行原 52 条 CPU 轨迹或未受影响的全套测试。复用依据为其余 18 条完整 authoring 不变、20 条答案和策略不变、生产代码未修改及本轮身份/分组核对。原 Q1 第一次正式未通过记录继续保留，问题是否关闭由独立复审决定。

| 新输入或证据 | SHA256 |
|---|---|
| authoring 输入 | `8eaa02d4df3910cc04ab33ae9c757c04b788be377fefabcc9b5374ce5f56304b` |
| tasks.json 文件 | `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015` |
| task list canonical hash | `4c9e7edaef35352a294aa8d62130847264645059dd5ce529fb528f926c339bd8` |
| package manifest | `e7ab7b10728513662ddf3521e2c4b73b83eee7c7d50af31b469539a5f9d0427c` |
| 全量身份 mapping 与不变性检查 | `77e50a9078ca6208b04cb9b4ced101cfe9907ef0540481c34f8ec2b9d910e1d4` |
| 四条定点轨迹验证摘要 | `82d0f02ba6ec1df3029a21028c5d91c524190bba243232ed041003ffe638f54b` |

原任务原文、完整 authoring、逐字段 raw 差异和轨迹留在新的私有 r2 包，位置随本机交接提供。公开变更仅本报告和[交接单](../coordination/handoffs/P05-g4-corpus-r2.md)。本轮未运行真实模型、正式候选、偏好池、DPO、tokenizer 或 GPU，未修改依赖或共享状态；r2 的正式生成输入需由 S1 按新身份绑定。
